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

function readCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`;
  const entry = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}
