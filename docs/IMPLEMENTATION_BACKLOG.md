# Cost Review - Initial Implementation Backlog

Derived from Product Specification v1.0. This backlog deliberately prioritizes domain correctness and Production/Test isolation before advanced UI.

## Epic 1 - Platform foundation
**Goal:** reproducible, persistent and secure application skeleton.

- CR-001 Docker Compose with frontend, backend/API and PostgreSQL services.
- CR-002 Persistent volumes and environment-based configuration.
- CR-003 Database migration framework and initial schema bootstrap.
- CR-004 First-run setup wizard and setup lock after initial user.
- CR-005 Local authentication, secure password hashing and session/cookie configuration.
- CR-006 Independent language, region, base currency and timezone settings.
- CR-007 Reverse-proxy/Cloudflare-safe trusted host/origin/proxy configuration.
- CR-008 Establish hard Production vs Demo/Test data boundary and automated isolation tests.

**Exit gate:** recreate containers without data loss; authenticate; switch to persistent test environment; destructive test operation cannot mutate production.

## Epic 2 - Ledger and master data
**Goal:** trustworthy economic source of truth.

- CR-010 Account CRUD with fixed account types, free names, opening balance/effective date and metadata.
- CR-011 Category CRUD with arbitrary-depth hierarchy.
- CR-012 Provider CRUD with aliases and provider links.
- CR-013 Tag CRUD, archive and merge.
- CR-014 Sharing Party CRUD and percentage allocations.
- CR-015 Transaction CRUD with transaction date + posting date and source metadata.
- CR-016 Expense and income semantics.
- CR-017 Internal transfer linking between owned accounts.
- CR-018 Refund and reimbursement links.
- CR-019 Split transactions with category/tag/base-cost/share data per split.
- CR-020 Multi-currency persistence and FX-rate status/manual override.
- CR-021 Account calculated balances, reconciliation and explicit balance adjustments.
- CR-022 Soft delete, Recycle Bin, restore and dependency-aware permanent deletion.
- CR-023 Central/object-level audit history and frozen historical account snapshots.
- CR-024 Bulk transaction edit with audit trail.

**Exit gate:** representative ledger test suite proves no double counting across transfers, card repayment, refunds, reimbursements, splits and sharing.

## Epic 3 - Recurring / Expected transactions
**Goal:** model future known cash events without contaminating actuals.

- CR-030 RecurringDefinition + version/effective-date model.
- CR-031 Fixed and variable recurring income/expense.
- CR-032 Configurable global variable-amount tolerance.
- CR-033 Generate Expected occurrences without affecting actual balances.
- CR-034 Confirm Expected occurrence as Actual.
- CR-035 Candidate matching with visible confidence and user approval.
- CR-036 Attention items for pending confirmation and deviations.
- CR-037 Optional periodization metadata for annual/quarterly costs.

## Epic 4 - Import, staging and rules
**Goal:** safe, explainable ingestion from CSV/XLSX.

- CR-040 Create Import Provider Profile from uploaded CSV/XLSX sample.
- CR-041 File preview and source-column mapping.
- CR-042 Persist profile transforms such as date/sign conventions.
- CR-043 Suggest saved profile with match confidence percentage.
- CR-044 Preview interpreted import before staging.
- CR-045 Row-level staging validation and direct corrections.
- CR-046 Bulk edit and partial approval in staging.
- CR-047 Duplicate candidates with confidence and explanation.
- CR-048 Split imported row in staging.
- CR-049 Rules CRUD, enable/disable and user-editable priority.
- CR-050 Visible rule conflicts with explanation; never silently resolve.
- CR-051 Import Batch history and persistent source metadata.
- CR-052 Undo Import with impact preview and soft delete.

**Exit gate:** malformed or ambiguous files cannot silently create incorrect production transactions.

## Epic 5 - Common filters, analysis and dashboards
**Goal:** one analytical selection language across the product.

- CR-060 Common backend filter/query model.
- CR-061 Transaction search: free text + date/account/category/provider/tag/base-cost/recurring/amount/currency.
- CR-062 Saved filters/views CRUD.
- CR-063 Provider and category links in analysis.
- CR-064 Analysis Groups CRUD and reuse.
- CR-065 Predefined Overview, Expenses, Income, Budget and Investments dashboards.
- CR-066 Common period presets, arbitrary date range and comparison periods.
- CR-067 Drill-down from chart/widget to filtered transactions.
- CR-068 Move/resize/hide/show widgets.
- CR-069 Save multiple named dashboard layouts and switch between them.
- CR-070 Reset dashboard to default layout.
- CR-071 Total vs My Share and Actual vs Periodized perspectives.

## Epic 6 - Budget
**Goal:** flexible budgeting built on the same filter engine.

- CR-080 Budget CRUD.
- CR-081 Reset vs rollover per budget.
- CR-082 Calendar month, salary-to-salary, year and custom periods.
- CR-083 Budget selection using common filters and Analysis Groups.
- CR-084 Detect and clearly flag overlapping budgets.
- CR-085 Total/My Share and Actual/Periodized budget consumption.

## Epic 7 - Backup, attachments and resilience
**Goal:** prove the user can recover their data.

- CR-090 Scheduled and manual backup creation.
- CR-091 Encrypted backup format including DB, configuration and attachments.
- CR-092 Password-protected manual backup and installation-key automatic backup.
- CR-093 Restore validation before overwrite.
- CR-094 Configurable backup frequency/storage.
- CR-095 Retention by count or age; manual backups exempt.
- CR-096 Automated backup/restore integration test.
- CR-097 Multiple PDF/JPG/PNG/WebP attachments per transaction.
- CR-098 File type and configurable size validation plus browser preview.

## Epic 8 - Demo/Test operations
**Goal:** persistent safe sandbox for realistic experimentation.

- CR-100 Persistent long-lived Demo/Test environment.
- CR-101 Unmistakable DEMO/TEST visual state.
- CR-102 Full transaction/budget/rule/import simulation in test.
- CR-103 Delete all test data with strong confirmation and isolation proof.
- CR-104 Selective one-way Production -> Test configuration copy.
- CR-105 Preview configuration copy.
- CR-106 Per-object conflict resolution: keep test / replace / copy / skip.

## Epic 9 - Extended MVP finance
- CR-110 Value-based accounts and valuation snapshots.
- CR-111 Asset and liability objects plus Financial/Total Net Worth.
- CR-112 Manual investment value/transaction semantics.
- CR-113 Financial Rules settings for relevant income, savings/wealth rates, base cost and net worth.
- CR-114 Savings/debt goals with history/versioning and common filter selection.
- CR-115 Data export CSV/Excel, chart image/PDF and printable report view.
- CR-116 Configurable proactive in-app economic alerts through Attention.

## Post-MVP backlog
- OCR/receipt interpretation.
- Market price/dividend providers and exact security holdings.
- Direct bank/open-banking integrations.
- Advanced cash-flow forecast/scenario engine.
- External push/email notifications.
- TOTP/2FA.
- Full arbitrary dashboard/widget builder.
- Native mobile apps.
