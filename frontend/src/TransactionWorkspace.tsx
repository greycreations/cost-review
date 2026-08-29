import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  createCategory,
  createProvider,
  createRecovery,
  createTransfer,
  createTransaction,
  getAccounts,
  getCategories,
  getLedgerSummary,
  getProviders,
  getTags,
  getTransfers,
  getTransactions,
  setTransferArchived,
  setRecoveryArchived,
  setTransactionArchived,
  updateTransfer,
  updateTransaction,
  type Account,
  type Category,
  type Environment,
  type Language,
  type LedgerSummary,
  type ManualTransactionKind,
  type Provider,
  type RecoveryKind,
  type Tag,
  type Transfer,
  type TransferInput,
  type TransferPurpose,
  type Transaction,
  type TransactionInput,
  type TransactionKind,
} from "./api";

const copy = {
  sv: {
    eyebrow: "Dagligt arbete",
    title: "Transaktioner",
    lead: "Registrera verkliga inkomster, utgifter och överföringar mellan dina egna konton.",
    newTransaction: "Ny transaktion",
    newTransfer: "Ny överföring",
    editTransaction: "Redigera transaktion",
    editTransfer: "Redigera överföring",
    expense: "Utgift",
    income: "Inkomst",
    transfer: "Överföring",
    refund: "Återbetalning",
    reimbursement: "Ersättning",
    addRefund: "Registrera återbetalning",
    addReimbursement: "Registrera ersättning",
    recoveryLead: "Den ursprungliga kostnaden bevaras. Beloppet dras av i nettokostnad och analys.",
    linkedExpense: "Hör till kostnad",
    transferLead: "Flytta pengar mellan egna konton utan att skapa en falsk inkomst eller utgift.",
    fromAccount: "Från konto",
    toAccount: "Till konto",
    sourcePostingDate: "Bokföringsdatum från",
    destinationPostingDate: "Bokföringsdatum till",
    receivedAmount: "Mottaget belopp",
    transferPurpose: "Syfte",
    purposeInternal: "Intern överföring",
    purposeSavings: "Sparande",
    purposeInvestment: "Investering",
    purposeCard: "Betalning av kreditkort",
    purposeDebt: "Amortering",
    transferValueHelp: "Beloppen i basvaluta måste motsvara samma ekonomiska värde. Avgifter registreras separat som utgift.",
    twoAccountsNeeded: "Du behöver minst två aktiva konton för en överföring.",
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
    saveTransfer: "Spara överföring",
    update: "Spara ändringar",
    optional: "Fler uppgifter",
    convertedAmount: "Belopp i basvaluta",
    convertedHelp: "Lämna tomt om historisk valutakurs saknas. Posten sparas och markeras för uppmärksamhet.",
    notes: "Anteckning",
    reference: "Referens",
    baseCost: "Baskostnad",
    tags: "Taggar",
    splitTransaction: "Dela upp transaktionen",
    splitLead: "Fördela beloppet mellan flera kategorier utan att skapa flera kontohändelser.",
    splitPart: "Del",
    splitMemo: "Beskrivning för delen",
    addSplit: "Lägg till del",
    removeSplit: "Ta bort del",
    remaining: "Kvar att fördela",
    parts: "delar",
    filters: "Filter",
    search: "Sök beskrivning",
    allKinds: "Alla typer",
    allAccounts: "Alla konton",
    allCategories: "Alla kategorier",
    allProviders: "Alla providers",
    allTags: "Alla taggar",
    baseCostsOnly: "Endast baskostnader",
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
    lead: "Record real income, expenses, and transfers between your own accounts.",
    newTransaction: "New transaction",
    newTransfer: "New transfer",
    editTransaction: "Edit transaction",
    editTransfer: "Edit transfer",
    expense: "Expense",
    income: "Income",
    transfer: "Transfer",
    refund: "Refund",
    reimbursement: "Reimbursement",
    addRefund: "Record refund",
    addReimbursement: "Record reimbursement",
    recoveryLead: "The original gross expense is preserved. This amount reduces net cost and analysis.",
    linkedExpense: "Linked expense",
    transferLead: "Move money between owned accounts without creating false income or expense.",
    fromAccount: "From account",
    toAccount: "To account",
    sourcePostingDate: "Posting date from",
    destinationPostingDate: "Posting date to",
    receivedAmount: "Received amount",
    transferPurpose: "Purpose",
    purposeInternal: "Internal transfer",
    purposeSavings: "Savings",
    purposeInvestment: "Investment",
    purposeCard: "Credit-card payment",
    purposeDebt: "Debt repayment",
    transferValueHelp: "Base-currency values must represent the same economic value. Record fees separately as an expense.",
    twoAccountsNeeded: "You need at least two active accounts for a transfer.",
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
    saveTransfer: "Save transfer",
    update: "Save changes",
    optional: "More details",
    convertedAmount: "Amount in base currency",
    convertedHelp: "Leave blank when the historical FX rate is unknown. The entry is saved and flagged for attention.",
    notes: "Note",
    reference: "Reference",
    baseCost: "Base cost",
    tags: "Tags",
    splitTransaction: "Split transaction",
    splitLead: "Allocate the amount across categories without creating multiple account events.",
    splitPart: "Split",
    splitMemo: "Split description",
    addSplit: "Add split",
    removeSplit: "Remove split",
    remaining: "Remaining to allocate",
    parts: "splits",
    filters: "Filters",
    search: "Search description",
    allKinds: "All types",
    allAccounts: "All accounts",
    allCategories: "All categories",
    allProviders: "All providers",
    allTags: "All tags",
    baseCostsOnly: "Base costs only",
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
  kind: ManualTransactionKind;
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
  splitMode: boolean;
  splits: SplitDraft[];
};

type SplitDraft = {
  key: string;
  amount: string;
  categoryId: string;
  tagIds: number[];
  isBaseCost: boolean;
  memo: string;
};

type TransferDraft = {
  sourceAccountId: string;
  destinationAccountId: string;
  purpose: TransferPurpose;
  transactionDate: string;
  sourcePostingDate: string;
  destinationPostingDate: string;
  description: string;
  sourceAmount: string;
  destinationAmount: string;
  sourceConvertedAmount: string;
  destinationConvertedAmount: string;
  sourceReference: string;
  notes: string;
};

type EntryKind = TransactionKind | "transfer";

type RecoveryDraft = {
  kind: RecoveryKind;
  expenseId: number;
  accountId: string;
  providerId: string;
  transactionDate: string;
  postingDate: string;
  description: string;
  amount: string;
  currency: string;
  convertedAmount: string;
  sourceReference: string;
  notes: string;
};

type Filters = {
  dateFrom: string;
  dateTo: string;
  kind: EntryKind | "";
  accountId: string;
  providerId: string;
  categoryId: string;
  tagId: string;
  baseCostOnly: boolean;
  search: string;
  showArchived: boolean;
};

export type TransactionInitialFilters = {
  dateFrom: string;
  dateTo: string;
  accountId?: number;
  providerId?: number;
  categoryId?: number;
  tagId?: number;
  isBaseCost?: boolean;
};

export function TransactionWorkspace({
  environment,
  language,
  baseCurrency,
  onNavigateAccounts,
  initialFilters,
}: {
  environment: Environment;
  language: Language;
  baseCurrency: string;
  onNavigateAccounts: () => void;
  initialFilters?: TransactionInitialFilters | null;
}) {
  const labels = copy[language];
  const period = useMemo(() => currentMonth(), []);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [filters, setFilters] = useState<Filters>({
    dateFrom: initialFilters?.dateFrom ?? period.from,
    dateTo: initialFilters?.dateTo ?? period.to,
    kind: "",
    accountId: String(initialFilters?.accountId ?? ""),
    providerId: String(initialFilters?.providerId ?? ""),
    categoryId: String(initialFilters?.categoryId ?? ""),
    tagId: String(initialFilters?.tagId ?? ""),
    baseCostOnly: initialFilters?.isBaseCost ?? false,
    search: "",
    showArchived: false,
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const [draft, setDraft] = useState(() => emptyDraft(baseCurrency));
  const [transferDraft, setTransferDraft] = useState(() => emptyTransferDraft());
  const [recoveryDraft, setRecoveryDraft] = useState<RecoveryDraft | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingTransferId, setEditingTransferId] = useState<number | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [transferFormOpen, setTransferFormOpen] = useState(false);
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
        kind: appliedFilters.kind === "transfer" ? "" : appliedFilters.kind,
        accountId: numberOrNull(appliedFilters.accountId),
        providerId: numberOrNull(appliedFilters.providerId),
        categoryId: numberOrNull(appliedFilters.categoryId),
        tagId: numberOrNull(appliedFilters.tagId),
        isBaseCost: appliedFilters.baseCostOnly ? true : null,
        search: appliedFilters.search,
        includeArchived: appliedFilters.showArchived,
      }),
      getTransfers(environment, {
        dateFrom: appliedFilters.dateFrom,
        dateTo: appliedFilters.dateTo,
        accountId: numberOrNull(appliedFilters.accountId),
        search: appliedFilters.search,
        includeArchived: appliedFilters.showArchived,
      }),
      getLedgerSummary(environment, appliedFilters.dateFrom, appliedFilters.dateTo, {
        accountId: numberOrNull(appliedFilters.accountId),
        providerId: numberOrNull(appliedFilters.providerId),
        categoryId: numberOrNull(appliedFilters.categoryId),
        tagId: numberOrNull(appliedFilters.tagId),
        isBaseCost: appliedFilters.baseCostOnly ? true : null,
      }),
    ])
      .then(([accountPage, categoryPage, providerPage, tagPage, transactionPage, transferPage, totals]) => {
        if (!active) return;
        setAccounts(accountPage.items);
        setCategories(categoryPage.items);
        setProviders(providerPage.items);
        setTags(tagPage.items);
        setTransactions(appliedFilters.kind === "transfer" ? [] : transactionPage.items);
        setTransfers(
          (appliedFilters.kind !== "" && appliedFilters.kind !== "transfer")
            || Boolean(appliedFilters.providerId || appliedFilters.categoryId || appliedFilters.tagId || appliedFilters.baseCostOnly)
            ? []
            : transferPage.items,
        );
        setSummary(totals);
        setDraft((current) => ({
          ...current,
          accountId: current.accountId || String(accountPage.items[0]?.account_id ?? ""),
        }));
        setTransferDraft((current) => ({
          ...current,
          sourceAccountId:
            current.sourceAccountId || String(accountPage.items[0]?.account_id ?? ""),
          destinationAccountId:
            current.destinationAccountId || String(accountPage.items[1]?.account_id ?? ""),
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
    setRecoveryDraft(null);
    setTransferFormOpen(false);
    setEditingTransferId(null);
    setEditingId(null);
    setDraft({
      ...emptyDraft(baseCurrency),
      accountId: String(accounts[0]?.account_id ?? ""),
    });
    setFormOpen(true);
    setError(null);
  };

  const openEdit = (transaction: Transaction) => {
    if (transaction.transaction_kind !== "expense" && transaction.transaction_kind !== "income") {
      return;
    }
    setRecoveryDraft(null);
    setTransferFormOpen(false);
    setEditingTransferId(null);
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
      splitMode: transaction.is_split,
      splits: transaction.is_split
        ? transaction.splits.map((split) => ({
            key: String(split.transaction_split_id),
            amount: split.original_amount,
            categoryId: String(split.category_id ?? ""),
            tagIds: split.tag_ids,
            isBaseCost: split.is_base_cost,
            memo: split.memo ?? "",
          }))
        : initialSplits(),
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

  const openNewTransfer = () => {
    setRecoveryDraft(null);
    setFormOpen(false);
    setEditingId(null);
    setEditingTransferId(null);
    setTransferDraft({
      ...emptyTransferDraft(),
      sourceAccountId: String(accounts[0]?.account_id ?? ""),
      destinationAccountId: String(accounts[1]?.account_id ?? ""),
    });
    setTransferFormOpen(true);
    setError(null);
  };

  const openEditTransfer = (transfer: Transfer) => {
    setRecoveryDraft(null);
    setFormOpen(false);
    setEditingId(null);
    setEditingTransferId(transfer.transfer_link_id);
    setTransferDraft({
      sourceAccountId: String(transfer.source_account_id),
      destinationAccountId: String(transfer.destination_account_id),
      purpose: transfer.purpose,
      transactionDate: transfer.transaction_date,
      sourcePostingDate: transfer.source_posting_date,
      destinationPostingDate: transfer.destination_posting_date,
      description: transfer.description,
      sourceAmount: transfer.source_amount,
      destinationAmount: transfer.destination_amount,
      sourceConvertedAmount: transfer.source_converted_amount ?? "",
      destinationConvertedAmount: transfer.destination_converted_amount ?? "",
      sourceReference: transfer.source_reference ?? "",
      notes: transfer.notes ?? "",
    });
    setTransferFormOpen(true);
    setError(null);
  };

  const closeTransferForm = () => {
    setTransferFormOpen(false);
    setEditingTransferId(null);
  };

  const openRecovery = (expense: Transaction, kind: RecoveryKind) => {
    setFormOpen(false);
    setTransferFormOpen(false);
    setEditingId(null);
    setEditingTransferId(null);
    const today = localDate(new Date());
    setRecoveryDraft({
      kind,
      expenseId: expense.transaction_id,
      accountId: String(expense.account_id),
      providerId: String(expense.provider_id ?? ""),
      transactionDate: today < expense.transaction_date ? expense.transaction_date : today,
      postingDate: today < expense.transaction_date ? expense.transaction_date : today,
      description: kind === "refund" ? labels.refund : labels.reimbursement,
      amount: "",
      currency: expense.original_currency,
      convertedAmount: "",
      sourceReference: "",
      notes: "",
    });
    setError(null);
  };

  const submitRecovery = async (event: FormEvent) => {
    event.preventDefault();
    if (!recoveryDraft) return;
    setWorking(true);
    setError(null);
    try {
      await createRecovery(environment, recoveryDraft.expenseId, recoveryDraft.kind, {
        account_id: Number(recoveryDraft.accountId),
        provider_id: numberOrNull(recoveryDraft.providerId),
        transaction_date: recoveryDraft.transactionDate,
        posting_date: recoveryDraft.postingDate,
        description: recoveryDraft.description,
        original_amount: normalizeDecimalInput(recoveryDraft.amount),
        original_currency: recoveryDraft.currency.toUpperCase(),
        converted_amount:
          recoveryDraft.currency.toUpperCase() !== baseCurrency
            ? recoveryDraft.convertedAmount
              ? normalizeDecimalInput(recoveryDraft.convertedAmount)
              : null
            : undefined,
        source_reference: recoveryDraft.sourceReference.trim() || null,
        notes: recoveryDraft.notes.trim() || null,
      });
      setRecoveryDraft(null);
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Recovery request failed.");
    } finally {
      setWorking(false);
    }
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
    if (draft.splitMode) {
      payload.splits = draft.splits.map((split) => ({
        original_amount: normalizeDecimalInput(split.amount),
        category_id: numberOrNull(split.categoryId),
        tag_ids: split.tagIds,
        is_base_cost: split.isBaseCost,
        memo: split.memo.trim() || null,
      }));
      payload.category_id = null;
      payload.tag_ids = [];
      payload.is_base_cost = false;
    }
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

  const submitTransfer = async (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    setError(null);
    const sourceAccount = accounts.find(
      (account) => account.account_id === Number(transferDraft.sourceAccountId),
    );
    const destinationAccount = accounts.find(
      (account) => account.account_id === Number(transferDraft.destinationAccountId),
    );
    const payload: TransferInput = {
      source_account_id: Number(transferDraft.sourceAccountId),
      destination_account_id: Number(transferDraft.destinationAccountId),
      purpose: transferDraft.purpose,
      transaction_date: transferDraft.transactionDate,
      source_posting_date: transferDraft.sourcePostingDate,
      destination_posting_date: transferDraft.destinationPostingDate,
      description: transferDraft.description,
      source_amount: normalizeDecimalInput(transferDraft.sourceAmount),
      destination_amount: normalizeDecimalInput(transferDraft.destinationAmount),
      source_reference: transferDraft.sourceReference.trim() || null,
      notes: transferDraft.notes.trim() || null,
    };
    if (sourceAccount?.currency !== baseCurrency && transferDraft.sourceConvertedAmount) {
      payload.source_converted_amount = normalizeDecimalInput(
        transferDraft.sourceConvertedAmount,
      );
    }
    if (
      destinationAccount?.currency !== baseCurrency
      && transferDraft.destinationConvertedAmount
    ) {
      payload.destination_converted_amount = normalizeDecimalInput(
        transferDraft.destinationConvertedAmount,
      );
    }
    try {
      if (editingTransferId === null) {
        await createTransfer(environment, payload);
      } else {
        await updateTransfer(environment, editingTransferId, payload);
      }
      closeTransferForm();
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Transfer request failed.");
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
        <div className="workspace-actions">
          <button
            className="secondary-button"
            disabled={accounts.length < 2}
            onClick={openNewTransfer}
            type="button"
          >
            ↔ {labels.newTransfer}
          </button>
          <button
            className="primary-button"
            disabled={accounts.length === 0}
            onClick={openNew}
            type="button"
          >
            + {labels.newTransaction}
          </button>
        </div>
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
          language={language}
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

      {transferFormOpen ? (
        <TransferForm
          accounts={accounts}
          baseCurrency={baseCurrency}
          draft={transferDraft}
          editing={editingTransferId !== null}
          labels={labels}
          setDraft={setTransferDraft}
          working={working}
          onCancel={closeTransferForm}
          onSubmit={submitTransfer}
        />
      ) : null}

      {recoveryDraft ? (
        <RecoveryForm
          accounts={accounts}
          baseCurrency={baseCurrency}
          draft={recoveryDraft}
          expense={transactions.find(
            (item) => item.transaction_id === recoveryDraft.expenseId,
          )}
          labels={labels}
          language={language}
          providers={providers}
          setDraft={setRecoveryDraft}
          working={working}
          onCancel={() => setRecoveryDraft(null)}
          onSubmit={submitRecovery}
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
          <span>{transactions.length + transfers.length} {labels.count}</span>
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
            <option value="refund">{labels.refund}</option>
            <option value="reimbursement">{labels.reimbursement}</option>
            <option value="transfer">{labels.transfer}</option>
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
        <label>{labels.category}<select onChange={(event) => setFilters({ ...filters, categoryId: event.target.value })} value={filters.categoryId}><option value="">{labels.allCategories}</option>{categories.map((category) => <option key={category.category_id} value={category.category_id}>{category.name}</option>)}</select></label>
        <label>{labels.provider}<select onChange={(event) => setFilters({ ...filters, providerId: event.target.value })} value={filters.providerId}><option value="">{labels.allProviders}</option>{providers.map((provider) => <option key={provider.provider_id} value={provider.provider_id}>{provider.name}</option>)}</select></label>
        <label>{labels.tags}<select onChange={(event) => setFilters({ ...filters, tagId: event.target.value })} value={filters.tagId}><option value="">{labels.allTags}</option>{tags.map((tag) => <option key={tag.tag_id} value={tag.tag_id}>{tag.name}</option>)}</select></label>
        <label className="checkbox-field filter-checkbox"><input checked={filters.baseCostOnly} onChange={(event) => setFilters({ ...filters, baseCostOnly: event.target.checked })} type="checkbox" />{labels.baseCostsOnly}</label>
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
              const cleared: Filters = { dateFrom: period.from, dateTo: period.to, kind: "", accountId: "", providerId: "", categoryId: "", tagId: "", baseCostOnly: false, search: "", showArchived: false };
              setFilters(cleared);
              setLoading(true);
              setAppliedFilters(cleared);
            }}
            type="button"
          >{labels.clear}</button>
        </div>
      </form>

      {loading ? <p className="quiet-copy">{labels.loading}</p> : null}
      {!loading && transactions.length + transfers.length === 0 ? (
        <div className="transaction-empty">
          <span className="empty-icon" aria-hidden="true">+</span>
          <div><strong>{labels.empty}</strong><p>{labels.emptyLead}</p></div>
        </div>
      ) : (
        <EntryList
          accounts={accounts}
          categories={categories}
          environment={environment}
          labels={labels}
          language={language}
          providers={providers}
          transfers={transfers}
          transactions={transactions}
          onEdit={openEdit}
          onRecovery={openRecovery}
          onEditTransfer={openEditTransfer}
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
  language,
  newCategory, newProvider, providers, setDraft, setNewCategory, setNewProvider,
  setShowNewCategory, setShowNewProvider, showNewCategory, showNewProvider, tags,
  working, onCancel, onCreateCategory, onCreateProvider, onSubmit,
}: {
  accounts: Account[]; availableCategories: Category[]; baseCurrency: string; categories: Category[];
  draft: Draft; editing: boolean; environment: Environment; labels: Labels; newCategory: string;
  language: Language;
  newProvider: string; providers: Provider[]; setDraft: React.Dispatch<React.SetStateAction<Draft>>;
  setNewCategory: (value: string) => void; setNewProvider: (value: string) => void;
  setShowNewCategory: (value: boolean) => void; setShowNewProvider: (value: boolean) => void;
  showNewCategory: boolean; showNewProvider: boolean; tags: Tag[]; working: boolean;
  onCancel: () => void; onCreateCategory: () => Promise<void>; onCreateProvider: () => Promise<void>;
  onSubmit: (event: FormEvent) => void;
}) {
  const splitRemaining = draft.splitMode
    ? Number(normalizeDecimalInput(draft.amount) || 0)
      - draft.splits.reduce(
        (total, split) => total + Number(normalizeDecimalInput(split.amount) || 0),
        0,
      )
    : 0;
  const splitBalanced = !draft.splitMode || Math.abs(splitRemaining) < 0.00005;
  return (
    <form className="transaction-editor" onSubmit={onSubmit}>
      <div className="editor-title"><h2>{editing ? labels.editTransaction : labels.newTransaction}</h2><button className="ghost-button" onClick={onCancel} type="button">{labels.cancel}</button></div>
      <div className="kind-switch" role="group" aria-label={labels.allKinds}>
        {(["expense", "income"] as const).map((kind) => <button className={draft.kind === kind ? "active" : ""} key={kind} onClick={() => setDraft((current) => ({ ...current, kind, categoryId: categories.some((category) => category.category_id === Number(current.categoryId) && category.category_kind === kind) ? current.categoryId : "" }))} type="button">{kind === "expense" ? labels.expense : labels.income}</button>)}
      </div>
      <label className="checkbox-field split-toggle"><input checked={draft.splitMode} onChange={(event) => setDraft({ ...draft, splitMode: event.target.checked, splits: event.target.checked && draft.splits.length < 2 ? initialSplits() : draft.splits })} type="checkbox" />{labels.splitTransaction}</label>
      <div className="transaction-form-grid">
        <label>{labels.date}<input onChange={(event) => setDraft({ ...draft, transactionDate: event.target.value })} required type="date" value={draft.transactionDate} /></label>
        <label>{labels.postingDate}<input onChange={(event) => setDraft({ ...draft, postingDate: event.target.value })} required type="date" value={draft.postingDate} /></label>
        <label>{labels.account}<select onChange={(event) => setDraft({ ...draft, accountId: event.target.value })} required value={draft.accountId}><option value="">{labels.chooseAccount}</option>{accounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.name}</option>)}</select></label>
        <label className="description-field">{labels.description}<input autoFocus onChange={(event) => setDraft({ ...draft, description: event.target.value })} required value={draft.description} /></label>
        <label>{labels.amount}<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, amount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" required value={draft.amount} /></label>
        <label>{labels.currency}<input maxLength={3} minLength={3} onChange={(event) => setDraft({ ...draft, currency: event.target.value.toUpperCase() })} pattern="[A-Z]{3}" required value={draft.currency} /></label>
        {!draft.splitMode ? <label>{labels.category}<select onChange={(event) => setDraft({ ...draft, categoryId: event.target.value })} value={draft.categoryId}><option value="">{labels.noCategory}</option>{availableCategories.map((category) => <option key={category.category_id} value={category.category_id}>{category.name}</option>)}</select><button className="inline-add" onClick={() => setShowNewCategory(!showNewCategory)} type="button">+ {labels.addCategory}</button></label> : null}
        <label>{labels.provider}<select onChange={(event) => setDraft({ ...draft, providerId: event.target.value })} value={draft.providerId}><option value="">{labels.noProvider}</option>{providers.map((provider) => <option key={provider.provider_id} value={provider.provider_id}>{provider.name}</option>)}</select><button className="inline-add" onClick={() => setShowNewProvider(!showNewProvider)} type="button">+ {labels.addProvider}</button></label>
      </div>
      {draft.splitMode ? <SplitEditor availableCategories={availableCategories} currency={draft.currency} draft={draft} labels={labels} language={language} setDraft={setDraft} tags={tags} /> : null}
      {showNewCategory ? <InlineCreate label={labels.addCategory} name={newCategory} labels={labels} onChange={setNewCategory} onCreate={onCreateCategory} /> : null}
      {showNewProvider ? <InlineCreate label={labels.addProvider} name={newProvider} labels={labels} onChange={setNewProvider} onCreate={onCreateProvider} /> : null}
      {draft.currency !== baseCurrency ? <label className="conversion-field">{labels.convertedAmount} ({baseCurrency})<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, convertedAmount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" value={draft.convertedAmount} /><small>{labels.convertedHelp}</small></label> : null}
      <details className="optional-fields"><summary>{labels.optional}</summary><div className="optional-grid"><label>{labels.reference}<input onChange={(event) => setDraft({ ...draft, sourceReference: event.target.value })} value={draft.sourceReference} /></label><label>{labels.notes}<input onChange={(event) => setDraft({ ...draft, notes: event.target.value })} value={draft.notes} /></label>{!draft.splitMode ? <><fieldset><legend>{labels.tags}</legend>{tags.map((tag) => <label className="checkbox-field" key={tag.tag_id}><input checked={draft.tagIds.includes(tag.tag_id)} onChange={(event) => setDraft({ ...draft, tagIds: event.target.checked ? [...draft.tagIds, tag.tag_id] : draft.tagIds.filter((id) => id !== tag.tag_id) })} type="checkbox" />{tag.name}</label>)}</fieldset><label className="checkbox-field"><input checked={draft.isBaseCost} onChange={(event) => setDraft({ ...draft, isBaseCost: event.target.checked })} type="checkbox" />{labels.baseCost}</label></> : null}</div></details>
      <div className="editor-actions"><button className="secondary-button" onClick={onCancel} type="button">{labels.cancel}</button><button className="primary-button" disabled={working || !splitBalanced} type="submit">{editing ? labels.update : labels.save}</button></div>
    </form>
  );
}

function SplitEditor({
  availableCategories,
  currency,
  draft,
  labels,
  language,
  setDraft,
  tags,
}: {
  availableCategories: Category[];
  currency: string;
  draft: Draft;
  labels: Labels;
  language: Language;
  setDraft: React.Dispatch<React.SetStateAction<Draft>>;
  tags: Tag[];
}) {
  const allocated = draft.splits.reduce(
    (total, split) => total + Number(normalizeDecimalInput(split.amount) || 0),
    0,
  );
  const remaining = Number(normalizeDecimalInput(draft.amount) || 0) - allocated;
  const updateSplit = (key: string, values: Partial<SplitDraft>) => {
    setDraft((current) => ({
      ...current,
      splits: current.splits.map((split) =>
        split.key === key ? { ...split, ...values } : split,
      ),
    }));
  };
  return (
    <section className="split-editor" aria-labelledby="split-editor-title">
      <div className="split-editor-heading">
        <div>
          <h3 id="split-editor-title">{labels.splitTransaction}</h3>
          <p>{labels.splitLead}</p>
        </div>
        <strong className={Math.abs(remaining) < 0.00005 ? "balanced" : "unbalanced"}>
          {labels.remaining}: {formatMoney(String(remaining), currency || "SEK", language)}
        </strong>
      </div>
      <div className="split-list">
        {draft.splits.map((split, index) => (
          <fieldset className="split-row" key={split.key}>
            <legend>{labels.splitPart} {index + 1}</legend>
            <label>{labels.amount}<input aria-label={`${labels.splitPart} ${index + 1} · ${labels.amount}`} inputMode="decimal" onChange={(event) => updateSplit(split.key, { amount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" required value={split.amount} /></label>
            <label>{labels.category}<select aria-label={`${labels.splitPart} ${index + 1} · ${labels.category}`} onChange={(event) => updateSplit(split.key, { categoryId: event.target.value })} value={split.categoryId}><option value="">{labels.noCategory}</option>{availableCategories.map((category) => <option key={category.category_id} value={category.category_id}>{category.name}</option>)}</select></label>
            <label>{labels.splitMemo}<input onChange={(event) => updateSplit(split.key, { memo: event.target.value })} value={split.memo} /></label>
            <label className="checkbox-field"><input checked={split.isBaseCost} onChange={(event) => updateSplit(split.key, { isBaseCost: event.target.checked })} type="checkbox" />{labels.baseCost}</label>
            {tags.length ? <details className="split-tags"><summary>{labels.tags}</summary>{tags.map((tag) => <label className="checkbox-field" key={tag.tag_id}><input checked={split.tagIds.includes(tag.tag_id)} onChange={(event) => updateSplit(split.key, { tagIds: event.target.checked ? [...split.tagIds, tag.tag_id] : split.tagIds.filter((id) => id !== tag.tag_id) })} type="checkbox" />{tag.name}</label>)}</details> : null}
            <button className="ghost-button" disabled={draft.splits.length <= 2} onClick={() => setDraft((current) => ({ ...current, splits: current.splits.filter((item) => item.key !== split.key) }))} type="button">{labels.removeSplit}</button>
          </fieldset>
        ))}
      </div>
      <button className="secondary-button" disabled={draft.splits.length >= 100} onClick={() => setDraft((current) => ({ ...current, splits: [...current.splits, newSplitDraft()] }))} type="button">+ {labels.addSplit}</button>
    </section>
  );
}

function RecoveryForm({
  accounts,
  baseCurrency,
  draft,
  expense,
  labels,
  language,
  providers,
  setDraft,
  working,
  onCancel,
  onSubmit,
}: {
  accounts: Account[];
  baseCurrency: string;
  draft: RecoveryDraft;
  expense: Transaction | undefined;
  labels: Labels;
  language: Language;
  providers: Provider[];
  setDraft: (draft: RecoveryDraft) => void;
  working: boolean;
  onCancel: () => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form className="transaction-editor recovery-editor" onSubmit={onSubmit}>
      <div className="editor-title">
        <div>
          <h2>{draft.kind === "refund" ? labels.addRefund : labels.addReimbursement}</h2>
          <p>{labels.recoveryLead}</p>
        </div>
        <button className="ghost-button" onClick={onCancel} type="button">
          {labels.cancel}
        </button>
      </div>
      <p className="linked-event-note">
        <strong>{labels.linkedExpense}:</strong> {expense?.description ?? `#${draft.expenseId}`}
        {expense ? ` · ${formatMoney(expense.original_amount, expense.original_currency, language)}` : ""}
      </p>
      <div className="transaction-form-grid">
        <label>{labels.date}<input min={expense?.transaction_date} onChange={(event) => setDraft({ ...draft, transactionDate: event.target.value })} required type="date" value={draft.transactionDate} /></label>
        <label>{labels.postingDate}<input onChange={(event) => setDraft({ ...draft, postingDate: event.target.value })} required type="date" value={draft.postingDate} /></label>
        <label>{labels.account}<select onChange={(event) => setDraft({ ...draft, accountId: event.target.value })} required value={draft.accountId}><option value="">{labels.chooseAccount}</option>{accounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.name}</option>)}</select></label>
        <label className="description-field">{labels.description}<input autoFocus onChange={(event) => setDraft({ ...draft, description: event.target.value })} required value={draft.description} /></label>
        <label>{labels.amount}<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, amount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" required value={draft.amount} /></label>
        <label>{labels.currency}<input maxLength={3} minLength={3} onChange={(event) => setDraft({ ...draft, currency: event.target.value.toUpperCase() })} pattern="[A-Z]{3}" required value={draft.currency} /></label>
        <label>{labels.provider}<select onChange={(event) => setDraft({ ...draft, providerId: event.target.value })} value={draft.providerId}><option value="">{labels.noProvider}</option>{providers.map((provider) => <option key={provider.provider_id} value={provider.provider_id}>{provider.name}</option>)}</select></label>
      </div>
      {draft.currency !== baseCurrency ? <label className="conversion-field">{labels.convertedAmount} ({baseCurrency})<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, convertedAmount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" value={draft.convertedAmount} /><small>{labels.convertedHelp}</small></label> : null}
      <details className="optional-fields"><summary>{labels.optional}</summary><div className="optional-grid"><label>{labels.reference}<input onChange={(event) => setDraft({ ...draft, sourceReference: event.target.value })} value={draft.sourceReference} /></label><label>{labels.notes}<input onChange={(event) => setDraft({ ...draft, notes: event.target.value })} value={draft.notes} /></label></div></details>
      <div className="editor-actions"><button className="secondary-button" onClick={onCancel} type="button">{labels.cancel}</button><button className="primary-button" disabled={working} type="submit">{draft.kind === "refund" ? labels.addRefund : labels.addReimbursement}</button></div>
    </form>
  );
}

function TransferForm({
  accounts,
  baseCurrency,
  draft,
  editing,
  labels,
  setDraft,
  working,
  onCancel,
  onSubmit,
}: {
  accounts: Account[];
  baseCurrency: string;
  draft: TransferDraft;
  editing: boolean;
  labels: Labels;
  setDraft: React.Dispatch<React.SetStateAction<TransferDraft>>;
  working: boolean;
  onCancel: () => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const sourceAccount = accounts.find(
    (account) => account.account_id === Number(draft.sourceAccountId),
  );
  const destinationAccount = accounts.find(
    (account) => account.account_id === Number(draft.destinationAccountId),
  );
  const sameCurrency = Boolean(
    sourceAccount && destinationAccount && sourceAccount.currency === destinationAccount.currency,
  );
  return (
    <form className="transaction-editor transfer-editor" onSubmit={onSubmit}>
      <div className="editor-title">
        <div>
          <h2>{editing ? labels.editTransfer : labels.newTransfer}</h2>
          <p>{labels.transferLead}</p>
        </div>
        <button className="ghost-button" onClick={onCancel} type="button">
          {labels.cancel}
        </button>
      </div>
      {accounts.length < 2 ? <p className="attention-note">{labels.twoAccountsNeeded}</p> : null}
      <div className="transaction-form-grid transfer-form-grid">
        <label>
          {labels.fromAccount}
          <select
            onChange={(event) => {
              const nextSourceId = event.target.value;
              setDraft((current) => {
                const nextDestinationId =
                  nextSourceId === current.destinationAccountId
                    ? current.sourceAccountId
                    : current.destinationAccountId;
                const nextSource = accounts.find(
                  (account) => account.account_id === Number(nextSourceId),
                );
                const nextDestination = accounts.find(
                  (account) => account.account_id === Number(nextDestinationId),
                );
                return {
                  ...current,
                  sourceAccountId: nextSourceId,
                  destinationAccountId: nextDestinationId,
                  destinationAmount:
                    nextSource?.currency === nextDestination?.currency
                      ? current.sourceAmount
                      : current.destinationAmount,
                  sourceConvertedAmount: "",
                };
              });
            }}
            required
            value={draft.sourceAccountId}
          >
            <option value="">{labels.chooseAccount}</option>
            {accounts.map((account) => (
              <option
                key={account.account_id}
                value={account.account_id}
              >
                {account.name} · {account.currency}
              </option>
            ))}
          </select>
        </label>
        <label>
          {labels.toAccount}
          <select
            onChange={(event) => {
              const nextDestinationId = event.target.value;
              setDraft((current) => {
                const nextSourceId =
                  nextDestinationId === current.sourceAccountId
                    ? current.destinationAccountId
                    : current.sourceAccountId;
                const nextSource = accounts.find(
                  (account) => account.account_id === Number(nextSourceId),
                );
                const nextDestination = accounts.find(
                  (account) => account.account_id === Number(nextDestinationId),
                );
                return {
                  ...current,
                  sourceAccountId: nextSourceId,
                  destinationAccountId: nextDestinationId,
                  destinationAmount:
                    nextSource?.currency === nextDestination?.currency
                      ? current.sourceAmount
                      : current.destinationAmount,
                  destinationConvertedAmount: "",
                };
              });
            }}
            required
            value={draft.destinationAccountId}
          >
            <option value="">{labels.chooseAccount}</option>
            {accounts.map((account) => (
              <option
                key={account.account_id}
                value={account.account_id}
              >
                {account.name} · {account.currency}
              </option>
            ))}
          </select>
        </label>
        <label>
          {labels.date}
          <input
            onChange={(event) => setDraft({ ...draft, transactionDate: event.target.value })}
            required
            type="date"
            value={draft.transactionDate}
          />
        </label>
        <label>
          {labels.transferPurpose}
          <select
            onChange={(event) =>
              setDraft({ ...draft, purpose: event.target.value as TransferPurpose })
            }
            value={draft.purpose}
          >
            <option value="internal">{labels.purposeInternal}</option>
            <option value="savings">{labels.purposeSavings}</option>
            <option value="investment">{labels.purposeInvestment}</option>
            <option value="credit_card_payment">{labels.purposeCard}</option>
            <option value="debt_repayment">{labels.purposeDebt}</option>
          </select>
        </label>
        <label className="description-field">
          {labels.description}
          <input
            autoFocus
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
            required
            value={draft.description}
          />
        </label>
        <label>
          {labels.amount} {sourceAccount ? `(${sourceAccount.currency})` : ""}
          <input
            inputMode="decimal"
            onChange={(event) =>
              setDraft({
                ...draft,
                sourceAmount: event.target.value,
                destinationAmount: sameCurrency ? event.target.value : draft.destinationAmount,
              })
            }
            pattern="[0-9]+([.,][0-9]{1,4})?"
            required
            value={draft.sourceAmount}
          />
        </label>
        <label>
          {labels.receivedAmount} {destinationAccount ? `(${destinationAccount.currency})` : ""}
          <input
            inputMode="decimal"
            onChange={(event) => setDraft({ ...draft, destinationAmount: event.target.value })}
            pattern="[0-9]+([.,][0-9]{1,4})?"
            readOnly={sameCurrency}
            required
            value={draft.destinationAmount}
          />
        </label>
        <label>
          {labels.sourcePostingDate}
          <input
            onChange={(event) =>
              setDraft({ ...draft, sourcePostingDate: event.target.value })
            }
            required
            type="date"
            value={draft.sourcePostingDate}
          />
        </label>
        <label>
          {labels.destinationPostingDate}
          <input
            onChange={(event) =>
              setDraft({ ...draft, destinationPostingDate: event.target.value })
            }
            required
            type="date"
            value={draft.destinationPostingDate}
          />
        </label>
      </div>
      {sourceAccount?.currency !== baseCurrency ? (
        <label className="conversion-field">
          {labels.convertedAmount} · {labels.fromAccount} ({baseCurrency})
          <input
            inputMode="decimal"
            onChange={(event) =>
              setDraft({ ...draft, sourceConvertedAmount: event.target.value })
            }
            pattern="[0-9]+([.,][0-9]{1,4})?"
            value={draft.sourceConvertedAmount}
          />
        </label>
      ) : null}
      {destinationAccount?.currency !== baseCurrency ? (
        <label className="conversion-field">
          {labels.convertedAmount} · {labels.toAccount} ({baseCurrency})
          <input
            inputMode="decimal"
            onChange={(event) =>
              setDraft({ ...draft, destinationConvertedAmount: event.target.value })
            }
            pattern="[0-9]+([.,][0-9]{1,4})?"
            value={draft.destinationConvertedAmount}
          />
          <small>{labels.transferValueHelp}</small>
        </label>
      ) : null}
      <details className="optional-fields">
        <summary>{labels.optional}</summary>
        <div className="optional-grid">
          <label>
            {labels.reference}
            <input
              onChange={(event) =>
                setDraft({ ...draft, sourceReference: event.target.value })
              }
              value={draft.sourceReference}
            />
          </label>
          <label>
            {labels.notes}
            <input
              onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
              value={draft.notes}
            />
          </label>
        </div>
      </details>
      <div className="editor-actions">
        <button className="secondary-button" onClick={onCancel} type="button">
          {labels.cancel}
        </button>
        <button
          className="primary-button"
          disabled={working || accounts.length < 2}
          type="submit"
        >
          {editing ? labels.update : labels.saveTransfer}
        </button>
      </div>
    </form>
  );
}

function InlineCreate({ label, name, labels, onChange, onCreate }: { label: string; name: string; labels: Labels; onChange: (value: string) => void; onCreate: () => Promise<void> }) {
  return <div className="inline-create"><label>{label} · {labels.name}<input onChange={(event) => onChange(event.target.value)} required value={name} /></label><button className="secondary-button" disabled={!name.trim()} onClick={() => void onCreate()} type="button">{labels.add}</button></div>;
}

function EntryList({ accounts, categories, environment, labels, language, providers, transactions, transfers, onEdit, onEditTransfer, onRecovery, onReload, onError }: { accounts: Account[]; categories: Category[]; environment: Environment; labels: Labels; language: Language; providers: Provider[]; transactions: Transaction[]; transfers: Transfer[]; onEdit: (transaction: Transaction) => void; onEditTransfer: (transfer: Transfer) => void; onRecovery: (transaction: Transaction, kind: RecoveryKind) => void; onReload: () => void; onError: (message: string) => void }) {
  const accountNames = new Map(accounts.map((item) => [item.account_id, item.name]));
  const categoryNames = new Map(categories.map((item) => [item.category_id, item.name]));
  const providerNames = new Map(providers.map((item) => [item.provider_id, item.name]));
  const entries = [
    ...transactions.map((transaction) => ({
      type: "transaction" as const,
      id: transaction.transaction_id,
      date: transaction.transaction_date,
      transaction,
    })),
    ...transfers.map((transfer) => ({
      type: "transfer" as const,
      id: transfer.transfer_link_id,
      date: transfer.transaction_date,
      transfer,
    })),
  ].sort((left, right) => right.date.localeCompare(left.date) || right.id - left.id);
  return (
    <div className="transaction-list">
      {entries.map((entry) => {
        if (entry.type === "transaction") {
          const transaction = entry.transaction;
          const recovery = transaction.transaction_kind === "refund" || transaction.transaction_kind === "reimbursement";
          const archiveRequest = recovery ? setRecoveryArchived : setTransactionArchived;
          const secondaryBase = recovery
            ? `${transaction.transaction_kind === "refund" ? labels.refund : labels.reimbursement} · ${labels.linkedExpense} #${transaction.linked_expense_id}`
            : providerNames.get(transaction.provider_id ?? -1) ?? categoryNames.get(transaction.category_id ?? -1) ?? accountNames.get(transaction.account_id);
          const secondary = transaction.is_split
            ? `${secondaryBase} · ${transaction.splits.length} ${labels.parts}`
            : secondaryBase;
          return <article className={`transaction-row ${transaction.status}`} key={`transaction-${transaction.transaction_id}`}><time dateTime={transaction.transaction_date}>{formatDate(transaction.transaction_date, language)}</time><div className="transaction-main"><strong>{transaction.description}</strong><span>{secondary}</span>{transaction.fx_rate_status === "missing" ? <em>{labels.missingFx}</em> : null}</div><div className={`transaction-value ${transaction.transaction_kind}`}><strong>{transaction.transaction_kind === "expense" ? "−" : "+"}{formatMoney(transaction.original_amount, transaction.original_currency, language)}</strong>{transaction.converted_amount && transaction.original_currency !== transaction.base_currency ? <span>{formatMoney(transaction.converted_amount, transaction.base_currency, language)}</span> : null}</div><div className="row-actions">{transaction.transaction_kind === "expense" && transaction.status === "active" ? <><button className="ghost-button" onClick={() => onRecovery(transaction, "refund")} type="button">{labels.refund}</button><button className="ghost-button" onClick={() => onRecovery(transaction, "reimbursement")} type="button">{labels.reimbursement}</button></> : null}<button className="ghost-button" disabled={transaction.status === "archived" || recovery} onClick={() => onEdit(transaction)} type="button">{labels.edit}</button><button className="ghost-button" onClick={() => void archiveRequest(environment, transaction.transaction_id, transaction.status === "active").then(onReload).catch((reason) => onError(reason instanceof Error ? reason.message : "Transaction request failed."))} type="button">{transaction.status === "active" ? labels.archive : labels.restore}</button></div></article>;
        }
        const transfer = entry.transfer;
        const missingFx = transfer.source_fx_rate_status === "missing" || transfer.destination_fx_rate_status === "missing";
        return <article className={`transaction-row transfer-row ${transfer.status}`} key={`transfer-${transfer.transfer_link_id}`}><time dateTime={transfer.transaction_date}>{formatDate(transfer.transaction_date, language)}</time><div className="transaction-main"><strong>{transfer.description}</strong><span>{accountNames.get(transfer.source_account_id)} → {accountNames.get(transfer.destination_account_id)} · {purposeLabel(transfer.purpose, labels)}</span>{missingFx ? <em>{labels.missingFx}</em> : null}</div><div className="transaction-value transfer"><strong>{formatMoney(transfer.source_amount, transfer.source_currency, language)} → {formatMoney(transfer.destination_amount, transfer.destination_currency, language)}</strong><span>{labels.transfer}</span></div><div className="row-actions"><button className="ghost-button" disabled={transfer.status === "archived"} onClick={() => onEditTransfer(transfer)} type="button">{labels.edit}</button><button className="ghost-button" onClick={() => void setTransferArchived(environment, transfer.transfer_link_id, transfer.status === "active").then(onReload).catch((reason) => onError(reason instanceof Error ? reason.message : "Transfer request failed."))} type="button">{transfer.status === "active" ? labels.archive : labels.restore}</button></div></article>;
      })}
    </div>
  );
}

function emptyDraft(baseCurrency: string): Draft {
  const today = localDate(new Date());
  return { accountId: "", providerId: "", kind: "expense", transactionDate: today, postingDate: today, description: "", amount: "", currency: baseCurrency, convertedAmount: "", categoryId: "", tagIds: [], isBaseCost: false, sourceReference: "", notes: "", splitMode: false, splits: initialSplits() };
}

function initialSplits(): SplitDraft[] {
  return [newSplitDraft(), newSplitDraft()];
}

function newSplitDraft(): SplitDraft {
  return {
    key: crypto.randomUUID(),
    amount: "",
    categoryId: "",
    tagIds: [],
    isBaseCost: false,
    memo: "",
  };
}

function emptyTransferDraft(): TransferDraft {
  const today = localDate(new Date());
  return {
    sourceAccountId: "",
    destinationAccountId: "",
    purpose: "internal",
    transactionDate: today,
    sourcePostingDate: today,
    destinationPostingDate: today,
    description: "",
    sourceAmount: "",
    destinationAmount: "",
    sourceConvertedAmount: "",
    destinationConvertedAmount: "",
    sourceReference: "",
    notes: "",
  };
}

function purposeLabel(purpose: TransferPurpose, labels: Labels): string {
  return {
    internal: labels.purposeInternal,
    savings: labels.purposeSavings,
    investment: labels.purposeInvestment,
    credit_card_payment: labels.purposeCard,
    debt_repayment: labels.purposeDebt,
  }[purpose];
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
