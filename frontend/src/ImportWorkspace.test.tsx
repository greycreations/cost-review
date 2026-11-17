import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ImportWorkspace } from "./ImportWorkspace";

const account = {
  account_id: 1,
  name: "Daily account",
  account_type: "current",
  opening_balance: "0",
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
};

const batch = {
  import_batch_id: 7,
  import_profile_id: null,
  account_id: 1,
  filename: "bank.csv",
  status: "staged",
  row_count: 2,
  status_counts: { ready: 1, duplicate: 1, invalid: 0, skipped: 0, committed: 0 },
  created_by_user_id: 1,
  created_at: "2026-11-16T10:00:00Z",
  committed_at: null,
  undone_at: null,
};

const row = (id: number, status: string, extra: Record<string, unknown> = {}) => ({
  import_row_id: id,
  row_number: id,
  raw: {},
  transaction_date: "2026-08-20",
  posting_date: null,
  description: id === 1 ? "ICA Kvantum" : "Salary",
  amount: id === 1 ? "-425.3500" : "32000.0000",
  currency: "SEK",
  reference: null,
  category_id: null,
  provider_id: null,
  status,
  errors: [],
  duplicate_transaction_id: null,
  duplicate_confidence: null,
  duplicate_reason: null,
  transaction_id: null,
  ...extra,
});

function respond(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("ImportWorkspace", () => {
  beforeEach(() => {
    document.cookie = "cost_review_production_csrf=import-csrf; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const path = input.toString();
        if (path.includes("/accounts")) return respond({ items: [account], total: 1, limit: 50, offset: 0 });
        if (path.includes("/categories")) return respond({ items: [], total: 0, limit: 50, offset: 0 });
        if (path.endsWith("/import-profiles")) return respond([]);
        if (path.endsWith("/imports/preview")) {
          return respond({
            filename: "bank.csv",
            headers: ["Datum", "Text", "Belopp"],
            sample_rows: [{ Datum: "2026-08-20", Text: "ICA Kvantum", Belopp: "-425,35" }],
            row_count: 2,
            delimiter: ";",
            suggested_mapping: {
              date_column: "Datum",
              description_column: "Text",
              amount_column: "Belopp",
              date_format: "%Y-%m-%d",
              decimal_separator: ",",
              header_row: 1,
            },
            profile_suggestions: [],
            previous_imports: [],
          });
        }
        if (path.endsWith("/imports") && init?.method === "POST") return respond(batch, 201);
        if (path.includes("/imports?")) return respond({ items: [], total: 0, limit: 50, offset: 0 });
        if (path.includes("/imports/7/rows?")) {
          return respond({
            items: [
              row(1, "ready"),
              row(2, "duplicate", {
                duplicate_reason: "matching_transaction",
                duplicate_confidence: 80,
                duplicate_transaction_id: 99,
              }),
            ],
            total: 2,
            limit: 1000,
            offset: 0,
          });
        }
        if (path.endsWith("/imports/7/commit")) {
          return respond({ ...batch, status: "committed", committed_at: "2026-11-16T10:05:00Z" });
        }
        return respond({}, 404);
      }),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("previews a bank file, stages it for review and records approved rows", async () => {
    const user = userEvent.setup();
    render(<ImportWorkspace canWrite environment="production" language="en" />);

    await screen.findByRole("option", { name: "Daily account · SEK" });
    const file = new File(["Datum;Text;Belopp\n2026-08-20;ICA Kvantum;-425,35\n"], "bank.csv", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText("Bank export"), file);
    await user.selectOptions(screen.getByLabelText("Account"), "1");
    await user.click(screen.getByRole("button", { name: "Read file" }));

    expect(await screen.findByRole("table", { name: "Preview" })).toBeInTheDocument();
    expect(screen.getByLabelText("Amount")).toHaveValue("Belopp");

    await user.click(screen.getByRole("button", { name: "Review rows" }));
    const review = await screen.findByRole("table", { name: "Review import" });
    expect(within(review).getByText("ICA Kvantum")).toBeInTheDocument();
    expect(
      within(review).getByText("Resembles an existing transaction · 80% confidence"),
    ).toBeInTheDocument();

    const stageCall = vi
      .mocked(fetch)
      .mock.calls.find(([input, init]) => input.toString().endsWith("/imports") && init?.method === "POST");
    const options = JSON.parse(String((stageCall?.[1]?.body as FormData).get("options")));
    expect(options).toMatchObject({
      account_id: 1,
      mapping: { date_column: "Datum", description_column: "Text", amount_column: "Belopp" },
    });
    expect(new Headers(stageCall?.[1]?.headers).get("X-CSRF-Token")).toBe("import-csrf");

    await user.click(screen.getByRole("button", { name: "Record approved rows" }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("The import was recorded."),
    );
  });

  it("keeps import controls away from view-only members", async () => {
    render(<ImportWorkspace canWrite={false} environment="production" language="en" />);

    expect(await screen.findByText("You have view-only access and cannot import.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Bank export")).not.toBeInTheDocument();
  });
});
