# ADR 0019 – Posted cash flow

## Status

Accepted for the first Financial Core delivery.

## Decision

The existing period result is income less net expenses on transaction date.
Its API field `net_cash_flow` retains its meaning for existing consumers.

A separate posted cash-flow read model reports the net movement during the period
on current and cash accounts in the configured base currency. This scope includes
archived accounts with active historical entries. The first release uses these two
account types as a fixed scope. Overview's analysis filters and sharing perspective
control the period result and charts. The posted cash-flow panel always shows the
full posted amounts for this scope.

Use posting date and the signed amount of each qualifying ledger entry. Refunds
and reimbursements enter the cash scope when posted. A credit-card purchase
contributes to costs on its transaction date. The linked card settlement
contributes to posted cash flow when its paying leg posts.

For a transfer across the account scope, only the leg within the scope contributes.
The transfer's purpose attributes savings, investment, debt principal and card
payments. Ordinary internal transfers returning from savings or investment accounts
reduce the corresponding net allocation. Transfers within the scope contribute
both legs to other transfers. Posting dates can differ, so the legs can offset in
different periods. Transfer valuation follows the persisted historical conversion.

Opening balances, account valuations, and reconciliation adjustments are outside
this movement measure. Missing or incompatible base-currency conversions are
counted and excluded from the displayed amounts. The panel shows a period
movement, with no estimate of ending balance.

## Verification

Reconcile a reference month through the existing transaction, refund and transfer
APIs. Cover a card purchase and payment, savings and a return from savings, an
investment deposit, principal repayment, interest, a transfer crossing a posting
period boundary and a transaction with missing historical FX.
