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

function readCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`;
  const entry = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}
