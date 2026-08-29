# Cost Review — Release 1 Core MVP delivery baseline

**Status:** aligned with Product Specification v1.0, with approved MVP clarifications for recurring-cost forecasting and payroll/income breakdown

**Authoritative requirements:** `docs/PRODUCT_SPECIFICATION.md`

**Delivery order:** `docs/IMPLEMENTATION_BACKLOG.md`

This document is a compact technical delivery guide. It does not override the
Product Specification. The recurring-cost and payroll clarifications below are
approved MVP requirements and must be consolidated into the Product Specification
when that baseline is next revised.

## Release 1 outcome

Cost Review is a self-hosted PostgreSQL-backed web application that preserves a
trustworthy economic ledger and supports controlled classification, recurring
events, safe import, analysis, budgeting, recovery, and a persistent isolated
Demo/Test environment.

The Release 1 Core MVP blockers are:

1. Platform foundation, setup, authentication, persistence, migrations, and a
   hard Production/Test boundary.
2. Accounts, balances, transactions, splits, income, expenses, transfers,
   refunds, reimbursements, adjustments, currency, sharing, and payroll/income
   breakdowns that preserve the difference between cash flow and economic cost.
3. Categories, providers and aliases/links, tags, and sharing parties.
4. Safe CRUD, audit, Recycle Bin, bulk edit, restore, and dependency-aware
   permanent deletion.
5. Versioned recurring definitions, Expected events, confirmation, matching,
   recurring-cost classification, and fixed/variable expected amounts.
6. CSV/XLSX profiles, preview, staging, validation, duplicate handling, rules,
   import batches, and undo.
7. Common filters, saved views, Analysis Groups, predefined dashboards, and
   saved layouts.
8. Flexible budgets and Actual/Periodized plus Total/My Share perspectives.
9. Encrypted backup/restore with retention and an automated restore test.
10. Persistent Demo/Test with safe reset, import simulation, and selective
    one-way Production-to-Test configuration copy.

Attachments, manual investment/asset/debt views, goals, reporting/export, and
proactive alerts follow after the Core MVP is stable. The Product Specification
defines the complete extended and post-MVP boundaries.

## Platform baseline

- Docker Compose deployment on Ubuntu.
- React, TypeScript, and Vite frontend served through a same-origin gateway.
- FastAPI backend with a versioned `/api/v1` contract.
- SQLAlchemy 2.x and Alembic against PostgreSQL only.
- Local username/password authentication with secure hashing, opaque
  server-side sessions, CSRF protection, and secure cookie controls.
- First-run setup for initial login, language, region, date/number formats, base
  currency, week start, and timezone.
- Explicit reverse-proxy, trusted host/origin, and secure-cookie configuration.

## Production and Demo/Test boundary

Production and Demo/Test use the same application images but run as separate
data planes:

- separate API processes;
- separate PostgreSQL services and persistent volumes;
- separate database roles and passwords;
- separate Docker data networks;
- separate session and CSRF cookie namespaces;
- persistent environment identity stored in each database;
- startup refusal if a database volume is mounted under the wrong environment;
- Demo/Test-only destructive reset endpoint with strong confirmation;
- automated proof that reset and ordinary Test writes cannot mutate Production.

There is no shared `is_test` discriminator on economic rows. Future selective
configuration copy is an explicit API export/import operation and never grants
one data plane direct database access to the other.

## Sprint 1 — Platform Foundation

Sprint 1 implements backlog CR-001 through CR-008. It includes:

- reproducible Compose services for gateway, Production API/PostgreSQL, and
  Demo/Test API/PostgreSQL;
- persistent database, attachment, and backup volumes;
- initial platform migration;
- setup lock, authentication, sessions, settings, and environment identity;
- Swedish/English setup and shell foundations;
- unmistakable Production and Demo/Test UI states;
- trusted proxy/host/origin configuration;
- PostgreSQL-only tests, migrations, Compose smoke tests, and destructive
  isolation tests.

Sprint 1 intentionally does not create the old Expense-centric schema. The
ledger schema starts only after its transaction semantics and invariants have
been reviewed against Product Specification v1.0.

### Sprint 1 exit gate

- A fresh Compose deployment becomes healthy with documented steps.
- Both data planes migrate from empty PostgreSQL databases.
- Setup creates the first local user and then locks.
- Login, authenticated session lookup, logout, and settings retrieval work.
- Production and Demo/Test identities remain stable across container recreation.
- Both databases and storage volumes persist independently.
- Demo/Test reset is unavailable in Production and cannot alter Production.
- Cross-environment database credentials and network routes fail.
- The Demo/Test UI is persistent and unmistakable.
- Backend lint/tests, Alembic checks, frontend lint/tests/build, and Compose
  verification pass.

## Ledger sequence after Sprint 1

1. Accounts and hierarchical/reusable master data.
2. Transaction and TransactionSplit with original currency and historical FX.
3. Expense/income, transfer, refund, reimbursement, credit-card, and adjustment
   semantics.
4. Sharing, balances, reconciliation, soft deletion, Recycle Bin, audit, frozen
   historical identity, and bulk edit.
5. Payroll/income breakdown semantics for economic events that occur before the
   net amount reaches an owned account.

Recurring/Expected events remain a separate later epic and never replace actual
ledger events.

## Recurring cost classification and forecasting

Recurring status is a first-class analytical dimension and must not be reduced
to a simple transaction checkbox. Actual transactions may be linked to a
versioned recurring definition while preserving the actual transaction as the
historical source of truth.

Cost nature supports at least:

- **Recurring fixed** — predictable amount and cadence, for example a streaming
  subscription.
- **Recurring variable** — predictable cadence but variable amount, for example
  electricity, water/waste, heating, or other utility bills.
- **One-off** — explicitly classified as a non-recurring economic event.
- **Unclassified** — no recurring/one-off assumption has yet been made.

Recurring definitions may specify cadence, expected date/window, provider,
account, category, sharing defaults, and either a fixed amount or a forecasted
variable amount. Generated occurrences remain Expected until confirmed or
matched to an actual transaction.

For variable recurring costs, Core MVP must support a simple explainable
forecast value and retain the data model needed for more capable forecasting.
Forecasting must never rewrite historical actual amounts. The product should be
able to evolve through forecast methods such as last amount, rolling average,
rolling median, and seasonal history. Where sufficient history exists, future
forecasting may provide an estimated range/confidence rather than false
precision, especially for seasonal costs such as electricity.

Analysis and saved views must be able to separate recurring fixed, recurring
variable, one-off, and unclassified costs. This enables views such as normal
monthly recurring cost, fixed commitments, expected variable costs, and
one-off spending. Forecast accuracy can later be measured by comparing an
Expected occurrence with the matched actual transaction.

## Payroll and income breakdown

Cost Review must represent economic costs and allocations that occur before a
net salary or other income reaches an owned account. A common example is a
salary-sacrifice/company-car arrangement where a fixed gross-salary deduction
is made before tax and net salary payment.

The actual net payment to the bank account remains the ledger transaction that
affects account balance. A payroll/income breakdown is linked to that income
transaction and may describe components such as:

- gross income;
- taxable benefits or other additions;
- pre-tax/gross-salary deductions;
- tax/withholding;
- post-tax deductions;
- net amount paid to the owned account.

Breakdown components are economic metadata/events and must not create a second
cash withdrawal from the bank account. This prevents double counting while
allowing a salary deduction, such as a company-car cost, to appear in expense
and compensation analysis.

Each relevant deduction/component may have a category, tags, sharing data and
recurring definition. A fixed monthly company-car salary deduction can therefore
be represented as a recurring fixed economic cost and included together with
ordinary bank-paid vehicle expenses in total vehicle-cost analysis.

The model must support at least two analytical perspectives:

- **Cash flow** — what actually entered or left owned accounts.
- **Economic/compensation** — income and costs including payroll components that
  occur before net settlement.

Cash-flow balances and reconciliation always use actual ledger transactions;
payroll breakdown components never alter an account balance independently.
Economic analysis may include eligible breakdown components according to the
selected perspective and must clearly indicate when values are not direct bank
transactions.

The payroll model must be generic rather than company-car-specific so that the
same mechanism can represent pension salary sacrifice, insurance, union fees,
employee benefits, and other payroll deductions or additions. Historical
breakdowns must remain stable. Changes to recurring payroll components use
versioned definitions/effective dates rather than rewriting prior salary
periods.

### Payroll acceptance criteria

- A user can register a net salary transaction and attach a payroll breakdown.
- The breakdown can reconcile gross/addition/deduction/tax components to the net
  paid amount, while allowing jurisdiction-specific components that affect tax
  basis without pretending to be cash movements.
- A payroll deduction can be classified and analyzed as an economic cost without
  reducing the bank-account balance a second time.
- A payroll component can be recurring fixed or recurring variable and can use
  versioned effective dates.
- Expense/category analysis can include payroll-derived economic costs when the
  Economic/compensation perspective is selected.
- Cash-flow analysis and account reconciliation exclude non-cash payroll
  components from account movements.
- The UI clearly distinguishes actual bank transactions from payroll-derived
  economic components.
