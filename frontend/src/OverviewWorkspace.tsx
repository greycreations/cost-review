import { useEffect, useMemo, useState, type CSSProperties } from "react";

import {
  getAccounts,
  getCategories,
  getLedgerAnalysis,
  getLedgerSummary,
  getProviders,
  getTags,
  getTransactions,
  type Account,
  type AnalysisComparisonMode,
  type Category,
  type Environment,
  type Language,
  type LedgerAnalysis,
  type LedgerSummary,
  type LedgerTrendPoint,
  type Provider,
  type Tag,
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
    expenseDistribution: "Vart går pengarna?",
    expenseDistributionLead: "Andel av månadens kategoriserade nettoutgifter.",
    spendingPace: "Ackumulerade utgifter",
    spendingPaceLead: "Visar hur utgifterna byggs upp under perioden jämfört med vald jämförelse.",
    currentPeriod: "Vald period",
    other: "Övrigt",
    share: "Andel",
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
    comparison: "Jämför med",
    noComparison: "Ingen jämförelse",
    previousPeriod: "Föregående period",
    previousYear: "Samma period föregående år",
    filters: "Analysfilter",
    allAccounts: "Alla konton",
    allCategories: "Alla kategorier",
    allProviders: "Alla providers",
    tags: "Alla taggar",
    baseCost: "Endast baskostnader",
    clearFilters: "Rensa filter",
    comparedWith: "jämfört med",
    drillDown: "Visa bidragande transaktioner",
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
    expenseDistribution: "Where does the money go?",
    expenseDistributionLead: "Share of the month's categorised net expenses.",
    spendingPace: "Cumulative expenses",
    spendingPaceLead: "Shows how expenses build through the period against the selected comparison.",
    currentPeriod: "Selected period",
    other: "Other",
    share: "Share",
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
    comparison: "Compare with",
    noComparison: "No comparison",
    previousPeriod: "Previous period",
    previousYear: "Same period last year",
    filters: "Analysis filters",
    allAccounts: "All accounts",
    allCategories: "All categories",
    allProviders: "All providers",
    tags: "All tags",
    baseCost: "Base costs only",
    clearFilters: "Clear filters",
    comparedWith: "compared with",
    drillDown: "View contributing transactions",
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
  categories: Category[];
  tags: Tag[];
};

export type OverviewDrilldown = {
  dateFrom: string;
  dateTo: string;
  accountId?: number;
  providerId?: number;
  categoryId?: number;
  tagId?: number;
  isBaseCost?: boolean;
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
  onNavigateTransactions: (drilldown?: OverviewDrilldown) => void;
}) {
  const labels = copy[language];
  const [selectedMonth, setSelectedMonth] = useState(currentMonthKey);
  const [comparison, setComparison] = useState<AnalysisComparisonMode>("previous_period");
  const [filters, setFilters] = useState({
    accountId: "",
    providerId: "",
    categoryId: "",
    tagId: "",
    baseCostOnly: false,
  });
  const period = useMemo(() => monthPeriod(selectedMonth), [selectedMonth]);
  const ledgerFilters = useMemo(
    () => ({
      accountId: numberOrNull(filters.accountId),
      providerId: numberOrNull(filters.providerId),
      categoryId: numberOrNull(filters.categoryId),
      tagId: numberOrNull(filters.tagId),
      isBaseCost: filters.baseCostOnly ? true : null,
    }),
    [filters],
  );
  const requestKey = `${environment}:${period.from}:${period.to}:${comparison}:${JSON.stringify(ledgerFilters)}`;
  const [data, setData] = useState<OverviewData | null>(null);
  const [requestError, setRequestError] = useState<{ key: string; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      getLedgerSummary(environment, period.from, period.to, ledgerFilters),
      getLedgerAnalysis(environment, period.from, period.to, comparison, ledgerFilters),
      getTransactions(environment, { dateFrom: period.from, dateTo: period.to, ...ledgerFilters, limit: 5 }),
      getAccounts(environment),
      getProviders(environment),
      getCategories(environment),
      getTags(environment),
    ])
      .then(([totals, analyticalData, transactionPage, accountPage, providerPage, categoryPage, tagPage]) => {
        if (!active) return;
        setData({
          key: requestKey,
          summary: totals,
          analysis: analyticalData,
          transactions: transactionPage.items,
          accounts: accountPage.items,
          providers: providerPage.items,
          categories: categoryPage.items,
          tags: tagPage.items,
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
  }, [comparison, environment, ledgerFilters, period.from, period.to, requestKey]);

  const currentData = data?.key === requestKey ? data : null;
  const summary = currentData?.summary ?? null;
  const analysis = currentData?.analysis ?? null;
  const transactions = currentData?.transactions ?? [];
  const accounts = currentData?.accounts ?? [];
  const providers = currentData?.providers ?? [];
  const categories = currentData?.categories ?? [];
  const tags = currentData?.tags ?? [];
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
          <button className="primary-button" onClick={() => onNavigateTransactions()} type="button">
            + {labels.add}
          </button>
        </div>
      </div>

      <div className="analysis-toolbar" aria-label={labels.filters}>
        <label>{labels.comparison}<select onChange={(event) => setComparison(event.target.value as AnalysisComparisonMode)} value={comparison}><option value="none">{labels.noComparison}</option><option value="previous_period">{labels.previousPeriod}</option><option value="previous_year">{labels.previousYear}</option></select></label>
        <label>{labels.allAccounts}<select onChange={(event) => setFilters({ ...filters, accountId: event.target.value })} value={filters.accountId}><option value="">{labels.allAccounts}</option>{accounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.name}</option>)}</select></label>
        <label>{labels.allCategories}<select onChange={(event) => setFilters({ ...filters, categoryId: event.target.value })} value={filters.categoryId}><option value="">{labels.allCategories}</option>{categories.filter((category) => category.category_kind === "expense").map((category) => <option key={category.category_id} value={category.category_id}>{category.name}</option>)}</select></label>
        <label>{labels.allProviders}<select onChange={(event) => setFilters({ ...filters, providerId: event.target.value })} value={filters.providerId}><option value="">{labels.allProviders}</option>{providers.map((provider) => <option key={provider.provider_id} value={provider.provider_id}>{provider.name}</option>)}</select></label>
        <label>{labels.tags}<select onChange={(event) => setFilters({ ...filters, tagId: event.target.value })} value={filters.tagId}><option value="">{labels.tags}</option>{tags.map((tag) => <option key={tag.tag_id} value={tag.tag_id}>{tag.name}</option>)}</select></label>
        <label className="checkbox-field"><input checked={filters.baseCostOnly} onChange={(event) => setFilters({ ...filters, baseCostOnly: event.target.checked })} type="checkbox" />{labels.baseCost}</label>
        <button className="ghost-button" disabled={!filters.accountId && !filters.providerId && !filters.categoryId && !filters.tagId && !filters.baseCostOnly} onClick={() => setFilters({ accountId: "", providerId: "", categoryId: "", tagId: "", baseCostOnly: false })} type="button">{labels.clearFilters}</button>
      </div>

      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {loading ? <p className="quiet-copy" role="status">{labels.loading}</p> : null}

      <div className="overview-metrics">
        <Metric comparison={analysis?.comparison?.income} label={labels.income} labels={labels} value={summary?.income ?? null} currency={summary?.base_currency} language={language} />
        <Metric comparison={analysis?.comparison?.expenses} label={labels.expenses} labels={labels} value={summary?.expenses ?? null} currency={summary?.base_currency} language={language} />
        <Metric comparison={analysis?.comparison?.net_cash_flow} label={labels.net} labels={labels} value={summary?.net_cash_flow ?? null} currency={summary?.base_currency} language={language} />
        <Metric label={labels.entries} value={summary ? String(summary.transaction_count) : null} />
      </div>

      {summary?.missing_fx_count ? (
        <p className="attention-note overview-attention">
          {summary.missing_fx_count} {labels.missingFx}
        </p>
      ) : null}

      <div className="overview-analysis-grid">
        <CashFlowChart
          comparison={analysis?.comparison ?? null}
          currency={summary?.base_currency ?? analysis?.base_currency ?? "SEK"}
          daily={analysis?.daily ?? []}
          labels={labels}
          language={language}
          period={period}
        />
        <ExpenseDistributionChart
          categories={analysis?.expense_categories ?? []}
          currency={summary?.base_currency ?? analysis?.base_currency ?? "SEK"}
          labels={labels}
          language={language}
          onDrillDown={(categoryId) => onNavigateTransactions({
            dateFrom: period.from,
            dateTo: period.to,
            accountId: ledgerFilters.accountId ?? undefined,
            providerId: ledgerFilters.providerId ?? undefined,
            categoryId,
            tagId: ledgerFilters.tagId ?? undefined,
            isBaseCost: ledgerFilters.isBaseCost ?? undefined,
          })}
        />
        <SpendingPaceChart
          comparison={analysis?.comparison ?? null}
          currency={summary?.base_currency ?? analysis?.base_currency ?? "SEK"}
          daily={analysis?.daily ?? []}
          labels={labels}
          language={language}
          period={period}
        />
        <CategoryChart
          categories={analysis?.expense_categories ?? []}
          comparisonCategories={analysis?.comparison?.expense_categories ?? []}
          currency={summary?.base_currency ?? analysis?.base_currency ?? "SEK"}
          labels={labels}
          language={language}
          onDrillDown={(categoryId) => onNavigateTransactions({
            dateFrom: period.from,
            dateTo: period.to,
            accountId: ledgerFilters.accountId ?? undefined,
            providerId: ledgerFilters.providerId ?? undefined,
            categoryId: categoryId ?? undefined,
            tagId: ledgerFilters.tagId ?? undefined,
            isBaseCost: ledgerFilters.isBaseCost ?? undefined,
          })}
        />
      </div>

      <section className="recent-panel">
        <div className="recent-heading">
          <h2>{labels.recent}</h2>
          <button className="ghost-button" onClick={() => onNavigateTransactions()} type="button">
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
              <button className="secondary-button" onClick={() => onNavigateTransactions()} type="button">
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

function Metric({ label, value, comparison, currency, language, labels }: { label: string; value: string | null; comparison?: string; currency?: string; language?: Language; labels?: Labels }) {
  const delta = comparison !== undefined && value !== null ? percentageChange(Number(value), Number(comparison)) : null;
  return <div className="metric-card"><span>{label}</span><strong>{value !== null && currency && language ? money(value, currency, language) : value ?? "—"}</strong>{delta !== null && labels ? <small className="metric-comparison">{delta > 0 ? "+" : ""}{delta.toLocaleString(language === "sv" ? "sv-SE" : "en-SE", { maximumFractionDigits: 1 })}% {labels.comparedWith}</small> : null}</div>;
}

function CashFlowChart({ comparison, currency, daily, labels, language, period }: { comparison: LedgerAnalysis["comparison"]; currency: string; daily: LedgerTrendPoint[]; labels: Labels; language: Language; period: { from: string; to: string } }) {
  const days = fillPeriod(period, daily);
  const comparisonDays = comparison ? fillPeriod({ from: comparison.date_from, to: comparison.date_to }, comparison.daily) : [];
  const hasValues = daily.length > 0;
  const width = 640;
  const height = 214;
  const padding = { top: 20, right: 18, bottom: 32, left: 54 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maximum = Math.max(1, ...days.flatMap((day) => [day.income, day.expenses]), ...comparisonDays.flatMap((day) => [day.income, day.expenses]));
  const x = (index: number) => padding.left + (index / Math.max(days.length - 1, 1)) * plotWidth;
  const y = (value: number) => padding.top + plotHeight - (value / maximum) * plotHeight;
  const incomePath = linePath(days.map((day) => day.income), x, y);
  const expensePath = linePath(days.map((day) => day.expenses), x, y);
  const comparisonIncomePath = linePath(comparisonDays.map((day) => day.income), x, y);
  const comparisonExpensePath = linePath(comparisonDays.map((day) => day.expenses), x, y);

  return (
    <section className="analysis-panel" aria-labelledby="cash-flow-title">
      <div className="analysis-panel-heading">
        <div><h2 id="cash-flow-title">{labels.cashFlow}</h2><p>{labels.cashFlowLead}</p></div>
        <div className="chart-legend" aria-label={`${labels.income}, ${labels.expenses}`}>
          <span><i className="legend-income" />{labels.income}</span>
          <span><i className="legend-expense" />{labels.expenses}</span>
          {comparison ? <span><i className="legend-comparison" />{labels.comparison}</span> : null}
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
              {comparison ? <><path className="chart-line chart-line-comparison-income" d={comparisonIncomePath} /><path className="chart-line chart-line-comparison-expense" d={comparisonExpensePath} /></> : null}
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
            <div className="table-scroll"><table aria-label={labels.cashFlow}>
              <thead><tr><th>{labels.date}</th><th>{labels.income}</th><th>{labels.expenses}</th><th>{labels.net}</th></tr></thead>
              <tbody>{daily.map((day) => <tr key={day.date}><td>{dateLabel(day.date, language)}</td><td>{money(day.income, currency, language)}</td><td>{money(day.expenses, currency, language)}</td><td>{money(day.net_cash_flow, currency, language)}</td></tr>)}</tbody>
            </table></div>
          </details>
        </>
      )}
    </section>
  );
}

function ExpenseDistributionChart({ categories, currency, labels, language, onDrillDown }: { categories: LedgerAnalysis["expense_categories"]; currency: string; labels: Labels; language: Language; onDrillDown: (categoryId: number) => void }) {
  const positiveCategories = categories.filter((category) => Number(category.amount) > 0);
  const total = positiveCategories.reduce((sum, category) => sum + Number(category.amount), 0);
  const leading = positiveCategories.slice(0, 5);
  const remaining = positiveCategories.slice(5);
  const slices = [
    ...leading.map((category) => ({
      categoryId: category.category_id,
      name: category.category_name ?? labels.uncategorized,
      amount: Number(category.amount),
    })),
    ...(remaining.length > 0 ? [{
      categoryId: null,
      name: labels.other,
      amount: remaining.reduce((sum, category) => sum + Number(category.amount), 0),
    }] : []),
  ];
  let offset = 0;

  return (
    <section className="analysis-panel distribution-panel" aria-labelledby="expense-distribution-title">
      <div className="analysis-panel-heading"><div><h2 id="expense-distribution-title">{labels.expenseDistribution}</h2><p>{labels.expenseDistributionLead}</p></div></div>
      {total <= 0 ? <p className="analysis-empty">{labels.noCategories}</p> : (
        <>
          <div className="distribution-layout">
            <svg className="donut-chart" role="img" viewBox="0 0 128 128" aria-labelledby="expense-distribution-title expense-distribution-description">
              <desc id="expense-distribution-description">{labels.expenseDistributionLead}</desc>
              <circle className="donut-track" cx="64" cy="64" r="48" pathLength="100" />
              {slices.map((slice, index) => {
                const percentage = (slice.amount / total) * 100;
                const start = offset;
                offset += percentage;
                return <circle className={`donut-segment chart-fill-${index}`} cx="64" cy="64" key={`${slice.categoryId ?? "other"}-${slice.name}`} pathLength="100" r="48" strokeDasharray={`${percentage} ${100 - percentage}`} strokeDashoffset={-start}>
                  <title>{slice.name}: {money(String(slice.amount), currency, language)} ({formatPercent(percentage, language)})</title>
                </circle>;
              })}
              <text className="donut-total-label" textAnchor="middle" x="64" y="59">{labels.expenses}</text>
              <text className="donut-total-value" textAnchor="middle" x="64" y="75">{compactMoney(total, currency, language)}</text>
            </svg>
            <div className="distribution-legend">
              {slices.map((slice, index) => {
                const content = <><i className={`chart-fill-${index}`} /><span><strong>{slice.name}</strong><small>{formatPercent((slice.amount / total) * 100, language)} · {money(String(slice.amount), currency, language)}</small></span></>;
                return slice.categoryId === null ? <div className="distribution-legend-row" key={`${slice.name}-${index}`}>{content}</div> : <button aria-label={`${labels.drillDown}: ${slice.name}`} className="distribution-legend-row" key={slice.categoryId} onClick={() => onDrillDown(slice.categoryId as number)} type="button">{content}</button>;
              })}
            </div>
          </div>
          <details className="chart-data-table">
            <summary>{labels.showTable}</summary>
            <div className="table-scroll"><table aria-label={labels.expenseDistribution}>
              <thead><tr><th>{labels.category}</th><th>{labels.amount}</th><th>{labels.share}</th></tr></thead>
              <tbody>{positiveCategories.map((category) => <tr key={category.category_id ?? "uncategorized"}><td>{category.category_name ?? labels.uncategorized}</td><td>{money(category.amount, currency, language)}</td><td>{formatPercent((Number(category.amount) / total) * 100, language)}</td></tr>)}</tbody>
            </table></div>
          </details>
        </>
      )}
    </section>
  );
}

function SpendingPaceChart({ comparison, currency, daily, labels, language, period }: { comparison: LedgerAnalysis["comparison"]; currency: string; daily: LedgerTrendPoint[]; labels: Labels; language: Language; period: { from: string; to: string } }) {
  const days = cumulativeExpenses(fillPeriod(period, daily));
  const comparisonDays = comparison ? cumulativeExpenses(fillPeriod({ from: comparison.date_from, to: comparison.date_to }, comparison.daily)) : [];
  const maximum = Math.max(1, days.at(-1)?.value ?? 0, comparisonDays.at(-1)?.value ?? 0);
  const width = 640;
  const height = 214;
  const padding = { top: 20, right: 18, bottom: 32, left: 54 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const x = (index: number, length: number) => padding.left + (index / Math.max(length - 1, 1)) * plotWidth;
  const y = (value: number) => padding.top + plotHeight - (value / maximum) * plotHeight;
  const path = (values: Array<{ value: number }>) => linePath(values.map((point) => point.value), (index) => x(index, values.length), y);
  const hasValues = (days.at(-1)?.value ?? 0) > 0;

  return (
    <section className="analysis-panel" aria-labelledby="spending-pace-title">
      <div className="analysis-panel-heading">
        <div><h2 id="spending-pace-title">{labels.spendingPace}</h2><p>{labels.spendingPaceLead}</p></div>
        <div className="chart-legend"><span><i className="legend-expense" />{labels.currentPeriod}</span>{comparison ? <span><i className="legend-comparison" />{labels.comparison}</span> : null}</div>
      </div>
      {!hasValues ? <p className="analysis-empty">{labels.noCashFlow}</p> : (
        <>
          <div className="chart-scroll">
            <svg className="cash-flow-chart" role="img" viewBox={`0 0 ${width} ${height}`} aria-labelledby="spending-pace-title spending-pace-description">
              <desc id="spending-pace-description">{labels.spendingPaceLead}</desc>
              {[0, 0.5, 1].map((ratio) => <g key={ratio}><line className="chart-grid-line" x1={padding.left} x2={width - padding.right} y1={y(maximum * ratio)} y2={y(maximum * ratio)} /><text className="chart-axis-label" x={padding.left - 8} y={y(maximum * ratio) + 4} textAnchor="end">{compactMoney(maximum * ratio, currency, language)}</text></g>)}
              <text className="chart-axis-label" x={padding.left} y={height - 8}>1</text>
              <text className="chart-axis-label" x={width - padding.right} y={height - 8} textAnchor="end">{days.length}</text>
              <path className="chart-area-expense" d={`${path(days)} L${x(days.length - 1, days.length)} ${y(0)} L${x(0, days.length)} ${y(0)} Z`} />
              <path className="chart-line chart-line-expense" d={path(days)} />
              {comparison ? <path className="chart-line chart-line-comparison-income" d={path(comparisonDays)} /> : null}
            </svg>
          </div>
          <details className="chart-data-table">
            <summary>{labels.showTable}</summary>
            <div className="table-scroll"><table aria-label={labels.spendingPace}>
              <thead><tr><th>{labels.date}</th><th>{labels.expenses}</th></tr></thead>
              <tbody>{days.map((day) => <tr key={day.date}><td>{dateLabel(day.date, language)}</td><td>{money(String(day.value), currency, language)}</td></tr>)}</tbody>
            </table></div>
          </details>
        </>
      )}
    </section>
  );
}

function CategoryChart({ categories, comparisonCategories, currency, labels, language, onDrillDown }: { categories: LedgerAnalysis["expense_categories"]; comparisonCategories: LedgerAnalysis["expense_categories"]; currency: string; labels: Labels; language: Language; onDrillDown: (categoryId: number | null) => void }) {
  const chartCategories = categories.slice(0, 8);
  const comparisonAmounts = new Map(comparisonCategories.map((category) => [category.category_id, Number(category.amount)]));
  const maximum = Math.max(1, ...chartCategories.flatMap((category) => [Number(category.amount), comparisonAmounts.get(category.category_id) ?? 0]));
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
              const comparisonPercentage = Math.max(0, ((comparisonAmounts.get(category.category_id) ?? 0) / maximum) * 100);
              return (
                <button aria-label={`${labels.drillDown}: ${name}`} className="category-bar-row" key={category.category_id ?? "uncategorized"} onClick={() => onDrillDown(category.category_id)} type="button">
                  <div className="category-bar-label"><span>{name}</span><strong>{money(category.amount, currency, language)}</strong></div>
                  <div className="category-bar-track" aria-label={`${name}: ${money(category.amount, currency, language)}`}><span style={{ "--bar-size": `${percentage}%` } as CSSProperties} />{comparisonPercentage > 0 ? <span className="comparison-bar" style={{ "--bar-size": `${comparisonPercentage}%` } as CSSProperties} /> : null}</div>
                </button>
              );
            })}
          </div>
          {categories.length > chartCategories.length ? <p className="chart-note">{labels.topCategories}</p> : null}
          <details className="chart-data-table">
            <summary>{labels.showTable}</summary>
            <div className="table-scroll"><table aria-label={labels.categoryBreakdown}>
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

function fillPeriod(period: { from: string; to: string }, daily: LedgerTrendPoint[]): Array<{ date: string; day: number; income: number; expenses: number }> {
  const values = new Map(daily.map((point) => [point.date, point]));
  const dates: string[] = [];
  const cursor = new Date(`${period.from}T12:00:00`);
  const end = new Date(`${period.to}T12:00:00`);
  while (cursor <= end) {
    dates.push(localDate(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return dates.map((date) => {
    const point = values.get(date);
    return { date, day: Number(date.slice(-2)), income: Number(point?.income ?? 0), expenses: Number(point?.expenses ?? 0) };
  });
}

function cumulativeExpenses(days: Array<{ date: string; expenses: number }>): Array<{ date: string; value: number }> {
  let total = 0;
  return days.map((day) => {
    total += day.expenses;
    return { date: day.date, value: total };
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

function formatPercent(value: number, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", { maximumFractionDigits: 1, style: "percent" }).format(value / 100);
}

function dateLabel(value: string, language: Language): string {
  return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-SE", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`));
}

function numberOrNull(value: string): number | null {
  return value ? Number(value) : null;
}

function percentageChange(current: number, comparison: number): number | null {
  if (comparison === 0) return null;
  return ((current - comparison) / Math.abs(comparison)) * 100;
}
