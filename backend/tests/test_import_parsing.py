"""Bank export interpretation without a database."""

from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.errors import ApiError
from app.import_parsing import (
    ColumnMapping,
    guess_date_format,
    guess_decimal_separator,
    header_signature,
    interpret_row,
    parse_amount,
    read_table,
    signature_confidence,
    suggest_mapping,
)

MINUS = chr(0x2212)
NBSP = chr(0xA0)


@pytest.mark.parametrize(
    ("value", "separator", "expected"),
    [
        ("-1 234,50", ",", Decimal("-1234.50")),
        (f"1{NBSP}234,50 kr", ",", Decimal("1234.50")),
        (f"{MINUS}99,90", ",", Decimal("-99.90")),
        ("(12,00)", ",", Decimal("-12.00")),
        ("45,00-", ",", Decimal("-45.00")),
        ("1,234.56", ".", Decimal("1234.56")),
        ("-0.10", ".", Decimal("-0.10")),
        (12, ",", Decimal("12")),
        (12.3, ",", Decimal("12.3000")),
        ("", ",", None),
        ("abc", ",", None),
        ("12,3,4", ",", None),
    ],
)
def test_parse_amount_is_decimal_safe(value, separator, expected) -> None:
    assert parse_amount(value, separator) == expected


def test_semicolon_csv_in_windows_encoding_is_read() -> None:
    content = (
        "Bokföringsdag;Transaktionsdag;Text;Belopp;Saldo\n"
        "2026-08-21;2026-08-20;ICA Kvantum;-425,35;10 000,00\n"
        "2026-08-25;2026-08-25;Lön;32 000,00;42 000,00\n"
    ).encode("cp1252")
    table = read_table("export.csv", content)

    assert table.delimiter == ";"
    assert table.headers == ["Bokföringsdag", "Transaktionsdag", "Text", "Belopp", "Saldo"]
    assert table.rows[0]["Text"] == "ICA Kvantum"
    mapping = suggest_mapping(table.headers)
    assert mapping["amount_column"] == "Belopp"
    assert mapping["description_column"] == "Text"
    assert mapping["date_column"] in {"Transaktionsdag", "Bokföringsdag"}


def test_xlsx_with_a_title_row_above_the_header() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Kontoutdrag för Vardagskonto"])
    sheet.append(["Datum", "Beskrivning", "Uttag", "Insättning"])
    sheet.append([datetime(2026, 8, 20), "Hyra", 9500, None])
    sheet.append([datetime(2026, 8, 25), "Lön", None, 32000.5])
    buffer = io.BytesIO()
    workbook.save(buffer)

    table = read_table("export.xlsx", buffer.getvalue(), header_row=2)
    mapping = suggest_mapping(table.headers)
    assert mapping["debit_column"] == "Uttag"
    assert mapping["credit_column"] == "Insättning"
    assert mapping["amount_column"] is None

    column_mapping = ColumnMapping(
        date_column="Datum",
        description_column="Beskrivning",
        debit_column="Uttag",
        credit_column="Insättning",
    )
    rent = interpret_row(table.rows[0], column_mapping)
    salary = interpret_row(table.rows[1], column_mapping)
    assert rent.amount == Decimal("-9500.0000")
    assert rent.transaction_date == date(2026, 8, 20)
    assert salary.amount == Decimal("32000.5000")
    assert not rent.errors and not salary.errors


def test_invalid_values_are_reported_per_row() -> None:
    row = {"Datum": "31/02/2026", "Text": "  ", "Belopp": "0,00", "Valuta": "kronor"}
    result = interpret_row(
        row,
        ColumnMapping(
            date_column="Datum",
            description_column="Text",
            amount_column="Belopp",
            currency_column="Valuta",
            date_format="%d/%m/%Y",
        ),
    )
    assert set(result.errors) == {
        "date_invalid",
        "description_missing",
        "amount_zero",
        "currency_invalid",
    }


def test_inverted_sign_for_credit_card_exports() -> None:
    result = interpret_row(
        {"Datum": "2026-08-20", "Text": "Bokhandel", "Belopp": "249,00"},
        ColumnMapping(
            date_column="Datum",
            description_column="Text",
            amount_column="Belopp",
            amount_sign="inverted",
        ),
    )
    assert result.amount == Decimal("-249.0000")


def test_format_guesses() -> None:
    assert guess_date_format(["20260820", "20260821"]) == "%Y%m%d"
    assert guess_date_format(["20.08.2026"]) == "%d.%m.%Y"
    assert guess_decimal_separator(["-1 234,50", "99,00"]) == ","
    assert guess_decimal_separator(["-1,234.50", "99.00"]) == "."


def test_profile_suggestion_confidence_uses_header_overlap() -> None:
    saved = header_signature(["Datum", "Text", "Belopp", "Saldo"])
    same = header_signature(["datum", "TEXT", "Belopp", "Saldo"])
    partial = header_signature(["Datum", "Text", "Belopp", "Valuta"])
    assert signature_confidence(saved, same) == 100
    assert signature_confidence(saved, partial) == 60


def test_unsupported_and_empty_files_are_rejected() -> None:
    with pytest.raises(ApiError) as unsupported:
        read_table("statement.pdf", b"%PDF")
    assert unsupported.value.code == "import_file_type_unsupported"
    with pytest.raises(ApiError) as empty:
        read_table("statement.csv", b"Datum;Text;Belopp\n")
    assert empty.value.code == "import_no_rows"
