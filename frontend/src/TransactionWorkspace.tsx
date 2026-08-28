import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  createCategory,
  createProvider,
  createTransaction,
  getAccounts,
  getCategories,
  getLedgerSummary,
  getProviders,
  getTags,
  getTransactions,
  setTransactionArchived,
  updateTransaction,
  type Account,
  type Category,
  type Environment,
  type Language,
  type LedgerSummary,
  type Provider,
  type Tag,
  type Transaction,
  type TransactionInput,
  type TransactionKind,
} from "./api";

const copy = {
  sv: {
    eyebrow: "Dagligt arbete",
    title: "Transaktioner",
    lead: "Registrera verkliga inkomster och utgifter. Överföringar, återbetalningar och delningar får egna säkra flöden senare.",
    newTransaction: "Ny transaktion",
    editTransaction: "Redigera transaktion",
    expense: "Utgift",
    income: "Inkomst",
    date: "Transaktionsdatum",
    postingDate: "Bokföringsdatum",
    account: "Konto",
    chooseAccount: "Välj konto",
    description: "Beskrivning",
    amount: "Belopp",
    currency: "Valuta",
    category: "Kategori",
    noCategory: "Ingen kategori ännu",
    provider: "Provider",
    noProvider: "Ingen provider",
    addProvider: "Ny provider",
    addCategory: "Ny kategori",
    name: "Namn",
    add: "Lägg till",
    cancel: "Avbryt",
    save: "Spara transaktion",
    update: "Spara ändringar",
    optional: "Fler uppgifter",
    convertedAmount: "Belopp i basvaluta",
    convertedHelp: "Lämna tomt om historisk valutakurs saknas. Posten sparas och markeras för uppmärksamhet.",
    notes: "Anteckning",
    reference: "Referens",
    baseCost: "Baskostnad",
    tags: "Taggar",
    filters: "Filter",
    search: "Sök beskrivning",
    allKinds: "Alla typer",
    allAccounts: "Alla konton",
    showArchived: "Visa arkiverade",
    apply: "Tillämpa",
    clear: "Rensa",
    empty: "Inga transaktioner i vald period.",
    emptyLead: "Skapa den första posten för att börja bygga din verkliga ekonomiska historik.",
    accountNeeded: "Du behöver först skapa minst ett konto.",
    goAccounts: "Gå till Konton",
    archive: "Arkivera",
    restore: "Återställ",
    edit: "Redigera",
    missingFx: "Saknar valutakurs",
    loading: "Läser transaktioner…",
    count: "poster",
    periodIncome: "Inkomster",
    periodExpenses: "Utgifter",
    periodNet: "Netto",
  },
  en: {
    eyebrow: "Daily work",
    title: "Transactions",
    lead: "Record real income and expenses. Transfers, refunds, and splits will get their own safe workflows later.",
    newTransaction: "New transaction",
    editTransaction: "Edit transaction",
    expense: "Expense",
    income: "Income",
    date: "Transaction date",
    postingDate: "Posting date",
    account: "Account",
    chooseAccount: "Choose account",
    description: "Description",
    amount: "Amount",
    currency: "Currency",
    category: "Category",
    noCategory: "No category yet",
    provider: "Provider",
    noProvider: "No provider",
    addProvider: "New provider",
    addCategory: "New category",
    name: "Name",
    add: "Add",
    cancel: "Cancel",
    save: "Save transaction",
    update: "Save changes",
    optional: "More details",
    convertedAmount: "Amount in base currency",
    convertedHelp: "Leave blank when the historical FX rate is unknown. The entry is saved and flagged for attention.",
    notes: "Note",
    reference: "Reference",
    baseCost: "Base cost",
    tags: "Tags",
    filters: "Filters",
    search: "Search description",
    allKinds: "All types",
    allAccounts: "All accounts",
    showArchived: "Show archived",
    apply: "Apply",
    clear: "Clear",
    empty: "No transactions in the selected period.",
    emptyLead: "Create the first entry to begin building your real economic history.",
    accountNeeded: "Create at least one account first.",
    goAccounts: "Go to Accounts",
    archive: "Archive",
    restore: "Restore",
    edit: "Edit",
    missingFx: "Missing FX rate",
    loading: "Loading transactions…",
    count: "entries",
    periodIncome: "Income",
    periodExpenses: "Expenses",
    periodNet: "Net",
  },
} as const;

type Draft = {
  accountId: string;
  providerId: string;
  kind: TransactionKind;
  transactionDate: string;
  postingDate: string;
  description: string;
  amount: string;
  currency: string;
  convertedAmount: string;
  categoryId: string;
  tagIds: number[];
  isBaseCost: boolean;
  sourceReference: string;
  notes: string;
};

type Filters = {
  dateFrom: string;
  dateTo: string;
  kind: TransactionKind | "";
  accountId: string;
  search: string;
  showArchived: boolean;
};

export function TransactionWorkspace({
  environment,
  language,
  baseCurrency,
  onNavigateAccounts,
}: {
  environment: Environment;
  language: Language;
  baseCurrency: string;
  onNavigateAccounts: () => void;
}) {
  const labels = copy[language];
  const period = useMemo(() => currentMonth(), []);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [filters, setFilters] = useState<Filters>({
    dateFrom: period.from,
    dateTo: period.to,
    kind: "",
    accountId: "",
    search: "",
    showArchived: false,
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const [draft, setDraft] = useState(() => emptyDraft(baseCurrency));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [newProvider, setNewProvider] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [showNewProvider, setShowNewProvider] = useState(false);
  const [showNewCategory, setShowNewCategory] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void Promise.all([
      getAccounts(environment),
      getCategories(environment),
      getProviders(environment),
      getTags(environment),
      getTransactions(environment, {
        dateFrom: appliedFilters.dateFrom,
        dateTo: appliedFilters.dateTo,
        kind: appliedFilters.kind,
        accountId: numberOrNull(appliedFilters.accountId),
        search: appliedFilters.search,
        includeArchived: appliedFilters.showArchived,
      }),
      getLedgerSummary(environment, appliedFilters.dateFrom, appliedFilters.dateTo),
    ])
      .then(([accountPage, categoryPage, providerPage, tagPage, transactionPage, totals]) => {
        if (!active) return;
        setAccounts(accountPage.items);
        setCategories(categoryPage.items);
        setProviders(providerPage.items);
        setTags(tagPage.items);
        setTransactions(transactionPage.items);
        setSummary(totals);
        setDraft((current) => ({
          ...current,
          accountId: current.accountId || String(accountPage.items[0]?.account_id ?? ""),
        }));
        setError(null);
      })
      .catch((reason) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Transaction request failed.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [appliedFilters, environment, reloadKey]);

  const availableCategories = categories.filter(
    (category) => category.category_kind === draft.kind,
  );

  const openNew = () => {
    setEditingId(null);
    setDraft({
      ...emptyDraft(baseCurrency),
      accountId: String(accounts[0]?.account_id ?? ""),
    });
    setFormOpen(true);
    setError(null);
  };

  const openEdit = (transaction: Transaction) => {
    setEditingId(transaction.transaction_id);
    setDraft({
      accountId: String(transaction.account_id),
      providerId: String(transaction.provider_id ?? ""),
      kind: transaction.transaction_kind,
      transactionDate: transaction.transaction_date,
      postingDate: transaction.posting_date,
      description: transaction.description,
      amount: transaction.original_amount,
      currency: transaction.original_currency,
      convertedAmount: transaction.converted_amount ?? "",
      categoryId: String(transaction.category_id ?? ""),
      tagIds: transaction.tag_ids,
      isBaseCost: transaction.is_base_cost,
      sourceReference: transaction.source_reference ?? "",
      notes: transaction.notes ?? "",
    });
    setFormOpen(true);
    setError(null);
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditingId(null);
    setShowNewProvider(false);
    setShowNewCategory(false);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const payload: TransactionInput = {
      account_id: Number(draft.accountId),
      provider_id: numberOrNull(draft.providerId),
      transaction_kind: draft.kind,
      transaction_date: draft.transactionDate,
      posting_date: draft.postingDate,
      description: draft.description,
      original_amount: normalizeDecimalInput(draft.amount),
      original_currency: draft.currency.toUpperCase(),
      category_id: numberOrNull(draft.categoryId),
      tag_ids: draft.tagIds,
      is_base_cost: draft.isBaseCost,
      source_reference: draft.sourceReference.trim() || null,
      notes: draft.notes.trim() || null,
    };
    if (draft.currency.toUpperCase() !== baseCurrency) {
      payload.converted_amount = draft.convertedAmount
        ? normalizeDecimalInput(draft.convertedAmount)
        : null;
    }
    try {
      if (editingId === null) {
        await createTransaction(environment, payload);
      } else {
        await updateTransaction(environment, editingId, payload);
      }
      closeForm();
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Transaction request failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <section className="workspace-view" aria-labelledby="transactions-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1 id="transactions-title">{labels.title}</h1>
          <p>{labels.lead}</p>
        </div>
        <button
          className="primary-button"
          disabled={accounts.length === 0}
          onClick={openNew}
          type="button"
        >
          + {labels.newTransaction}
        </button>
      </div>

      {accounts.length === 0 && !loading ? (
        <div className="guided-empty panel">
          <span className="empty-icon" aria-hidden="true">1</span>
          <div>
            <h2>{labels.accountNeeded}</h2>
            <p>{labels.emptyLead}</p>
          </div>
          <button className="secondary-button" onClick={onNavigateAccounts} type="button">
            {labels.goAccounts}
          </button>
        </div>
      ) : null}

      <SummaryStrip labels={labels} language={language} summary={summary} />

      {formOpen ? (
        <TransactionForm
          accounts={accounts}
          availableCategories={availableCategories}
          baseCurrency={baseCurrency}
          categories={categories}
          draft={draft}
          editing={editingId !== null}
          environment={environment}
          labels={labels}
          newCategory={newCategory}
          newProvider={newProvider}
          providers={providers}
          setDraft={setDraft}
          setNewCategory={setNewCategory}
          setNewProvider={setNewProvider}
          setShowNewCategory={setShowNewCategory}
          setShowNewProvider={setShowNewProvider}
          showNewCategory={showNewCategory}
          showNewProvider={showNewProvider}
          tags={tags}
          working={working}
          onCancel={closeForm}
          onCreateCategory={async () => {
            try {
              const created = await createCategory(environment, {
                name: newCategory,
                category_kind: draft.kind,
                parent_category_id: null,
              });
              setCategories((current) => [...current, created]);
              setDraft((current) => ({
                ...current,
                categoryId: String(created.category_id),
              }));
              setNewCategory("");
              setShowNewCategory(false);
            } catch (reason) {
              setError(reason instanceof Error ? reason.message : "Category request failed.");
            }
          }}
          onCreateProvider={async () => {
            try {
              const created = await createProvider(environment, { name: newProvider });
              setProviders((current) => [...current, created]);
              setDraft((current) => ({
                ...current,
                providerId: String(created.provider_id),
              }));
              setNewProvider("");
              setShowNewProvider(false);
            } catch (reason) {
              setError(reason instanceof Error ? reason.message : "Provider request failed.");
            }
          }}
          onSubmit={submit}
        />
      ) : null}

      {error ? <p className="form-error" role="alert">{error}</p> : null}

      <form
        className="transaction-filters"
        onSubmit={(event) => {
          event.preventDefault();
          setLoading(true);
          setAppliedFilters(filters);
        }}
      >
        <div className="filter-heading">
          <h2>{labels.filters}</h2>
          <span>{transactions.length} {labels.count}</span>
        </div>
        <label>
          {labels.search}
          <input
            onChange={(event) => setFilters({ ...filters, search: event.target.value })}
            type="search"
            value={filters.search}
          />
        </label>
        <label>
          {labels.date}
          <span className="date-range">
            <input
              aria-label={`${labels.date} from`}
              onChange={(event) => setFilters({ ...filters, dateFrom: event.target.value })}
              required
              type="date"
              value={filters.dateFrom}
            />
            <input
              aria-label={`${labels.date} to`}
              onChange={(event) => setFilters({ ...filters, dateTo: event.target.value })}
              required
              type="date"
              value={filters.dateTo}
            />
          </span>
        </label>
        <label>
          {labels.allKinds}
          <select
            onChange={(event) => setFilters({ ...filters, kind: event.target.value as Filters["kind"] })}
            value={filters.kind}
          >
            <option value="">{labels.allKinds}</option>
            <option value="expense">{labels.expense}</option>
            <option value="income">{labels.income}</option>
          </select>
        </label>
        <label>
          {labels.account}
          <select
            onChange={(event) => setFilters({ ...filters, accountId: event.target.value })}
            value={filters.accountId}
          >
            <option value="">{labels.allAccounts}</option>
            {accounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.name}</option>)}
          </select>
        </label>
        <label className="checkbox-field filter-checkbox">
          <input
            checked={filters.showArchived}
            onChange={(event) => setFilters({ ...filters, showArchived: event.target.checked })}
            type="checkbox"
          />
          {labels.showArchived}
        </label>
        <div className="filter-actions">
          <button className="secondary-button" type="submit">{labels.apply}</button>
          <button
            className="ghost-button"
            onClick={() => {
              const cleared: Filters = { dateFrom: period.from, dateTo: period.to, kind: "", accountId: "", search: "", showArchived: false };
              setFilters(cleared);
              setLoading(true);
              setAppliedFilters(cleared);
            }}
            type="button"
          >{labels.clear}</button>
        </div>
      </form>

      {loading ? <p className="quiet-copy">{labels.loading}</p> : null}
      {!loading && transactions.length === 0 ? (
        <div className="transaction-empty">
          <span className="empty-icon" aria-hidden="true">+</span>
          <div><strong>{labels.empty}</strong><p>{labels.emptyLead}</p></div>
        </div>
      ) : (
        <TransactionList
          accounts={accounts}
          categories={categories}
          environment={environment}
          labels={labels}
          language={language}
          providers={providers}
          transactions={transactions}
          onEdit={openEdit}
          onReload={() => {
            setLoading(true);
            setReloadKey((value) => value + 1);
          }}
          onError={(message) => setError(message)}
        />
      )}
    </section>
  );
}

type Labels = (typeof copy)[Language];

function SummaryStrip({ labels, language, summary }: { labels: Labels; language: Language; summary: LedgerSummary | null }) {
  const cards = [
    [labels.periodIncome, summary?.income],
    [labels.periodExpenses, summary?.expenses],
    [labels.periodNet, summary?.net_cash_flow],
  ] as const;
  return (
    <div className="summary-strip" aria-label={`${labels.title} summary`}>
      {cards.map(([label, value]) => (
        <div className="summary-card" key={label}>
          <span>{label}</span>
          <strong>{summary && value !== undefined ? formatMoney(value, summary.base_currency, language) : "—"}</strong>
        </div>
      ))}
      {summary?.missing_fx_count ? <div className="attention-note">{summary.missing_fx_count} · {labels.missingFx}</div> : null}
    </div>
  );
}

function TransactionForm({
  accounts, availableCategories, baseCurrency, categories, draft, editing, labels,
  newCategory, newProvider, providers, setDraft, setNewCategory, setNewProvider,
  setShowNewCategory, setShowNewProvider, showNewCategory, showNewProvider, tags,
  working, onCancel, onCreateCategory, onCreateProvider, onSubmit,
}: {
  accounts: Account[]; availableCategories: Category[]; baseCurrency: string; categories: Category[];
  draft: Draft; editing: boolean; environment: Environment; labels: Labels; newCategory: string;
  newProvider: string; providers: Provider[]; setDraft: React.Dispatch<React.SetStateAction<Draft>>;
  setNewCategory: (value: string) => void; setNewProvider: (value: string) => void;
  setShowNewCategory: (value: boolean) => void; setShowNewProvider: (value: boolean) => void;
  showNewCategory: boolean; showNewProvider: boolean; tags: Tag[]; working: boolean;
  onCancel: () => void; onCreateCategory: () => Promise<void>; onCreateProvider: () => Promise<void>;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form className="transaction-editor" onSubmit={onSubmit}>
      <div className="editor-title"><h2>{editing ? labels.editTransaction : labels.newTransaction}</h2><button className="ghost-button" onClick={onCancel} type="button">{labels.cancel}</button></div>
      <div className="kind-switch" role="group" aria-label={labels.allKinds}>
        {(["expense", "income"] as const).map((kind) => <button className={draft.kind === kind ? "active" : ""} key={kind} onClick={() => setDraft((current) => ({ ...current, kind, categoryId: categories.some((category) => category.category_id === Number(current.categoryId) && category.category_kind === kind) ? current.categoryId : "" }))} type="button">{kind === "expense" ? labels.expense : labels.income}</button>)}
      </div>
      <div className="transaction-form-grid">
        <label>{labels.date}<input onChange={(event) => setDraft({ ...draft, transactionDate: event.target.value })} required type="date" value={draft.transactionDate} /></label>
        <label>{labels.postingDate}<input onChange={(event) => setDraft({ ...draft, postingDate: event.target.value })} required type="date" value={draft.postingDate} /></label>
        <label>{labels.account}<select onChange={(event) => setDraft({ ...draft, accountId: event.target.value })} required value={draft.accountId}><option value="">{labels.chooseAccount}</option>{accounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.name}</option>)}</select></label>
        <label className="description-field">{labels.description}<input autoFocus onChange={(event) => setDraft({ ...draft, description: event.target.value })} required value={draft.description} /></label>
        <label>{labels.amount}<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, amount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" required value={draft.amount} /></label>
        <label>{labels.currency}<input maxLength={3} minLength={3} onChange={(event) => setDraft({ ...draft, currency: event.target.value.toUpperCase() })} pattern="[A-Z]{3}" required value={draft.currency} /></label>
        <label>{labels.category}<select onChange={(event) => setDraft({ ...draft, categoryId: event.target.value })} value={draft.categoryId}><option value="">{labels.noCategory}</option>{availableCategories.map((category) => <option key={category.category_id} value={category.category_id}>{category.name}</option>)}</select><button className="inline-add" onClick={() => setShowNewCategory(!showNewCategory)} type="button">+ {labels.addCategory}</button></label>
        <label>{labels.provider}<select onChange={(event) => setDraft({ ...draft, providerId: event.target.value })} value={draft.providerId}><option value="">{labels.noProvider}</option>{providers.map((provider) => <option key={provider.provider_id} value={provider.provider_id}>{provider.name}</option>)}</select><button className="inline-add" onClick={() => setShowNewProvider(!showNewProvider)} type="button">+ {labels.addProvider}</button></label>
      </div>
      {showNewCategory ? <InlineCreate label={labels.addCategory} name={newCategory} labels={labels} onChange={setNewCategory} onCreate={onCreateCategory} /> : null}
      {showNewProvider ? <InlineCreate label={labels.addProvider} name={newProvider} labels={labels} onChange={setNewProvider} onCreate={onCreateProvider} /> : null}
      {draft.currency !== baseCurrency ? <label className="conversion-field">{labels.convertedAmount} ({baseCurrency})<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, convertedAmount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" value={draft.convertedAmount} /><small>{labels.convertedHelp}</small></label> : null}
      <details className="optional-fields"><summary>{labels.optional}</summary><div className="optional-grid"><label>{labels.reference}<input onChange={(event) => setDraft({ ...draft, sourceReference: event.target.value })} value={draft.sourceReference} /></label><label>{labels.notes}<input onChange={(event) => setDraft({ ...draft, notes: event.target.value })} value={draft.notes} /></label><fieldset><legend>{labels.tags}</legend>{tags.map((tag) => <label className="checkbox-field" key={tag.tag_id}><input checked={draft.tagIds.includes(tag.tag_id)} onChange={(event) => setDraft({ ...draft, tagIds: event.target.checked ? [...draft.tagIds, tag.tag_id] : draft.tagIds.filter((id) => id !== tag.tag_id) })} type="checkbox" />{tag.name}</label>)}</fieldset><label className="checkbox-field"><input checked={draft.isBaseCost} onChange={(event) => setDraft({ ...draft, isBaseCost: event.target.checked })} type="checkbox" />{labels.baseCost}</label></div></details>
      <div className="editor-actions"><button className="secondary-button" onClick={onCancel} type="button">{labels.cancel}</button><button className="primary-button" disabled={working} type="submit">{editing ? labels.update : labels.save}</button></div>
    </form>
  );
}

function InlineCreate({ label, name, labels, onChange, onCreate }: { label: string; name: string; labels: Labels; onChange: (value: string) => void; onCreate: () => Promise<void> }) {
  return <div className="inline-create"><label>{label} · {labels.name}<input onChange={(event) => onChange(event.target.value)} required value={name} /></label><button className="secondary-button" disabled={!name.trim()} onClick={() => void onCreate()} type="button">{labels.add}</button></div>;
}

function TransactionList({ accounts, categories, environment, labels, language, providers, transactions, onEdit, onReload, onError }: { accounts: Account[]; categories: Category[]; environment: Environment; labels: Labels; language: Language; providers: Provider[]; transactions: Transaction[]; onEdit: (transaction: Transaction) => void; onReload: () => void; onError: (message: string) => void }) {
  const accountNames = new Map(accounts.map((item) => [item.account_id, item.name]));
  const categoryNames = new Map(categories.map((item) => [item.category_id, item.name]));
  const providerNames = new Map(providers.map((item) => [item.provider_id, item.name]));
  return <div className="transaction-list">{transactions.map((transaction) => <article className={`transaction-row ${transaction.status}`} key={transaction.transaction_id}><time dateTime={transaction.transaction_date}>{formatDate(transaction.transaction_date, language)}</time><div className="transaction-main"><strong>{transaction.description}</strong><span>{providerNames.get(transaction.provider_id ?? -1) ?? categoryNames.get(transaction.category_id ?? -1) ?? accountNames.get(transaction.account_id)}</span>{transaction.fx_rate_status === "missing" ? <em>{labels.missingFx}</em> : null}</div><div className={`transaction-value ${transaction.transaction_kind}`}><strong>{transaction.transaction_kind === "expense" ? "−" : "+"}{formatMoney(transaction.original_amount, transaction.original_currency, language)}</strong>{transaction.converted_amount && transaction.original_currency !== transaction.base_currency ? <span>{formatMoney(transaction.converted_amount, transaction.base_currency, language)}</span> : null}</div><div className="row-actions"><button className="ghost-button" disabled={transaction.status === "archived"} onClick={() => onEdit(transaction)} type="button">{labels.edit}</button><button className="ghost-button" onClick={() => void setTransactionArchived(environment, transaction.transaction_id, transaction.status === "active").then(onReload).catch((reason) => onError(reason instanceof Error ? reason.message : "Transaction request failed."))} type="button">{transaction.status === "active" ? labels.archive : labels.restore}</button></div></article>)}</div>;
}

function emptyDraft(baseCurrency: string): Draft {
  const today = localDate(new Date());
  return { accountId: "", providerId: "", kind: "expense", transactionDate: today, postingDate: today, description: "", amount: "", currency: baseCurrency, convertedAmount: "", categoryId: "", tagIds: [], isBaseCost: false, sourceReference: "", notes: "" };
}

function currentMonth(): { from: string; to: string } {
  const today = new Date();
  return { from: localDate(new Date(today.getFullYear(), today.getMonth(), 1)), to: localDate(new Date(today.getFullYear(), today.getMonth() + 1, 0)) };
}

function localDate(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function numberOrNull(value: string): number | null { return value ? Number(value) : null; }
function normalizeDecimalInput(value: string): string { return value.replace(",", "."); }
function formatMoney(value: string, currency: string, language: Language): string { return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", { style: "currency", currency }).format(Number(value)); }
function formatDate(value: string, language: Language): string { return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-SE", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`)); }
