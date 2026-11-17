import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import {
  confirmOccurrence,
  createRecurring,
  getAccounts,
  getCategories,
  getExpectedOccurrences,
  getRecurring,
  reopenOccurrence,
  setRecurringArchived,
  skipOccurrence,
  type Account,
  type Category,
  type Environment,
  type ExpectedOccurrence,
  type Language,
  type RecurringDefinition,
  type RecurringFrequency,
  type RecurringInput,
} from "./api";
import { text } from "./i18n/recurring";


type Labels = (typeof text)["sv"];

export function RecurringWorkspace({
  environment,
  language,
  canWrite,
  today,
}: {
  environment: Environment;
  language: Language;
  canWrite: boolean;
  today?: Date;
}) {
  const labels = text[language];
  const [anchor] = useState(() => today ?? new Date());
  const range = useMemo(
    () => ({ from: isoDate(addDays(anchor, -30)), to: isoDate(addDays(anchor, 60)) }),
    [anchor],
  );
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [definitions, setDefinitions] = useState<RecurringDefinition[]>([]);
  const [occurrences, setOccurrences] = useState<ExpectedOccurrence[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const load = useCallback(
    () =>
      Promise.all([
        getRecurring(environment),
        getExpectedOccurrences(environment, range.from, range.to),
      ]).then(([items, expected]) => {
        setDefinitions(items);
        setOccurrences(expected);
      }),
    [environment, range],
  );

  useEffect(() => {
    let active = true;
    void Promise.all([getAccounts(environment), getCategories(environment), load()])
      .then(([accountPage, categoryPage]) => {
        if (!active) return;
        setAccounts(accountPage.items);
        setCategories(categoryPage.items);
      })
      .catch((reason) => {
        if (active) setError(errorText(reason));
      });
    return () => {
      active = false;
    };
  }, [environment, load]);

  const act = (action: () => Promise<unknown>) => {
    setWorking(true);
    setError(null);
    return action()
      .then(() => load())
      .catch((reason) => setError(errorText(reason)))
      .finally(() => setWorking(false));
  };

  return (
    <section className="recurring-workspace" aria-labelledby="recurring-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1 id="recurring-title">{labels.title}</h1>
          <p>{labels.lead}</p>
        </div>
        {canWrite && !showForm ? (
          <button className="primary-button" onClick={() => setShowForm(true)} type="button">
            {labels.add}
          </button>
        ) : null}
      </div>
      {error ? <div className="error-banner" role="alert">{error}</div> : null}
      {showForm ? (
        <RecurringForm
          accounts={accounts}
          categories={categories}
          labels={labels}
          onCancel={() => setShowForm(false)}
          onSubmit={(payload) =>
            act(() => createRecurring(environment, payload).then(() => setShowForm(false)))
          }
          working={working}
        />
      ) : null}

      <section className="settings-section" aria-labelledby="expected-title">
        <h2 id="expected-title">{labels.upcoming}</h2>
        <p className="quiet-copy">{labels.range}</p>
        {occurrences.length === 0 ? <p className="resource-empty">{labels.nothing}</p> : null}
        <div className="operations-list">
          {occurrences.map((item) => (
            <OccurrenceRow
              canWrite={canWrite}
              item={item}
              key={`${item.recurring_definition_id}-${item.due_date}`}
              labels={labels}
              language={language}
              onConfirm={(payload) =>
                act(() =>
                  confirmOccurrence(environment, item.recurring_definition_id, item.due_date, payload),
                )
              }
              onReopen={() =>
                act(() => reopenOccurrence(environment, item.recurring_definition_id, item.due_date))
              }
              onSkip={() =>
                act(() => skipOccurrence(environment, item.recurring_definition_id, item.due_date))
              }
              working={working}
            />
          ))}
        </div>
      </section>

      <section className="settings-section" aria-labelledby="definitions-title">
        <h2 id="definitions-title">{labels.definitions}</h2>
        {definitions.length === 0 ? <p className="resource-empty">{labels.none}</p> : null}
        <div className="operations-list">
          {definitions.map((item) => {
            const current = item.versions[item.versions.length - 1];
            return (
              <div className="operation-row" key={item.recurring_definition_id}>
                <div>
                  <strong>{item.name}</strong>
                  <span>
                    {item.transaction_kind === "income" ? labels.income : labels.expense} ·{" "}
                    {money(current.amount, item.currency, language)} ({labels[current.amount_type]}) ·{" "}
                    {frequencyLabel(item.frequency, item.interval_count, labels)}
                  </span>
                </div>
                {canWrite ? (
                  <div className="row-actions">
                    <button
                      className="ghost-button"
                      disabled={working}
                      onClick={() =>
                        void act(() =>
                          setRecurringArchived(environment, item.recurring_definition_id, true),
                        )
                      }
                      type="button"
                    >
                      {labels.archive}
                    </button>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>
    </section>
  );
}

function OccurrenceRow({
  canWrite,
  item,
  labels,
  language,
  onConfirm,
  onReopen,
  onSkip,
  working,
}: {
  canWrite: boolean;
  item: ExpectedOccurrence;
  labels: Labels;
  language: Language;
  onConfirm: (payload: { transaction_id?: number; amount?: string }) => void;
  onReopen: () => void;
  onSkip: () => void;
  working: boolean;
}) {
  const [amount, setAmount] = useState(String(Number(item.expected_amount)));
  const open = item.status === "expected" || item.status === "overdue";
  return (
    <div className={`operation-row recurring-occurrence recurring-${item.status}`}>
      <div>
        <strong>
          {item.name} · {money(item.expected_amount, item.currency, language)}
        </strong>
        <span>
          {dateLabel(item.due_date, language)} · {labels.status[item.status]}
          {item.deviation_percent !== null && Number(item.deviation_percent) !== 0
            ? ` · ${Number(item.deviation_percent).toLocaleString(language === "sv" ? "sv-SE" : "en-SE")} % ${labels.deviation}`
            : ""}
        </span>
        {item.outside_tolerance ? <span className="attention-note">{labels.outside}</span> : null}
        {canWrite && open
          ? item.candidates.map((candidate) => (
              <button
                className="ghost-button recurring-candidate"
                disabled={working}
                key={candidate.transaction_id}
                onClick={() => onConfirm({ transaction_id: candidate.transaction_id })}
                type="button"
              >
                {labels.link}: {candidate.description} · {dateLabel(candidate.transaction_date, language)} ·{" "}
                {money(candidate.amount, item.currency, language)} · {candidate.confidence}% {labels.match}
              </button>
            ))
          : null}
      </div>
      {canWrite ? (
        <div className="row-actions">
          {open ? (
            <>
              {item.amount_type === "variable" ? (
                <input
                  aria-label={`${labels.confirmAmount} · ${item.name} ${item.due_date}`}
                  className="table-number-input"
                  inputMode="decimal"
                  onChange={(event) => setAmount(event.target.value)}
                  value={amount}
                />
              ) : null}
              <button
                className="secondary-button"
                disabled={working}
                onClick={() =>
                  onConfirm(
                    item.amount_type === "variable"
                      ? { amount: amount.replace(",", ".").replace(/\s/g, "") }
                      : {},
                  )
                }
                type="button"
              >
                {labels.confirm}
              </button>
              <button className="ghost-button" disabled={working} onClick={onSkip} type="button">
                {labels.skip}
              </button>
            </>
          ) : (
            <button className="ghost-button" disabled={working} onClick={onReopen} type="button">
              {labels.reopen}
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}

function RecurringForm({
  accounts,
  categories,
  labels,
  onCancel,
  onSubmit,
  working,
}: {
  accounts: Account[];
  categories: Category[];
  labels: Labels;
  onCancel: () => void;
  onSubmit: (payload: RecurringInput) => void;
  working: boolean;
}) {
  const [draft, setDraft] = useState({
    name: "",
    accountId: accounts[0] ? String(accounts[0].account_id) : "",
    kind: "expense" as "expense" | "income",
    amount: "",
    amountType: "fixed" as "fixed" | "variable",
    frequency: "monthly" as RecurringFrequency,
    interval: "1",
    startDate: isoDate(new Date()),
    endDate: "",
    categoryId: "",
  });
  const fitting = categories.filter((category) => category.category_kind === draft.kind);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      name: draft.name,
      account_id: Number(draft.accountId),
      category_id: draft.categoryId ? Number(draft.categoryId) : null,
      transaction_kind: draft.kind,
      amount: draft.amount.replace(",", ".").replace(/\s/g, ""),
      amount_type: draft.amountType,
      frequency: draft.frequency,
      interval_count: Number(draft.interval) || 1,
      start_date: draft.startDate,
      end_date: draft.endDate || null,
    });
  };
  return (
    <form className="budget-editor recurring-editor" onSubmit={submit}>
      <div className="budget-form-grid">
        <label>
          {labels.name}
          <input maxLength={160} onChange={(event) => setDraft({ ...draft, name: event.target.value })} required value={draft.name} />
        </label>
        <label>
          {labels.account}
          <select onChange={(event) => setDraft({ ...draft, accountId: event.target.value })} required value={draft.accountId}>
            {accounts.map((account) => (
              <option key={account.account_id} value={account.account_id}>{account.name}</option>
            ))}
          </select>
        </label>
        <label>
          {labels.kind}
          <select
            onChange={(event) =>
              setDraft({ ...draft, kind: event.target.value as "expense" | "income", categoryId: "" })
            }
            value={draft.kind}
          >
            <option value="expense">{labels.expense}</option>
            <option value="income">{labels.income}</option>
          </select>
        </label>
        <label>
          {labels.amount}
          <input inputMode="decimal" onChange={(event) => setDraft({ ...draft, amount: event.target.value })} pattern="[0-9 ]+([.,][0-9]{1,4})?" required value={draft.amount} />
        </label>
        <label>
          {labels.amountType}
          <select onChange={(event) => setDraft({ ...draft, amountType: event.target.value as "fixed" | "variable" })} value={draft.amountType}>
            <option value="fixed">{labels.fixed}</option>
            <option value="variable">{labels.variable}</option>
          </select>
        </label>
        <label>
          {labels.frequency}
          <select onChange={(event) => setDraft({ ...draft, frequency: event.target.value as RecurringFrequency })} value={draft.frequency}>
            <option value="weekly">{labels.weekly}</option>
            <option value="monthly">{labels.monthly}</option>
            <option value="quarterly">{labels.quarterly}</option>
            <option value="yearly">{labels.yearly}</option>
          </select>
        </label>
        <label>
          {labels.startDate}
          <input onChange={(event) => setDraft({ ...draft, startDate: event.target.value })} required type="date" value={draft.startDate} />
        </label>
        <label>
          {labels.endDate}
          <input onChange={(event) => setDraft({ ...draft, endDate: event.target.value })} type="date" value={draft.endDate} />
        </label>
        <label>
          {labels.category}
          <select onChange={(event) => setDraft({ ...draft, categoryId: event.target.value })} value={draft.categoryId}>
            <option value="">{labels.noCategory}</option>
            {fitting.map((category) => (
              <option key={category.category_id} value={category.category_id}>{category.name}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="editor-actions">
        <button className="secondary-button" onClick={onCancel} type="button">{labels.cancel}</button>
        <button className="primary-button" disabled={working} type="submit">{labels.save}</button>
      </div>
    </form>
  );
}

function frequencyLabel(frequency: RecurringFrequency, interval: number, labels: Labels): string {
  const base = labels[frequency];
  return interval > 1 ? `${base} (${labels.every} ${interval})` : base;
}

function money(value: string, currency: string, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", {
    style: "currency",
    currency,
  }).format(Number(value));
}

function dateLabel(value: string, language: Language): string {
  return new Date(`${value}T12:00:00`).toLocaleDateString(language === "sv" ? "sv-SE" : "en-SE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function addDays(value: Date, days: number): Date {
  const copy = new Date(value);
  copy.setDate(copy.getDate() + days);
  return copy;
}

function isoDate(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function errorText(reason: unknown): string {
  return reason instanceof Error ? reason.message : String(reason);
}
