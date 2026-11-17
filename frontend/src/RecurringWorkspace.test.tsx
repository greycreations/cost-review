import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RecurringWorkspace } from "./RecurringWorkspace";

const occurrence = {
  recurring_definition_id: 3,
  name: "Electricity",
  account_id: 1,
  transaction_kind: "expense",
  due_date: "2026-08-25",
  expected_amount: "800.0000",
  amount_type: "variable",
  currency: "SEK",
  status: "overdue",
  transaction_id: null,
  deviation_percent: null,
  outside_tolerance: false,
  candidates: [
    {
      transaction_id: 41,
      transaction_date: "2026-08-24",
      description: "Vattenfall",
      amount: "812.0000",
      confidence: 82,
    },
  ],
};

function respond(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("RecurringWorkspace", () => {
  beforeEach(() => {
    document.cookie = "cost_review_production_csrf=recurring-csrf; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = input.toString();
        if (path.includes("/accounts")) return respond({ items: [], total: 0, limit: 50, offset: 0 });
        if (path.includes("/categories")) return respond({ items: [], total: 0, limit: 50, offset: 0 });
        if (path.endsWith("/recurring")) return respond([]);
        if (path.includes("/recurring/expected?")) return respond([occurrence]);
        if (path.includes("/occurrences/")) return respond({ ...occurrence, status: "confirmed" });
        return respond({}, 404);
      }),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("asks for the expected range once and links a suggested transaction", async () => {
    const user = userEvent.setup();
    render(
      <RecurringWorkspace
        canWrite
        environment="production"
        language="en"
        today={new Date(2026, 7, 26)}
      />,
    );

    const link = await screen.findByRole("button", { name: /Link: Vattenfall/ });
    expect(screen.getByText(/Awaiting confirmation/)).toBeInTheDocument();
    const expectedCalls = vi
      .mocked(fetch)
      .mock.calls.filter(([input]) => input.toString().includes("/recurring/expected?"));
    expect(expectedCalls).toHaveLength(1);
    expect(expectedCalls[0][0].toString()).toContain("date_from=2026-07-27&date_to=2026-10-25");

    await user.click(link);
    await waitFor(() => {
      const confirm = vi
        .mocked(fetch)
        .mock.calls.find(([input]) => input.toString().endsWith("/recurring/3/occurrences/2026-08-25/confirm"));
      expect(confirm).toBeDefined();
      expect(JSON.parse(String(confirm?.[1]?.body))).toEqual({ transaction_id: 41 });
    });
  });

  it("confirms a variable amount with the value the member entered", async () => {
    const user = userEvent.setup();
    render(
      <RecurringWorkspace canWrite environment="production" language="en" today={new Date(2026, 7, 26)} />,
    );

    const amount = await screen.findByLabelText("Actual amount · Electricity 2026-08-25");
    await user.clear(amount);
    await user.type(amount, "915,40");
    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      const confirm = vi
        .mocked(fetch)
        .mock.calls.find(([input]) => input.toString().endsWith("/confirm"));
      expect(JSON.parse(String(confirm?.[1]?.body))).toEqual({ amount: "915.40" });
    });
  });
});
