import { useEffect, useMemo, useState } from "react";

import {
  getAccounts,
  getLedgerSummary,
  getProviders,
  getTransactions,
  type Account,
  type Environment,
  type Language,
  type LedgerSummary,
  type Provider,
  type Transaction,
} from "./api";

const copy = {
  sv: {
    eyebrow: "Release 1 · Core MVP",
    title: "Din ekonomi, den här månaden",
    lead: "En verklig sammanställning av registrerade poster. Inga exempelvärden visas.",
    income: "Inkomster",
    expenses: "Utgifter",
    net: "Netto",
    entries: "Registrerade poster",
    recent: "Senaste transaktioner",
    all: "Visa alla transaktioner",
    add: "Registrera transaktion",
    empty: "Översikten är tom eftersom inga transaktioner har registrerats den här månaden.",
    emptyAction: "Börja med att lägga till ett konto och därefter din första post.",
    accounts: "Skapa konto",
    missingFx: "poster saknar historisk valutakurs och ingår inte i totalsummorna.",
    loading: "Bygger översikten…",
  },
  en: {
    eyebrow: "Release 1 · Core MVP",
    title: "Your finances this month",
    lead: "A real summary of recorded entries. No sample figures are shown.",
    income: "Income",
    expenses: "Expenses",
    net: "Net",
    entries: "Recorded entries",
    recent: "Recent transactions",
    all: "View all transactions",
    add: "Record transaction",
    empty: "The overview is empty because no transactions have been recorded this month.",
    emptyAction: "Start by adding an account, then record your first entry.",
    accounts: "Create account",
    missingFx: "entries are missing historical FX and are excluded from totals.",
    loading: "Building overview…",
  },
} as const;

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
  const period = useMemo(() => currentMonth(), []);
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      getLedgerSummary(environment, period.from, period.to),
      getTransactions(environment, { dateFrom: period.from, dateTo: period.to, limit: 5 }),
      getAccounts(environment),
      getProviders(environment),
    ])
      .then(([totals, transactionPage, accountPage, providerPage]) => {
        if (!active) return;
        setSummary(totals);
        setTransactions(transactionPage.items);
        setAccounts(accountPage.items);
        setProviders(providerPage.items);
        setError(null);
      })
      .catch((reason) => {
        if (active) setError(reason instanceof Error ? reason.message : "Overview request failed.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [environment, period.from, period.to]);

  const accountNames = new Map(accounts.map((account) => [account.account_id, account.name]));
  const providerNames = new Map(providers.map((provider) => [provider.provider_id, provider.name]));

  return (
    <section className="workspace-view overview-view" aria-labelledby="overview-title">
      <div className="workspace-heading overview-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1 id="overview-title">{labels.title}</h1>
          <p>{labels.lead}</p>
        </div>
        <button className="primary-button" onClick={onNavigateTransactions} type="button">
          + {labels.add}
        </button>
      </div>

      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {loading ? <p className="quiet-copy">{labels.loading}</p> : null}

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
                <time dateTime={transaction.transaction_date}>
                  {dateLabel(transaction.transaction_date, language)}
                </time>
                <div>
                  <strong>{transaction.description}</strong>
                  <span>
                    {providerNames.get(transaction.provider_id ?? -1) ??
                      accountNames.get(transaction.account_id)}
                  </span>
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

function Metric({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

function currentMonth(): { from: string; to: string } {
  const now = new Date();
  return {
    from: localDate(new Date(now.getFullYear(), now.getMonth(), 1)),
    to: localDate(new Date(now.getFullYear(), now.getMonth() + 1, 0)),
  };
}

function localDate(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function money(value: string, currency: string, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", {
    style: "currency",
    currency,
  }).format(Number(value));
}

function dateLabel(value: string, language: Language): string {
  return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-SE", {
    day: "numeric",
    month: "short",
  }).format(new Date(`${value}T12:00:00`));
}
