import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
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
  getSharingParties,
  getTags,
  getTransfers,
  getTransactions,
  updateTransfer,
  updateTransaction,
  type Account,
  type Category,
  type Environment,
  type Language,
  type LedgerSummary,
  type Provider,
  type RecoveryKind,
  type SharingParty,
  type Tag,
  type Transfer,
  type TransferInput,
  type Transaction,
  type TransactionInput,
} from "./api";
import { copy } from "./i18n/transactions";
import {
  type RecoveryDraft,
  type Filters,
  shareAllocationPayload,
  emptyDraft,
  initialSplits,
  emptyTransferDraft,
  currentMonth,
  localDate,
  numberOrNull,
  normalizeDecimalInput,
} from "./transactions/model";
import { SummaryStrip, TransactionForm, RecoveryForm } from "./transactions/TransactionForm";
import { TransferForm } from "./transactions/TransferForm";
import { EntryList } from "./transactions/EntryList";

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
  currentUserId,
}: {
  environment: Environment;
  language: Language;
  baseCurrency: string;
  onNavigateAccounts: () => void;
  initialFilters?: TransactionInitialFilters | null;
  currentUserId?: number;
}) {
  const labels = copy[language];
  const period = useMemo(() => currentMonth(), []);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [sharingParties, setSharingParties] = useState<SharingParty[]>([]);
  // The signed-in member's own party is listed first and preselected when sharing.
  const orderedParties = useMemo(
    () =>
      [...sharingParties].sort(
        (first, second) =>
          Number(second.user_id === currentUserId) - Number(first.user_id === currentUserId),
      ),
    [sharingParties, currentUserId],
  );
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
      getSharingParties(environment),
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
      .then(([accountPage, categoryPage, providerPage, tagPage, partyPage, transactionPage, transferPage, totals]) => {
        if (!active) return;
        setAccounts(accountPage.items);
        setCategories(categoryPage.items);
        setProviders(providerPage.items);
        setTags(tagPage.items);
        setSharingParties(partyPage.items);
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
      sharingAllocations: transaction.sharing_allocations.map((allocation) => ({
        partyId: String(allocation.sharing_party_id),
        percentage: allocation.percentage,
      })),
      splitMode: transaction.is_split,
      splits: transaction.is_split
        ? transaction.splits.map((split) => ({
            key: String(split.transaction_split_id),
            amount: split.original_amount,
            categoryId: String(split.category_id ?? ""),
            tagIds: split.tag_ids,
            isBaseCost: split.is_base_cost,
            memo: split.memo ?? "",
            sharingAllocations: split.sharing_allocations.map((allocation) => ({
              partyId: String(allocation.sharing_party_id),
              percentage: allocation.percentage,
            })),
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
      sharing_allocations: shareAllocationPayload(draft.sharingAllocations),
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
        sharing_allocations: shareAllocationPayload(split.sharingAllocations),
      }));
      payload.category_id = null;
      payload.tag_ids = [];
      payload.is_base_cost = false;
      payload.sharing_allocations = [];
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
          sharingParties={orderedParties}
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




















