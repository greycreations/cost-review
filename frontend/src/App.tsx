import { useEffect, useState } from "react";

import { loadFoundation, type ResourceCounts } from "./api";

type ApiState =
  | { status: "loading"; counts: ResourceCounts }
  | { status: "connected"; counts: ResourceCounts }
  | { status: "error"; counts: ResourceCounts };

const emptyCounts: ResourceCounts = {
  providers: 0,
  categories: 0,
  expenses: 0,
};

const periods = [
  { id: "month", label: "Monthly", suffix: "month" },
  { id: "quarter", label: "Quarterly", suffix: "quarter" },
  { id: "year", label: "Annual", suffix: "year" },
] as const;

type PeriodId = (typeof periods)[number]["id"];

function App() {
  const [period, setPeriod] = useState<PeriodId>("month");
  const [apiState, setApiState] = useState<ApiState>({
    status: "loading",
    counts: emptyCounts,
  });

  useEffect(() => {
    let active = true;

    loadFoundation()
      .then(({ counts }) => {
        if (active) {
          setApiState({ status: "connected", counts });
        }
      })
      .catch(() => {
        if (active) {
          setApiState({ status: "error", counts: emptyCounts });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const selectedPeriod = periods.find((item) => item.id === period) ?? periods[0];
  const statusLabel =
    apiState.status === "connected"
      ? "API connected"
      : apiState.status === "error"
        ? "API unavailable"
        : "Connecting";

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#overview" aria-label="Cost Review overview">
          Cost Review
        </a>
        <nav className="primary-nav" aria-label="Primary navigation">
          <a className="active" href="#overview" aria-current="page">
            Overview
          </a>
          <a href="#expenses">Expenses</a>
          <a href="#analysis">Analysis</a>
          <a href="#upcoming">Upcoming</a>
          <a href="#review">Review</a>
          <a href="#settings">Settings</a>
        </nav>
      </header>

      <main id="overview">
        <div className="connection-row" aria-live="polite">
          <span className={"status-dot " + apiState.status} aria-hidden="true" />
          <span>{statusLabel}</span>
          {apiState.status === "connected" ? (
            <span className="foundation-counts">
              {apiState.counts.providers} providers · {apiState.counts.categories} categories
            </span>
          ) : null}
        </div>

        <section className="hero" aria-labelledby="recurring-cost-title">
          <div>
            <p className="eyebrow" id="recurring-cost-title">
              Recurring cost
            </p>
            <p className="primary-amount">
              0 kr <span>/ {selectedPeriod.suffix}</span>
            </p>
            <p className="hero-meta">
              No recurring expenses yet · {apiState.counts.expenses} registered
            </p>
          </div>

          <div className="period-control" role="group" aria-label="Normalization period">
            {periods.map((item) => (
              <button
                className={period === item.id ? "active" : undefined}
                key={item.id}
                onClick={() => setPeriod(item.id)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
        </section>

        {apiState.status === "error" ? (
          <section className="api-error" role="alert">
            <div>
              <strong>The application shell is running, but the API cannot be reached.</strong>
              <p>Start the backend and refresh this page to verify the full connection.</p>
            </div>
            <button type="button" onClick={() => window.location.reload()}>
              Try again
            </button>
          </section>
        ) : null}

        <div className="overview-grid">
          <section className="panel category-panel" aria-labelledby="category-title">
            <div className="panel-heading">
              <div>
                <h2 id="category-title">Cost by category</h2>
                <p>Monthly equivalents will appear here</p>
              </div>
              <span className="quiet-chip">No data</span>
            </div>
            <div className="empty-visual" aria-hidden="true">
              <span style={{ width: "74%" }} />
              <span style={{ width: "55%" }} />
              <span style={{ width: "36%" }} />
            </div>
            <div className="empty-copy">
              <strong>Your categories will tell the story.</strong>
              <p>Add expenses to compare where your recurring commitments go.</p>
            </div>
          </section>

          <section className="panel" aria-labelledby="commitments-title">
            <div className="panel-heading">
              <div>
                <h2 id="commitments-title">Largest commitments</h2>
                <p>{selectedPeriod.label} equivalent</p>
              </div>
            </div>
            <div className="empty-list">
              <span className="empty-list-icon" aria-hidden="true">
                0
              </span>
              <strong>No commitments to rank</strong>
              <p>Your highest normalized costs will be easy to spot here.</p>
            </div>
          </section>

          <section className="panel wide-panel" aria-labelledby="upcoming-title">
            <div className="panel-heading">
              <div>
                <h2 id="upcoming-title">Upcoming</h2>
                <p>Actual payments · next 30 days</p>
              </div>
              <button className="ghost-button" type="button" disabled>
                View all
              </button>
            </div>
            <div className="upcoming-empty">
              <span>No upcoming payments</span>
              <span>Payment dates remain separate from normalized cost.</span>
            </div>
          </section>
        </div>

        <section className="attention-strip" id="review">
          <div>
            <strong>Technical foundation ready</strong>
            <p>
              Provider, Category, and Expense schemas are connected. Data-entry flows arrive in
              the next vertical slice.
            </p>
          </div>
          <button type="button" disabled>
            Add first expense
          </button>
        </section>
      </main>

      <footer>
        <span>Private by design</span>
        <span>Data stays in your self-hosted SQLite database.</span>
      </footer>
    </div>
  );
}

export default App;
