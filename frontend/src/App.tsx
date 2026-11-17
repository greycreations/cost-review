import { useEffect, useState, type FormEvent } from "react";
import {
  ApiError,
  getSession,
  getSetupStatus,
  login,
  logout,
  registerAccount,
  setup,
  type AppSettings,
  type Environment,
  type EnvironmentStatus,
  type Language,
  type Session,
} from "./api";
import { LedgerWorkspace } from "./LedgerWorkspace";
import { BudgetWorkspace } from "./BudgetWorkspace";
import { ImportWorkspace } from "./ImportWorkspace";
import { InvestmentWorkspace } from "./InvestmentWorkspace";
import { RecurringWorkspace } from "./RecurringWorkspace";
import { OverviewWorkspace, type OverviewDrilldown } from "./OverviewWorkspace";
import { TransactionWorkspace, type TransactionInitialFilters } from "./TransactionWorkspace";
import { applyTheme, readStoredTheme, type Theme } from "./theme";
import { copy, type Labels } from "./i18n/app";
import { FormError } from "./components/FormError";
import { OperationalSafetyPanel } from "./settings/OperationalSafetyPanel";
import { SettingsPanel, SecurityPanel } from "./settings/AccountSettings";
import { UserAdministrationPanel } from "./settings/UserAdministrationPanel";
import { TestResetPanel } from "./settings/TestResetPanel";

type LoadState =
  | { kind: "loading" }
  | { kind: "setup"; status: EnvironmentStatus }
  | { kind: "login"; status: EnvironmentStatus }
  | { kind: "ready"; session: Session }
  | { kind: "error"; message: string };

const defaultSettings: AppSettings = {
  language: "sv",
  region: "SE",
  base_currency: "SEK",
  timezone: "Europe/Stockholm",
  date_format: "YYYY-MM-DD",
  number_format: "space-comma",
  week_start: "monday",
};


function App() {
  const [theme, setTheme] = useState<Theme>(readStoredTheme);
  const [environment, setEnvironment] = useState<Environment>(() => {
    return localStorage.getItem("cost-review-environment") === "test" ? "test" : "production";
  });
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    localStorage.setItem("cost-review-environment", environment);
    let active = true;
    async function load() {
      try {
        const status = await getSetupStatus(environment);
        if (!active) return;
        if (status.setup_required) {
          setState({ kind: "setup", status });
          return;
        }
        try {
          const session = await getSession(environment);
          if (active) setState({ kind: "ready", session });
        } catch (error) {
          if (!active) return;
          if (error instanceof ApiError && error.status === 401) {
            setState({ kind: "login", status });
          } else {
            throw error;
          }
        }
      } catch (error) {
        if (active) {
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Cost Review API is unavailable.",
          });
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [environment, reloadKey]);

  const language: Language =
    state.kind === "ready"
      ? state.session.settings.language
      : navigator.language.toLowerCase().startsWith("sv")
        ? "sv"
        : "en";
  const labels = copy[language];

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const selectEnvironment = (next: Environment) => {
    if (next !== environment) {
      setState({ kind: "loading" });
      setEnvironment(next);
    }
  };

  if (import.meta.env.DEV && window.location.hash === "#investments-preview") {
    return (
      <div className="app-shell">
        <div className="test-banner" role="status">
          <strong>LOKAL FÖRHANDSVISNING</strong>
          <span>Visar enbart illustrativ marknads- och portföljdata.</span>
        </div>
        <header className="topbar">
          <span className="brand">Cost Review</span>
          <nav className="primary-nav" aria-label="Primär navigering">
            <a className="active" href="#investments-preview" aria-current="page">
              Investeringar
            </a>
          </nav>
          <div className="topbar-controls">
            <ThemeToggle labels={labels} theme={theme} onTheme={setTheme} />
          </div>
        </header>
        <main>
          <InvestmentWorkspace language="sv" preview />
        </main>
      </div>
    );
  }

  if (state.kind === "loading") {
    return (
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment} theme={theme} onTheme={setTheme}>
        <div className="center-state" role="status">
          <span className="status-pulse" aria-hidden="true" />
          <p>{labels.loading}</p>
        </div>
      </PageFrame>
    );
  }

  if (state.kind === "error") {
    return (
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment} theme={theme} onTheme={setTheme}>
        <div className="center-state error-state" role="alert">
          <strong>{state.message}</strong>
          <button
            type="button"
            onClick={() => {
              setState({ kind: "loading" });
              setReloadKey((value) => value + 1);
            }}
          >
            {labels.retry}
          </button>
        </div>
      </PageFrame>
    );
  }

  if (state.kind === "setup") {
    return (
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment} theme={theme} onTheme={setTheme}>
        <SetupForm
          environment={environment}
          labels={labels}
          onComplete={(session) => setState({ kind: "ready", session })}
        />
      </PageFrame>
    );
  }

  if (state.kind === "login") {
    return (
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment} theme={theme} onTheme={setTheme}>
        <LoginForm
          environment={environment}
          labels={labels}
          status={state.status}
          onComplete={(session) => setState({ kind: "ready", session })}
        />
      </PageFrame>
    );
  }

  return (
    <ApplicationShell
      environment={environment}
      labels={copy[state.session.settings.language]}
      session={state.session}
      onEnvironment={selectEnvironment}
      theme={theme}
      onTheme={setTheme}
      onSession={(session) => setState({ kind: "ready", session })}
      onLogout={async () => {
        await logout(environment);
        setReloadKey((value) => value + 1);
      }}
    />
  );
}


function PageFrame({
  environment,
  labels,
  onEnvironment,
  theme,
  onTheme,
  children,
}: {
  environment: Environment;
  labels: Labels;
  onEnvironment: (environment: Environment) => void;
  theme: Theme;
  onTheme: (theme: Theme) => void;
  children: React.ReactNode;
}) {
  return (
    <div className={`page-frame environment-${environment}`}>
      <header className="minimal-header">
        <span className="brand">Cost Review</span>
        <div className="topbar-controls">
          <ThemeToggle labels={labels} theme={theme} onTheme={onTheme} />
          <EnvironmentSwitcher
            environment={environment}
            labels={labels}
            onEnvironment={onEnvironment}
          />
        </div>
      </header>
      <main className="auth-main">{children}</main>
    </div>
  );
}

function ThemeToggle({
  labels,
  theme,
  onTheme,
}: {
  labels: Labels;
  theme: Theme;
  onTheme: (theme: Theme) => void;
}) {
  const isDark = theme === "dark";
  const actionLabel = isDark ? labels.switchToLightTheme : labels.switchToDarkTheme;

  return (
    <button
      aria-label={actionLabel}
      aria-pressed={isDark}
      className="theme-toggle"
      onClick={() => onTheme(isDark ? "light" : "dark")}
      title={actionLabel}
      type="button"
    >
      {isDark ? (
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="3.5" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
        </svg>
      ) : (
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="M20.4 15.1A8 8 0 0 1 8.9 3.6 8.5 8.5 0 1 0 20.4 15.1Z" />
        </svg>
      )}
      <span>{isDark ? labels.lightTheme : labels.darkTheme}</span>
    </button>
  );
}

function EnvironmentSwitcher({
  environment,
  labels,
  onEnvironment,
}: {
  environment: Environment;
  labels: Labels;
  onEnvironment: (environment: Environment) => void;
}) {
  return (
    <div className="environment-switcher" role="group" aria-label={labels.switchEnvironment}>
      {(["production", "test"] as const).map((item) => (
        <button
          className={environment === item ? "active" : undefined}
          key={item}
          onClick={() => onEnvironment(item)}
          type="button"
        >
          {item === "production" ? labels.production : labels.test}
        </button>
      ))}
    </div>
  );
}

function SetupForm({
  environment,
  labels: initialLabels,
  onComplete,
}: {
  environment: Environment;
  labels: Labels;
  onComplete: (session: Session) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const labels = copy[settings.language] ?? initialLabels;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    setError(null);
    try {
      onComplete(await setup(environment, username, password, settings));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Setup failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <form className="auth-card" onSubmit={submit}>
      <p className="eyebrow">{environment === "test" ? labels.test : labels.production}</p>
      <h1>{labels.setupTitle}</h1>
      <p className="lead">{labels.setupLead}</p>
      <FormError message={error} />
      <label>
        {labels.username}
        <input
          autoComplete="username"
          minLength={3}
          maxLength={64}
          onChange={(event) => setUsername(event.target.value)}
          required
          value={username}
        />
      </label>
      <label>
        {labels.password}
        <input
          autoComplete="new-password"
          minLength={12}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      <div className="form-grid">
        <label>
          {labels.language}
          <select
            onChange={(event) =>
              setSettings({ ...settings, language: event.target.value as Language })
            }
            value={settings.language}
          >
            <option value="sv">Svenska</option>
            <option value="en">English</option>
          </select>
        </label>
        <label>
          {labels.region}
          <input
            maxLength={16}
            onChange={(event) => setSettings({ ...settings, region: event.target.value })}
            required
            value={settings.region}
          />
        </label>
        <label>
          {labels.currency}
          <input
            maxLength={3}
            minLength={3}
            onChange={(event) =>
              setSettings({ ...settings, base_currency: event.target.value.toUpperCase() })
            }
            pattern="[A-Z]{3}"
            required
            value={settings.base_currency}
          />
        </label>
        <label>
          {labels.timezone}
          <input
            onChange={(event) => setSettings({ ...settings, timezone: event.target.value })}
            required
            value={settings.timezone}
          />
        </label>
      </div>
      <button className="primary-button" disabled={working} type="submit">
        {labels.create}
      </button>
    </form>
  );
}

function LoginForm({
  environment,
  labels,
  status,
  onComplete,
}: {
  environment: Environment;
  labels: Labels;
  status: EnvironmentStatus;
  onComplete: (session: Session) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [registering, setRegistering] = useState(false);
  const [language, setLanguage] = useState<Language>(labels === copy.sv ? "sv" : "en");
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    setError(null);
    try {
      onComplete(
        registering
          ? await registerAccount(environment, username, password, {
              ...defaultSettings,
              language,
            })
          : await login(environment, username, password),
      );
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <form className="auth-card compact" onSubmit={submit}>
      <p className="eyebrow">{environment === "test" ? labels.test : labels.production}</p>
      <h1>{registering ? labels.registerTitle : labels.loginTitle}</h1>
      {registering ? <p className="lead">{labels.registerLead}</p> : null}
      <FormError message={error} />
      <label>
        {labels.username}
        <input
          autoComplete="username"
          minLength={3}
          maxLength={64}
          onChange={(event) => setUsername(event.target.value)}
          required
          value={username}
        />
      </label>
      <label>
        {labels.password}
        <input
          autoComplete={registering ? "new-password" : "current-password"}
          minLength={registering ? 12 : 1}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      {registering ? (
        <label>
          {labels.language}
          <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
            <option value="sv">Svenska</option>
            <option value="en">English</option>
          </select>
        </label>
      ) : null}
      <button className="primary-button" disabled={working} type="submit">
        {registering ? labels.registerAction : labels.signIn}
      </button>
      {status.registration_allowed ? (
        <button
          className="auth-mode-button"
          disabled={working}
          onClick={() => {
            setError(null);
            setRegistering((current) => !current);
          }}
          type="button"
        >
          {registering ? labels.showLogin : labels.showRegister}
        </button>
      ) : (
        <p className="quiet-copy auth-registration-note">{labels.noSelfRegistration}</p>
      )}
    </form>
  );
}

function ApplicationShell({
  environment,
  labels,
  session,
  onEnvironment,
  theme,
  onTheme,
  onSession,
  onLogout,
}: {
  environment: Environment;
  labels: Labels;
  session: Session;
  onEnvironment: (environment: Environment) => void;
  theme: Theme;
  onTheme: (theme: Theme) => void;
  onSession: (session: Session) => void;
  onLogout: () => Promise<void>;
}) {
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [view, setView] = useState<AppView>(() => viewFromHash(window.location.hash));
  const [transactionFilters, setTransactionFilters] = useState<TransactionInitialFilters | null>(null);

  useEffect(() => {
    const readHash = () => setView(viewFromHash(window.location.hash));
    window.addEventListener("hashchange", readHash);
    return () => window.removeEventListener("hashchange", readHash);
  }, []);

  const navigate = (nextView: AppView) => {
    window.location.hash = nextView;
    setView(nextView);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className={`app-shell environment-${environment}`}>
      {environment === "test" ? (
        <div className="test-banner" role="status">
          <strong>DEMO / TEST</strong>
          <span>{labels.testWarning}</span>
        </div>
      ) : null}
      <header className="topbar">
        <a
          className="brand"
          href="#overview"
          aria-label="Cost Review overview"
          onClick={() => setView("overview")}
        >
          Cost Review
        </a>
        <nav className="primary-nav" aria-label="Primary navigation">
          <a
            className={view === "overview" ? "active" : undefined}
            href="#overview"
            aria-current={view === "overview" ? "page" : undefined}
          >
            {labels.overview}
          </a>
          <a
            className={view === "transactions" ? "active" : undefined}
            href="#transactions"
            onClick={() => setTransactionFilters(null)}
            aria-current={view === "transactions" ? "page" : undefined}
          >
            {labels.transactions}
          </a>
          <a
            className={view === "import" ? "active" : undefined}
            href="#import"
            aria-current={view === "import" ? "page" : undefined}
          >
            {labels.importNav}
          </a>
          <a
            className={view === "recurring" ? "active" : undefined}
            href="#recurring"
            aria-current={view === "recurring" ? "page" : undefined}
          >
            {labels.recurringNav}
          </a>
          <a
            className={view === "accounts" ? "active" : undefined}
            href="#accounts"
            aria-current={view === "accounts" ? "page" : undefined}
          >
            {labels.accounts}
          </a>
          <a
            className={view === "budget" ? "active" : undefined}
            href="#budget"
            aria-current={view === "budget" ? "page" : undefined}
          >
            {labels.budget}
          </a>
          <a
            className={view === "investments" ? "active" : undefined}
            href="#investments"
            aria-current={view === "investments" ? "page" : undefined}
          >
            {labels.investments}
          </a>
          <a
            className={view === "settings" ? "active" : undefined}
            href="#settings"
            aria-current={view === "settings" ? "page" : undefined}
          >
            {labels.settings}
          </a>
        </nav>
        <div className="topbar-controls">
          <ThemeToggle labels={labels} theme={theme} onTheme={onTheme} />
          <EnvironmentSwitcher
            environment={environment}
            labels={labels}
            onEnvironment={onEnvironment}
          />
        </div>
      </header>

      <main>
        {session.role === "viewer" ? (
          <p className="read-only-notice" role="note">{labels.readOnlyNotice}</p>
        ) : null}
        {view === "overview" ? (
          <OverviewWorkspace
            environment={environment}
            language={session.settings.language}
            onNavigateAccounts={() => navigate("accounts")}
            onNavigateTransactions={(drilldown?: OverviewDrilldown) => {
              setTransactionFilters(drilldown ?? null);
              navigate("transactions");
            }}
          />
        ) : null}
        {view === "transactions" ? (
          <TransactionWorkspace
            baseCurrency={session.settings.base_currency}
            currentUserId={session.user_id}
            environment={environment}
            language={session.settings.language}
            initialFilters={transactionFilters}
            key={`${environment}:${JSON.stringify(transactionFilters)}`}
            onNavigateAccounts={() => navigate("accounts")}
          />
        ) : null}
        {view === "accounts" ? (
          <LedgerWorkspace
            baseCurrency={session.settings.base_currency}
            environment={environment}
            key={`${environment}-accounts`}
            language={session.settings.language}
            view="accounts"
          />
        ) : null}
        {view === "import" ? (
          <ImportWorkspace
            canWrite={session.role !== "viewer"}
            environment={environment}
            key={`${environment}-import`}
            language={session.settings.language}
          />
        ) : null}
        {view === "recurring" ? (
          <RecurringWorkspace
            canWrite={session.role !== "viewer"}
            environment={environment}
            key={`${environment}-recurring`}
            language={session.settings.language}
          />
        ) : null}
        {view === "budget" ? (
          <BudgetWorkspace
            baseCurrency={session.settings.base_currency}
            environment={environment}
            key={`${environment}-budget`}
            language={session.settings.language}
          />
        ) : null}
        {view === "investments" ? (
          <InvestmentWorkspace
            environment={environment}
            key={`${environment}-investments`}
            language={session.settings.language}
          />
        ) : null}
        {view === "settings" ? (
          <div className="settings-view">
            <div className="workspace-heading compact-heading">
              <div>
                <p className="eyebrow">Cost Review</p>
                <h1>{labels.settings}</h1>
                <p>{labels.foundationLead}</p>
              </div>
              <span className={`environment-badge ${environment}`}>
                {environment === "test" ? labels.test : labels.production}
              </span>
            </div>
            <SettingsPanel
              environment={environment}
              labels={labels}
              session={session}
              onSession={onSession}
            />
            <SecurityPanel environment={environment} labels={labels} />
            {session.role === "owner" ? (
              <UserAdministrationPanel
                environment={environment}
                labels={labels}
                session={session}
                onSession={onSession}
              />
            ) : null}
            <OperationalSafetyPanel
              canManageBackups={session.role === "owner"}
              environment={environment}
              labels={labels}
              language={session.settings.language}
            />
            <LedgerWorkspace
              baseCurrency={session.settings.base_currency}
              environment={environment}
              key={`${environment}-master-data`}
              language={session.settings.language}
              view="master-data"
            />
            <div className="foundation-grid settings-system-grid">
              <section className="panel">
                <p className="panel-label">PostgreSQL</p>
                <h2>{labels.dataPlane}</h2>
                <code>{session.data_plane_id}</code>
                <p className="quiet-copy">
                  {labels.resetGeneration}: {session.reset_generation}
                </p>
              </section>
              <section className="panel">
                <p className="panel-label">Session</p>
                <h2>{labels.sessionAs}</h2>
                <p className="session-user">{session.username}</p>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => {
                    setLogoutError(null);
                    void onLogout().catch((error) =>
                      setLogoutError(
                        error instanceof Error ? error.message : "Logout failed.",
                      ),
                    );
                  }}
                >
                  {labels.signOut}
                </button>
                <FormError message={logoutError} />
              </section>
            </div>
            {environment === "test" && session.role === "owner" ? (
              <TestResetPanel labels={labels} session={session} onSession={onSession} />
            ) : null}
          </div>
        ) : null}
      </main>

      <footer>
        <span>Cost Review</span>
        <span>{session.environment_label} · PostgreSQL</span>
      </footer>
    </div>
  );
}


type AppView =
  | "overview"
  | "transactions"
  | "import"
  | "recurring"
  | "accounts"
  | "budget"
  | "investments"
  | "settings";

function viewFromHash(hash: string): AppView {
  const value = hash.replace("#", "");
  const views: AppView[] = [
    "transactions",
    "import",
    "recurring",
    "accounts",
    "budget",
    "investments",
    "settings",
  ];
  return (views as string[]).includes(value) ? (value as AppView) : "overview";
}









export default App;
