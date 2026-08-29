import { cleanup, render, screen } from "@testing-library/react";
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

const account = (
  accountId: number,
  name: string,
  accountType: "current" | "savings" | "credit_card" = "current",
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
    vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
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
        } else if (
          path.includes("/categories?") ||
          path.includes("/providers?") ||
          path.includes("/tags?") ||
          path.includes("/sharing-parties?")
        ) {
          body = { items: [], total: 0, limit: 50, offset: 0 };
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
          body = { items: [], total: 0, limit: 100, offset: 0 };
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

    expect(await screen.findByText("Your finances this month")).toBeInTheDocument();
    expect(
      await screen.findByText(
        "The overview is empty because no transactions have been recorded this month.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("DEMO / TEST")).not.toBeInTheDocument();
  });

  it("keeps daily entry and account setup in separate views", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Your finances this month");

    await user.click(screen.getByRole("link", { name: "Transactions" }));
    expect(await screen.findByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    expect(screen.getByText("Create at least one account first.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Account name")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Go to Accounts" }));
    expect(await screen.findByLabelText("Account name")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Transactions" })).not.toBeInTheDocument();
  });

  it("opens a focused transaction form when an account exists", async () => {
    accountItems = [account(1, "Daily account")];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Your finances this month");

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

  it("creates a credit-card payment through the dedicated transfer workflow", async () => {
    accountItems = [
      account(1, "Daily account"),
      account(2, "Credit card", "credit_card"),
    ];
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Your finances this month");

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

  it("switches to the isolated Demo/Test context with a persistent warning", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Your finances this month");

    await user.click(screen.getByRole("button", { name: "Demo/Test" }));

    expect(
      await screen.findByText("You are working with fictional and isolated test data."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("DEMO / TEST").length).toBeGreaterThan(0);
    expect(localStorage.getItem("cost-review-environment")).toBe("test");
  });
});
