import { useEffect, useState, type FormEvent } from "react";

import {
  ApiError,
  backupDownloadUrl,
  createBackup,
  getAuditEvents,
  getBackups,
  getRecycleBin,
  getSession,
  getSetupStatus,
  login,
  logout,
  resetTestEnvironment,
  saveSettings,
  setup,
  validateBackup,
  type AuditEvent,
  type AppSettings,
  type Backup,
  type Environment,
  type EnvironmentStatus,
  type Language,
  type RecycleBinItem,
  type Session,
} from "./api";
import { LedgerWorkspace } from "./LedgerWorkspace";
import { BudgetWorkspace } from "./BudgetWorkspace";
import { OverviewWorkspace, type OverviewDrilldown } from "./OverviewWorkspace";
import {
  TransactionWorkspace,
  type TransactionInitialFilters,
} from "./TransactionWorkspace";

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

const copy = {
  sv: {
    loading: "Ansluter till den valda datamiljön…",
    production: "Produktion",
    test: "Demo/Test",
    switchEnvironment: "Byt datamiljö",
    setupTitle: "Skapa den första användaren",
    setupLead: "Inställningen sparas endast i den valda datamiljön.",
    loginTitle: "Logga in",
    username: "Användarnamn",
    password: "Lösenord",
    language: "Språk",
    region: "Region",
    currency: "Basvaluta",
    timezone: "Tidszon",
    create: "Skapa och fortsätt",
    signIn: "Logga in",
    overview: "Översikt",
    transactions: "Transaktioner",
    accounts: "Konton",
    budget: "Budget",
    settings: "Inställningar",
    attention: "Uppmärksamhet",
    foundationReady: "Ledger-grunden är aktiv",
    foundationLead:
      "Konton och återanvändbar masterdata lagras nu i PostgreSQL med samma hårda dataseparation.",
    sessionAs: "Inloggad som",
    signOut: "Logga ut",
    save: "Spara inställningar",
    saved: "Sparat",
    dataPlane: "Dataplan",
    resetGeneration: "Teståterställningar",
    testWarning: "Du arbetar med fiktiv och isolerad testdata.",
    resetTitle: "Radera all testdata",
    resetLead:
      "Detta återställer Demo/Test-konfigurationen. Produktions-API:t och produktionsdatabasen är inte åtkomliga från denna operation.",
    resetPhrase: "Skriv DELETE ALL TEST DATA för att bekräfta",
    resetAction: "Radera testdata",
    retry: "Försök igen",
    backups: "Krypterade säkerhetskopior",
    backupsLead:
      "Databas och bilagor paketeras tillsammans. Kopian är låst till den här datamiljön och kan hämtas för extern förvaring.",
    createBackup: "Skapa säkerhetskopia",
    validate: "Validera",
    download: "Hämta",
    noBackups: "Inga säkerhetskopior har skapats i denna datamiljö.",
    lifecycle: "Papperskorg och ändringshistorik",
    lifecycleLead:
      "Arkiverade poster ligger kvar och kan återställas. De senaste Ledger-ändringarna visas som ett granskningsspår.",
    recycleBin: "Arkiverade poster",
    auditTrail: "Senaste ändringar",
    noArchived: "Papperskorgen är tom.",
    noAudit: "Inga ändringar har registrerats ännu.",
  },
  en: {
    loading: "Connecting to the selected data environment…",
    production: "Production",
    test: "Demo/Test",
    switchEnvironment: "Switch data environment",
    setupTitle: "Create the initial user",
    setupLead: "These settings are stored only in the selected data environment.",
    loginTitle: "Sign in",
    username: "Username",
    password: "Password",
    language: "Language",
    region: "Region",
    currency: "Base currency",
    timezone: "Timezone",
    create: "Create and continue",
    signIn: "Sign in",
    overview: "Overview",
    transactions: "Transactions",
    accounts: "Accounts",
    budget: "Budget",
    settings: "Settings",
    attention: "Attention",
    foundationReady: "Ledger foundation is active",
    foundationLead:
      "Accounts and reusable master data now live in PostgreSQL behind the same hard data boundary.",
    sessionAs: "Signed in as",
    signOut: "Sign out",
    save: "Save settings",
    saved: "Saved",
    dataPlane: "Data plane",
    resetGeneration: "Test resets",
    testWarning: "You are working with fictional and isolated test data.",
    resetTitle: "Delete all test data",
    resetLead:
      "This resets Demo/Test configuration. The Production API and database are not reachable from this operation.",
    resetPhrase: "Type DELETE ALL TEST DATA to confirm",
    resetAction: "Delete test data",
    retry: "Try again",
    backups: "Encrypted backups",
    backupsLead:
      "The database and attachments are bundled together. Each backup is bound to this data plane and can be downloaded for off-site storage.",
    createBackup: "Create backup",
    validate: "Validate",
    download: "Download",
    noBackups: "No backups have been created in this data plane.",
    lifecycle: "Recycle bin and change history",
    lifecycleLead:
      "Archived records remain recoverable. Recent Ledger changes are shown as an audit trail.",
    recycleBin: "Archived records",
    auditTrail: "Recent changes",
    noArchived: "The recycle bin is empty.",
    noAudit: "No changes have been recorded yet.",
  },
} as const;

function App() {
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

  const selectEnvironment = (next: Environment) => {
    if (next !== environment) {
      setState({ kind: "loading" });
      setEnvironment(next);
    }
  };

  if (state.kind === "loading") {
    return (
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment}>
        <div className="center-state" role="status">
          <span className="status-pulse" aria-hidden="true" />
          <p>{labels.loading}</p>
        </div>
      </PageFrame>
    );
  }

  if (state.kind === "error") {
    return (
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment}>
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
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment}>
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
      <PageFrame environment={environment} labels={labels} onEnvironment={selectEnvironment}>
        <LoginForm
          environment={environment}
          labels={labels}
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
      onSession={(session) => setState({ kind: "ready", session })}
      onLogout={async () => {
        await logout(environment);
        setReloadKey((value) => value + 1);
      }}
    />
  );
}

type Labels = (typeof copy)[Language];

function PageFrame({
  environment,
  labels,
  onEnvironment,
  children,
}: {
  environment: Environment;
  labels: Labels;
  onEnvironment: (environment: Environment) => void;
  children: React.ReactNode;
}) {
  return (
    <div className={`page-frame environment-${environment}`}>
      <header className="minimal-header">
        <span className="brand">Cost Review</span>
        <EnvironmentSwitcher
          environment={environment}
          labels={labels}
          onEnvironment={onEnvironment}
        />
      </header>
      <main className="auth-main">{children}</main>
    </div>
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
  onComplete,
}: {
  environment: Environment;
  labels: Labels;
  onComplete: (session: Session) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    setError(null);
    try {
      onComplete(await login(environment, username, password));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <form className="auth-card compact" onSubmit={submit}>
      <p className="eyebrow">{environment === "test" ? labels.test : labels.production}</p>
      <h1>{labels.loginTitle}</h1>
      <FormError message={error} />
      <label>
        {labels.username}
        <input
          autoComplete="username"
          onChange={(event) => setUsername(event.target.value)}
          required
          value={username}
        />
      </label>
      <label>
        {labels.password}
        <input
          autoComplete="current-password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      <button className="primary-button" disabled={working} type="submit">
        {labels.signIn}
      </button>
    </form>
  );
}

function ApplicationShell({
  environment,
  labels,
  session,
  onEnvironment,
  onSession,
  onLogout,
}: {
  environment: Environment;
  labels: Labels;
  session: Session;
  onEnvironment: (environment: Environment) => void;
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
            className={view === "settings" ? "active" : undefined}
            href="#settings"
            aria-current={view === "settings" ? "page" : undefined}
          >
            {labels.settings}
          </a>
        </nav>
        <EnvironmentSwitcher
          environment={environment}
          labels={labels}
          onEnvironment={onEnvironment}
        />
      </header>

      <main>
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
        {view === "budget" ? (
          <BudgetWorkspace
            baseCurrency={session.settings.base_currency}
            environment={environment}
            key={`${environment}-budget`}
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
            <OperationalSafetyPanel
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
            {environment === "test" ? (
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

function OperationalSafetyPanel({
  environment,
  labels,
  language,
}: {
  environment: Environment;
  labels: Labels;
  language: Language;
}) {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [archived, setArchived] = useState<RecycleBinItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const refresh = () =>
    Promise.all([getBackups(environment), getRecycleBin(environment), getAuditEvents(environment)])
      .then(([backupItems, recycleItems, auditPage]) => {
        setBackups(backupItems);
        setArchived(recycleItems);
        setAuditEvents(auditPage.items);
      });

  useEffect(() => {
    let active = true;
    void Promise.all([getBackups(environment), getRecycleBin(environment), getAuditEvents(environment)])
      .then(([backupItems, recycleItems, auditPage]) => {
        if (!active) return;
        setBackups(backupItems);
        setArchived(recycleItems);
        setAuditEvents(auditPage.items);
      })
      .catch((error) => {
        if (active) setMessage(error instanceof Error ? error.message : "Could not load safety data.");
      });
    return () => {
      active = false;
    };
  }, [environment]);

  return (
    <div className="operations-grid">
      <section className="settings-section operations-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Backup</p>
            <h2>{labels.backups}</h2>
            <p className="quiet-copy">{labels.backupsLead}</p>
          </div>
          <button
            className="primary-button"
            disabled={working}
            onClick={() => {
              setWorking(true);
              setMessage(null);
              void createBackup(environment)
                .then((created) => refresh().then(() => setMessage(created.filename)))
                .catch((error) => setMessage(error instanceof Error ? error.message : "Backup failed."))
                .finally(() => setWorking(false));
            }}
            type="button"
          >
            {labels.createBackup}
          </button>
        </div>
        {backups.length === 0 ? <p className="resource-empty">{labels.noBackups}</p> : null}
        <div className="operations-list">
          {backups.map((backup) => (
            <div className="operation-row" key={backup.filename}>
              <div>
                <strong>{new Date(backup.created_at).toLocaleString(language === "sv" ? "sv-SE" : "en-US")}</strong>
                <span>{backup.kind.replace("_", " ")} · {(backup.size_bytes / 1024).toFixed(1)} kB</span>
              </div>
              <div className="row-actions">
                <button
                  className="ghost-button"
                  onClick={() => {
                    setMessage(null);
                    void validateBackup(environment, backup.filename)
                      .then(() => setMessage(`${labels.validate}: ${backup.filename}`))
                      .catch((error) => setMessage(error instanceof Error ? error.message : "Validation failed."));
                  }}
                  type="button"
                >
                  {labels.validate}
                </button>
                <a className="ghost-button button-link" href={backupDownloadUrl(environment, backup.filename)}>
                  {labels.download}
                </a>
              </div>
            </div>
          ))}
        </div>
        {message ? <p className="form-message" role="status">{message}</p> : null}
      </section>

      <section className="settings-section operations-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ledger safety</p>
            <h2>{labels.lifecycle}</h2>
            <p className="quiet-copy">{labels.lifecycleLead}</p>
          </div>
        </div>
        <div className="lifecycle-columns">
          <div>
            <h3>{labels.recycleBin}</h3>
            {archived.length === 0 ? <p className="resource-empty">{labels.noArchived}</p> : null}
            <div className="operations-list compact-list">
              {archived.slice(0, 8).map((item) => (
                <div className="operation-row" key={`${item.entity_type}:${item.entity_id}`}>
                  <div><strong>{item.label}</strong><span>{item.entity_type}</span></div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3>{labels.auditTrail}</h3>
            {auditEvents.length === 0 ? <p className="resource-empty">{labels.noAudit}</p> : null}
            <div className="operations-list compact-list">
              {auditEvents.map((event) => (
                <div className="operation-row" key={event.audit_event_id}>
                  <div><strong>{event.action.replace("_", " ")}</strong><span>{event.entity_type} #{event.entity_id ?? "—"}</span></div>
                  <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleDateString(language === "sv" ? "sv-SE" : "en-US")}</time>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

type AppView = "overview" | "transactions" | "accounts" | "budget" | "settings";

function viewFromHash(hash: string): AppView {
  const value = hash.replace("#", "");
  return value === "transactions" || value === "accounts" || value === "budget" || value === "settings"
    ? value
    : "overview";
}

function SettingsPanel({
  environment,
  labels,
  session,
  onSession,
}: {
  environment: Environment;
  labels: Labels;
  session: Session;
  onSession: (session: Session) => void;
}) {
  const [draft, setDraft] = useState(session.settings);
  const [status, setStatus] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const update = (field: keyof AppSettings, value: string) => {
    setDraft((current) => ({ ...current, [field]: value }) as AppSettings);
  };

  return (
    <section className="settings-section" id="settings">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{environment === "test" ? labels.test : labels.production}</p>
          <h2>{labels.settings}</h2>
        </div>
        {status ? <span className="save-status">{status}</span> : null}
      </div>
      <form
        className="settings-form"
        onSubmit={(event) => {
          event.preventDefault();
          setWorking(true);
          setStatus(null);
          void saveSettings(environment, draft)
            .then((saved) => {
              onSession({ ...session, settings: saved });
              setStatus(labels.saved);
            })
            .catch((error) => setStatus(error instanceof Error ? error.message : "Save failed."))
            .finally(() => setWorking(false));
        }}
      >
        <label>
          {labels.language}
          <select value={draft.language} onChange={(event) => update("language", event.target.value)}>
            <option value="sv">Svenska</option>
            <option value="en">English</option>
          </select>
        </label>
        <label>
          {labels.region}
          <input value={draft.region} onChange={(event) => update("region", event.target.value)} />
        </label>
        <label>
          {labels.currency}
          <input
            maxLength={3}
            value={draft.base_currency}
            onChange={(event) => update("base_currency", event.target.value.toUpperCase())}
          />
        </label>
        <label>
          {labels.timezone}
          <input value={draft.timezone} onChange={(event) => update("timezone", event.target.value)} />
        </label>
        <button className="primary-button" disabled={working} type="submit">
          {labels.save}
        </button>
      </form>
    </section>
  );
}

function TestResetPanel({
  labels,
  session,
  onSession,
}: {
  labels: Labels;
  session: Session;
  onSession: (session: Session) => void;
}) {
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const canReset = confirmation === "DELETE ALL TEST DATA";

  return (
    <section className="danger-section" id="attention">
      <div>
        <p className="eyebrow">DEMO / TEST</p>
        <h2>{labels.resetTitle}</h2>
        <p>{labels.resetLead}</p>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setWorking(true);
          setMessage(null);
          void resetTestEnvironment(confirmation)
            .then(async (result) => {
              const refreshed = await getSession("test");
              onSession(refreshed);
              setConfirmation("");
              setMessage(`${result.message} #${result.reset_generation}`);
            })
            .catch((error) => setMessage(error instanceof Error ? error.message : "Reset failed."))
            .finally(() => setWorking(false));
        }}
      >
        <label>
          {labels.resetPhrase}
          <input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
        </label>
        <button className="destructive-button" disabled={!canReset || working} type="submit">
          {labels.resetAction}
        </button>
        {message ? <p className="form-message">{message}</p> : null}
      </form>
      <span className="sr-only">{session.data_plane_id}</span>
    </section>
  );
}

function FormError({ message }: { message: string | null }) {
  return message ? (
    <p className="form-error" role="alert">
      {message}
    </p>
  ) : null;
}

export default App;
