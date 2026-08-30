import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const session = (environment: "production" | "test") => ({
  username: `${environment}-owner`,
  environment,
  environment_label: environment === "production" ? "Production" : "Demo/Test",
  data_plane_id: environment === "production" ? "prod-plane" : "test-plane",
  reset_generation: 0,
  expires_at: "2026-08-29T00:00:00Z",
  settings: {
    language: "en",
    region: "SE",
    base_currency: "SEK",
    timezone: "Europe/Stockholm",
    date_format: "YYYY-MM-DD",
    number_format: "space-comma",
    week_start: "monday",
  },
});

let accountItems: object[] = [];
let transactionItems: object[] = [];
let budgetItems: Record<string, unknown>[] = [];
let providerItems: object[] = [];
let analysisData: object;

const account = (
  accountId: number,
  name: string,
  accountType: "current" | "savings" | "credit_card" | "investment" = "current",
) => ({
  account_id: accountId,
  name,
  account_type: accountType,
  opening_balance: "0.0000",
  opening_balance_date: "2026-08-01",
  currency: "SEK",
  interest_rate: null,
  is_locked: false,
  lock_start_date: null,
  lock_end_date: null,
  notes: null,
  status: "active",
  archived_at: null,
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
});

describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    window.location.hash = "";
    accountItems = [];
    transactionItems = [];
    budgetItems = [];
    providerItems = [];
    analysisData = {
      date_from: "2026-08-01",
      date_to: "2026-08-31",
      base_currency: "SEK",
      daily: [],
      expense_categories: [],
    };
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const path = input.toString();
        const environment = path.includes("/test/") ? "test" : "production";
        let body: object;
        if (path.endsWith("/setup/status")) {
          body = {
            environment,
            label: environment === "test" ? "Demo/Test" : "Production",
            data_plane_id: `${environment}-plane`,
            reset_generation: 0,
            setup_required: false,
          };
        } else if (path.includes("/accounts?")) {
          body = { items: accountItems, total: accountItems.length, limit: 50, offset: 0 };
        } else if (/\/accounts\/\d+\/snapshots$/.test(path) && init?.method === "POST") {
          body = {
            account_snapshot_id: 1,
            account_id: 1,
            valuation_date: "2026-08-28",
            reported_balance: "125000.0000",
            currency: "SEK",
            converted_balance: "125000.0000",
            base_currency: "SEK",
            fx_rate: "1.0000000000",
            fx_rate_status: "not_required",
            calculated_balance: "0.0000",
            difference: "125000.0000",
            calculation_status: "complete",
            notes: null,
            status: "active",
            archived_at: null,
            created_at: "2026-08-28T00:00:00Z",
            updated_at: "2026-08-28T00:00:00Z",
          };
        } else if (/\/accounts\/\d+\/snapshots$/.test(path)) {
          body = [];
        } else if (path.endsWith("/budgets") && init?.method === "POST") {
          const submitted = JSON.parse(String(init.body));
          body = {
            budget_id: 1,
            ...submitted,
            status: "active",
            archived_at: null,
            created_at: "2026-08-29T00:00:00Z",
            updated_at: "2026-08-29T00:00:00Z",
          };
        } else if (/\/budgets\/\d+\/outcome\?/.test(path)) {
          body = {
            budget: budgetItems[0],
            date_from: "2026-08-01",
            date_to: "2026-08-31",
            base_currency: "SEK",
            target_amount: "3500.0000",
            actual_amount: "2800.0000",
            remaining_amount: "700.0000",
            consumed_percent: "80.00",
            period_count: 1,
            rollover_adjustment: "0.0000",
            matched_transaction_count: 4,
            missing_fx_count: 0,
            overlapping_budget_ids: [],
          };
        } else if (/\/budgets\/\d+\/trend\?/.test(path)) {
          body = {
            budget_id: 1,
            base_currency: "SEK",
            points: [
              { period_start: "2026-07-01", period_end: "2026-07-31", target_amount: "3500.0000", actual_amount: "3200.0000", remaining_amount: "300.0000", consumed_percent: "91.43", missing_fx_count: 0 },
              { period_start: "2026-08-01", period_end: "2026-08-31", target_amount: "3500.0000", actual_amount: "2800.0000", remaining_amount: "700.0000", consumed_percent: "80.00", missing_fx_count: 0 },
            ],
          };
        } else if (path.includes("/budgets?")) {
          body = budgetItems;
        } else if (path.includes("/analysis-groups?")) {
          body = [];
        } else if (path.includes("/providers?")) {
          body = { items: providerItems, total: providerItems.length, limit: 50, offset: 0 };
        } else if (
          path.includes("/categories?") ||
          path.includes("/tags?") ||
          path.includes("/sharing-parties?")
        ) {
          body = { items: [], total: 0, limit: 50, offset: 0 };
        } else if (path.includes("/transactions/analysis?")) {
          body = analysisData;
        } else if (path.includes("/transactions/summary?")) {
          body = {
            date_from: "2026-08-01",
            date_to: "2026-08-31",
            base_currency: "SEK",
            income: "0.0000",
            expenses: "0.0000",
            net_cash_flow: "0.0000",
            transaction_count: 0,
            missing_fx_count: 0,
          };
        } else if (path.includes("/transactions?")) {
          body = {
            items: transactionItems,
            total: transactionItems.length,
            limit: 100,
            offset: 0,
          };
        } else if (path.includes("/transfers?")) {
          body = { items: [], total: 0, limit: 100, offset: 0 };
        } else {
          body = session(environment);
        }
        return Promise.resolve(
          new Response(JSON.stringify(body), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("loads the authenticated Production ledger without financial sample data", async () => {
    render(<App />);

    expect(await screen.findByText(/Your finances ·/)).toBeInTheDocument();
    expect(
      await screen.findByText(
        "The overview is empty because no transactions have been recorded in the selected month.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("DEMO / TEST")).not.toBeInTheDocument();
  });

  it("defaults the overview to the current month and can move to a previous month", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText(/Your finances ·/);
    const monthInput = screen.getByLabelText("Select month", { selector: "input" });
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    expect(monthInput).toHaveValue(currentMonth);
    expect(screen.getByRole("heading", { name: "Income and expenses through the month" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Expenses by category" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Previous month" }));
    const previous = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const previousMonth = `${previous.getFullYear()}-${String(previous.getMonth() + 1).padStart(2, "0")}`;
    expect(monthInput).toHaveValue(previousMonth);
    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) => {
        const path = input.toString();
        return path.includes("/transactions/summary?") && path.includes(`date_from=${previousMonth}-01`);
      })).toBe(true);
    });
    expect(screen.getByRole("button", { name: "This month" })).toBeInTheDocument();
  });

  it("renders truthful daily and category analysis with accessible data tables", async () => {
    analysisData = {
      date_from: "2026-08-01",
      date_to: "2026-08-31",
      base_currency: "SEK",
      daily: [{ date: "2026-08-12", income: "30000.0000", expenses: "650.0000", net_cash_flow: "29350.0000" }],
      expense_categories: [
        { category_id: 1, category_name: "Groceries", amount: "650.0000", transaction_count: 2 },
        { category_id: 2, category_name: "Transport", amount: "350.0000", transaction_count: 1 },
      ],
    };
    const user = userEvent.setup();
    render(<App />);

    expect((await screen.findAllByText("Groceries")).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Where does the money go?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cumulative expenses" })).toBeInTheDocument();

    const distributionTable = screen.getByRole("table", { hidden: true, name: "Where does the money go?" });
    const distributionPanel = screen.getByRole("heading", { name: "Where does the money go?" }).closest("section");
    expect(distributionPanel).not.toBeNull();
    await user.click(within(distributionPanel as HTMLElement).getByText("Show data as a table"));
    expect(within(distributionTable).getByRole("cell", { name: /65\s*%/ })).toBeInTheDocument();

    const categoryPanel = screen.getByRole("heading", { name: "Expenses by category" }).closest("section");
    expect(categoryPanel).not.toBeNull();
    await user.click(within(categoryPanel as HTMLElement).getByText("Show data as a table"));
    const categoryTable = screen.getByRole("table", { name: "Expenses by category" });
    expect(within(categoryTable).getByRole("columnheader", { name: "Category" })).toBeInTheDocument();
    expect(within(categoryTable).getByRole("cell", { name: "2" })).toBeInTheDocument();
    await user.click(within(categoryPanel as HTMLElement).getByRole("button", { name: "View contributing transactions: Groceries" }));
    expect(await screen.findByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    await waitFor(() => {
      expect(vi.mocked(fetch).mock.calls.some(([input]) => {
        const path = input.toString();
        return path.includes("/transactions?") && path.includes("category_id=1");
      })).toBe(true);
    });
  });

  it("keeps daily entry and account setup in separate views", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Transactions" }));
    expect(await screen.findByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    expect(screen.getByText("Create at least one account first.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Account name")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Go to Accounts" }));
    expect(await screen.findByLabelText("Account name")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Transactions" })).not.toBeInTheDocument();
  });

  it("creates a monthly budget from the dedicated planning workspace", async () => {
    accountItems = [account(1, "Daily account")];
    providerItems = [{
      provider_id: 7,
      name: "Grocery store",
      website: null,
      notes: null,
      status: "active",
      archived_at: null,
      created_at: "2026-08-01T00:00:00Z",
      updated_at: "2026-08-01T00:00:00Z",
    }];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Budget" }));
    expect(
      await screen.findByText("No budgets yet. Create one to start comparing actuals."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "+ New budget" }));
    await user.type(screen.getByLabelText("Budget name"), "Groceries");
    await user.type(screen.getByLabelText("Amount per period"), "3500");
    await user.selectOptions(screen.getByLabelText("Accounts: Daily account"), "include");
    await user.selectOptions(screen.getByLabelText("Providers: Grocery store"), "include");
    await user.click(screen.getByRole("button", { name: "Create budget" }));

    await waitFor(() => {
      const createCall = vi.mocked(fetch).mock.calls.find(
        ([input, init]) => input.toString().endsWith("/budgets") && init?.method === "POST",
      );
      expect(createCall).toBeDefined();
      expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
        name: "Groceries",
        amount: "3500",
        currency: "SEK",
        period_type: "calendar_month",
        rollover_mode: "reset",
        categories: [],
        tags: [],
        accounts: [{ account_id: 1, mode: "include" }],
        providers: [{ provider_id: 7, mode: "include" }],
      });
    });
  });

  it("renders server-derived budget trends with exact accessible values", async () => {
    budgetItems = [{
      budget_id: 1,
      analysis_group_id: null,
      name: "Groceries",
      amount: "3500.0000",
      currency: "SEK",
      period_type: "calendar_month",
      rollover_mode: "reset",
      starts_on: "2026-07-01",
      ends_on: null,
      anchor_day: 25,
      notes: null,
      categories: [],
      tags: [],
      accounts: [],
      providers: [],
      status: "active",
      archived_at: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    }];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Budget" }));
    expect(await screen.findByRole("heading", { name: "Groceries" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Actuals by budget period" })).toBeInTheDocument();
    const trendTable = screen.getByRole("table", { name: "Actuals by budget period" });
    expect(within(trendTable).getAllByRole("cell", { name: /3.*500,00/ })).toHaveLength(2);
    expect(within(trendTable).getByRole("cell", { name: /3.*200,00/ })).toBeInTheDocument();
    expect(within(trendTable).getByRole("cell", { name: /2.*800,00/ })).toBeInTheDocument();
  });

  it("opens a focused transaction form when an account exists", async () => {
    accountItems = [account(1, "Daily account")];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Transactions" }));
    const newButton = await screen.findByRole("button", { name: "+ New transaction" });
    expect(newButton).toBeEnabled();
    await user.click(newButton);

    expect(screen.getByRole("heading", { name: "New transaction" })).toBeInTheDocument();
    expect(screen.getAllByLabelText("Account")[0]).toHaveValue("1");
    expect(screen.getByLabelText("Description")).toBeInTheDocument();
    expect(screen.getByText("More details")).toBeInTheDocument();
    expect(screen.queryByLabelText("Amount in base currency (SEK)")).not.toBeInTheDocument();
  });

  it("records a refund through the original expense", async () => {
    accountItems = [account(1, "Daily account")];
    transactionItems = [{
      transaction_id: 41,
      account_id: 1,
      provider_id: null,
      transaction_kind: "expense",
      transaction_date: "2026-08-10",
      posting_date: "2026-08-10",
      description: "Train tickets",
      original_amount: "1000.0000",
      original_currency: "SEK",
      converted_amount: "1000.0000",
      base_currency: "SEK",
      fx_rate: "1.0000000000",
      fx_rate_status: "not_required",
      source_type: "manual",
      source_reference: null,
      notes: null,
      category_id: null,
      tag_ids: [],
      is_base_cost: false,
      linked_expense_id: null,
      status: "active",
      archived_at: null,
      created_at: "2026-08-10T00:00:00Z",
      updated_at: "2026-08-10T00:00:00Z",
    }];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Transactions" }));
    await user.click(await screen.findByRole("button", { name: "Refund" }));
    expect(screen.getByRole("heading", { name: "Record refund" })).toBeInTheDocument();
    expect(screen.getByText(/Linked expense:/).closest("p")).toHaveTextContent("Train tickets");
    await user.type(screen.getByLabelText("Amount"), "250");
    await user.click(screen.getByRole("button", { name: "Record refund" }));

    await waitFor(() => {
      const recoveryCall = vi.mocked(fetch).mock.calls.find(([input, init]) =>
        input.toString().includes("/transactions/41/refunds") && init?.method === "POST"
      );
      expect(recoveryCall).toBeDefined();
      expect(JSON.parse(String(recoveryCall?.[1]?.body))).toMatchObject({
        account_id: 1,
        original_amount: "250",
        original_currency: "SEK",
      });
    });
  });

  it("creates a balanced split transaction from one account event", async () => {
    accountItems = [account(1, "Daily account")];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Transactions" }));
    await user.click(await screen.findByRole("button", { name: "+ New transaction" }));
    await user.type(screen.getByLabelText("Description"), "Mixed receipt");
    await user.type(screen.getByLabelText("Amount"), "1000");
    await user.click(screen.getByLabelText("Split transaction"));
    await user.type(screen.getByLabelText("Split 1 · Amount"), "600");
    await user.type(screen.getByLabelText("Split 2 · Amount"), "400");
    expect(screen.getByText(/Remaining to allocate:/)).toHaveClass("balanced");
    await user.click(screen.getByRole("button", { name: "Save transaction" }));

    await waitFor(() => {
      const createCall = vi.mocked(fetch).mock.calls.find(([input, init]) =>
        input.toString().endsWith("/transactions") && init?.method === "POST"
      );
      expect(createCall).toBeDefined();
      expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
        original_amount: "1000",
        splits: [
          { original_amount: "600" },
          { original_amount: "400" },
        ],
      });
    });
  });

  it("creates a credit-card payment through the dedicated transfer workflow", async () => {
    accountItems = [
      account(1, "Daily account"),
      account(2, "Credit card", "credit_card"),
    ];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Transactions" }));
    const transferButton = await screen.findByRole("button", { name: "↔ New transfer" });
    expect(transferButton).toBeEnabled();
    await user.click(transferButton);

    expect(screen.getByRole("heading", { name: "New transfer" })).toBeInTheDocument();
    expect(screen.getByLabelText("From account")).toHaveValue("1");
    expect(screen.getByLabelText("To account")).toHaveValue("2");
    await user.selectOptions(screen.getByLabelText("Purpose"), "credit_card_payment");
    await user.type(screen.getByLabelText("Description"), "August card bill");
    await user.type(screen.getByLabelText("Amount (SEK)"), "450");
    expect(screen.getByLabelText("Received amount (SEK)")).toHaveValue("450");
    await user.click(screen.getByRole("button", { name: "Save transfer" }));

    const transferCall = vi.mocked(fetch).mock.calls.find(([input, init]) =>
      input.toString().includes("/transfers") && init?.method === "POST"
    );
    expect(transferCall).toBeDefined();
    expect(JSON.parse(String(transferCall?.[1]?.body))).toMatchObject({
      source_account_id: 1,
      destination_account_id: 2,
      purpose: "credit_card_payment",
      source_amount: "450",
      destination_amount: "450",
    });
  });

  it("records an investment value without changing the opening balance", async () => {
    accountItems = [account(1, "Investment account", "investment")];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("link", { name: "Accounts" }));
    await user.click(await screen.findByRole("button", { name: "Record current value" }));
    await user.clear(screen.getByLabelText("Date"));
    await user.type(screen.getByLabelText("Date"), "2026-08-28");
    await user.type(screen.getByLabelText("Amount (SEK)"), "125000");
    await user.click(screen.getByRole("button", { name: "Save value" }));

    await waitFor(() => {
      const snapshotCall = vi.mocked(fetch).mock.calls.find(([input, init]) =>
        input.toString().endsWith("/accounts/1/snapshots") && init?.method === "POST",
      );
      expect(snapshotCall).toBeDefined();
      expect(JSON.parse(String(snapshotCall?.[1]?.body))).toMatchObject({
        valuation_date: "2026-08-28",
        reported_balance: "125000",
      });
    });
    expect(screen.getByText("Opening balance · 2026-08-01")).toBeInTheDocument();
  });

  it("switches to the isolated Demo/Test context with a persistent warning", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(/Your finances ·/);

    await user.click(screen.getByRole("button", { name: "Demo/Test" }));

    expect(
      await screen.findByText("You are working with fictional and isolated test data."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("DEMO / TEST").length).toBeGreaterThan(0);
    expect(localStorage.getItem("cost-review-environment")).toBe("test");
  });
});
