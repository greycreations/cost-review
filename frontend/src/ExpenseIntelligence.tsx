import { useEffect, useRef, useState } from "react";

import {
  getExpenseContributions,
  getMonthExpenseForecast,
  type Environment,
  type ExpenseContribution,
  type Language,
  type LedgerComparison,
  type LedgerFilters,
  type MonthExpenseForecast,
  type Page,
} from "./api";

const copy = {
  sv: {
    title: "Månadens utgiftsprognos",
    actual: "Utgifter hittills",
    estimate: "Beräknade utgifter för hela månaden",
    basis: "Utfall hittills plus medianen av nettoutgifterna efter samma dag i de senaste tre avslutade månaderna.",
    insufficient: "Prognosen kräver registrerade utgifter i de tre senaste avslutade månaderna.",
    forecastError: "Det gick inte att hämta prognosen.",
    missingFx: "Prognosen saknas eftersom registrerade poster hittills saknar valutakurs.",
    budgetRisk: "Månadsbudgetar som väntas överskridas",
    budget: "Budget",
    target: "Budgetmål",
    loading: "Hämtar underlag…",
    changes: "Vad förändrade nettoutgifterna?",
    current: "Vald period",
    previous: "Jämförelseperiod",
    difference: "Förändring",
    category: "Kategori",
    uncategorized: "Okategoriserat",
    noChanges: "Inga registrerade förändringar mellan perioderna.",
    largestIncrease: "Största ökningen",
    netChange: "Nettoförändring",
    contribution: "Bidrag till nettoutgiften",
    transactions: "Bidragande transaktioner",
    empty: "Inga transaktioner bidrog till beloppet under perioden.",
    rowError: "Det gick inte att hämta transaktionerna.",
    close: "Stäng underlaget",
    openTransactions: "Öppna i Transaktioner",
    back: "Föregående sida",
    next: "Nästa sida",
    date: "Datum",
    description: "Beskrivning",
  },
  en: {
    title: "Monthly expense forecast",
    actual: "Expenses so far",
    estimate: "Estimated expenses for the full month",
    basis: "Actuals to date plus the median net expenses after the same day in the last three completed months.",
    insufficient: "The forecast needs recorded expenses in each of the last three completed months.",
    forecastError: "The forecast could not be loaded.",
    missingFx: "A forecast is unavailable because some entries to date are missing exchange rates.",
    budgetRisk: "Monthly budgets projected to overspend",
    budget: "Budget",
    target: "Budget target",
    loading: "Loading…",
    changes: "What changed net expenses?",
    current: "Selected period",
    previous: "Comparison period",
    difference: "Change",
    category: "Category",
    uncategorized: "Uncategorised",
    noChanges: "No recorded changes between these periods.",
    largestIncrease: "Largest increase",
    netChange: "Net change",
    contribution: "Contribution to net expenses",
    transactions: "Contributing transactions",
    empty: "No transactions contributed to the amount in this period.",
    rowError: "The transactions could not be loaded.",
    close: "Close details",
    openTransactions: "Open in Transactions",
    back: "Previous page",
    next: "Next page",
    date: "Date",
    description: "Description",
  },
};

export type ExpenseSelection = { from: string; to: string; categoryId: number | null };

export function ExpenseIntelligence({
  environment, language, from, to, currency, comparison, filters, showForecast, detail, selectDetail, openTransactions,
}: {
  environment: Environment;
  language: Language;
  from: string;
  to: string;
  currency?: string;
  comparison: LedgerComparison | null;
  filters: LedgerFilters;
  showForecast: boolean;
  detail: ExpenseSelection | null;
  selectDetail: (value: ExpenseSelection | null) => void;
  openTransactions: (value: ExpenseSelection) => void;
}) {
  const labels = copy[language];
  const [forecast, setForecast] = useState<MonthExpenseForecast | null>(null);
  const [forecastFailed, setForecastFailed] = useState(false);

  useEffect(() => {
    if (!showForecast) return;
    let active = true;
    getMonthExpenseForecast(environment, filters).then(
      (value) => { if (active) setForecast(value); },
      () => { if (active) setForecastFailed(true); },
    );
    return () => { active = false; };
  }, [environment, filters, showForecast]);

  const changes = comparison?.expense_changes ?? [];
  const largest = changes.find((row) => Number(row.change) > 0);
  const currentForecast = forecast?.date_from === from ? forecast : null;

  return (
    <>
      {showForecast ? (
        <section className="analysis-panel">
          <div className="analysis-panel-heading"><div><h2>{labels.title}</h2></div></div>
          {forecastFailed ? <p role="alert">{labels.forecastError}</p> : null}
          {!forecast && !forecastFailed ? <p role="status">{labels.loading}</p> : null}
          {currentForecast ? (
            <>
              <p><time dateTime={currentForecast.as_of}>{currentForecast.as_of}</time></p>
              <p>{labels.actual} <strong>{money(currentForecast.actual_expenses, currentForecast.base_currency, language)}</strong></p>
              {currentForecast.forecast_expenses !== null ? (
                <>
                  <p>{labels.estimate} <strong>{money(currentForecast.forecast_expenses, currentForecast.base_currency, language)}</strong></p>
                  <p className="quiet-copy">{labels.basis}</p>
                </>
              ) : <p className="quiet-copy">{currentForecast.missing_fx_count ? labels.missingFx : labels.insufficient}</p>}
              {currentForecast.budget_risks?.length ? (
                <div className="table-scroll">
                  <h3>{labels.budgetRisk}</h3>
                  <table aria-label={labels.budgetRisk}>
                    <thead><tr><th>{labels.budget}</th><th>{labels.target}</th><th>{labels.estimate}</th><th>{labels.difference}</th></tr></thead>
                    <tbody>{currentForecast.budget_risks.map((risk) => (
                      <tr key={risk.budget_id}>
                        <th scope="row">{risk.name}</th>
                        <td>{money(risk.target_amount, currentForecast.base_currency, language)}</td>
                        <td>{money(risk.forecast_amount, currentForecast.base_currency, language)}</td>
                        <td>{money(risk.overrun, currentForecast.base_currency, language)}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              ) : null}
            </>
          ) : null}
        </section>
      ) : null}
      {comparison && currency ? (
        <section className="analysis-panel">
          <div className="analysis-panel-heading"><div><h2>{labels.changes}</h2></div></div>
          {largest ? (
            <p className="quiet-copy">{labels.largestIncrease} <strong>{largest.category_name ?? labels.uncategorized} · {money(largest.change, currency, language)}</strong></p>
          ) : null}
          {changes.length === 0 ? <p className="analysis-empty">{labels.noChanges}</p> : (
            <div className="table-scroll"><table aria-label={labels.changes}>
              <thead><tr><th>{labels.category}</th><th>{labels.current}<br /><small>{from} – {to}</small></th><th>{labels.previous}<br /><small>{comparison.date_from} – {comparison.date_to}</small></th><th>{labels.difference}</th></tr></thead>
              <tbody>{changes.map((change) => {
                const name = change.category_name ?? labels.uncategorized;
                return (
                  <tr key={change.category_id ?? "uncategorized"}>
                    <th scope="row">{name}</th>
                    <td><button aria-label={`${labels.transactions} · ${name} · ${labels.current} · ${money(change.current_amount, currency, language)}`} className="ghost-button" type="button" onClick={() => selectDetail({ from, to, categoryId: change.category_id })}>{money(change.current_amount, currency, language)}</button></td>
                    <td><button aria-label={`${labels.transactions} · ${name} · ${labels.previous} · ${money(change.previous_amount, currency, language)}`} className="ghost-button" type="button" onClick={() => selectDetail({ from: comparison.date_from, to: comparison.date_to, categoryId: change.category_id })}>{money(change.previous_amount, currency, language)}</button></td>
                    <td>{money(change.change, currency, language)}</td>
                  </tr>
                );
              })}</tbody>
              <tfoot><tr><th scope="row" colSpan={3}>{labels.netChange}</th><td>{money(comparison.expense_change_total, currency, language)}</td></tr></tfoot>
            </table></div>
          )}
        </section>
      ) : null}
      {detail && currency ? (
        <ExpenseDetail key={`${detail.from}:${detail.to}:${detail.categoryId}`} detail={detail} environment={environment} language={language} filters={filters} currency={currency} close={() => selectDetail(null)} openTransactions={() => openTransactions(detail)} />
      ) : null}
    </>
  );
}

function ExpenseDetail({ detail, environment, language, filters, currency, close, openTransactions }: {
  detail: ExpenseSelection;
  environment: Environment;
  language: Language;
  filters: LedgerFilters;
  currency: string;
  close: () => void;
  openTransactions: () => void;
}) {
  const labels = copy[language];
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<{ offset: number; page: Page<ExpenseContribution> | null } | null>(null);
  const current = result?.offset === offset ? result : null;
  useEffect(() => {
    let active = true;
    getExpenseContributions(
      environment, detail.from, detail.to, { ...filters, categoryId: detail.categoryId },
      detail.categoryId === null, offset,
    ).then(
      (page) => { if (active) setResult({ offset, page }); },
      () => { if (active) setResult({ offset, page: null }); },
    );
    return () => { active = false; };
  }, [environment, detail, filters, offset]);

  return (
    <section className="analysis-panel" aria-label={labels.transactions}>
      <h2 tabIndex={-1} ref={heading}>{labels.transactions}</h2>
      <p>{detail.from} – {detail.to}</p>
      <button className="ghost-button" type="button" onClick={close}>{labels.close}</button>
      {detail.categoryId !== null ? <button className="ghost-button" type="button" onClick={openTransactions}>{labels.openTransactions}</button> : null}
      {!current ? <p role="status">{labels.loading}</p> : current.page === null ? (
        <p role="alert">{labels.rowError}</p>
      ) : current.page.total === 0 ? <p>{labels.empty}</p> : (
        <>
          <div className="table-scroll"><table aria-label={labels.transactions}>
            <thead><tr><th>{labels.date}</th><th>{labels.description}</th><th>{labels.contribution}</th></tr></thead>
            <tbody>{current.page.items.map((row) => (
              <tr key={row.transaction_id}><td>{row.transaction_date}</td><td>{row.description}</td><td>{money(row.amount, currency, language)}</td></tr>
            ))}</tbody>
          </table></div>
          {offset > 0 ? <button className="ghost-button" type="button" onClick={() => setOffset(Math.max(0, offset - (current.page?.limit ?? 50)))}>{labels.back}</button> : null}
          {offset + current.page.limit < current.page.total ? <button className="ghost-button" type="button" onClick={() => setOffset(offset + (current.page?.limit ?? 50))}>{labels.next}</button> : null}
        </>
      )}
    </section>
  );
}

function money(amount: string, currency: string, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", {
    style: "currency", currency, maximumFractionDigits: 4,
  }).format(Number(amount));
}
