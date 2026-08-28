import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  createAccount,
  createAccountSnapshot,
  createCategory,
  createProvider,
  createSharingParty,
  createTag,
  getAccounts,
  getAccountSnapshots,
  getCategories,
  getProviders,
  getSharingParties,
  getTags,
  setAccountArchived,
  setCategoryArchived,
  setProviderArchived,
  setSharingPartyArchived,
  setTagArchived,
  type Account,
  type AccountSnapshot,
  type AccountType,
  type Category,
  type Environment,
  type Language,
  type Provider,
  type SharingParty,
  type Tag,
} from "./api";

const copy = {
  sv: {
    eyebrow: "Sprint 2 · Ledger",
    accountsTitle: "Konton",
    masterDataTitle: "Kategorier och register",
    masterDataLead:
      "Återanvändbara kategorier, providers, taggar och delningsparter hanteras här – utanför det dagliga transaktionsflödet.",
    lead: "Öppningssaldo är en startpunkt för saldot och bokförs aldrig som inkomst.",
    showArchived: "Visa arkiverade",
    accounts: "Konton",
    accountName: "Kontonamn",
    accountType: "Kontotyp",
    openingBalance: "Öppningssaldo",
    effectiveDate: "Gäller från",
    currency: "Valuta",
    addAccount: "Lägg till konto",
    noAccounts: "Inga konton ännu.",
    currentValue: "Aktuellt värde",
    reconciledBalance: "Avstämt saldo",
    registerValue: "Registrera aktuellt värde",
    registerBalance: "Stäm av saldo",
    balanceDate: "Datum",
    amount: "Belopp",
    noteOptional: "Anteckning (valfritt)",
    saveValue: "Spara värde",
    saveBalance: "Spara saldo",
    openingBalanceLabel: "Öppningssaldo",
    calculatedBalance: "Beräknat saldo",
    difference: "Avvikelse",
    unavailable: "Ej tillgängligt",
    valueHistory: "Värdehistorik",
    balanceHistory: "Saldohistorik",
    noSnapshots: "Inga senare saldon har registrerats ännu.",
    snapshotHelp:
      "Varje datum sparas som en historisk observation. Öppningssaldot och transaktionerna ändras inte.",
    categories: "Kategorier",
    categoryName: "Kategorinamn",
    categoryKind: "Typ",
    parent: "Överordnad kategori",
    noParent: "Ingen – toppnivå",
    expense: "Utgift",
    income: "Inkomst",
    addCategory: "Lägg till kategori",
    providers: "Providers",
    providerName: "Provider-namn",
    website: "Webbplats (valfritt)",
    addProvider: "Lägg till provider",
    tags: "Taggar",
    tagName: "Taggnamn",
    color: "Färg",
    addTag: "Lägg till tagg",
    parties: "Delningsparter",
    partyName: "Namn",
    isSelf: "Representerar mig",
    addParty: "Lägg till part",
    archive: "Arkivera",
    restore: "Återställ",
    active: "Aktiv",
    archived: "Arkiverad",
    empty: "Inga poster ännu.",
    loading: "Läser Ledger-data…",
  },
  en: {
    eyebrow: "Sprint 2 · Ledger",
    accountsTitle: "Accounts",
    masterDataTitle: "Categories and registers",
    masterDataLead:
      "Reusable categories, providers, tags, and sharing parties are managed here, outside the daily transaction flow.",
    lead: "An opening balance is a balance starting point and is never recorded as income.",
    showArchived: "Show archived",
    accounts: "Accounts",
    accountName: "Account name",
    accountType: "Account type",
    openingBalance: "Opening balance",
    effectiveDate: "Effective date",
    currency: "Currency",
    addAccount: "Add account",
    noAccounts: "No accounts yet.",
    currentValue: "Current value",
    reconciledBalance: "Reconciled balance",
    registerValue: "Record current value",
    registerBalance: "Reconcile balance",
    balanceDate: "Date",
    amount: "Amount",
    noteOptional: "Note (optional)",
    saveValue: "Save value",
    saveBalance: "Save balance",
    openingBalanceLabel: "Opening balance",
    calculatedBalance: "Calculated balance",
    difference: "Difference",
    unavailable: "Unavailable",
    valueHistory: "Value history",
    balanceHistory: "Balance history",
    noSnapshots: "No later balances have been recorded yet.",
    snapshotHelp:
      "Each date is preserved as a historical observation. The opening balance and transactions are unchanged.",
    categories: "Categories",
    categoryName: "Category name",
    categoryKind: "Type",
    parent: "Parent category",
    noParent: "None – top level",
    expense: "Expense",
    income: "Income",
    addCategory: "Add category",
    providers: "Providers",
    providerName: "Provider name",
    website: "Website (optional)",
    addProvider: "Add provider",
    tags: "Tags",
    tagName: "Tag name",
    color: "Color",
    addTag: "Add tag",
    parties: "Sharing parties",
    partyName: "Name",
    isSelf: "Represents me",
    addParty: "Add party",
    archive: "Archive",
    restore: "Restore",
    active: "Active",
    archived: "Archived",
    empty: "No records yet.",
    loading: "Loading ledger data…",
  },
} as const;

const accountTypes: AccountType[] = [
  "current",
  "savings",
  "credit_card",
  "investment",
  "loan_debt",
  "value_based",
  "cash",
  "other",
];

type LedgerData = {
  accounts: Account[];
  categories: Category[];
  providers: Provider[];
  tags: Tag[];
  parties: SharingParty[];
};

const emptyData: LedgerData = {
  accounts: [],
  categories: [],
  providers: [],
  tags: [],
  parties: [],
};

export function LedgerWorkspace({
  environment,
  language,
  baseCurrency,
  view,
}: {
  environment: Environment;
  language: Language;
  baseCurrency: string;
  view: "accounts" | "master-data";
}) {
  const labels = copy[language];
  const [data, setData] = useState<LedgerData>(emptyData);
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all([
      getAccounts(environment, showArchived),
      getCategories(environment, showArchived),
      getProviders(environment, showArchived),
      getTags(environment, showArchived),
      getSharingParties(environment, showArchived),
    ])
      .then(([accounts, categories, providers, tags, parties]) => {
        if (!active) return;
        setError(null);
        setData({
          accounts: accounts.items,
          categories: categories.items,
          providers: providers.items,
          tags: tags.items,
          parties: parties.items,
        });
      })
      .catch((reason) => {
        if (active) setError(reason instanceof Error ? reason.message : "Ledger request failed.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [environment, reloadKey, showArchived]);

  const mutate = async (operation: () => Promise<unknown>) => {
    setError(null);
    try {
      await operation();
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ledger request failed.");
      throw reason;
    }
  };

  return (
    <section className="ledger-section" id={view === "accounts" ? "accounts" : "master-data"}>
      <div className="section-heading ledger-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1>{view === "accounts" ? labels.accountsTitle : labels.masterDataTitle}</h1>
          <p>{view === "accounts" ? labels.lead : labels.masterDataLead}</p>
        </div>
        <label className="archive-toggle">
          <input
            checked={showArchived}
            onChange={(event) => setShowArchived(event.target.checked)}
            type="checkbox"
          />
          {labels.showArchived}
        </label>
      </div>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {loading ? <p className="quiet-copy">{labels.loading}</p> : null}

      {view === "accounts" ? (
        <AccountPanel
          accounts={data.accounts}
          baseCurrency={baseCurrency}
          environment={environment}
          labels={labels}
          mutate={mutate}
        />
      ) : (
        <div className="master-data-grid">
          <CategoryPanel
            categories={data.categories}
            environment={environment}
            labels={labels}
            mutate={mutate}
          />
          <ProviderPanel
            providers={data.providers}
            environment={environment}
            labels={labels}
            mutate={mutate}
          />
          <TagPanel
            tags={data.tags}
            environment={environment}
            labels={labels}
            mutate={mutate}
          />
          <PartyPanel
            parties={data.parties}
            environment={environment}
            labels={labels}
            mutate={mutate}
          />
        </div>
      )}
    </section>
  );
}

type Labels = (typeof copy)[Language];
type Mutate = (operation: () => Promise<unknown>) => Promise<void>;

function AccountPanel({
  accounts,
  environment,
  baseCurrency,
  labels,
  mutate,
}: {
  accounts: Account[];
  environment: Environment;
  baseCurrency: string;
  labels: Labels;
  mutate: Mutate;
}) {
  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("current");
  const [openingBalance, setOpeningBalance] = useState("0");
  const [openingDate, setOpeningDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [currency, setCurrency] = useState(baseCurrency);
  const [working, setWorking] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    void mutate(() =>
      createAccount(environment, {
        name,
        account_type: accountType,
        opening_balance: openingBalance,
        opening_balance_date: openingDate,
        currency,
      }),
    )
      .then(() => {
        setName("");
        setOpeningBalance("0");
      })
      .catch(() => undefined)
      .finally(() => setWorking(false));
  };

  return (
    <div className="ledger-panel account-panel">
      <div className="ledger-panel-title">
        <h3>{labels.accounts}</h3>
        <span>{accounts.length}</span>
      </div>
      <form className="inline-resource-form account-form" onSubmit={submit}>
        <label>
          {labels.accountName}
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          {labels.accountType}
          <select value={accountType} onChange={(event) => setAccountType(event.target.value as AccountType)}>
            {accountTypes.map((type) => (
              <option key={type} value={type}>
                {accountTypeLabel(type, languageFrom(labels))}
              </option>
            ))}
          </select>
        </label>
        <label>
          {labels.openingBalance}
          <input
            inputMode="decimal"
            required
            value={openingBalance}
            onChange={(event) => setOpeningBalance(event.target.value)}
          />
        </label>
        <label>
          {labels.effectiveDate}
          <input
            required
            type="date"
            value={openingDate}
            onChange={(event) => setOpeningDate(event.target.value)}
          />
        </label>
        <label>
          {labels.currency}
          <input
            maxLength={3}
            required
            value={currency}
            onChange={(event) => setCurrency(event.target.value.toUpperCase())}
          />
        </label>
        <button className="primary-button" disabled={working} type="submit">
          {labels.addAccount}
        </button>
      </form>
      {accounts.length === 0 ? <p className="resource-empty">{labels.noAccounts}</p> : null}
      <div className="account-list">
        {accounts.map((account) => (
          <AccountRow
            account={account}
            environment={environment}
            key={account.account_id}
            labels={labels}
            mutate={mutate}
          />
        ))}
      </div>
    </div>
  );
}

function AccountRow({
  account,
  environment,
  labels,
  mutate,
}: {
  account: Account;
  environment: Environment;
  labels: Labels;
  mutate: Mutate;
}) {
  const language = languageFrom(labels);
  const isValuation = account.account_type === "investment" || account.account_type === "value_based";
  const [snapshots, setSnapshots] = useState<AccountSnapshot[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [working, setWorking] = useState(false);

  const loadSnapshots = () =>
    getAccountSnapshots(environment, account.account_id).then(setSnapshots);

  useEffect(() => {
    let active = true;
    getAccountSnapshots(environment, account.account_id)
      .then((items) => {
        if (active) setSnapshots(items);
      })
      .catch(() => {
        if (active) setSnapshots([]);
      });
    return () => {
      active = false;
    };
  }, [account.account_id, environment]);

  const latest = snapshots[0];
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    void mutate(() =>
      createAccountSnapshot(environment, account.account_id, {
        valuation_date: date,
        reported_balance: amount,
        notes: notes || null,
      }),
    )
      .then(() => loadSnapshots())
      .then(() => {
        setAmount("");
        setNotes("");
      })
      .catch(() => undefined)
      .finally(() => setWorking(false));
  };

  return (
    <article className={`account-card ${account.status}`}>
      <div className="resource-row account-summary">
        <div>
          <strong>{account.name}</strong>
          <span>{accountTypeLabel(account.account_type, language)}</span>
        </div>
        <div className="account-amount">
          <strong>
            {formatMoney(
              latest?.reported_balance ?? account.opening_balance,
              account.currency,
              language,
            )}
          </strong>
          <span>
            {latest
              ? `${isValuation ? labels.currentValue : labels.reconciledBalance} · ${latest.valuation_date}`
              : `${labels.openingBalanceLabel} · ${account.opening_balance_date}`}
          </span>
        </div>
        {account.status === "active" ? (
          <button
            aria-expanded={expanded}
            className="secondary-button snapshot-toggle"
            onClick={() => setExpanded((value) => !value)}
            type="button"
          >
            {isValuation ? labels.registerValue : labels.registerBalance}
          </button>
        ) : null}
        <LifecycleButton
          archived={account.status === "archived"}
          labels={labels}
          onClick={() =>
            mutate(() =>
              setAccountArchived(environment, account.account_id, account.status === "active"),
            )
          }
        />
      </div>
      {expanded ? (
        <div className="snapshot-workspace">
          <form className="snapshot-form" onSubmit={submit}>
            <p>{labels.snapshotHelp}</p>
            <label>
              {labels.balanceDate}
              <input required type="date" value={date} onChange={(event) => setDate(event.target.value)} />
            </label>
            <label>
              {labels.amount} ({account.currency})
              <input
                inputMode="decimal"
                required
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
              />
            </label>
            <label>
              {labels.noteOptional}
              <input value={notes} onChange={(event) => setNotes(event.target.value)} />
            </label>
            <button className="primary-button" disabled={working} type="submit">
              {isValuation ? labels.saveValue : labels.saveBalance}
            </button>
          </form>
          <SnapshotHistory
            account={account}
            isValuation={isValuation}
            labels={labels}
            snapshots={snapshots}
          />
        </div>
      ) : null}
    </article>
  );
}

function SnapshotHistory({
  account,
  isValuation,
  labels,
  snapshots,
}: {
  account: Account;
  isValuation: boolean;
  labels: Labels;
  snapshots: AccountSnapshot[];
}) {
  const language = languageFrom(labels);
  const chronological = [...snapshots].reverse();
  const values = chronological.map((item) => Number(item.reported_balance));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const points = chronological
    .map((item, index) => {
      const x = chronological.length === 1 ? 50 : (index / (chronological.length - 1)) * 100;
      const y = max === min ? 24 : 44 - ((Number(item.reported_balance) - min) / (max - min)) * 40;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="snapshot-history">
      <h4>{isValuation ? labels.valueHistory : labels.balanceHistory}</h4>
      {snapshots.length === 0 ? <p className="resource-empty">{labels.noSnapshots}</p> : null}
      {snapshots.length > 0 ? (
        <>
          {snapshots.length > 1 ? (
            <svg
              aria-hidden="true"
              className="snapshot-chart"
              preserveAspectRatio="none"
              viewBox="0 0 100 48"
            >
              <polyline fill="none" points={points} vectorEffect="non-scaling-stroke" />
            </svg>
          ) : null}
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{labels.balanceDate}</th>
                  <th>{isValuation ? labels.currentValue : labels.reconciledBalance}</th>
                  {!isValuation ? <th>{labels.calculatedBalance}</th> : null}
                  {!isValuation ? <th>{labels.difference}</th> : null}
                </tr>
              </thead>
              <tbody>
                {snapshots.map((snapshot) => (
                  <tr key={snapshot.account_snapshot_id}>
                    <td>{snapshot.valuation_date}</td>
                    <td>{formatMoney(snapshot.reported_balance, account.currency, language)}</td>
                    {!isValuation ? (
                      <td>
                        {snapshot.calculated_balance === null
                          ? labels.unavailable
                          : formatMoney(snapshot.calculated_balance, account.currency, language)}
                      </td>
                    ) : null}
                    {!isValuation ? (
                      <td>
                        {snapshot.difference === null
                          ? labels.unavailable
                          : formatMoney(snapshot.difference, account.currency, language)}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}

function CategoryPanel({
  categories,
  environment,
  labels,
  mutate,
}: {
  categories: Category[];
  environment: Environment;
  labels: Labels;
  mutate: Mutate;
}) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"expense" | "income">("expense");
  const [parentId, setParentId] = useState("");
  const ordered = useMemo(() => orderCategories(categories), [categories]);

  return (
    <ResourcePanel title={labels.categories} count={categories.length}>
      <form
        className="stacked-resource-form"
        onSubmit={(event) => {
          event.preventDefault();
          void mutate(() =>
            createCategory(environment, {
              name,
              category_kind: kind,
              parent_category_id: parentId ? Number(parentId) : null,
            }),
          )
            .then(() => setName(""))
            .catch(() => undefined);
        }}
      >
        <label>
          {labels.categoryName}
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <div className="split-fields">
          <label>
            {labels.categoryKind}
            <select value={kind} onChange={(event) => setKind(event.target.value as typeof kind)}>
              <option value="expense">{labels.expense}</option>
              <option value="income">{labels.income}</option>
            </select>
          </label>
          <label>
            {labels.parent}
            <select value={parentId} onChange={(event) => setParentId(event.target.value)}>
              <option value="">{labels.noParent}</option>
              {ordered
                .filter(({ category }) => category.status === "active")
                .map(({ category, depth }) => (
                  <option key={category.category_id} value={category.category_id}>
                    {"— ".repeat(depth)}{category.name}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <button className="secondary-button" type="submit">
          {labels.addCategory}
        </button>
      </form>
      <ResourceList
        empty={labels.empty}
        items={ordered.map(({ category, depth }) => ({
          id: category.category_id,
          label: `${"— ".repeat(depth)}${category.name}`,
          meta: category.category_kind === "expense" ? labels.expense : labels.income,
          archived: category.status === "archived",
          onLifecycle: () =>
            mutate(() =>
              setCategoryArchived(
                environment,
                category.category_id,
                category.status === "active",
              ),
            ),
        }))}
        labels={labels}
      />
    </ResourcePanel>
  );
}

function ProviderPanel({
  providers,
  environment,
  labels,
  mutate,
}: {
  providers: Provider[];
  environment: Environment;
  labels: Labels;
  mutate: Mutate;
}) {
  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  return (
    <ResourcePanel title={labels.providers} count={providers.length}>
      <form
        className="stacked-resource-form"
        onSubmit={(event) => {
          event.preventDefault();
          void mutate(() => createProvider(environment, { name, website: website || undefined }))
            .then(() => {
              setName("");
              setWebsite("");
            })
            .catch(() => undefined);
        }}
      >
        <label>
          {labels.providerName}
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          {labels.website}
          <input type="url" value={website} onChange={(event) => setWebsite(event.target.value)} />
        </label>
        <button className="secondary-button" type="submit">
          {labels.addProvider}
        </button>
      </form>
      <ResourceList
        empty={labels.empty}
        items={providers.map((provider) => ({
          id: provider.provider_id,
          label: provider.name,
          meta: provider.website ?? "—",
          archived: provider.status === "archived",
          onLifecycle: () =>
            mutate(() =>
              setProviderArchived(
                environment,
                provider.provider_id,
                provider.status === "active",
              ),
            ),
        }))}
        labels={labels}
      />
    </ResourcePanel>
  );
}

function TagPanel({
  tags,
  environment,
  labels,
  mutate,
}: {
  tags: Tag[];
  environment: Environment;
  labels: Labels;
  mutate: Mutate;
}) {
  const [name, setName] = useState("");
  const [color, setColor] = useState("#4A67D6");
  return (
    <ResourcePanel title={labels.tags} count={tags.length}>
      <form
        className="stacked-resource-form"
        onSubmit={(event) => {
          event.preventDefault();
          void mutate(() => createTag(environment, { name, color }))
            .then(() => setName(""))
            .catch(() => undefined);
        }}
      >
        <div className="split-fields tag-fields">
          <label>
            {labels.tagName}
            <input required value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            {labels.color}
            <input type="color" value={color} onChange={(event) => setColor(event.target.value)} />
          </label>
        </div>
        <button className="secondary-button" type="submit">
          {labels.addTag}
        </button>
      </form>
      <ResourceList
        empty={labels.empty}
        items={tags.map((tag) => ({
          id: tag.tag_id,
          label: tag.name,
          meta: tag.color ?? "—",
          color: tag.color,
          archived: tag.status === "archived",
          onLifecycle: () =>
            mutate(() => setTagArchived(environment, tag.tag_id, tag.status === "active")),
        }))}
        labels={labels}
      />
    </ResourcePanel>
  );
}

function PartyPanel({
  parties,
  environment,
  labels,
  mutate,
}: {
  parties: SharingParty[];
  environment: Environment;
  labels: Labels;
  mutate: Mutate;
}) {
  const [name, setName] = useState("");
  const [isSelf, setIsSelf] = useState(false);
  return (
    <ResourcePanel title={labels.parties} count={parties.length}>
      <form
        className="stacked-resource-form"
        onSubmit={(event) => {
          event.preventDefault();
          void mutate(() => createSharingParty(environment, { name, is_self: isSelf }))
            .then(() => {
              setName("");
              setIsSelf(false);
            })
            .catch(() => undefined);
        }}
      >
        <label>
          {labels.partyName}
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="checkbox-field">
          <input
            checked={isSelf}
            onChange={(event) => setIsSelf(event.target.checked)}
            type="checkbox"
          />
          {labels.isSelf}
        </label>
        <button className="secondary-button" type="submit">
          {labels.addParty}
        </button>
      </form>
      <ResourceList
        empty={labels.empty}
        items={parties.map((party) => ({
          id: party.sharing_party_id,
          label: party.name,
          meta: party.is_self ? labels.isSelf : "—",
          archived: party.status === "archived",
          onLifecycle: () =>
            mutate(() =>
              setSharingPartyArchived(
                environment,
                party.sharing_party_id,
                party.status === "active",
              ),
            ),
        }))}
        labels={labels}
      />
    </ResourcePanel>
  );
}

function ResourcePanel({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="ledger-panel">
      <div className="ledger-panel-title">
        <h3>{title}</h3>
        <span>{count}</span>
      </div>
      {children}
    </div>
  );
}

function ResourceList({
  items,
  empty,
  labels,
}: {
  items: Array<{
    id: number;
    label: string;
    meta: string;
    color?: string | null;
    archived: boolean;
    onLifecycle: () => Promise<void>;
  }>;
  empty: string;
  labels: Labels;
}) {
  if (items.length === 0) return <p className="resource-empty">{empty}</p>;
  return (
    <div className="resource-list">
      {items.map((item) => (
        <div className={`resource-row compact ${item.archived ? "archived" : "active"}`} key={item.id}>
          <div>
            <strong>
              {item.color ? (
                <span className="tag-dot" style={{ backgroundColor: item.color }} aria-hidden="true" />
              ) : null}
              {item.label}
            </strong>
            <span>{item.meta}</span>
          </div>
          <LifecycleButton
            archived={item.archived}
            labels={labels}
            onClick={item.onLifecycle}
          />
        </div>
      ))}
    </div>
  );
}

function LifecycleButton({
  archived,
  labels,
  onClick,
}: {
  archived: boolean;
  labels: Labels;
  onClick: () => Promise<void>;
}) {
  const [working, setWorking] = useState(false);
  return (
    <button
      className="ghost-button"
      disabled={working}
      onClick={() => {
        setWorking(true);
        void onClick()
          .catch(() => undefined)
          .finally(() => setWorking(false));
      }}
      type="button"
    >
      {archived ? labels.restore : labels.archive}
    </button>
  );
}

function orderCategories(categories: Category[]): Array<{ category: Category; depth: number }> {
  const byParent = new Map<number | null, Category[]>();
  for (const category of categories) {
    const siblings = byParent.get(category.parent_category_id) ?? [];
    siblings.push(category);
    byParent.set(category.parent_category_id, siblings);
  }
  for (const siblings of byParent.values()) {
    siblings.sort((left, right) => left.name.localeCompare(right.name));
  }
  const result: Array<{ category: Category; depth: number }> = [];
  const visited = new Set<number>();
  const visit = (parentId: number | null, depth: number) => {
    for (const category of byParent.get(parentId) ?? []) {
      if (visited.has(category.category_id)) continue;
      visited.add(category.category_id);
      result.push({ category, depth });
      visit(category.category_id, depth + 1);
    }
  };
  visit(null, 0);
  for (const category of categories) {
    if (!visited.has(category.category_id)) result.push({ category, depth: 0 });
  }
  return result;
}

function formatMoney(value: string, currency: string, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-US", {
    style: "currency",
    currency,
  }).format(Number(value));
}

function languageFrom(labels: Labels): Language {
  return labels === copy.sv ? "sv" : "en";
}

function accountTypeLabel(type: AccountType, language: Language): string {
  const names: Record<Language, Record<AccountType, string>> = {
    sv: {
      current: "Transaktionskonto",
      savings: "Sparkonto",
      credit_card: "Kreditkort",
      investment: "Investeringskonto",
      loan_debt: "Lån eller skuld",
      value_based: "Värdebaserat konto",
      cash: "Kontanter",
      other: "Annat",
    },
    en: {
      current: "Current account",
      savings: "Savings account",
      credit_card: "Credit card",
      investment: "Investment account",
      loan_debt: "Loan or debt",
      value_based: "Value-based account",
      cash: "Cash",
      other: "Other",
    },
  };
  return names[language][type];
}
