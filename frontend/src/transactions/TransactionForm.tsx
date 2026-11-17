import { type FormEvent } from "react";
import {
  type Account,
  type Category,
  type Environment,
  type Language,
  type LedgerSummary,
  type Provider,
  type SharingParty,
  type Tag,
  type Transaction,
} from "../api";
import { type Labels } from "../i18n/transactions";
import {
  type Draft,
  type RecoveryDraft,
  allocationsBalanced,
  initialSplits,
  normalizeDecimalInput,
  formatMoney,
} from "./model";
import { SplitEditor, SharingEditor } from "./SharingEditor";

export function SummaryStrip({ labels, language, summary }: { labels: Labels; language: Language; summary: LedgerSummary | null }) {
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

export function TransactionForm({
  accounts, availableCategories, baseCurrency, categories, draft, editing, labels,
  language,
  newCategory, newProvider, providers, sharingParties, setDraft, setNewCategory, setNewProvider,
  setShowNewCategory, setShowNewProvider, showNewCategory, showNewProvider, tags,
  working, onCancel, onCreateCategory, onCreateProvider, onSubmit,
}: {
  accounts: Account[]; availableCategories: Category[]; baseCurrency: string; categories: Category[];
  draft: Draft; editing: boolean; environment: Environment; labels: Labels; newCategory: string;
  language: Language;
  newProvider: string; providers: Provider[]; setDraft: React.Dispatch<React.SetStateAction<Draft>>;
  sharingParties: SharingParty[];
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
  const sharingBalanced = draft.splitMode
    ? draft.splits.every((split) => allocationsBalanced(split.sharingAllocations))
    : allocationsBalanced(draft.sharingAllocations);
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
      {draft.splitMode ? <SplitEditor availableCategories={availableCategories} currency={draft.currency} draft={draft} labels={labels} language={language} setDraft={setDraft} sharingParties={sharingParties} tags={tags} /> : <SharingEditor allocations={draft.sharingAllocations} labels={labels} onChange={(sharingAllocations) => setDraft({ ...draft, sharingAllocations })} parties={sharingParties} />}
      {showNewCategory ? <InlineCreate label={labels.addCategory} name={newCategory} labels={labels} onChange={setNewCategory} onCreate={onCreateCategory} /> : null}
      {showNewProvider ? <InlineCreate label={labels.addProvider} name={newProvider} labels={labels} onChange={setNewProvider} onCreate={onCreateProvider} /> : null}
      {draft.currency !== baseCurrency ? <label className="conversion-field">{labels.convertedAmount} ({baseCurrency})<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, convertedAmount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" value={draft.convertedAmount} /><small>{labels.convertedHelp}</small></label> : null}
      <details className="optional-fields"><summary>{labels.optional}</summary><div className="optional-grid"><label>{labels.reference}<input onChange={(event) => setDraft({ ...draft, sourceReference: event.target.value })} value={draft.sourceReference} /></label><label>{labels.notes}<input onChange={(event) => setDraft({ ...draft, notes: event.target.value })} value={draft.notes} /></label>{!draft.splitMode ? <><fieldset><legend>{labels.tags}</legend>{tags.map((tag) => <label className="checkbox-field" key={tag.tag_id}><input checked={draft.tagIds.includes(tag.tag_id)} onChange={(event) => setDraft({ ...draft, tagIds: event.target.checked ? [...draft.tagIds, tag.tag_id] : draft.tagIds.filter((id) => id !== tag.tag_id) })} type="checkbox" />{tag.name}</label>)}</fieldset><label className="checkbox-field"><input checked={draft.isBaseCost} onChange={(event) => setDraft({ ...draft, isBaseCost: event.target.checked })} type="checkbox" />{labels.baseCost}</label></> : null}</div></details>
      <div className="editor-actions"><button className="secondary-button" onClick={onCancel} type="button">{labels.cancel}</button><button className="primary-button" disabled={working || !splitBalanced || !sharingBalanced} type="submit">{editing ? labels.update : labels.save}</button></div>
    </form>
  );
}

export function RecoveryForm({
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

export function InlineCreate({ label, name, labels, onChange, onCreate }: { label: string; name: string; labels: Labels; onChange: (value: string) => void; onCreate: () => Promise<void> }) {
  return <div className="inline-create"><label>{label} · {labels.name}<input onChange={(event) => onChange(event.target.value)} required value={name} /></label><button className="secondary-button" disabled={!name.trim()} onClick={() => void onCreate()} type="button">{labels.add}</button></div>;
}
