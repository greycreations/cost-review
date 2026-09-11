import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { InvestmentWorkspace } from "./InvestmentWorkspace";

describe("InvestmentWorkspace", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => cleanup());

  it("filters the sample universe and keeps stock selection explicit", async () => {
    const user = userEvent.setup();
    render(<InvestmentWorkspace language="en" preview />);

    const screener = screen.getByRole("heading", { name: "Stockholm exchange" }).closest("section");
    expect(screener).not.toBeNull();

    await user.selectOptions(screen.getByLabelText("Dividend"), "no");
    expect(within(screener as HTMLElement).getByText("Sinch")).toBeInTheDocument();
    expect(within(screener as HTMLElement).queryByText("Investor B")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.click(screen.getByRole("checkbox", { name: "Select Atlas Copco A" }));
    expect(screen.getAllByText("6 selected").length).toBeGreaterThan(0);
  });

  it("calculates portfolio value and annual dividends from whole shares", async () => {
    const user = userEvent.setup();
    render(<InvestmentWorkspace language="en" preview />);

    await user.type(screen.getByRole("spinbutton", { name: "Shares held · Investor B" }), "10");
    await user.type(screen.getByRole("spinbutton", { name: "Shares held · Volvo B" }), "5");

    const holdings = screen.getByRole("heading", { name: "Holdings & dividends" }).closest("section");
    expect(holdings).not.toBeNull();
    expect(within(holdings as HTMLElement).getAllByText("3,148.00 kr").length).toBeGreaterThan(0);
    expect(within(holdings as HTMLElement).getAllByText("148.50 kr").length).toBeGreaterThan(0);
  });

  it("turns a budget allocation into purchasable whole shares", () => {
    render(<InvestmentWorkspace language="en" preview />);

    const purchase = screen.getByRole("heading", { name: "Allocate your next investment" }).closest("section");
    expect(purchase).not.toBeNull();
    expect(within(purchase as HTMLElement).getByText("The full budget is allocated.")).toBeInTheDocument();
    expect(within(purchase as HTMLElement).getByText("9,229.95 kr")).toBeInTheDocument();
    expect(within(purchase as HTMLElement).getByText("770.05 kr")).toBeInTheDocument();
  });
});
