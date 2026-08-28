import { useEffect, useMemo, useState, type CSSProperties } from "react";

import {
  getAccounts,
  getLedgerAnalysis,
  getLedgerSummary,
  getProviders,
  getTransactions,
  type Account,
  type Environment,
  type Language,
  type LedgerAnalysis,
  type LedgerSummary,
  type LedgerTrendPoint,
  type Provider,
  type Transaction,
} from "./api";

const copy = {
  sv: {
    eyebrow: "Release 1 · Core MVP",
    title: "Din ekonomi",
    lead: "En verklig sammanställning av registrerade poster. Inga exempelvärden visas.",
    period: "Välj månad",
    previousMonth: "Föregående månad",
    nextMonth: "Nästa månad",
    currentMonth: "Denna månad",
    income: "Inkomster",
    expenses: "Utgifter",
    net: "Netto",
    entries: "Registrerade poster",
    cashFlow: "Inkomster och utgifter över månaden",
    cashFlowLead: "Beloppen visas per transaktionsdatum i basvalutan.",
    categoryBreakdown: "Utgifter per kategori",
    categoryLead: "De största kategorierna för den valda månaden.",
    uncategorized: "Okategoriserat",
    noCashFlow: "Det finns ännu inga växlade inkomst- eller utgiftsposter att visa.",
    noCategories: "Kategorifördelningen visas när månaden innehåller kategoriserade utgifter.",
    showTable: "Visa data som tabell",
    date: "Datum",
    category: "Kategori",
    amount: "Belopp",
    count: "Antal poster",
    topCategories: "Diagrammet visar de åtta största kategorierna. Tabellen innehåller alla.",
    recent: "Senaste posterna i månaden",
    all: "Visa alla transaktioner",
    add: "Registrera transaktion",
    empty: "Översikten är tom eftersom inga transaktioner har registrerats den valda månaden.",
    emptyAction: "Börja med att lägga till ett konto och därefter din första post.",
    accounts: "Skapa konto",
    missingFx: "poster saknar historisk valutakurs och ingår inte i totalsummor eller grafer.",
    loading: "Bygger översikten…",
  },
  en: {
    eyebrow: "Release 1 · Core MVP",
    title: "Your finances",
    lead: "A real summary of recorded entries. No sample figures are shown.",
    period: "Select month",
    previousMonth: "Previous month",
    nextMonth: "Next month",
    currentMonth: "This month",
    income: "Income",
    expenses: "Expenses",
    net: "Net",
    entries: "Recorded entries",
    cashFlow: "Income and expenses through the month",
    cashFlowLead: "Amounts are shown by transaction date in the base currency.",
    categoryBreakdown: "Expenses by category",
    categoryLead: "The largest categories for the selected month.",
    uncategorized: "Uncategorised",
    noCashFlow: "There are no converted income or expense entries to show yet.",
    noCategories: "The category breakdown appears when the month has categorised expenses.",
    showTable: "Show data as a table",
    date: "Date",
    category: "Category",
    amount: "Amount",
    count: "Entries",
    topCategories: "The chart shows the eight largest categories. The table contains all.",
    recent: "Latest entries this month",
    all: "View all transactions",
    add: "Record transaction",
    empty: "The overview is empty because no transactions have been recorded in the selected month.",
    emptyAction: "Start by adding an account, then record your first entry.",
    accounts: "Create account",
    missingFx: "entries are missing historical FX and are excluded from totals and charts.",
    loading: "Building overview…",
  },
} as const;

type Labels = (typeof copy)[Language];

type OverviewData = {
  key: string;
  summary: LedgerSummary;
  analysis: LedgerAnalysis;
  transactions: Transaction[];
  accounts: Account[];
  providers: Provider[];
};

export function OverviewWorkspace({
  environment,
  language,
  onNavigateAccounts,
  onNavigateTransactions,
}: {
  environment: Environment;
  language: Language;
  onNavigateAccounts: () => void;
  onNavigateTransactions: () => void;
}) {
  const labels = copy[language];
  const [selectedMonth, setSelectedMonth] = useState(currentMonthKey);
  const period = useMemo(() => monthPeriod(selectedMonth), [selectedMonth]);
  const requestKey = `${environment}:${period.from}:${period.to}`;
  const [data, setData] = useState<OverviewData | null>(null);
  const [requestError, setRequestError] = useState<{ key: string; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      getLedgerSummary(environment, period.from, period.to),
      getLedgerAnalysis(environment, period.from, period.to),
      getTransactions(environment, { dateFrom: period.from, dateTo: period.to, limit: 5 }),
      getAccounts(environment),
      getProviders(environment),
    ])
      .then(([totals, analyticalData, transactionPage, accountPage, providerPage]) => {
        if (!active) return;
        setData({
          key: requestKey,
          summary: totals,
          analysis: analyticalData,
          transactions: transactionPage.items,
          accounts: accountPage.items,
          providers: providerPage.items,
        });
        setRequestError(null);
      })
      .catch((reason) => {
        if (active) {
          setRequestError({
            key: requestKey,
            message: reason instanceof Error ? reason.message : "Overview request failed.",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [environment, period.from, period.to, requestKey]);

  const currentData = data?.key === requestKey ? data : null;
  const summary = currentData?.summary ?? null;
  const analysis = currentData?.analysis ?? null;
  const transactions = currentData?.transactions ?? [];
  const accounts = currentData?.accounts ?? [];
  const providers = currentData?.providers ?? [];
  const error = requestError?.key === requestKey ? requestError.message : null;
  const loading = currentData === null && error === null;

  const accountNames = new Map(accounts.map((account) => [account.account_id, account.name]));
  const providerNames = new Map(providers.map((provider) => [provider.provider_id, provider.name]));
  const isCurrentMonth = selectedMonth === currentMonthKey();

  return (
    <section className="workspace-view overview-view" aria-busy={loading} aria-labelledby="overview-title">
      <div className="workspace-heading overview-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1 id="overview-title">{labels.title} · {monthLabel(selectedMonth, language)}</h1>
          <p>{labels.lead}</p>
        </div>
        <div className="workspace-actions">
          <MonthPicker labels={labels} onChange={setSelectedMonth} selectedMonth={selectedMonth} />
          {!isCurrentMonth ? (
            <button className="ghost-button" onClick={() => setSelectedMonth(currentMonthKey())} type="button">
              {labels.currentMonth}
            </button>
          ) : null}
          <button className="primary-button" onClick={onNavigateTransactions} type="button">
            + {labels.add}
          </button>
        </div>
      </div>

      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {loading ? <p className="quiet-copy" role="status">{labels.loading}</p> : null}

      <div className="overview-metrics">
        <Metric label={labels.income} value={summary && money(summary.income, summary.base_currency, language)} />
        <Metric label={labels.expenses} value={summary && money(summary.expenses, summary.base_currency, language)} />
        <Metric label={labels.net} value={summary && money(summary.net_cash_flow, summary.base_currency, language)} />
        <Metric label={labels.entries} value={summary ? String(summary.transaction_count) : null} />
      </div>

      {summary?.missing_fx_count ? (
        <p className="attention-note overview-attention">
          {summary.missing_fx_count} {labels.missingFx}
        </p>
      ) : null}

      <div className="overview-analysis-grid">
        <CashFlowChart
          currency={summary?.base_currency ?? analysis?.base_currency ?? "SEK"}
          daily={analysis?.daily ?? []}
          labels={labels}
          language={language}
          period={period}
        />
        <CategoryChart
          categories={analysis?.expense_categories ?? []}
          currency={summary?.base_currency ?? analysis?.base_currency ?? "SEK"}
          labels={labels}
          language={language}
        />
      </div>

      <section className="recent-panel">
        <div className="recent-heading">
          <h2>{labels.recent}</h2>
          <button className="ghost-button" onClick={onNavigateTransactions} type="button">
            {labels.all} →
          </button>
        </div>
        {!loading && transactions.length === 0 ? (
          <div className="guided-empty">
            <span className="empty-icon" aria-hidden="true">+</span>
            <div>
              <strong>{labels.empty}</strong>
              <p>{labels.emptyAction}</p>
            </div>
            {accounts.length === 0 ? (
              <button className="secondary-button" onClick={onNavigateAccounts} type="button">
                {labels.accounts}
              </button>
            ) : (
              <button className="secondary-button" onClick={onNavigateTransactions} type="button">
                {labels.add}
              </button>
            )}
          </div>
        ) : (
          <div className="overview-transaction-list">
            {transactions.map((transaction) => (
              <div className="overview-transaction" key={transaction.transaction_id}>
                <time dateTime={transaction.transaction_date}>{dateLabel(transaction.transaction_date, language)}</time>
                <div>
                  <strong>{transaction.description}</strong>
                  <span>{providerNames.get(transaction.provider_id ?? -1) ?? accountNames.get(transaction.account_id)}</span>
                </div>
                <strong className={transaction.transaction_kind}>
                  {transaction.transaction_kind === "expense" ? "−" : "+"}
                  {money(transaction.original_amount, transaction.original_currency, language)}
                </strong>
              </div>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

function MonthPicker({ labels, onChange, selectedMonth }: { labels: Labels; onChange: (month: string) => void; selectedMonth: string }) {
  return (
    <div className="month-picker" role="group" aria-label={labels.period}>
      <button aria-label={labels.previousMonth} className="month-arrow" onClick={() => onChange(shiftMonth(selectedMonth, -1))} type="button">←</button>
      <label>
        <span>{labels.period}</span>
        <input aria-label={labels.period} onChange={(event) => event.target.value && onChange(event.target.value)} type="month" value={selectedMonth} />
      </label>
      <button aria-label={labels.nextMonth} className="month-arrow" onClick={() => onChange(shiftMonth(selectedMonth, 1))} type="button">→</button>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | null }) {
  return <div className="metric-card"><span>{label}</span><strong>{value ?? "—"}</strong></div>;
}

function CashFlowChart({ currency, daily, labels, language, period }: { currency: string; daily: LedgerTrendPoint[]; labels: Labels; language: Language; period: { from: string; to: string } }) {
  const days = fillMonth(period, daily);
  const hasValues = daily.length > 0;
  const width = 640;
  const height = 214;
  const padding = { top: 20, right: 18, bottom: 32, left: 54 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maximum = Math.max(1, ...days.flatMap((day) => [day.income, day.expenses]));
  const x = (index: number) => padding.left + (index / Math.max(days.length - 1, 1)) * plotWidth;
  const y = (value: number) => padding.top + plotHeight - (value / maximum) * plotHeight;
  const incomePath = linePath(days.map((day) => day.income), x, y);
  const expensePath = linePath(days.map((day) => day.expenses), x, y);

  return (
    <section className="analysis-panel" aria-labelledby="cash-flow-title">
      <div className="analysis-panel-heading">
        <div><h2 id="cash-flow-title">{labels.cashFlow}</h2><p>{labels.cashFlowLead}</p></div>
        <div className="chart-legend" aria-label={`${labels.income}, ${labels.expenses}`}>
          <span><i className="legend-income" />{labels.income}</span>
          <span><i className="legend-expense" />{labels.expenses}</span>
        </div>
      </div>
      {!hasValues ? <p className="analysis-empty">{labels.noCashFlow}</p> : (
        <>
          <div className="chart-scroll">
            <svg className="cash-flow-chart" role="img" viewBox={`0 0 ${width} ${height}`} aria-labelledby="cash-flow-title cash-flow-description">
              <desc id="cash-flow-description">{labels.cashFlowLead}</desc>
              {[0, 0.5, 1].map((ratio) => {
                const value = maximum * ratio;
                const gridY = y(value);
                return (
                  <g key={ratio}>
                    <line className="chart-grid-line" x1={padding.left} x2={width - padding.right} y1={gridY} y2={gridY} />
                    <text className="chart-axis-label" x={padding.left - 8} y={gridY + 4} textAnchor="end">{compactMoney(value, currency, language)}</text>
                  </g>
                );
              })}
              <text className="chart-axis-label" x={padding.left} y={height - 8}>{days[0]?.day}</text>
              <text className="chart-axis-label" x={width - padding.right} y={height - 8} textAnchor="end">{days.at(-1)?.day}</text>
              <path className="chart-line chart-line-income" d={incomePath} />
              <path className="chart-line chart-line-expense" d={expensePath} />
              {days.flatMap((day, index) => [
                day.income > 0 ? (
                  <circle aria-label={`${dateLabel(day.date, language)}: ${labels.income} ${money(String(day.income), currency, language)}`} className="chart-point chart-point-income" cx={x(index)} cy={y(day.income)} key={`income-${day.date}`} r={3} tabIndex={0}>
                    <title>{dateLabel(day.date, language)} · {labels.income}: {money(String(day.income), currency, language)}</title>
                  </circle>
                ) : null,
                day.expenses > 0 ? (
                  <circle aria-label={`${dateLabel(day.date, language)}: ${labels.expenses} ${money(String(day.expenses), currency, language)}`} className="chart-point chart-point-expense" cx={x(index)} cy={y(day.expenses)} key={`expense-${day.date}`} r={3} tabIndex={0}>
                    <title>{dateLabel(day.date, language)} · {labels.expenses}: {money(String(day.expenses), currency, language)}</title>
                  </circle>
                ) : null,
              ])}
            </svg>
          </div>
          <details className="chart-data-table">
            <summary>{labels.showTable}</summary>
            <div className="table-scroll"><table>
              <thead><tr><th>{labels.date}</th><th>{labels.income}</th><th>{labels.expenses}</th><th>{labels.net}</th></tr></thead>
              <tbody>{daily.map((day) => <tr key={day.date}><td>{dateLabel(day.date, language)}</td><td>{money(day.income, currency, language)}</td><td>{money(day.expenses, currency, language)}</td><td>{money(day.net_cash_flow, currency, language)}</td></tr>)}</tbody>
            </table></div>
          </details>
        </>
      )}
    </section>
  );
}

function CategoryChart({ categories, currency, labels, language }: { categories: LedgerAnalysis["expense_categories"]; currency: string; labels: Labels; language: Language }) {
  const chartCategories = categories.slice(0, 8);
  const maximum = Math.max(1, ...chartCategories.map((category) => Number(category.amount)));
  return (
    <section className="analysis-panel" aria-labelledby="category-chart-title">
      <div className="analysis-panel-heading"><div><h2 id="category-chart-title">{labels.categoryBreakdown}</h2><p>{labels.categoryLead}</p></div></div>
      {categories.length === 0 ? <p className="analysis-empty">{labels.noCategories}</p> : (
        <>
          <div className="category-bars" role="img" aria-labelledby="category-chart-title category-chart-description">
            <span className="sr-only" id="category-chart-description">{labels.categoryLead}</span>
            {chartCategories.map((category) => {
              const name = category.category_name ?? labels.uncategorized;
              const percentage = Math.max(2, (Number(category.amount) / maximum) * 100);
              return (
                <div className="category-bar-row" key={category.category_id ?? "uncategorized"}>
                  <div className="category-bar-label"><span>{name}</span><strong>{money(category.amount, currency, language)}</strong></div>
                  <div className="category-bar-track" aria-label={`${name}: ${money(category.amount, currency, language)}`}><span style={{ "--bar-size": `${percentage}%` } as CSSProperties} /></div>
                </div>
              );
            })}
          </div>
          {categories.length > chartCategories.length ? <p className="chart-note">{labels.topCategories}</p> : null}
          <details className="chart-data-table">
            <summary>{labels.showTable}</summary>
            <div className="table-scroll"><table>
              <thead><tr><th>{labels.category}</th><th>{labels.amount}</th><th>{labels.count}</th></tr></thead>
              <tbody>{categories.map((category) => <tr key={category.category_id ?? "uncategorized"}><td>{category.category_name ?? labels.uncategorized}</td><td>{money(category.amount, currency, language)}</td><td>{category.transaction_count}</td></tr>)}</tbody>
            </table></div>
          </details>
        </>
      )}
    </section>
  );
}

function currentMonthKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function monthPeriod(month: string): { from: string; to: string } {
  const [year, monthNumber] = month.split("-").map(Number);
  return { from: localDate(new Date(year, monthNumber - 1, 1)), to: localDate(new Date(year, monthNumber, 0)) };
}

function shiftMonth(month: string, delta: number): string {
  const [year, monthNumber] = month.split("-").map(Number);
  const value = new Date(year, monthNumber - 1 + delta, 1);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(month: string, language: Language): string {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-SE", { month: "long", year: "numeric" }).format(new Date(year, monthNumber - 1, 1));
}

function fillMonth(period: { from: string; to: string }, daily: LedgerTrendPoint[]): Array<{ date: string; day: number; income: number; expenses: number }> {
  const values = new Map(daily.map((point) => [point.date, point]));
  const end = Number(period.to.slice(-2));
  return Array.from({ length: end }, (_, index) => {
    const date = `${period.from.slice(0, 8)}${String(index + 1).padStart(2, "0")}`;
    const point = values.get(date);
    return { date, day: index + 1, income: Number(point?.income ?? 0), expenses: Number(point?.expenses ?? 0) };
  });
}

function linePath(values: number[], x: (index: number) => number, y: (value: number) => number): string {
  return values.map((value, index) => `${index === 0 ? "M" : "L"}${x(index)} ${y(value)}`).join(" ");
}

function localDate(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function money(value: string, currency: string, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", { style: "currency", currency }).format(Number(value));
}

function compactMoney(value: number, currency: string, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", { notation: "compact", maximumFractionDigits: 1, style: "currency", currency }).format(value);
}

function dateLabel(value: string, language: Language): string {
  return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-SE", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}
