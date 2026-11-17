import {
  setTransferArchived,
  setRecoveryArchived,
  setTransactionArchived,
  type Account,
  type Category,
  type Environment,
  type Language,
  type Provider,
  type RecoveryKind,
  type Transfer,
  type Transaction,
} from "../api";
import { type Labels } from "../i18n/transactions";
import { purposeLabel, formatMoney, formatDate } from "./model";

export function EntryList({ accounts, categories, environment, labels, language, providers, transactions, transfers, onEdit, onEditTransfer, onRecovery, onReload, onError }: { accounts: Account[]; categories: Category[]; environment: Environment; labels: Labels; language: Language; providers: Provider[]; transactions: Transaction[]; transfers: Transfer[]; onEdit: (transaction: Transaction) => void; onEditTransfer: (transfer: Transfer) => void; onRecovery: (transaction: Transaction, kind: RecoveryKind) => void; onReload: () => void; onError: (message: string) => void }) {
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
