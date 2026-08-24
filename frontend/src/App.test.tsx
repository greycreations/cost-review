import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = input.toString();
        const body = path.endsWith("/health")
          ? { status: "ok", database: "reachable" }
          : [];

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
    vi.unstubAllGlobals();
  });

  it("shows the connected empty-state foundation", async () => {
    render(<App />);

    expect(await screen.findByText("API connected")).toBeInTheDocument();
    expect(screen.getByText("No recurring expenses yet · 0 registered")).toBeInTheDocument();
  });

  it("changes the selected normalization period", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Annual" }));

    await waitFor(() => {
      expect(screen.getByText("/ year")).toBeInTheDocument();
    });
  });
});
