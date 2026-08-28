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

describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const path = input.toString();
        const environment = path.includes("/test/") ? "test" : "production";
        const body = path.endsWith("/setup/status")
          ? {
              environment,
              label: environment === "test" ? "Demo/Test" : "Production",
              data_plane_id: `${environment}-plane`,
              reset_generation: 0,
              setup_required: false,
            }
          : session(environment);
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

  it("loads the authenticated Production foundation without financial sample data", async () => {
    render(<App />);

    expect(await screen.findByText("Platform foundation is active")).toBeInTheDocument();
    expect(screen.getByText("No economic data was created in Sprint 1.")).toBeInTheDocument();
    expect(screen.queryByText("DEMO / TEST")).not.toBeInTheDocument();
  });

  it("switches to the isolated Demo/Test context with a persistent warning", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Platform foundation is active");

    await user.click(screen.getByRole("button", { name: "Demo/Test" }));

    expect(
      await screen.findByText("You are working with fictional and isolated test data."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("DEMO / TEST").length).toBeGreaterThan(0);
    expect(localStorage.getItem("cost-review-environment")).toBe("test");
  });
});
