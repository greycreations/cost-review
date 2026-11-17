"""Read bank exports (CSV or XLSX) and interpret their values.

This module has no database access. It turns an uploaded file into header
names and raw rows, suggests a column mapping for common Swedish bank exports
and interprets dates and amounts with decimal-safe arithmetic.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.errors import ApiError

MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_IMPORT_ROWS = 20_000
CSV_DELIMITERS = (";", ",", "\t", "|")
TEXT_ENCODINGS = ("utf-8-sig", "cp1252")

# Header names used by Swedish banks and common English exports.
DATE_HEADERS = (
    "transaktionsdatum",
    "datum",
    "bokforingsdatum",
    "bokforingsdag",
    "reskontradatum",
    "date",
    "transaction date",
    "booking date",
)
POSTING_DATE_HEADERS = ("valutadag", "valutadatum", "bokforingsdag", "posting date", "value date")
AMOUNT_HEADERS = ("belopp", "belopp sek", "summa", "amount", "transaktionsbelopp")
DEBIT_HEADERS = ("uttag", "debet", "debit", "withdrawal")
CREDIT_HEADERS = ("insattning", "kredit", "credit", "deposit")
DESCRIPTION_HEADERS = (
    "text",
    "beskrivning",
    "rubrik",
    "specifikation",
    "transaktion",
    "meddelande",
    "mottagare",
    "description",
    "details",
    "payee",
)
CURRENCY_HEADERS = ("valuta", "currency")
REFERENCE_HEADERS = ("referens", "verifikationsnummer", "reference", "id")
DATE_FORMATS = ("%Y-%m-%d", "%Y%m%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d")
UNICODE_MINUS = chr(0x2212)
NO_BREAK_SPACE = chr(0xA0)


@dataclass(frozen=True, slots=True)
class ParsedTable:
    headers: list[str]
    rows: list[dict[str, Any]]
    delimiter: str | None


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    date_column: str
    description_column: str
    amount_column: str | None = None
    debit_column: str | None = None
    credit_column: str | None = None
    posting_date_column: str | None = None
    currency_column: str | None = None
    reference_column: str | None = None
    date_format: str = "%Y-%m-%d"
    decimal_separator: str = ","
    amount_sign: str = "as_is"


@dataclass(frozen=True, slots=True)
class InterpretedRow:
    transaction_date: date | None
    posting_date: date | None
    description: str | None
    amount: Decimal | None
    currency: str | None
    reference: str | None
    errors: list[str]


def normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().casefold()


def header_signature(headers: list[str]) -> str:
    return "|".join(sorted({normalize_header(header) for header in headers if header}))


def signature_confidence(first: str, second: str) -> int:
    left = set(filter(None, first.split("|")))
    right = set(filter(None, second.split("|")))
    if not left or not right:
        return 0
    return round(100 * len(left & right) / len(left | right))


def read_table(
    filename: str,
    content: bytes,
    *,
    delimiter: str | None = None,
    header_row: int = 1,
) -> ParsedTable:
    if len(content) > MAX_IMPORT_BYTES:
        raise ApiError(413, "import_file_too_large", "The import file exceeds 10 MB.")
    if not content:
        raise ApiError(422, "import_file_empty", "The import file is empty.")
    suffix = filename.rsplit(".", 1)[-1].casefold() if "." in filename else ""
    if suffix == "xlsx":
        matrix = _read_xlsx(content)
        used_delimiter = None
    elif suffix in ("csv", "txt", "tsv"):
        text = _decode(content)
        used_delimiter = delimiter or _sniff_delimiter(text)
        matrix = [list(row) for row in csv.reader(io.StringIO(text), delimiter=used_delimiter)]
    else:
        raise ApiError(
            422,
            "import_file_type_unsupported",
            "Choose a CSV or XLSX export from your bank.",
        )
    return _table_from_matrix(matrix, header_row, used_delimiter)


def suggest_mapping(headers: list[str]) -> dict[str, str | None]:
    normalized = {normalize_header(header): header for header in headers}

    def find(candidates: tuple[str, ...], exclude: set[str] | None = None) -> str | None:
        for candidate in candidates:
            header = normalized.get(candidate)
            if header is not None and header not in (exclude or set()):
                return header
        for candidate in candidates:
            for key, header in normalized.items():
                if candidate in key and header not in (exclude or set()):
                    return header
        return None

    date_column = find(DATE_HEADERS)
    used = {date_column} if date_column else set()
    amount_column = find(AMOUNT_HEADERS, used)
    debit_column = None if amount_column else find(DEBIT_HEADERS, used)
    credit_column = None if amount_column else find(CREDIT_HEADERS, used)
    used |= {value for value in (amount_column, debit_column, credit_column) if value}
    description_column = find(DESCRIPTION_HEADERS, used)
    used |= {description_column} if description_column else set()
    return {
        "date_column": date_column,
        "description_column": description_column,
        "amount_column": amount_column,
        "debit_column": debit_column,
        "credit_column": credit_column,
        "posting_date_column": find(POSTING_DATE_HEADERS, used),
        "currency_column": find(CURRENCY_HEADERS, used),
        "reference_column": find(REFERENCE_HEADERS, used),
    }


def guess_date_format(values: list[Any]) -> str:
    samples = [value for value in values if value not in (None, "")][:50]
    if samples and all(isinstance(value, (date, datetime)) for value in samples):
        return "%Y-%m-%d"
    for candidate in DATE_FORMATS:
        if samples and all(_parse_date_text(str(value), candidate) for value in samples):
            return candidate
    return "%Y-%m-%d"


def guess_decimal_separator(values: list[Any]) -> str:
    text_values = [str(value) for value in values if isinstance(value, str) and value.strip()]
    comma = sum(1 for value in text_values if re.search(r",\d{1,2}\s*$", value))
    dot = sum(1 for value in text_values if re.search(r"\.\d{1,2}\s*$", value))
    return "." if dot > comma else ","


def interpret_row(raw: dict[str, Any], mapping: ColumnMapping) -> InterpretedRow:
    errors: list[str] = []
    transaction_date = parse_date(raw.get(mapping.date_column), mapping.date_format)
    if transaction_date is None:
        errors.append("date_invalid")
    posting_date = (
        parse_date(raw.get(mapping.posting_date_column), mapping.date_format)
        if mapping.posting_date_column
        else None
    )

    description = _clean_text(raw.get(mapping.description_column), 240)
    if not description:
        errors.append("description_missing")

    amount = _row_amount(raw, mapping)
    if amount is None:
        errors.append("amount_invalid")
    elif amount == 0:
        errors.append("amount_zero")

    currency = None
    if mapping.currency_column:
        currency = _clean_text(raw.get(mapping.currency_column), 16)
        currency = currency.upper() if currency else None
        if currency is not None and not re.fullmatch(r"[A-Z]{3}", currency):
            errors.append("currency_invalid")
            currency = None

    reference = (
        _clean_text(raw.get(mapping.reference_column), 240) if mapping.reference_column else None
    )
    return InterpretedRow(
        transaction_date=transaction_date,
        posting_date=posting_date,
        description=description or None,
        amount=amount,
        currency=currency,
        reference=reference,
        errors=errors,
    )


def parse_date(value: Any, date_format: str) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return _parse_date_text(str(value).strip(), date_format)


def parse_amount(value: Any, decimal_separator: str) -> Decimal | None:
    """Interpret one amount cell without binary floating point arithmetic.

    Spreadsheet cells may already be numbers. Text accepts spaces or
    apostrophes as thousand separators, a leading minus sign (including the
    Unicode minus), a trailing minus sign, parentheses for negatives and a
    trailing currency label such as ``kr`` or ``SEK``.
    """

    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value)).quantize(Decimal("0.0001"))
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(UNICODE_MINUS, "-").replace(NO_BREAK_SPACE, " ")
    text = re.sub(r"\s*(kr|sek|eur|usd|nok|dkk)\.?$", "", text, flags=re.IGNORECASE)
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1]
    if text.endswith("-"):
        negative, text = True, text[:-1]
    text = text.replace(" ", "").replace("'", "")
    if decimal_separator == ",":
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", text):
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return -amount if negative else amount


def _row_amount(raw: dict[str, Any], mapping: ColumnMapping) -> Decimal | None:
    if mapping.amount_column:
        amount = parse_amount(raw.get(mapping.amount_column), mapping.decimal_separator)
    else:
        debit = (
            parse_amount(raw.get(mapping.debit_column), mapping.decimal_separator)
            if mapping.debit_column
            else None
        )
        credit = (
            parse_amount(raw.get(mapping.credit_column), mapping.decimal_separator)
            if mapping.credit_column
            else None
        )
        if debit is None and credit is None:
            return None
        amount = (credit or Decimal("0")).copy_abs() - (debit or Decimal("0")).copy_abs()
    if amount is None:
        return None
    if mapping.amount_sign == "inverted":
        amount = -amount
    if amount.copy_abs() >= Decimal("1e16"):
        return None
    return amount.quantize(Decimal("0.0001"))


def _parse_date_text(text: str, date_format: str) -> date | None:
    try:
        candidate = text[:10] if date_format == "%Y-%m-%d" else text
        return datetime.strptime(candidate, date_format).date()
    except ValueError:
        return None


def _clean_text(value: Any, limit: int) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()[:limit]


def _decode(content: bytes) -> str:
    for encoding in TEXT_ENCODINGS:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ApiError(422, "import_encoding_unsupported", "The file encoding could not be read.")


def _sniff_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:20])
    counts = {candidate: sample.count(candidate) for candidate in CSV_DELIMITERS}
    best = max(counts, key=lambda candidate: counts[candidate])
    return best if counts[best] else ","


def _read_xlsx(content: bytes) -> list[list[Any]]:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as error:  # openpyxl raises several unrelated types for bad files
        raise ApiError(
            422, "import_file_unreadable", "The XLSX file could not be read."
        ) from error
    try:
        sheet = workbook.worksheets[0]
        matrix: list[list[Any]] = []
        for row in sheet.iter_rows(values_only=True):
            matrix.append(list(row))
            if len(matrix) > MAX_IMPORT_ROWS + 50:
                break
        return matrix
    finally:
        workbook.close()


def _table_from_matrix(
    matrix: list[list[Any]], header_row: int, delimiter: str | None
) -> ParsedTable:
    if header_row < 1 or header_row > len(matrix):
        raise ApiError(422, "import_header_row_missing", "The header row is not in the file.")
    raw_headers = matrix[header_row - 1]
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index, value in enumerate(raw_headers):
        name = _clean_text(value, 120) or f"Column {index + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        headers.append(name)

    rows: list[dict[str, Any]] = []
    for values in matrix[header_row:]:
        if all(value is None or str(value).strip() == "" for value in values):
            continue
        rows.append(
            {
                header: values[index] if index < len(values) else None
                for index, header in enumerate(headers)
            }
        )
        if len(rows) > MAX_IMPORT_ROWS:
            raise ApiError(
                413,
                "import_too_many_rows",
                f"The import file has more than {MAX_IMPORT_ROWS} rows.",
            )
    if not rows:
        raise ApiError(422, "import_no_rows", "The file contains no rows below the header.")
    return ParsedTable(headers=headers, rows=rows, delimiter=delimiter)


def json_safe(value: Any) -> Any:
    """Raw cell values are stored as evidence; keep them JSON serialisable."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return value
