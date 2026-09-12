# Cost Review Product & MVP Specification

**Version:** 1.4
**Date:** 2026-09-12
**Status:** Requirements baseline / source of truth

## 1. Product vision
Cost Review is a self-hosted web application for understanding personal and household economics across income, expenses, budgets, savings, investments, assets and liabilities. It combines reliable transaction history with flexible analysis and planning while keeping the user in control of automation.

### Product principles
- Preserve economic truth and original source data.
- Transfers, reimbursements, refunds, investment trades, debt reduction and balance adjustments must not be misclassified as ordinary consumption or income.
- Automation may suggest; uncertain or conflicting actions remain visible and user-confirmed.
- Analysis must not require destructive reclassification.
- Configuration is a first-class product capability.
- Production and Demo/Test are separate trust domains.
- UI should be calm, spacious and informative rather than traditional accounting software.

## 2. Deployment and platform
- Web-based application deployed with Docker Compose on Ubuntu.
- PostgreSQL is the relational source of truth.
- Persistent volumes for database, attachments, backups and persistent Demo/Test data.
- Frontend -> versionable backend/API -> PostgreSQL; frontend never connects directly to the database.
- Schema migrations from the first release.
- Designed to operate behind Cloudflare/reverse proxy with explicit trusted-proxy, host/origin and secure-cookie configuration.
- Local multi-user username/password authentication in MVP with secure password hashing,
  environment-scoped roles and session management.
- No secrets hardcoded in repository or images.
- 2FA/TOTP is post-MVP but the authentication architecture must permit it later.

## 3. First-run setup and localization
Fresh installation enters setup mode when no user exists. The wizard creates the initial
administrator, selects base currency, language/region, timezone and optionally initial accounts,
then locks setup mode. After setup, any person who can reach the installation may create a regular
account when operator-controlled self-registration is enabled. Every user can change their own
password; doing so revokes their other sessions. Administrators can create, rename, reset the
password of and delete other accounts, and may delegate or remove administrator access. The active
account cannot delete itself and the final administrator cannot be demoted or deleted. Production
and Demo/Test keep independent users, roles, password hashes and sessions.

Release 1 supports Swedish and English. Language, region, base currency, date/number formats, week start and timezone are independent settings.

## 4. Core economic model
### Transaction semantics
- **Expense:** consumption/cost event; may be split.
- **Income:** user-defined category; recurring or one-off.
- **Internal transfer:** movement between owned accounts; never ordinary income/expense. May carry savings/investment meaning.
- **Refund:** separate event linked to the original purchase; preserve gross purchase, refund and net cost.
- **Reimbursement:** linked inflow reducing personal cost, e.g. Swish reimbursement; not ordinary income.
- **Credit-card purchase:** expense occurs on purchase date; card-bill payment is an internal transfer.
- **Investment trade:** buy/sell within investment account is not household consumption. Dividends are investment income; realized gain/loss is tracked on sale; unrealized value change is not income.
- **Balance adjustment:** explicit traceable reconciliation correction excluded from ordinary income/expense.
- **Expected transaction:** future/recurring expectation that does not affect actual balance until confirmed or matched.
- **Opening balance:** account starting point with effective date; not income.

Store both transaction/purchase date and posting/book date. Transaction date normally drives budgets and expense analysis.

### Currency
- Multiple currencies with configurable base currency.
- Persist original amount/currency, converted amount and actual historical FX rate used.
- Automatically request historical FX rate for transaction date; manual override allowed.
- FX lookup failure never blocks entry. Missing rate is surfaced in Attention and can be completed later.
- Historical analysis does not change when current exchange rates change.

### Splits and base costs
Transactions may be split across multiple components. Each split can have its own category, tags and base-cost flag. Base cost is primarily a transaction/split attribute; provider/category defaults may later reduce manual work.

## 5. Accounts, assets and liabilities
### Accounts
Fixed base account types with free account names: current/salary, savings, credit card, investment, loan/debt, value-based, cash and other.

Account metadata may include interest rate, locked/bound status and lock period/dates.

- Calculated balance = opening balance + qualifying transactions.
- Reconciliation compares calculated with actual balance and identifies the difference before an optional balance adjustment is created.
- Value-based accounts use timestamped value snapshots.
- Loans: principal repayment reduces liability and is capital movement; interest/fees are expenses.
- Investment accounts appear with normal accounts but expose investment-specific content.

### Assets and net worth
Non-account assets such as home and vehicle are separate Asset objects with timestamped valuations. Analysis distinguishes Financial Net Worth and Total Net Worth. Definitions are configurable under Financial Rules.

### Shared economics
Accounts, assets, liabilities, recurring items and transactions may be shared.
- Simple CRUD Sharing Party register; parties are metadata, not users.
- UI may use a Shared checkbox but stores ownership/responsibility percentages.
- Multiple parties can be allocated to one item.
- Transaction-level share is authoritative; account/provider/category/recurring item may provide a default.
- Dashboards, analysis and budgets can switch between Total and My Share.
- Periodization is calculated on full amount first, then share perspective is applied.

### Account deletion
- Future planned/recurring dependencies block deletion and are shown to the user.
- First deletion is always soft delete to Recycle Bin; restore is supported.
- Permanent deletion requires blocking future dependencies to be resolved.
- Historical transactions may retain a frozen snapshot of deleted-account identity so history and analysis survive.

## 6. Classification
### Categories
Full CRUD with arbitrary-depth hierarchy in the data model; UI normally presents one to two levels. Income and expense categories are user-defined.

### Providers / correspondents
Reusable editable providers. A canonical provider may have multiple aliases/match names; imported raw provider text is always preserved.

Providers can be persistently linked to related providers without merging historical data. Categories support the same linking concept.

### Tags
Tags support create, rename, archive, delete and merge. One primary category per cost component, multiple optional tags.

### Analysis Groups and saved views
Reusable named Analysis Groups combine providers, categories, tags and other filter conditions without rewriting base data. They can be reused by analysis, dashboards, budgets and goals.

Saved filters/views combine free text with properties such as date, account, category, provider, tag, base-cost status, recurring status, amount and currency.

## 7. Recurring and future events
- Same recurring engine for income and expenses.
- Fixed or variable expected amount.
- Variable items use a forecast value; default deviation tolerance is configurable in app settings.
- Scheduled occurrences are Expected until confirmed or matched to actual/imported transactions.
- Matching uses date, amount, account, provider/sender and history to calculate visible confidence; no automatic merge without confirmation.
- Recurring definitions are versioned with effective dates; edits never rewrite history.
- Annual/quarterly costs may be periodized for analysis while actual cash flow remains on payment date.

## 8. Budgets, savings and goals
### Budgets
- Reset or rollover configured per budget.
- Periods: calendar month, salary-to-salary, year or custom date interval.
- Uses the common filter engine and may include/exclude categories, descendants, providers, tags, accounts and Analysis Groups.
- Overlapping budgets are allowed but clearly marked as non-additive.
- Supports Total/My Share and Actual/Periodized perspectives.

### Savings and Financial Rules
Savings classifications distinguish liquid savings, invested savings and debt reduction.

Initial metrics:
- Savings Rate = liquid savings + invested savings / relevant income.
- Wealth Rate = liquid savings + invested savings + debt reduction / relevant income.

Settings > Financial Rules contains transparent/configurable definitions for Savings Rate, Wealth Rate, Base Cost, Net Worth, Relevant Income and accounts included in metrics.

### Goals
Savings and debt goals support target value, optional target date and flexible source selection across accounts, investments, assets, liabilities and groups. Goals are versioned and progress/history is visualized.

## 9. Investments
- Investment accounts are first-class accounts.
- Transfer into an ISK/investment account is an internal transfer and may be classified as invested savings.
- Buys/sells inside the account are not household expenses.
- Unrealized value change is not income; dividends are investment income; realized gains/losses are tracked on sale.
- Release 1 baseline uses manual value updates/snapshots.
- Post-MVP: exact holdings, market prices, dividend feeds and richer analytics through modular provider adapters.

## 10. Import, staging and rules
### Import provider profiles
User selects **Create new provider profile for import**, then supplies CSV or Excel. Cost Review reads headers/sample rows and previews the file so columns can be mapped to transaction date, posting date, amount, currency, provider/description, reference and other fields.

Profiles are named and reusable. They may store transformations such as sign convention and date format.

On later imports the app proposes a matching profile with a visible confidence percentage. Before import, the user sees the probability and a preview of how the file will be interpreted. User confirms, changes profile or cancels. Nothing external becomes an ordinary transaction before staging approval.

### Staging
- Row-level validation for invalid dates, missing amounts, unknown currency, parse failures and duplicates.
- Edit rows directly, bulk edit, skip invalid rows or import remaining valid rows.
- Imported rows can be split before finalization.
- Duplicate detection uses account, amount, currency, dates, provider/description and other evidence; show confidence and reasons.
- User chooses ignore, import anyway or link to existing.

### Rules engine
- CRUD, enable/disable and user-editable priority/order.
- Rules can be created manually or proposed from corrections.
- Conflicting results are never silently chosen; staging shows Conflict and explains which rules/conditions caused it.

### Import batches
Each import retains source metadata and batch identity. Batch history supports filtering/debugging and Undo Import. Undo uses soft delete and shows impact when imported transactions have since been edited or gained dependencies.

## 11. Dashboards, analysis and reporting
Predefined dashboards: Overview, Expenses, Income, Budget and Investments.

- Interactive widgets/charts with drill-down.
- Common periods: current/previous month, 3/6/12 months, year-to-date, previous year and arbitrary range.
- Compare with previous period or same period previous year.
- Move, resize, hide/show and configure widgets within defined limits.
- Save multiple named user-defined layouts and switch between them.
- Every predefined dashboard retains a resettable standard layout.
- Common filters and saved views power transaction list, analysis, budgets, goals and widgets.
- Analysis supports provider/category links and Analysis Groups.
- Export underlying data to CSV/Excel, charts to image/PDF and provide a simple printable/report view.

A central Attention area contains persistent actionable notifications such as recurring confirmation, import review, rule conflicts, possible duplicates, missing FX and backup failure. States include active, acknowledged, dismissed, remind again and do not remind again.

Configurable proactive economic alerts are part of the approved product: e.g. spending above trend, recurring cost increases, budget threshold, projected negative balance and stale investment valuation.

Future forecasting provides 30-day / 3 / 6 / 12-month cash-flow projections while clearly separating Actual, Expected and Forecast.

## 12. Attachments
- Multiple attachments per transaction.
- MVP file types: PDF, JPG, PNG and WebP.
- Configurable maximum file size.
- Validate actual file type, not only extension.
- Store files in persistent storage outside the relational database; metadata/links in PostgreSQL.
- Built-in browser preview for images/PDF.
- Backup/restore includes attachments.
- Data model ready for future OCR; OCR is post-MVP.

## 13. Data lifecycle and audit
- User-managed master data supports CRUD.
- Destructive actions default to soft delete and Recycle Bin.
- Bulk edit works on historical transactions and recalculates dashboards while preserving change history.
- Central and object-level Audit History stores material old/new values, timestamp and change source without automatic retention limit.
- Permanent deletion removes object and attachments; audit retains only a minimal anonymized deletion event without full financial detail.

## 14. Backup and restore
- Automatic scheduled backups plus manual Create/Download and Restore/Import.
- Includes financial data, configuration and attachments.
- Encryption is an MVP requirement. Manual backups may be password-protected; automatic backups may use an installation secret/key.
- Restore validates format, integrity and decryption before replacing data.
- Frequency and storage location are configurable.
- Automatic retention can be by count or age window. Manual backups are never removed by automatic retention.
- Restore must be tested as a release acceptance criterion.

## 15. Production vs Demo/Test
**Hard requirement:** Demo/Test data is persistent and isolated from production. Do not model this solely with an `is_test` flag.

- Long-lived test data survives restart and upgrade.
- User can enter fictional accounts, transactions, investments, budgets, rules, etc.
- Test supports full CSV/Excel import simulation, staging, rules, duplicates, splitting and analysis.
- UI unmistakably indicates DEMO/TEST context.
- `Delete all test data` exists with strong confirmation and cannot affect production.
- Explicit one-way Production -> Test configuration copy; never copy economic data.
- Copy is selective and previewed.
- Per-object conflicts: keep test, replace with production, create copy or skip. Never silently overwrite.

## 16. Recommended Release 1 boundary
### Core release blockers
1. Platform foundation: Compose, PostgreSQL, persistence, migrations, setup, auth and Production/Test boundary.
2. Economic ledger: accounts, balances, expenses, income, transfers, refunds/reimbursements, adjustments, splits, currency and sharing.
3. Master data: categories, providers/aliases/links, tags and sharing parties.
4. CRUD safety: edit, bulk edit, soft delete, recycle bin, audit and dependency-aware permanent deletion.
5. Recurring/Expected transactions and confirmation/matching.
6. CSV/XLSX import profiles, confidence/preview, staging, validation, duplicates, rules, batches and undo.
7. Predefined dashboards, common filters, saved views/layouts and Analysis Groups.
8. Flexible budgeting and periodization.
9. Encrypted backup/restore and retention.
10. Persistent isolated Demo/Test with import simulation and selective Production -> Test config copy.

### Extended MVP after core is stable
- Attachments.
- Manual investments/assets/debt/net-worth views.
- Economic goals.
- Reporting/export.
- Proactive in-app alerts.

## 17. Explicitly post-MVP
- OCR / automatic receipt interpretation.
- Live market prices, exact holdings and dividend feeds.
- Direct bank/open-banking integrations.
- Advanced cash-flow forecasting/scenario engine (domain must support Actual/Expected/Forecast now).
- External email/push notifications unless reprioritized.
- 2FA/TOTP.
- Full arbitrary dashboard/widget builder beyond saved configurable layouts.
- Native mobile apps.

## 18. Candidate core entities
- User / AppSettings / FinancialRules
- EnvironmentContext (Production/Test boundary)
- Account / AccountSnapshot / BalanceReconciliation
- Transaction / TransactionSplit / TransferLink / RefundLink / ReimbursementLink
- Category / Provider / ProviderAlias / Tag / SharingParty / ShareAllocation
- RecurringDefinition / RecurringVersion / ExpectedTransaction
- Budget / Goal / AnalysisGroup / SavedFilter
- InvestmentAsset / InvestmentTransaction / Asset / ValuationSnapshot / Liability
- ImportProviderProfile / ImportBatch / ImportRow / DuplicateCandidate
- Rule / RuleCondition / RuleAction / RuleConflict
- DashboardLayout / WidgetConfiguration
- Attachment / Notification / AuditEvent / BackupRecord

## 19. Key consistency decisions
- Provider/category links and Analysis Groups replace destructive merging for analytical purposes.
- Hierarchy expresses taxonomy; links/groups express analytical relationships.
- Historical transactions may retain frozen account identity after permanent master-record deletion.
- Login accounts control application access. Sharing parties remain separate economic metadata and
  are not inferred from login identities.
- Manual transactions save directly; imported/automated data goes through staging.
- Confidence scores and previews are advisory; uncertain actions remain user-confirmed.
- Demo/Test uses a real data boundary rather than flags alone.
- Actual cash flow and periodized cost are separate analytical perspectives.

## 20. Main implementation risks
1. **Domain invariants:** transfers, splits, refunds, reimbursements, sharing, periodization and deletion snapshots interact. Put invariants in backend/domain services and DB constraints where appropriate.
2. **Scope:** Release 1 is ambitious. Build vertical slices and do not start with advanced charts before ledger semantics are trustworthy.
3. **Production/Test isolation:** automated tests must prove test reset/import/copy cannot mutate production.
4. **Restore integrity:** backup/restore needs automated integration testing including attachments and encrypted archives.
5. **Import safety:** treat files as untrusted input; enforce type/size limits, robust parsing, staging and idempotent batch behavior.
6. **Rule explainability:** deterministic evaluation, explicit priority and human-readable conflicts.
7. **Historical correctness:** persist FX, snapshots and versions rather than recalculating history from today's values.

## 21. Release 1 acceptance criteria
- Fresh Ubuntu host can start the application with documented Docker Compose steps and persistent data survives container recreation.
- Setup creates the initial local administrator and independent locale/currency/timezone settings;
  self-registration, password change and administrator-controlled account lifecycle work per data
  plane without weakening Production/Test isolation.
- Account/master-data CRUD, soft delete/restore and dependency-safe deletion work.
- Expense, income, transfer, refund/reimbursement, adjustment and split semantics do not double-count economics.
- Credit-card purchase and repayment behavior is correct.
- Shared allocations produce correct Total and My Share values.
- Recurring definitions produce Expected events and matching requires user confirmation.
- CSV/XLSX import profiles can be created from sample files, mapped, saved and later suggested with visible confidence plus preview.
- Staging supports correction, bulk edit, conflicts, duplicate confidence/reasons, splits and partial approval.
- Import batches are traceable and safely undoable with impact preview.
- Common filters are consistent across transaction list, analysis and budgets.
- Dashboards support period presets, arbitrary ranges, comparisons, drill-down, saved layouts and reset-to-default.
- Budgets support period types, reset/rollover and overlap warnings.
- Audit shows material changes and permanent deletion retains only minimal anonymized evidence.
- Encrypted backup including attachments/configuration can be restored successfully into a compatible clean installation.
- Automatic retention works by count or age and never removes manual backups.
- Demo/Test survives restart, supports import simulation and can be cleared without changing production.
- Selective Production -> Test config copy previews changes and resolves conflicts explicitly.
- Application operates safely behind the intended Cloudflare/reverse-proxy deployment.
- No release blocker depends on OCR, live market data, bank APIs or 2FA.
- The Investments workspace may use an optional server-side market-data provider. When enabled,
  the source, observation date, delay and forecast basis must be visible; unavailable live data
  must never be silently replaced with fictional values.
- Investment watchlist, whole-share holdings, purchase budget and target allocations are persisted
  independently in Production and Demo/Test. Market observations remain derived external data and
  must not be recorded as investment trades or household income.

## 22. Recommended implementation sequence
1. **Foundation:** repo structure, Compose, PostgreSQL, migrations, API/backend, frontend shell, auth, setup and environment boundary.
2. **Ledger:** accounts, master data, transaction semantics, splits, sharing, balances, reconciliation, audit and recycle bin.
3. **Recurring:** Expected transactions, versions, variable amounts, matching and Attention.
4. **Import:** CSV/XLSX profiles, confidence/preview, staging, duplicate detection, rules, batches and undo.
5. **Analysis & budget:** common filter engine, saved views, Analysis Groups, dashboards, comparisons, budgets and periodization.
6. **Resilience:** encrypted backup/restore, retention, attachments and destructive-operation tests.
7. **Extended MVP:** investments/assets/debt, goals, exports/reporting and proactive alerts.

## 23. Change control
This document is the implementation requirements baseline. New product behavior should be evaluated as a change against this baseline rather than silently added to Release 1. Material changes should increment the specification version and identify impact on the data model, API, migrations, UX and acceptance criteria.

### Version 1.1 change impact

- **Data model and migration:** adds per-user investment portfolio settings and selected-position
  planning rows inside each existing data plane.
- **API:** adds authenticated market-data and portfolio endpoints under `/api/v1/investments`;
  writes remain CSRF-protected.
- **UX:** promotes the approved investment concept to a first-class tab with transparent delayed
  data and a trailing-12-month dividend estimate.
- **Operations:** adds one optional server-side EODHD token and a bounded cache; the token is never
  sent to the browser or stored in PostgreSQL.
- **Boundary:** this opt-in slice does not make external market data a release blocker and does not
  change ledger, investment-trade, income or valuation-snapshot semantics.

### Version 1.2 change impact

- **Provider:** Yahoo Finance becomes the keyless default for the curated Stockholm market-data
  adapter. EODHD remains an explicit operator-selected alternative.
- **Reliability:** provider responses use a bounded in-process cache and conservative retry policy.
  When a refresh fails after a successful retrieval, the last snapshot remains visible and is
  explicitly marked stale; fictional values are never substituted.
- **API and UX:** market-data responses add a stale indicator, while the Investments tab derives its
  source label dynamically and continues to show market date, retrieval time, delay and the
  trailing-12-month dividend basis.
- **Boundary:** external observations remain derived, non-canonical data and never create or modify
  investment trades, valuation snapshots, dividends received or other economic history.

### Version 1.3 change impact

- **Provider and coverage:** the Yahoo adapter discovers Stockholm equities dynamically through
  exchange and sector queries instead of a maintained nine-share list. Temporary subscription
  instruments, rights and structured products are excluded.
- **API:** the market-data endpoint returns the cached exchange catalog by default and accepts up to
  50 repeated `ticker` parameters for detailed one-year history and dividend-month enrichment.
  Portfolio writes are validated against the current discovered catalog.
- **Data model and migration:** investment ticker capacity increases from 16 to 32 characters so
  the wider universe can be persisted without changing existing position identities.
- **UX and performance:** the Investments tab searches and filters the full cached catalog, renders
  it in batches of 50 and loads heavier 1-month, 6-month and dividend-event history only for selected
  shares. Source, count, freshness and the historical estimate basis remain visible.
- **Boundary:** catalog and history observations remain derived external data. They never create or
  alter investment trades, valuation snapshots, dividend-income events or ledger history.
