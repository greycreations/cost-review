import { type FormEvent } from "react";
import { type Account, type TransferPurpose } from "../api";
import { type Labels } from "../i18n/transactions";
import { type TransferDraft } from "./model";

export function TransferForm({
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
