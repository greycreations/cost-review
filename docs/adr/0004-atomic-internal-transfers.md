# ADR 0004: Atomic internal transfers

- Status: Accepted
- Date: 2026-08-28
- Product baseline: Product Specification v1.0

## Context

Money moving between accounts owned by the user changes account balances but
does not create household income or consumption. A credit-card purchase is an
expense on its purchase date, while payment of the card bill is such an
internal transfer. Representing either side as ordinary income or expense
would double-count the economics.

## Decision

- `TransferLink` is the aggregate root for an internal transfer. It atomically
  links one outgoing and one incoming `Transaction`, each with one neutral
  component.
- Source and destination accounts must be active and distinct. Transfer legs
  cannot carry provider, category, tag, or base-cost classifications.
- Same-currency legs must have equal original amounts. Cross-currency legs
  preserve the amount and account currency on each side plus each historical
  base-currency conversion and effective rate. When one side supplies the base
  value, the other rate is derived with decimal-safe arithmetic.
- When both base-currency values are known they must be equal. Fees are separate
  expense events rather than a hidden imbalance in the transfer.
- Transfer purpose preserves `internal`, `savings`, `investment`,
  `credit_card_payment`, or `debt_repayment` meaning without treating the event
  as ordinary income or expense.
- Create, edit, archive, and restore operate on both legs in one database
  transaction. A single leg is not exposed through the income/expense API.
- PostgreSQL deferred constraint triggers validate link roles, distinct
  accounts, account currencies, neutral components, synchronized lifecycle,
  and value equality at commit time. These rules therefore also protect writes
  outside the HTTP service.
- Income, expense, and net cash-flow summaries explicitly exclude transfers.
  The browser combines a transfer into one user-facing event while retaining
  the two ledger legs needed for later calculated account balances.
- Production and Demo/Test contain the same schema in separate data planes.
  The isolation scenario creates transfers in both planes, resets Demo/Test,
  and proves the Production transfer survives unchanged.

## Consequences

Users can now register normal account movements, savings transfers,
investments, credit-card payments, and debt principal movements without
distorting consumption or income. Refunds, reimbursements, interest/fee
expenses, calculated balances, and audit-backed deletion retain their separate
ordered Ledger slices.
