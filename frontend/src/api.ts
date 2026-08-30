export type Environment = "production" | "test";
export type Language = "sv" | "en";

export type EnvironmentStatus = {
  environment: Environment;
  label: string;
  data_plane_id: string;
  reset_generation: number;
  setup_required: boolean;
};

export type AppSettings = {
  language: Language;
  region: string;
  base_currency: string;
  timezone: string;
  date_format: "YYYY-MM-DD" | "DD/MM/YYYY" | "MM/DD/YYYY";
  number_format: "space-comma" | "comma-dot" | "dot-comma";
  week_start: "monday" | "saturday" | "sunday";
};

export type Session = {
  username: string;
  environment: Environment;
  environment_label: string;
  data_plane_id: string;
  reset_generation: number;
  expires_at: string;
  settings: AppSettings;
};

export type LifecycleStatus = "active" | "archived";

export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type AccountType =
  | "current"
  | "savings"
  | "credit_card"
  | "investment"
  | "loan_debt"
  | "value_based"
  | "cash"
  | "other";

export type Account = {
  account_id: number;
  name: string;
  account_type: AccountType;
  opening_balance: string;
  opening_balance_date: string;
  currency: string;
  interest_rate: string | null;
  is_locked: boolean;
  lock_start_date: string | null;
  lock_end_date: string | null;
  notes: string | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AccountSnapshot = {
  account_snapshot_id: number;
  account_id: number;
  valuation_date: string;
  reported_balance: string;
  currency: string;
  converted_balance: string | null;
  base_currency: string;
  fx_rate: string | null;
  fx_rate_status: "not_required" | "manual" | "automatic" | "missing";
  calculated_balance: string | null;
  difference: string | null;
  calculation_status: "complete" | "incomplete";
  notes: string | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Category = {
  category_id: number;
  parent_category_id: number | null;
  name: string;
  category_kind: "expense" | "income";
  notes: string | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Provider = {
  provider_id: number;
  name: string;
  website: string | null;
  notes: string | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Tag = {
  tag_id: number;
  name: string;
  color: string | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SharingParty = {
  sharing_party_id: number;
  name: string;
  is_self: boolean;
  notes: string | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SelectionMode = "include" | "exclude";
export type CategorySelection = {
  category_id: number;
  mode: SelectionMode;
  include_descendants: boolean;
};
export type TagSelection = { tag_id: number; mode: SelectionMode };
export type AccountSelection = { account_id: number; mode: SelectionMode };
export type ProviderSelection = { provider_id: number; mode: SelectionMode };

export type AnalysisGroup = {
  analysis_group_id: number;
  name: string;
  notes: string | null;
  categories: CategorySelection[];
  tags: TagSelection[];
  accounts: AccountSelection[];
  providers: ProviderSelection[];
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BudgetPeriodType =
  | "calendar_month"
  | "salary_cycle"
  | "calendar_year"
  | "custom";
export type BudgetRolloverMode = "reset" | "rollover";

export type Budget = {
  budget_id: number;
  analysis_group_id: number | null;
  name: string;
  amount: string;
  currency: string;
  period_type: BudgetPeriodType;
  rollover_mode: BudgetRolloverMode;
  starts_on: string;
  ends_on: string | null;
  anchor_day: number;
  notes: string | null;
  categories: CategorySelection[];
  tags: TagSelection[];
  accounts: AccountSelection[];
  providers: ProviderSelection[];
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type BudgetInput = {
  name: string;
  amount: string;
  currency: string;
  period_type: BudgetPeriodType;
  rollover_mode: BudgetRolloverMode;
  starts_on: string;
  ends_on: string | null;
  anchor_day: number;
  analysis_group_id: number | null;
  notes: string | null;
  categories: CategorySelection[];
  tags: TagSelection[];
  accounts: AccountSelection[];
  providers: ProviderSelection[];
};

export type BudgetOutcome = {
  budget: Budget;
  date_from: string;
  date_to: string;
  base_currency: string;
  target_amount: string;
  actual_amount: string;
  remaining_amount: string;
  consumed_percent: string;
  period_count: number;
  rollover_adjustment: string;
  matched_transaction_count: number;
  missing_fx_count: number;
  overlapping_budget_ids: number[];
};

export type BudgetTransaction = {
  transaction_id: number;
  transaction_date: string;
  description: string;
  transaction_kind: TransactionKind;
  matched_amount: string;
  base_currency: string;
};

export type BudgetTrendPoint = {
  period_start: string;
  period_end: string;
  target_amount: string;
  actual_amount: string;
  remaining_amount: string;
  consumed_percent: string;
  missing_fx_count: number;
};

export type BudgetTrend = {
  budget_id: number;
  base_currency: string;
  points: BudgetTrendPoint[];
};

export type ManualTransactionKind = "expense" | "income";
export type RecoveryKind = "refund" | "reimbursement";
export type TransactionKind = ManualTransactionKind | RecoveryKind;
export type TransferPurpose =
  | "internal"
  | "savings"
  | "investment"
  | "credit_card_payment"
  | "debt_repayment";

export type Transaction = {
  transaction_id: number;
  account_id: number;
  provider_id: number | null;
  transaction_kind: TransactionKind;
  transaction_date: string;
  posting_date: string;
  description: string;
  original_amount: string;
  original_currency: string;
  converted_amount: string | null;
  base_currency: string;
  fx_rate: string | null;
  fx_rate_status: "not_required" | "manual" | "automatic" | "missing";
  source_type: "manual" | "import" | "recurring" | "system";
  source_reference: string | null;
  notes: string | null;
  category_id: number | null;
  tag_ids: number[];
  is_base_cost: boolean;
  is_split: boolean;
  splits: TransactionSplit[];
  linked_expense_id: number | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type TransactionSplit = {
  transaction_split_id: number;
  original_amount: string;
  converted_amount: string | null;
  category_id: number | null;
  tag_ids: number[];
  is_base_cost: boolean;
  memo: string | null;
};

export type TransactionSplitInput = {
  original_amount: string;
  category_id: number | null;
  tag_ids: number[];
  is_base_cost: boolean;
  memo?: string | null;
};

export type TransactionInput = {
  account_id: number;
  provider_id: number | null;
  transaction_kind: ManualTransactionKind;
  transaction_date: string;
  posting_date: string;
  description: string;
  original_amount: string;
  original_currency: string;
  converted_amount?: string | null;
  fx_rate?: string | null;
  category_id: number | null;
  tag_ids: number[];
  is_base_cost: boolean;
  splits?: TransactionSplitInput[] | null;
  source_reference?: string | null;
  notes?: string | null;
};

export type RecoveryInput = {
  account_id: number;
  provider_id?: number | null;
  transaction_date: string;
  posting_date: string;
  description: string;
  original_amount: string;
  original_currency: string;
  converted_amount?: string | null;
  source_reference?: string | null;
  notes?: string | null;
};

export type Transfer = {
  transfer_link_id: number;
  source_account_id: number;
  destination_account_id: number;
  purpose: TransferPurpose;
  transaction_date: string;
  source_posting_date: string;
  destination_posting_date: string;
  description: string;
  source_amount: string;
  source_currency: string;
  source_converted_amount: string | null;
  source_fx_rate: string | null;
  source_fx_rate_status: "not_required" | "manual" | "automatic" | "missing";
  destination_amount: string;
  destination_currency: string;
  destination_converted_amount: string | null;
  destination_fx_rate: string | null;
  destination_fx_rate_status: "not_required" | "manual" | "automatic" | "missing";
  base_currency: string;
  source_reference: string | null;
  notes: string | null;
  status: LifecycleStatus;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
};

export type TransferInput = {
  source_account_id: number;
  destination_account_id: number;
  purpose: TransferPurpose;
  transaction_date: string;
  source_posting_date: string;
  destination_posting_date: string;
  description: string;
  source_amount: string;
  destination_amount: string;
  source_converted_amount?: string | null;
  source_fx_rate?: string | null;
  destination_converted_amount?: string | null;
  destination_fx_rate?: string | null;
  source_reference?: string | null;
  notes?: string | null;
};

export type LedgerSummary = {
  date_from: string;
  date_to: string;
  base_currency: string;
  income: string;
  expenses: string;
  net_cash_flow: string;
  transaction_count: number;
  missing_fx_count: number;
};

export type LedgerTrendPoint = {
  date: string;
  income: string;
  expenses: string;
  net_cash_flow: string;
};

export type LedgerCategoryBreakdown = {
  category_id: number | null;
  category_name: string | null;
  amount: string;
  transaction_count: number;
};

export type LedgerAnalysis = {
  date_from: string;
  date_to: string;
  base_currency: string;
  daily: LedgerTrendPoint[];
  expense_categories: LedgerCategoryBreakdown[];
  comparison: LedgerComparison | null;
};

export type AnalysisComparisonMode = "none" | "previous_period" | "previous_year";

export type LedgerComparison = {
  mode: Exclude<AnalysisComparisonMode, "none">;
  date_from: string;
  date_to: string;
  income: string;
  expenses: string;
  net_cash_flow: string;
  daily: LedgerTrendPoint[];
  expense_categories: LedgerCategoryBreakdown[];
};

export type LedgerFilters = {
  accountId?: number | null;
  providerId?: number | null;
  categoryId?: number | null;
  tagId?: number | null;
  isBaseCost?: boolean | null;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

const csrfCookieNames: Record<Environment, string> = {
  production: "cost_review_production_csrf",
  test: "cost_review_test_csrf",
};

function apiBase(environment: Environment): string {
  return `/api/${environment}/v1`;
}

async function request<T>(
  environment: Environment,
  path: string,
  init: RequestInit = {},
  csrf = false,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (csrf) {
    const token = readCookie(csrfCookieNames[environment]);
    if (token) {
      headers.set("X-CSRF-Token", token);
    }
  }

  const response = await fetch(`${apiBase(environment)}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: { code?: string; message?: string } }
      | null;
    throw new ApiError(
      response.status,
      payload?.error?.code ?? "request_failed",
      payload?.error?.message ?? "Cost Review API is unavailable.",
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function getSetupStatus(environment: Environment): Promise<EnvironmentStatus> {
  return request(environment, "/setup/status");
}

export function getSession(environment: Environment): Promise<Session> {
  return request(environment, "/auth/session");
}

export function setup(
  environment: Environment,
  username: string,
  password: string,
  settings: AppSettings,
): Promise<Session> {
  return request(environment, "/setup", {
    method: "POST",
    body: JSON.stringify({ username, password, settings }),
  });
}

export function login(
  environment: Environment,
  username: string,
  password: string,
): Promise<Session> {
  return request(environment, "/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout(environment: Environment): Promise<void> {
  return request(environment, "/auth/logout", { method: "POST" }, true);
}

export function saveSettings(
  environment: Environment,
  settings: AppSettings,
): Promise<AppSettings> {
  return request(
    environment,
    "/settings",
    { method: "PATCH", body: JSON.stringify(settings) },
    true,
  );
}

export function resetTestEnvironment(confirmation: string): Promise<{
  reset_generation: number;
  message: string;
}> {
  return request(
    "test",
    "/test/reset",
    { method: "POST", body: JSON.stringify({ confirmation }) },
    true,
  );
}

export function getAccounts(
  environment: Environment,
  includeArchived = false,
): Promise<Page<Account>> {
  return request(environment, `/accounts?include_archived=${includeArchived}`);
}

export function createAccount(
  environment: Environment,
  payload: {
    name: string;
    account_type: AccountType;
    opening_balance: string;
    opening_balance_date: string;
    currency: string;
  },
): Promise<Account> {
  return request(
    environment,
    "/accounts",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function setAccountArchived(
  environment: Environment,
  accountId: number,
  archived: boolean,
): Promise<Account> {
  return request(
    environment,
    `/accounts/${accountId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function getAccountSnapshots(
  environment: Environment,
  accountId: number,
): Promise<AccountSnapshot[]> {
  return request(environment, `/accounts/${accountId}/snapshots`);
}

export function createAccountSnapshot(
  environment: Environment,
  accountId: number,
  payload: { valuation_date: string; reported_balance: string; notes?: string | null },
): Promise<AccountSnapshot> {
  return request(
    environment,
    `/accounts/${accountId}/snapshots`,
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function getCategories(
  environment: Environment,
  includeArchived = false,
): Promise<Page<Category>> {
  return request(environment, `/categories?include_archived=${includeArchived}`);
}

export function createCategory(
  environment: Environment,
  payload: {
    name: string;
    category_kind: "expense" | "income";
    parent_category_id: number | null;
  },
): Promise<Category> {
  return request(
    environment,
    "/categories",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function setCategoryArchived(
  environment: Environment,
  categoryId: number,
  archived: boolean,
): Promise<Category> {
  return request(
    environment,
    `/categories/${categoryId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function getProviders(
  environment: Environment,
  includeArchived = false,
): Promise<Page<Provider>> {
  return request(environment, `/providers?include_archived=${includeArchived}`);
}

export function createProvider(
  environment: Environment,
  payload: { name: string; website?: string },
): Promise<Provider> {
  return request(
    environment,
    "/providers",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function setProviderArchived(
  environment: Environment,
  providerId: number,
  archived: boolean,
): Promise<Provider> {
  return request(
    environment,
    `/providers/${providerId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function getTags(
  environment: Environment,
  includeArchived = false,
): Promise<Page<Tag>> {
  return request(environment, `/tags?include_archived=${includeArchived}`);
}

export function createTag(
  environment: Environment,
  payload: { name: string; color?: string },
): Promise<Tag> {
  return request(
    environment,
    "/tags",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function setTagArchived(
  environment: Environment,
  tagId: number,
  archived: boolean,
): Promise<Tag> {
  return request(
    environment,
    `/tags/${tagId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function getSharingParties(
  environment: Environment,
  includeArchived = false,
): Promise<Page<SharingParty>> {
  return request(environment, `/sharing-parties?include_archived=${includeArchived}`);
}

export function createSharingParty(
  environment: Environment,
  payload: { name: string; is_self: boolean },
): Promise<SharingParty> {
  return request(
    environment,
    "/sharing-parties",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function setSharingPartyArchived(
  environment: Environment,
  partyId: number,
  archived: boolean,
): Promise<SharingParty> {
  return request(
    environment,
    `/sharing-parties/${partyId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function getAnalysisGroups(
  environment: Environment,
  includeArchived = false,
): Promise<AnalysisGroup[]> {
  return request(environment, `/analysis-groups?include_archived=${includeArchived}`);
}

export function createAnalysisGroup(
  environment: Environment,
  payload: Omit<AnalysisGroup, "analysis_group_id" | "status" | "archived_at" | "created_at" | "updated_at">,
): Promise<AnalysisGroup> {
  return request(environment, "/analysis-groups", { method: "POST", body: JSON.stringify(payload) }, true);
}

export function getBudgets(
  environment: Environment,
  includeArchived = false,
): Promise<Budget[]> {
  return request(environment, `/budgets?include_archived=${includeArchived}`);
}

export function createBudget(
  environment: Environment,
  payload: BudgetInput,
): Promise<Budget> {
  return request(environment, "/budgets", { method: "POST", body: JSON.stringify(payload) }, true);
}

export function updateBudget(
  environment: Environment,
  budgetId: number,
  payload: BudgetInput,
): Promise<Budget> {
  return request(environment, `/budgets/${budgetId}`, { method: "PATCH", body: JSON.stringify(payload) }, true);
}

export function setBudgetArchived(
  environment: Environment,
  budgetId: number,
  archived: boolean,
): Promise<Budget> {
  return request(environment, `/budgets/${budgetId}/${archived ? "archive" : "restore"}`, { method: "POST" }, true);
}

export function getBudgetOutcome(
  environment: Environment,
  budgetId: number,
  dateFrom: string,
  dateTo: string,
): Promise<BudgetOutcome> {
  const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  return request(environment, `/budgets/${budgetId}/outcome?${query.toString()}`);
}

export function getBudgetTransactions(
  environment: Environment,
  budgetId: number,
  dateFrom: string,
  dateTo: string,
): Promise<BudgetTransaction[]> {
  const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  return request(environment, `/budgets/${budgetId}/transactions?${query.toString()}`);
}

export function getBudgetTrend(
  environment: Environment,
  budgetId: number,
  through: string,
  periods = 6,
): Promise<BudgetTrend> {
  const query = new URLSearchParams({ through, periods: String(periods) });
  return request(environment, `/budgets/${budgetId}/trend?${query.toString()}`);
}

export function getTransactions(
  environment: Environment,
  filters: {
    dateFrom?: string;
    dateTo?: string;
    kind?: TransactionKind | "";
    accountId?: number | null;
    categoryId?: number | null;
    providerId?: number | null;
    tagId?: number | null;
    isBaseCost?: boolean | null;
    originalCurrency?: string;
    amountMin?: string;
    amountMax?: string;
    search?: string;
    includeArchived?: boolean;
    limit?: number;
  } = {},
): Promise<Page<Transaction>> {
  const query = new URLSearchParams();
  query.set("limit", String(filters.limit ?? 100));
  if (filters.dateFrom) query.set("date_from", filters.dateFrom);
  if (filters.dateTo) query.set("date_to", filters.dateTo);
  if (filters.kind) query.set("transaction_kind", filters.kind);
  if (filters.accountId) query.set("account_id", String(filters.accountId));
  if (filters.categoryId) query.set("category_id", String(filters.categoryId));
  if (filters.providerId) query.set("provider_id", String(filters.providerId));
  if (filters.tagId) query.set("tag_id", String(filters.tagId));
  if (filters.isBaseCost !== undefined && filters.isBaseCost !== null) {
    query.set("is_base_cost", String(filters.isBaseCost));
  }
  if (filters.originalCurrency) query.set("original_currency", filters.originalCurrency);
  if (filters.amountMin) query.set("amount_min", filters.amountMin);
  if (filters.amountMax) query.set("amount_max", filters.amountMax);
  if (filters.search?.trim()) query.set("search", filters.search.trim());
  if (filters.includeArchived) query.set("include_archived", "true");
  return request(environment, `/transactions?${query.toString()}`);
}

export function getLedgerSummary(
  environment: Environment,
  dateFrom: string,
  dateTo: string,
  filters: LedgerFilters = {},
): Promise<LedgerSummary> {
  const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo });
  appendLedgerFilters(query, filters);
  return request(environment, `/transactions/summary?${query.toString()}`);
}

export function getLedgerAnalysis(
  environment: Environment,
  dateFrom: string,
  dateTo: string,
  comparison: AnalysisComparisonMode = "none",
  filters: LedgerFilters = {},
): Promise<LedgerAnalysis> {
  const query = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    comparison,
  });
  appendLedgerFilters(query, filters);
  return request(environment, `/transactions/analysis?${query.toString()}`);
}

function appendLedgerFilters(query: URLSearchParams, filters: LedgerFilters): void {
  if (filters.accountId) query.set("account_id", String(filters.accountId));
  if (filters.providerId) query.set("provider_id", String(filters.providerId));
  if (filters.categoryId) query.set("category_id", String(filters.categoryId));
  if (filters.tagId) query.set("tag_id", String(filters.tagId));
  if (filters.isBaseCost !== undefined && filters.isBaseCost !== null) {
    query.set("is_base_cost", String(filters.isBaseCost));
  }
}

export function createTransaction(
  environment: Environment,
  payload: TransactionInput,
): Promise<Transaction> {
  return request(
    environment,
    "/transactions",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function updateTransaction(
  environment: Environment,
  transactionId: number,
  payload: Partial<TransactionInput>,
): Promise<Transaction> {
  return request(
    environment,
    `/transactions/${transactionId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
    true,
  );
}

export function setTransactionArchived(
  environment: Environment,
  transactionId: number,
  archived: boolean,
): Promise<Transaction> {
  return request(
    environment,
    `/transactions/${transactionId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function createRecovery(
  environment: Environment,
  expenseId: number,
  kind: RecoveryKind,
  payload: RecoveryInput,
): Promise<Transaction> {
  const resource = kind === "refund" ? "refunds" : "reimbursements";
  return request(
    environment,
    `/transactions/${expenseId}/${resource}`,
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function setRecoveryArchived(
  environment: Environment,
  transactionId: number,
  archived: boolean,
): Promise<Transaction> {
  return request(
    environment,
    `/recoveries/${transactionId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function getTransfers(
  environment: Environment,
  filters: {
    dateFrom?: string;
    dateTo?: string;
    accountId?: number | null;
    purpose?: TransferPurpose | "";
    search?: string;
    includeArchived?: boolean;
    limit?: number;
  } = {},
): Promise<Page<Transfer>> {
  const query = new URLSearchParams();
  query.set("limit", String(filters.limit ?? 100));
  if (filters.dateFrom) query.set("date_from", filters.dateFrom);
  if (filters.dateTo) query.set("date_to", filters.dateTo);
  if (filters.accountId) query.set("account_id", String(filters.accountId));
  if (filters.purpose) query.set("purpose", filters.purpose);
  if (filters.search?.trim()) query.set("search", filters.search.trim());
  if (filters.includeArchived) query.set("include_archived", "true");
  return request(environment, `/transfers?${query.toString()}`);
}

export function createTransfer(
  environment: Environment,
  payload: TransferInput,
): Promise<Transfer> {
  return request(
    environment,
    "/transfers",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function updateTransfer(
  environment: Environment,
  transferId: number,
  payload: Partial<TransferInput>,
): Promise<Transfer> {
  return request(
    environment,
    `/transfers/${transferId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
    true,
  );
}

export function setTransferArchived(
  environment: Environment,
  transferId: number,
  archived: boolean,
): Promise<Transfer> {
  return request(
    environment,
    `/transfers/${transferId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

function readCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`;
  const entry = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}
