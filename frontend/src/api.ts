export type Environment = "production" | "test";
export type Language = "sv" | "en";

export type EnvironmentStatus = {
  environment: Environment;
  label: string;
  data_plane_id: string;
  reset_generation: number;
  setup_required: boolean;
  registration_allowed: boolean;
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

export type UserRole = "owner" | "member" | "viewer";

export type Session = {
  user_id: number;
  username: string;
  role: UserRole;
  environment: Environment;
  environment_label: string;
  data_plane_id: string;
  reset_generation: number;
  expires_at: string;
  settings: AppSettings;
};

export type HouseholdMember = {
  user_id: number;
  username: string;
  role: UserRole;
};

export type UserAccount = {
  user_id: number;
  username: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
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

export type Backup = {
  filename: string;
  environment: Environment;
  kind: "manual" | "automatic" | "pre_restore";
  created_at: string;
  size_bytes: number;
};

export type BackupValidation = {
  filename: string;
  environment: Environment;
  data_plane_id: string;
  created_at: string;
  schema_revision: string;
  file_count: number;
  valid: boolean;
};

export type RecycleBinItem = {
  entity_type: string;
  entity_id: number;
  label: string;
  archived_at: string;
  restore_path: string;
};

export type AuditEvent = {
  audit_event_id: number;
  entity_type: string;
  entity_id: number | null;
  action: string;
  change_source: string;
  changes: Record<string, unknown>;
  created_at: string;
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
  user_id: number | null;
  username: string | null;
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
  perspective: AnalysisPerspective;
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
  perspective: AnalysisPerspective;
  points: BudgetTrendPoint[];
};

export type ManualTransactionKind = "expense" | "income";
export type RecoveryKind = "refund" | "reimbursement";
export type TransactionKind = ManualTransactionKind | RecoveryKind | "adjustment";
export type AnalysisPerspective = "total" | "my_share";
export type ShareAllocation = {
  sharing_party_id: number;
  percentage: string;
  user_id: number | null;
};
export type ShareAllocationInput = {
  sharing_party_id: number;
  percentage: string;
};
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
  adjustment_direction: "increase" | "decrease" | null;
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
  sharing_allocations: ShareAllocation[];
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
  sharing_allocations: ShareAllocation[];
};

export type TransactionSplitInput = {
  original_amount: string;
  category_id: number | null;
  tag_ids: number[];
  is_base_cost: boolean;
  memo?: string | null;
  sharing_allocations?: ShareAllocationInput[];
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
  sharing_allocations?: ShareAllocationInput[];
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
  perspective: AnalysisPerspective;
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
  perspective: AnalysisPerspective;
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

export type InvestmentMarketStock = {
  ticker: string;
  provider_symbol: string;
  name: string;
  sector: string;
  currency: string;
  price: string;
  price_date: string;
  changes: {
    one_day: string;
    one_month: string | null;
    six_months: string | null;
    one_year: string;
  };
  annual_dividend_per_share: string;
  dividend_yield: string;
  dividend_pattern: Array<{
    month: number;
    amount: string;
    date_basis: "payment_date" | "ex_dividend_date";
  }>;
  detail_level: "summary" | "history";
};

export type InvestmentMarketData = {
  source: string;
  source_url: string;
  exchange: string;
  retrieved_at: string;
  data_date: string;
  is_delayed: boolean;
  is_stale: boolean;
  estimate_basis: "trailing_12_months";
  universe_note: string;
  stock_count: number;
  stocks: InvestmentMarketStock[];
  unavailable_symbols: string[];
};

export type InvestmentDividendOpportunity = {
  ticker: string;
  name: string;
  sector: string;
  currency: string;
  price: string;
  annual_dividend_per_share: string;
  dividend_yield: string;
  payments_per_year: number;
  compared_cycles: number;
};

export type InvestmentDividendOpportunities = {
  source: string;
  source_url: string;
  retrieved_at: string;
  is_delayed: boolean;
  is_stale: boolean;
  candidate_count: number;
  qualified_count: number;
  excluded_count: number;
  unavailable_count: number;
  opportunities: InvestmentDividendOpportunity[];
};

export type InvestmentFund = {
  isin: string;
  provider_id: string;
  name: string;
  category: string;
  fund_type: string;
  fund_company: string;
  currency: string;
  nav: string;
  nav_date: string;
  changes: {
    one_day: string;
    one_month: string | null;
    six_months: string | null;
    one_year: string;
  };
  product_fee: string;
  management_fee: string;
  risk: number | null;
  rating: number | null;
  index_fund: boolean;
};

export type InvestmentFundData = {
  source: string;
  source_url: string;
  retrieved_at: string;
  data_date: string | null;
  is_delayed: boolean;
  is_stale: boolean;
  query: string | null;
  result_count: number;
  funds: InvestmentFund[];
  unavailable_isins: string[];
};

export type InvestmentPortfolio = {
  purchase_budget: string;
  currency: string;
  positions: Array<{
    instrument_type: "stock" | "fund";
    ticker: string;
    shares: string;
    target_percentage: string;
  }>;
  updated_at: string | null;
};

export type LedgerFilters = {
  accountId?: number | null;
  providerId?: number | null;
  categoryId?: number | null;
  tagId?: number | null;
  isBaseCost?: boolean | null;
  perspective?: AnalysisPerspective;
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
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
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
    const fallback =
      response.status === 429
        ? "Too many attempts. Wait a few minutes and try again."
        : "Cost Review API is unavailable.";
    throw new ApiError(
      response.status,
      payload?.error?.code ?? (response.status === 429 ? "rate_limited" : "request_failed"),
      payload?.error?.message ?? fallback,
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

export function registerAccount(
  environment: Environment,
  username: string,
  password: string,
  settings: AppSettings,
): Promise<Session> {
  return request(environment, "/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password, settings }),
  });
}

export function logout(environment: Environment): Promise<void> {
  return request(environment, "/auth/logout", { method: "POST" }, true);
}

export function changePassword(
  environment: Environment,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  return request(
    environment,
    "/auth/password",
    {
      method: "PATCH",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    },
    true,
  );
}

export function getHouseholdMembers(environment: Environment): Promise<HouseholdMember[]> {
  return request(environment, "/household/members");
}

export function getUsers(environment: Environment): Promise<UserAccount[]> {
  return request(environment, "/users");
}

export function createUser(
  environment: Environment,
  username: string,
  password: string,
  role: UserRole,
  settings: AppSettings,
): Promise<UserAccount> {
  return request(
    environment,
    "/users",
    {
      method: "POST",
      body: JSON.stringify({ username, password, role, settings }),
    },
    true,
  );
}

export function updateUser(
  environment: Environment,
  userId: number,
  values: { username?: string; role?: UserRole },
): Promise<UserAccount> {
  return request(
    environment,
    `/users/${userId}`,
    { method: "PATCH", body: JSON.stringify(values) },
    true,
  );
}

export function resetUserPassword(
  environment: Environment,
  userId: number,
  newPassword: string,
): Promise<void> {
  return request(
    environment,
    `/users/${userId}/reset-password`,
    { method: "POST", body: JSON.stringify({ new_password: newPassword }) },
    true,
  );
}

export function deleteUser(
  environment: Environment,
  userId: number,
  confirmation: string,
): Promise<void> {
  return request(
    environment,
    `/users/${userId}`,
    { method: "DELETE", body: JSON.stringify({ confirmation }) },
    true,
  );
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

export function getInvestmentMarketData(
  environment: Environment,
  tickers: string[] = [],
): Promise<InvestmentMarketData> {
  const query = new URLSearchParams();
  tickers.forEach((ticker) => query.append("ticker", ticker));
  const suffix = query.size ? `?${query.toString()}` : "";
  return request(environment, `/investments/market-data${suffix}`);
}

export function getInvestmentPortfolio(environment: Environment): Promise<InvestmentPortfolio> {
  return request(environment, "/investments/portfolio");
}

export function getInvestmentDividendOpportunities(
  environment: Environment,
): Promise<InvestmentDividendOpportunities> {
  return request(environment, "/investments/dividend-opportunities");
}

export function getInvestmentFundData(
  environment: Environment,
  options: { query?: string; isins?: string[] },
): Promise<InvestmentFundData> {
  const query = new URLSearchParams();
  if (options.query) query.set("query", options.query);
  options.isins?.forEach((isin) => query.append("isin", isin));
  const suffix = query.size ? `?${query.toString()}` : "";
  return request(environment, `/investments/fund-data${suffix}`);
}

export function saveInvestmentPortfolio(
  environment: Environment,
  payload: {
    purchase_budget: string;
    positions: Array<{
      instrument_type: "stock" | "fund";
      ticker: string;
      shares: string;
      target_percentage: string;
    }>;
  },
): Promise<InvestmentPortfolio> {
  return request(
    environment,
    "/investments/portfolio",
    { method: "PUT", body: JSON.stringify(payload) },
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

export function createBalanceAdjustment(
  environment: Environment,
  snapshotId: number,
  confirmation: string,
): Promise<Transaction> {
  return request(
    environment,
    `/account-snapshots/${snapshotId}/adjustment`,
    { method: "POST", body: JSON.stringify({ confirmation }) },
    true,
  );
}

export function getBackups(environment: Environment): Promise<Backup[]> {
  return request(environment, "/backups");
}

export function createBackup(environment: Environment): Promise<Backup> {
  return request(environment, "/backups", { method: "POST" }, true);
}

export function importBackup(
  environment: Environment,
  file: File,
): Promise<BackupValidation> {
  const body = new FormData();
  body.append("file", file, file.name);
  return request(environment, "/backups/import", { method: "POST", body }, true);
}

export function validateBackup(
  environment: Environment,
  filename: string,
): Promise<BackupValidation> {
  return request(
    environment,
    `/backups/${encodeURIComponent(filename)}/validate`,
    { method: "POST" },
    true,
  );
}

export function backupDownloadUrl(environment: Environment, filename: string): string {
  return `${apiBase(environment)}/backups/${encodeURIComponent(filename)}/download`;
}

export function getRecycleBin(environment: Environment): Promise<RecycleBinItem[]> {
  return request(environment, "/recycle-bin");
}

export function getAuditEvents(environment: Environment): Promise<Page<AuditEvent>> {
  return request(environment, "/audit-events?limit=10&offset=0");
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

export function mergeTag(
  environment: Environment,
  sourceTagId: number,
  targetTagId: number,
  confirmation: string,
): Promise<Tag> {
  return request(
    environment,
    `/tags/${sourceTagId}/merge`,
    {
      method: "POST",
      body: JSON.stringify({ target_tag_id: targetTagId, confirmation }),
    },
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
  payload: { name: string; user_id: number | null },
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
  perspective: AnalysisPerspective = "total",
): Promise<BudgetOutcome> {
  const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo, perspective });
  return request(environment, `/budgets/${budgetId}/outcome?${query.toString()}`);
}

export function getBudgetTransactions(
  environment: Environment,
  budgetId: number,
  dateFrom: string,
  dateTo: string,
  perspective: AnalysisPerspective = "total",
): Promise<BudgetTransaction[]> {
  const query = new URLSearchParams({ date_from: dateFrom, date_to: dateTo, perspective });
  return request(environment, `/budgets/${budgetId}/transactions?${query.toString()}`);
}

export function getBudgetTrend(
  environment: Environment,
  budgetId: number,
  through: string,
  periods = 6,
  perspective: AnalysisPerspective = "total",
): Promise<BudgetTrend> {
  const query = new URLSearchParams({ through, periods: String(periods), perspective });
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
  if (filters.perspective) query.set("perspective", filters.perspective);
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

export type ImportRowStatus = "ready" | "duplicate" | "invalid" | "skipped" | "committed";

export type ImportMapping = {
  date_column: string;
  description_column: string;
  amount_column: string | null;
  debit_column: string | null;
  credit_column: string | null;
  posting_date_column: string | null;
  currency_column: string | null;
  reference_column: string | null;
  date_format: string;
  decimal_separator: "," | ".";
  amount_sign: "as_is" | "inverted";
  delimiter: string | null;
  header_row: number;
};

export type ImportPreview = {
  filename: string;
  headers: string[];
  sample_rows: Record<string, unknown>[];
  row_count: number;
  delimiter: string | null;
  suggested_mapping: Partial<ImportMapping> & Record<string, unknown>;
  profile_suggestions: { import_profile_id: number; name: string; confidence: number }[];
  previous_imports: { import_batch_id: number; status: string; created_at: string }[];
};

export type ImportProfile = ImportMapping & {
  import_profile_id: number;
  name: string;
  default_account_id: number | null;
  status: LifecycleStatus;
};

export type ImportBatch = {
  import_batch_id: number;
  import_profile_id: number | null;
  account_id: number;
  filename: string;
  status: "staged" | "committed" | "undone";
  row_count: number;
  status_counts: Record<ImportRowStatus, number>;
  created_by_user_id: number | null;
  created_at: string;
  committed_at: string | null;
  undone_at: string | null;
};

export type ImportRow = {
  import_row_id: number;
  row_number: number;
  raw: Record<string, unknown>;
  transaction_date: string | null;
  posting_date: string | null;
  description: string | null;
  amount: string | null;
  currency: string | null;
  reference: string | null;
  category_id: number | null;
  provider_id: number | null;
  status: ImportRowStatus;
  errors: string[];
  duplicate_transaction_id: number | null;
  duplicate_confidence: number | null;
  duplicate_reason: string | null;
  transaction_id: number | null;
};

export type ImportUndoPreview = {
  import_batch_id: number;
  transaction_count: number;
  active_transaction_count: number;
  expenses: string;
  income: string;
  edited_after_import_count: number;
  linked_recovery_count: number;
  can_undo: boolean;
};

export type ImportRowChange = {
  transaction_date?: string;
  posting_date?: string;
  description?: string;
  amount?: string;
  category_id?: number | null;
  provider_id?: number | null;
  status?: "ready" | "skipped";
};

export function previewImport(environment: Environment, file: File): Promise<ImportPreview> {
  const body = new FormData();
  body.append("file", file, file.name);
  return request(environment, "/imports/preview", { method: "POST", body }, true);
}

export function stageImport(
  environment: Environment,
  file: File,
  options: {
    account_id: number;
    import_profile_id?: number | null;
    mapping?: ImportMapping | null;
    save_profile_name?: string | null;
  },
): Promise<ImportBatch> {
  const body = new FormData();
  body.append("file", file, file.name);
  body.append("options", JSON.stringify(options));
  return request(environment, "/imports", { method: "POST", body }, true);
}

export function getImports(environment: Environment): Promise<Page<ImportBatch>> {
  return request(environment, "/imports?limit=50");
}

export function getImport(environment: Environment, batchId: number): Promise<ImportBatch> {
  return request(environment, `/imports/${batchId}`);
}

export function getImportRows(
  environment: Environment,
  batchId: number,
): Promise<Page<ImportRow>> {
  return request(environment, `/imports/${batchId}/rows?limit=1000`);
}

export function updateImportRow(
  environment: Environment,
  batchId: number,
  rowId: number,
  change: ImportRowChange,
): Promise<ImportRow> {
  return request(
    environment,
    `/imports/${batchId}/rows/${rowId}`,
    { method: "PATCH", body: JSON.stringify(change) },
    true,
  );
}

export function bulkUpdateImportRows(
  environment: Environment,
  batchId: number,
  rowIds: number[],
  change: Pick<ImportRowChange, "status" | "category_id" | "provider_id">,
): Promise<{ updated: number }> {
  return request(
    environment,
    `/imports/${batchId}/rows/bulk`,
    { method: "POST", body: JSON.stringify({ import_row_ids: rowIds, ...change }) },
    true,
  );
}

export function commitImport(environment: Environment, batchId: number): Promise<ImportBatch> {
  return request(environment, `/imports/${batchId}/commit`, { method: "POST" }, true);
}

export function getImportUndoPreview(
  environment: Environment,
  batchId: number,
): Promise<ImportUndoPreview> {
  return request(environment, `/imports/${batchId}/undo-preview`);
}

export function undoImport(
  environment: Environment,
  batchId: number,
  confirmation: string,
): Promise<ImportBatch> {
  return request(
    environment,
    `/imports/${batchId}/undo`,
    { method: "POST", body: JSON.stringify({ confirmation }) },
    true,
  );
}

export function getImportProfiles(environment: Environment): Promise<ImportProfile[]> {
  return request(environment, "/import-profiles");
}

export type RecurringFrequency = "weekly" | "monthly" | "quarterly" | "yearly";

export type RecurringDefinition = {
  recurring_definition_id: number;
  name: string;
  account_id: number;
  provider_id: number | null;
  category_id: number | null;
  transaction_kind: "expense" | "income";
  currency: string;
  frequency: RecurringFrequency;
  interval_count: number;
  start_date: string;
  end_date: string | null;
  tolerance_percent: string;
  notes: string | null;
  versions: { effective_from: string; amount: string; amount_type: "fixed" | "variable" }[];
  status: LifecycleStatus;
};

export type RecurringInput = {
  name: string;
  account_id: number;
  category_id: number | null;
  transaction_kind: "expense" | "income";
  amount: string;
  amount_type: "fixed" | "variable";
  frequency: RecurringFrequency;
  interval_count: number;
  start_date: string;
  end_date: string | null;
};

export type ExpectedOccurrence = {
  recurring_definition_id: number;
  name: string;
  account_id: number;
  transaction_kind: "expense" | "income";
  due_date: string;
  expected_amount: string;
  amount_type: "fixed" | "variable";
  currency: string;
  status: "expected" | "overdue" | "confirmed" | "skipped";
  transaction_id: number | null;
  deviation_percent: string | null;
  outside_tolerance: boolean;
  candidates: {
    transaction_id: number;
    transaction_date: string;
    description: string;
    amount: string;
    confidence: number;
  }[];
};

export function getRecurring(environment: Environment): Promise<RecurringDefinition[]> {
  return request(environment, "/recurring");
}

export function createRecurring(
  environment: Environment,
  payload: RecurringInput,
): Promise<RecurringDefinition> {
  return request(
    environment,
    "/recurring",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function setRecurringArchived(
  environment: Environment,
  definitionId: number,
  archived: boolean,
): Promise<RecurringDefinition> {
  return request(
    environment,
    `/recurring/${definitionId}/${archived ? "archive" : "restore"}`,
    { method: "POST" },
    true,
  );
}

export function getExpectedOccurrences(
  environment: Environment,
  dateFrom: string,
  dateTo: string,
): Promise<ExpectedOccurrence[]> {
  return request(environment, `/recurring/expected?date_from=${dateFrom}&date_to=${dateTo}`);
}

export function confirmOccurrence(
  environment: Environment,
  definitionId: number,
  dueDate: string,
  payload: { transaction_id?: number; amount?: string },
): Promise<ExpectedOccurrence> {
  return request(
    environment,
    `/recurring/${definitionId}/occurrences/${dueDate}/confirm`,
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function skipOccurrence(
  environment: Environment,
  definitionId: number,
  dueDate: string,
): Promise<ExpectedOccurrence> {
  return request(
    environment,
    `/recurring/${definitionId}/occurrences/${dueDate}/skip`,
    { method: "POST" },
    true,
  );
}

export function reopenOccurrence(
  environment: Environment,
  definitionId: number,
  dueDate: string,
): Promise<void> {
  return request(
    environment,
    `/recurring/${definitionId}/occurrences/${dueDate}/reopen`,
    { method: "POST" },
    true,
  );
}
