import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  getInvestmentMarketData,
  getInvestmentPortfolio,
  saveInvestmentPortfolio,
  type Environment,
  type InvestmentMarketData,
  type InvestmentMarketStock,
  type Language,
} from "./api";

type DividendPayment = {
  month: number;
  amountOre: number;
  dateBasis?: "payment_date" | "ex_dividend_date";
};

type Stock = {
  ticker: string;
  name: string;
  sector: string;
  priceOre: number;
  changeToday: number;
  change1m: number;
  change6m: number;
  change1y: number;
  dividends: DividendPayment[];
};

const PREVIEW_STOCKS: Stock[] = [
  {
    ticker: "INVE B",
    name: "Investor B",
    sector: "investment",
    priceOre: 31480,
    changeToday: 0.6,
    change1m: 2.8,
    change6m: 11.2,
    change1y: 18.4,
    dividends: [{ month: 5, amountOre: 180 }, { month: 11, amountOre: 380 }],
  },
  {
    ticker: "VOLV B",
    name: "Volvo B",
    sector: "industry",
    priceOre: 28940,
    changeToday: -0.3,
    change1m: 4.1,
    change6m: 8.7,
    change1y: 11.8,
    dividends: [{ month: 4, amountOre: 1850 }],
  },
  {
    ticker: "SEB A",
    name: "SEB A",
    sector: "finance",
    priceOre: 18155,
    changeToday: 0.2,
    change1m: 5.5,
    change6m: 14.9,
    change1y: 22.6,
    dividends: [{ month: 3, amountOre: 1150 }],
  },
  {
    ticker: "ATCO A",
    name: "Atlas Copco A",
    sector: "industry",
    priceOre: 17230,
    changeToday: -0.8,
    change1m: -1.9,
    change6m: 3.4,
    change1y: -2.7,
    dividends: [{ month: 5, amountOre: 150 }, { month: 10, amountOre: 150 }],
  },
  {
    ticker: "ASSA B",
    name: "Assa Abloy B",
    sector: "industry",
    priceOre: 34120,
    changeToday: 0.4,
    change1m: 1.3,
    change6m: 7.2,
    change1y: 13.9,
    dividends: [{ month: 4, amountOre: 320 }, { month: 11, amountOre: 320 }],
  },
  {
    ticker: "AXFO",
    name: "Axfood",
    sector: "consumer",
    priceOre: 25210,
    changeToday: 0.1,
    change1m: -0.6,
    change6m: 5.8,
    change1y: 9.6,
    dividends: [{ month: 3, amountOre: 438 }, { month: 9, amountOre: 437 }],
  },
  {
    ticker: "TEL2 B",
    name: "Tele2 B",
    sector: "telecom",
    priceOre: 11690,
    changeToday: 0.7,
    change1m: 3.6,
    change6m: 12.1,
    change1y: 16.8,
    dividends: [{ month: 5, amountOre: 318 }, { month: 10, amountOre: 317 }],
  },
  {
    ticker: "EPI A",
    name: "Epiroc A",
    sector: "industry",
    priceOre: 20860,
    changeToday: -0.2,
    change1m: 0.9,
    change6m: 6.6,
    change1y: 8.1,
    dividends: [{ month: 5, amountOre: 190 }, { month: 10, amountOre: 190 }],
  },
  {
    ticker: "SINCH",
    name: "Sinch",
    sector: "technology",
    priceOre: 2560,
    changeToday: 1.1,
    change1m: -4.2,
    change6m: 9.8,
    change1y: -7.4,
    dividends: [],
  },
];

const DEFAULT_SELECTED = ["INVE B", "VOLV B", "SEB A", "AXFO", "TEL2 B"];
const DEFAULT_ALLOCATIONS: Record<string, string> = {
  "INVE B": "30",
  "VOLV B": "20",
  "SEB A": "20",
  AXFO: "15",
  "TEL2 B": "15",
};

const copy = {
  sv: {
    eyebrow: "Portföljverktyg",
    title: "Investeringar",
    lead: "Sålla bland svenska aktier, uppskatta årets utdelningar och fördela nästa köp — på en och samma sida.",
    sample: "Exempeldata · inte live",
    sampleHint: "Kurser och utdelningar är illustrativa i den lokala förhandsvisningen.",
    delayedClosingPrices: "fördröjda slutkurser",
    liveHint: "Kurserna är indikativa och inte handelsunderlag. Utdelning per år bygger på senaste 12 månaderna och kalendermånaderna är historiska, inte bekräftade framtida utbetalningar.",
    liveAsOf: "Senaste handelsdag",
    retrieved: "Hämtad",
    staleData: "Datakällan kunde inte nås. Senast lyckade hämtning visas.",
    saved: "Portföljen sparas i den valda datamiljön.",
    previewSaved: "Dina inmatningar sparas lokalt på den här enheten.",
    savePortfolio: "Spara portfölj",
    saving: "Sparar…",
    saveSuccess: "Portföljen är sparad.",
    unsaved: "Du har osparade ändringar.",
    retry: "Försök igen",
    marketLoading: "Hämtar slutkurser och utdelningshistorik…",
    marketNotConfigured: "Marknadsdata är inte konfigurerad",
    marketNotConfiguredLead: "Den valda marknadsdatakällan saknar nödvändig konfiguration. Kontrollera installationens .env och starta om API-tjänsterna.",
    marketUnavailable: "Marknadsdata kunde inte hämtas just nu.",
    limitedUniverse: "Första urvalet omfattar nio välkända aktier på Nasdaq Stockholm.",
    selectedShares: "Valda aktier",
    portfolioValue: "Portföljvärde",
    expectedDividend: "Beräknad utdelning",
    nextPurchase: "Planerat köp",
    perYear: "/ år",
    addHoldings: "Fyll i dina innehav nedan",
    noPurchase: "Ange en köpbudget nedan",
    screener: "Aktiescreener",
    exchange: "Stockholmsbörsen",
    exchangeLead: "Välj bolag att ta med i din portföljvy och köpplan.",
    search: "Sök bolag eller ticker",
    sector: "Sektor",
    allSectors: "Alla sektorer",
    dividend: "Utdelning",
    all: "Alla",
    paysDividend: "Delar ut",
    noDividend: "Delar inte ut",
    oneYear: "Utveckling 1 år",
    anyDevelopment: "Alla nivåer",
    positive: "Över 0 %",
    overTen: "Över 10 %",
    maxPrice: "Högsta pris",
    maxPricePlaceholder: "Valfritt",
    clear: "Rensa filter",
    matches: "träffar",
    select: "Välj",
    company: "Bolag",
    price: "Pris",
    today: "I dag",
    oneMonth: "1 mån",
    sixMonths: "6 mån",
    dividendYield: "Direktavk.",
    dividendShare: "Utd./aktie",
    payout: "Utbetalning",
    noMatches: "Inga aktier matchar de valda filtren.",
    currentPortfolio: "Nuvarande portfölj",
    holdingsTitle: "Innehav & utdelningar",
    holdingsLead: "Ange antal aktier. Beloppen nedan är en årsprognos före skatt.",
    owned: "Antal ägda",
    value: "Värde",
    annualDividend: "Utdelning / år",
    total: "Totalt",
    weightedYield: "Historisk direktavkastning på senaste slutkurs",
    dividendCalendar: "Utdelningskalender",
    dividendCalendarLead: "Indikativ årsfördelning från de senaste 12 månadernas betalnings- eller X-datum.",
    noHoldings: "Lägg in minst ett innehav för att se utdelningen över året.",
    planning: "Köpplan",
    purchaseTitle: "Fördela nästa investering",
    purchaseLead: "Budgeten delas enligt dina procenttal. Endast hela aktier räknas med.",
    budget: "Total köpbudget",
    allocation: "Fördelning",
    equal: "Fördela jämnt",
    reset: "Nollställ",
    percentage: "Andel",
    budgetShare: "Budgetandel",
    sharesToBuy: "Antal att köpa",
    purchaseCost: "Kostnad",
    cashLeft: "Kvar i andel",
    allocationExact: "Hela budgeten är fördelad.",
    allocationLow: "av budgeten är ännu inte fördelad.",
    allocationHigh: "Fördelningen överskrider 100 %. Sänk någon av andelarna.",
    actualCost: "Total köpkostnad",
    remainingCash: "Kvar efter köp",
    allocatedBudget: "Fördelad budget",
    noSelected: "Välj minst en aktie i screenern för att skapa en portfölj och köpplan.",
    sectors: { investment: "Investmentbolag", industry: "Industri", finance: "Finans", consumer: "Dagligvaror", telecom: "Telekom", technology: "Teknik" },
  },
  en: {
    eyebrow: "Portfolio workspace",
    title: "Investments",
    lead: "Screen Swedish shares, estimate annual dividends and allocate your next purchase — all on one page.",
    sample: "Sample data · not live",
    sampleHint: "Prices and dividends are illustrative in the local preview.",
    delayedClosingPrices: "delayed closing prices",
    liveHint: "Prices are indicative and not trading data. Annual dividends use the trailing 12 months and calendar months show history, not confirmed future payments.",
    liveAsOf: "Latest trading day",
    retrieved: "Retrieved",
    staleData: "The data source could not be reached. Showing the latest successful retrieval.",
    saved: "The portfolio is stored in the selected data environment.",
    previewSaved: "Your entries are stored locally on this device.",
    savePortfolio: "Save portfolio",
    saving: "Saving…",
    saveSuccess: "Portfolio saved.",
    unsaved: "You have unsaved changes.",
    retry: "Try again",
    marketLoading: "Loading closing prices and dividend history…",
    marketNotConfigured: "Market data is not configured",
    marketNotConfiguredLead: "The selected market-data source is missing required configuration. Check the installation .env and restart the API services.",
    marketUnavailable: "Market data could not be loaded right now.",
    limitedUniverse: "The starter universe contains nine well-known Nasdaq Stockholm shares.",
    selectedShares: "Selected shares",
    portfolioValue: "Portfolio value",
    expectedDividend: "Estimated dividend",
    nextPurchase: "Planned purchase",
    perYear: "/ year",
    addHoldings: "Add your holdings below",
    noPurchase: "Enter a purchase budget below",
    screener: "Stock screener",
    exchange: "Stockholm exchange",
    exchangeLead: "Choose companies to include in your portfolio and purchase plan.",
    search: "Search company or ticker",
    sector: "Sector",
    allSectors: "All sectors",
    dividend: "Dividend",
    all: "All",
    paysDividend: "Pays dividend",
    noDividend: "No dividend",
    oneYear: "1-year performance",
    anyDevelopment: "Any performance",
    positive: "Above 0%",
    overTen: "Above 10%",
    maxPrice: "Maximum price",
    maxPricePlaceholder: "Optional",
    clear: "Clear filters",
    matches: "matches",
    select: "Select",
    company: "Company",
    price: "Price",
    today: "Today",
    oneMonth: "1 mo",
    sixMonths: "6 mo",
    dividendYield: "Yield",
    dividendShare: "Dividend/share",
    payout: "Payout",
    noMatches: "No shares match the selected filters.",
    currentPortfolio: "Current portfolio",
    holdingsTitle: "Holdings & dividends",
    holdingsLead: "Enter the number of shares held. Amounts are annual estimates before tax.",
    owned: "Shares held",
    value: "Value",
    annualDividend: "Dividend / year",
    total: "Total",
    weightedYield: "Historical yield at the latest closing price",
    dividendCalendar: "Dividend calendar",
    dividendCalendarLead: "Indicative annual pattern from payment or ex-dividend dates during the trailing 12 months.",
    noHoldings: "Add at least one holding to see how dividends are distributed through the year.",
    planning: "Purchase plan",
    purchaseTitle: "Allocate your next investment",
    purchaseLead: "The budget is divided by your percentages. Only whole shares are included.",
    budget: "Total purchase budget",
    allocation: "Allocation",
    equal: "Split equally",
    reset: "Reset",
    percentage: "Share",
    budgetShare: "Budget allocation",
    sharesToBuy: "Shares to buy",
    purchaseCost: "Cost",
    cashLeft: "Left in allocation",
    allocationExact: "The full budget is allocated.",
    allocationLow: "of the budget is not yet allocated.",
    allocationHigh: "The allocation exceeds 100%. Reduce one of the percentages.",
    actualCost: "Total purchase cost",
    remainingCash: "Cash remaining",
    allocatedBudget: "Allocated budget",
    noSelected: "Select at least one share in the screener to create a portfolio and purchase plan.",
    sectors: { investment: "Investment company", industry: "Industrials", finance: "Financials", consumer: "Consumer staples", telecom: "Telecom", technology: "Technology" },
  },
} as const;

function readStoredRecord(key: string, fallback: Record<string, string>): Record<string, string> {
  try {
    const value = localStorage.getItem(key);
    return value ? { ...fallback, ...(JSON.parse(value) as Record<string, string>) } : fallback;
  } catch {
    return fallback;
  }
}

function readStoredSelection(): string[] {
  try {
    const stored = JSON.parse(localStorage.getItem("cost-review-selected-stocks") ?? "null") as unknown;
    if (!Array.isArray(stored)) return DEFAULT_SELECTED;
    const valid = stored.filter((ticker): ticker is string => typeof ticker === "string" && PREVIEW_STOCKS.some((stock) => stock.ticker === ticker));
    return valid;
  } catch {
    return DEFAULT_SELECTED;
  }
}

function dividendPerShare(stock: Stock): number {
  return stock.dividends.reduce((sum, payment) => sum + payment.amountOre, 0);
}

function parsePositiveInteger(value: string): number {
  if (!/^\d+$/.test(value.trim())) return 0;
  return Math.min(Number(value), 1_000_000_000);
}

function parseMoneyToOre(value: string): number {
  const normalized = value.trim().replace(/\s/g, "").replace(",", ".");
  if (!/^\d+(\.\d{0,2})?$/.test(normalized)) return 0;
  const [whole, decimals = ""] = normalized.split(".");
  const ore = Number(whole) * 100 + Number(decimals.padEnd(2, "0"));
  return Number.isSafeInteger(ore) ? Math.min(ore, 100_000_000_000) : 0;
}

function decimalStringToOre(value: string): number {
  const normalized = value.trim();
  if (!/^\d+(\.\d+)?$/.test(normalized)) return 0;
  const [whole, decimals = ""] = normalized.split(".");
  const rounded = Number(decimals[2] ?? "0") >= 5;
  const ore =
    Number(whole) * 100 +
    Number(decimals.slice(0, 2).padEnd(2, "0")) +
    (rounded ? 1 : 0);
  return Number.isSafeInteger(ore) ? ore : 0;
}

function moneyInputFromDecimal(value: string): string {
  const normalized = value.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  return normalized === "0" ? "" : normalized;
}

function percentInputFromDecimal(value: string): string {
  return value.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "") || "0";
}

function apiStockToStock(stock: InvestmentMarketStock): Stock {
  return {
    ticker: stock.ticker,
    name: stock.name,
    sector: stock.sector,
    priceOre: decimalStringToOre(stock.price),
    changeToday: Number(stock.changes.one_day),
    change1m: Number(stock.changes.one_month),
    change6m: Number(stock.changes.six_months),
    change1y: Number(stock.changes.one_year),
    dividends: stock.dividend_pattern.map((payment) => ({
      month: payment.month,
      amountOre: decimalStringToOre(payment.amount),
      dateBasis: payment.date_basis,
    })),
  };
}

function percentageToBasisPoints(value: string): number {
  const normalized = value.trim().replace(",", ".");
  if (!/^\d+(\.\d{0,2})?$/.test(normalized)) return 0;
  const [whole, decimals = ""] = normalized.split(".");
  return Math.min(Number(whole) * 100 + Number(decimals.padEnd(2, "0")), 100_000);
}

function formatMoney(ore: number, language: Language, decimals = true): string {
  const locale = language === "sv" ? "sv-SE" : "en-GB";
  const whole = Math.floor(Math.abs(ore) / 100);
  const cents = Math.abs(ore) % 100;
  const sign = ore < 0 ? "−" : "";
  const fraction = decimals ? `${language === "sv" ? "," : "."}${String(cents).padStart(2, "0")}` : "";
  return `${sign}${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(whole)}${fraction} kr`;
}

function formatPercent(value: number, language: Language): string {
  return `${value > 0 ? "+" : ""}${value.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
}

function monthName(month: number, language: Language, short = false): string {
  return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-GB", { month: short ? "short" : "long" }).format(new Date(2026, month - 1, 1)).replace(".", "");
}

function TrendValue({ value, language }: { value: number; language: Language }) {
  return <span className={value >= 0 ? "stock-trend positive" : "stock-trend negative"}>{formatPercent(value, language)}</span>;
}

export function InvestmentWorkspace({
  language,
  environment = "production",
  preview = false,
}: {
  language: Language;
  environment?: Environment;
  preview?: boolean;
}) {
  const labels = copy[language];
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("all");
  const [dividendFilter, setDividendFilter] = useState("all");
  const [performanceFilter, setPerformanceFilter] = useState("all");
  const [maxPrice, setMaxPrice] = useState("");
  const [stocks, setStocks] = useState<Stock[]>(preview ? PREVIEW_STOCKS : []);
  const [marketSnapshot, setMarketSnapshot] = useState<InvestmentMarketData | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "not-configured" | "error">(
    preview ? "ready" : "loading",
  );
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [selected, setSelected] = useState<string[]>(preview ? readStoredSelection() : []);
  const [holdings, setHoldings] = useState<Record<string, string>>(() =>
    preview ? readStoredRecord("cost-review-stock-holdings", {}) : {},
  );
  const [allocations, setAllocations] = useState<Record<string, string>>(() =>
    preview ? readStoredRecord("cost-review-stock-allocations", DEFAULT_ALLOCATIONS) : {},
  );
  const [budget, setBudget] = useState(() =>
    preview ? (localStorage.getItem("cost-review-stock-budget") ?? "10000") : "",
  );
  const [dirty, setDirty] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (preview) localStorage.setItem("cost-review-selected-stocks", JSON.stringify(selected));
  }, [preview, selected]);
  useEffect(() => {
    if (preview) localStorage.setItem("cost-review-stock-holdings", JSON.stringify(holdings));
  }, [holdings, preview]);
  useEffect(() => {
    if (preview) localStorage.setItem("cost-review-stock-allocations", JSON.stringify(allocations));
  }, [allocations, preview]);
  useEffect(() => {
    if (preview) localStorage.setItem("cost-review-stock-budget", budget);
  }, [budget, preview]);

  useEffect(() => {
    if (preview) return;
    let active = true;
    void Promise.all([getInvestmentMarketData(environment), getInvestmentPortfolio(environment)])
      .then(([market, portfolio]) => {
        if (!active) return;
        setMarketSnapshot(market);
        setStocks(market.stocks.map(apiStockToStock));
        setSelected(portfolio.positions.map((position) => position.ticker));
        setHoldings(
          Object.fromEntries(
            portfolio.positions.map((position) => [
              position.ticker,
              position.shares ? String(position.shares) : "",
            ]),
          ),
        );
        setAllocations(
          Object.fromEntries(
            portfolio.positions.map((position) => [
              position.ticker,
              percentInputFromDecimal(position.target_percentage),
            ]),
          ),
        );
        setBudget(moneyInputFromDecimal(portfolio.purchase_budget));
        setDirty(false);
        setSaveState("idle");
        setLoadState("ready");
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof ApiError && error.code === "market_data_not_configured") {
          setLoadState("not-configured");
        } else {
          setLoadError(error instanceof Error ? error.message : labels.marketUnavailable);
          setLoadState("error");
        }
      });
    return () => {
      active = false;
    };
  }, [environment, labels.marketUnavailable, preview, reloadKey]);

  const markDirty = () => {
    if (!preview) {
      setDirty(true);
      setSaveState("idle");
      setSaveError(null);
    }
  };

  const selectedStocks = useMemo(
    () => stocks.filter((stock) => selected.includes(stock.ticker)),
    [selected, stocks],
  );
  const visibleStocks = useMemo(() => {
    const maximumOre = maxPrice ? parseMoneyToOre(maxPrice) : Number.POSITIVE_INFINITY;
    const normalizedQuery = query.trim().toLocaleLowerCase(language === "sv" ? "sv-SE" : "en-GB");
    return stocks.filter((stock) => {
      const matchesQuery = `${stock.name} ${stock.ticker}`.toLocaleLowerCase().includes(normalizedQuery);
      const matchesSector = sector === "all" || stock.sector === sector;
      const hasDividend = dividendPerShare(stock) > 0;
      const matchesDividend = dividendFilter === "all" || (dividendFilter === "yes" ? hasDividend : !hasDividend);
      const matchesPerformance = performanceFilter === "all" || (performanceFilter === "positive" ? stock.change1y > 0 : stock.change1y > 10);
      return matchesQuery && matchesSector && matchesDividend && matchesPerformance && stock.priceOre <= maximumOre;
    });
  }, [dividendFilter, language, maxPrice, performanceFilter, query, sector, stocks]);

  const portfolioValueOre = selectedStocks.reduce((sum, stock) => sum + stock.priceOre * parsePositiveInteger(holdings[stock.ticker] ?? "0"), 0);
  const annualDividendOre = selectedStocks.reduce((sum, stock) => sum + dividendPerShare(stock) * parsePositiveInteger(holdings[stock.ticker] ?? "0"), 0);
  const weightedYield = portfolioValueOre > 0 ? (annualDividendOre / portfolioValueOre) * 100 : 0;
  const monthlyDividends = Array.from({ length: 12 }, (_, index) => selectedStocks.reduce((sum, stock) => {
    const payment = stock.dividends.find((item) => item.month === index + 1);
    return sum + (payment?.amountOre ?? 0) * parsePositiveInteger(holdings[stock.ticker] ?? "0");
  }, 0));
  const maxMonthlyDividend = Math.max(...monthlyDividends, 1);

  const budgetOre = parseMoneyToOre(budget);
  const purchaseRows = selectedStocks.map((stock) => {
    const basisPoints = percentageToBasisPoints(allocations[stock.ticker] ?? "0");
    const allocatedOre = Math.floor((budgetOre * basisPoints) / 10_000);
    const shareCount = Math.floor(allocatedOre / stock.priceOre);
    const costOre = shareCount * stock.priceOre;
    return { stock, basisPoints, allocatedOre, shareCount, costOre, remainingOre: allocatedOre - costOre };
  });
  const totalBasisPoints = purchaseRows.reduce((sum, row) => sum + row.basisPoints, 0);
  const totalPurchaseCostOre = purchaseRows.reduce((sum, row) => sum + row.costOre, 0);
  const totalAllocatedOre = purchaseRows.reduce((sum, row) => sum + row.allocatedOre, 0);
  const remainingBudgetOre = Math.max(0, budgetOre - totalPurchaseCostOre);

  const toggleSelected = (ticker: string) => {
    setSelected((current) => current.includes(ticker) ? current.filter((item) => item !== ticker) : [...current, ticker]);
    markDirty();
  };

  const distributeEqually = () => {
    if (selectedStocks.length === 0) return;
    const base = Math.floor(10_000 / selectedStocks.length);
    let remainder = 10_000 - base * selectedStocks.length;
    setAllocations((current) => ({ ...current, ...Object.fromEntries(selectedStocks.map((stock) => {
      const value = base + (remainder-- > 0 ? 1 : 0);
      return [stock.ticker, (value / 100).toFixed(2).replace(/\.00$/, "")];
    })) }));
    markDirty();
  };

  const resetFilters = () => {
    setQuery("");
    setSector("all");
    setDividendFilter("all");
    setPerformanceFilter("all");
    setMaxPrice("");
  };

  const savePortfolio = async () => {
    if (preview || totalBasisPoints > 10_000) return;
    setSaveState("saving");
    setSaveError(null);
    try {
      const saved = await saveInvestmentPortfolio(environment, {
        purchase_budget: (budgetOre / 100).toFixed(2),
        positions: selectedStocks.map((stock) => ({
          ticker: stock.ticker,
          shares: parsePositiveInteger(holdings[stock.ticker] ?? "0"),
          target_percentage: (percentageToBasisPoints(allocations[stock.ticker] ?? "0") / 100).toFixed(2),
        })),
      });
      setBudget(moneyInputFromDecimal(saved.purchase_budget));
      setDirty(false);
      setSaveState("saved");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : labels.marketUnavailable);
      setSaveState("error");
    }
  };

  if (!preview && loadState !== "ready") {
    return (
      <section className="investment-workspace workspace-view" aria-labelledby="investment-title">
        <div className="investment-heading">
          <div>
            <p className="eyebrow">{labels.eyebrow}</p>
            <h1 id="investment-title">{labels.title}</h1>
            <p>{labels.lead}</p>
          </div>
        </div>
        <div
          className={`investment-panel investment-market-state ${loadState === "loading" ? "loading" : "error"}`}
          role={loadState === "loading" ? "status" : "alert"}
        >
          {loadState === "loading" ? (
            <>
              <span className="status-pulse" aria-hidden="true" />
              <p>{labels.marketLoading}</p>
            </>
          ) : (
            <>
              <h2>
                {loadState === "not-configured"
                  ? labels.marketNotConfigured
                  : labels.marketUnavailable}
              </h2>
              <p>
                {loadState === "not-configured"
                  ? labels.marketNotConfiguredLead
                  : loadError ?? labels.marketUnavailable}
              </p>
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  setLoadState("loading");
                  setLoadError(null);
                  setReloadKey((value) => value + 1);
                }}
              >
                {labels.retry}
              </button>
            </>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className="investment-workspace workspace-view" aria-labelledby="investment-title">
      <div className="investment-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1 id="investment-title">{labels.title}</h1>
          <p>{labels.lead}</p>
        </div>
        <div className="investment-data-note">
          {preview || !marketSnapshot ? (
            <span className="demo-data-badge">{labels.sample}</span>
          ) : (
            <a
              className="live-data-badge"
              href={marketSnapshot.source_url}
              rel="noreferrer"
              target="_blank"
            >
              {marketSnapshot.source} · {labels.delayedClosingPrices}
            </a>
          )}
          <span>{preview ? labels.sampleHint : labels.liveHint}</span>
          {!preview && marketSnapshot ? (
            <small>
              {marketSnapshot.is_stale ? (
                <span className="stale-data-note">{labels.staleData}</span>
              ) : null}
              {labels.liveAsOf}: {marketSnapshot.data_date} · {labels.retrieved}{" "}
              {new Date(marketSnapshot.retrieved_at).toLocaleString(
                language === "sv" ? "sv-SE" : "en-GB",
                { dateStyle: "short", timeStyle: "short" },
              )}
              <br />
              {labels.limitedUniverse}
            </small>
          ) : null}
          {!preview ? (
            <div className="investment-save-row">
              <button
                className="primary-button"
                disabled={!dirty || saveState === "saving" || totalBasisPoints > 10_000}
                type="button"
                onClick={() => void savePortfolio()}
              >
                {saveState === "saving" ? labels.saving : labels.savePortfolio}
              </button>
              <span className={saveState === "error" ? "save-error" : undefined}>
                {saveState === "saved"
                  ? labels.saveSuccess
                  : saveState === "error"
                    ? saveError
                    : dirty
                      ? labels.unsaved
                      : labels.saved}
              </span>
            </div>
          ) : null}
        </div>
      </div>

      <div className="investment-summary" aria-label={labels.selectedShares}>
        <div>
          <span>{labels.selectedShares}</span>
          <strong>{selectedStocks.length}</strong>
          <p>{preview ? labels.previewSaved : labels.saved}</p>
        </div>
        <div>
          <span>{labels.portfolioValue}</span>
          <strong>{formatMoney(portfolioValueOre, language)}</strong>
          <p>{portfolioValueOre > 0 ? `${selectedStocks.filter((stock) => parsePositiveInteger(holdings[stock.ticker] ?? "0") > 0).length} ${language === "sv" ? "innehav" : "holdings"}` : labels.addHoldings}</p>
        </div>
        <div className="summary-feature">
          <span>{labels.expectedDividend}</span>
          <strong>{formatMoney(annualDividendOre, language)} <small>{labels.perYear}</small></strong>
          <p>{portfolioValueOre > 0 ? `${weightedYield.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} % ${language === "sv" ? "av portföljvärdet" : "of portfolio value"}` : labels.addHoldings}</p>
        </div>
        <div>
          <span>{labels.nextPurchase}</span>
          <strong>{formatMoney(totalPurchaseCostOre, language)}</strong>
          <p>{budgetOre > 0 ? `${purchaseRows.reduce((sum, row) => sum + row.shareCount, 0)} ${language === "sv" ? "aktier" : "shares"}` : labels.noPurchase}</p>
        </div>
      </div>

      <section className="investment-panel screener-panel" aria-labelledby="stock-list-title">
        <div className="investment-panel-heading">
          <div>
            <p className="panel-label">{labels.screener}</p>
            <h2 id="stock-list-title">{labels.exchange}</h2>
            <p>{labels.exchangeLead}</p>
          </div>
          <button className="quiet-button" type="button" onClick={resetFilters}>{labels.clear}</button>
        </div>

        <div className="investment-filter-grid">
          <label className="search-filter">
            <span>{labels.search}</span>
            <div className="input-with-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={language === "sv" ? "t.ex. Investor" : "e.g. Investor"} />
            </div>
          </label>
          <label>
            <span>{labels.sector}</span>
            <select value={sector} onChange={(event) => setSector(event.target.value)}>
              <option value="all">{labels.allSectors}</option>
              {Object.entries(labels.sectors).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            <span>{labels.dividend}</span>
            <select value={dividendFilter} onChange={(event) => setDividendFilter(event.target.value)}>
              <option value="all">{labels.all}</option>
              <option value="yes">{labels.paysDividend}</option>
              <option value="no">{labels.noDividend}</option>
            </select>
          </label>
          <label>
            <span>{labels.oneYear}</span>
            <select value={performanceFilter} onChange={(event) => setPerformanceFilter(event.target.value)}>
              <option value="all">{labels.anyDevelopment}</option>
              <option value="positive">{labels.positive}</option>
              <option value="ten">{labels.overTen}</option>
            </select>
          </label>
          <label>
            <span>{labels.maxPrice}</span>
            <div className="money-input"><input inputMode="decimal" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} placeholder={labels.maxPricePlaceholder} /><span>kr</span></div>
          </label>
        </div>

        <div className="table-meta"><span>{visibleStocks.length} {labels.matches}</span><span>{selectedStocks.length} {language === "sv" ? "valda" : "selected"}</span></div>
        <div className="investment-table-scroll">
          <table className="investment-table" aria-label={labels.exchange}>
            <thead>
              <tr><th className="select-column"><span className="sr-only">{labels.select}</span></th><th>{labels.company}</th><th>{labels.price}</th><th>{labels.today}</th><th>{labels.oneMonth}</th><th>{labels.sixMonths}</th><th>1 år</th><th>{labels.dividendYield}</th><th>{labels.dividendShare}</th><th>{labels.payout}</th></tr>
            </thead>
            <tbody>
              {visibleStocks.map((stock) => {
                const annualPerShare = dividendPerShare(stock);
                const isSelected = selected.includes(stock.ticker);
                return (
                  <tr key={stock.ticker} className={isSelected ? "selected-row" : undefined}>
                    <td className="select-column"><input type="checkbox" aria-label={`${labels.select} ${stock.name}`} checked={isSelected} onChange={() => toggleSelected(stock.ticker)} /></td>
                    <td><strong>{stock.name}</strong><span>{stock.ticker} · {(labels.sectors as Record<string, string>)[stock.sector] ?? stock.sector}</span></td>
                    <td>{formatMoney(stock.priceOre, language)}</td>
                    <td><TrendValue value={stock.changeToday} language={language} /></td>
                    <td><TrendValue value={stock.change1m} language={language} /></td>
                    <td><TrendValue value={stock.change6m} language={language} /></td>
                    <td><TrendValue value={stock.change1y} language={language} /></td>
                    <td>{annualPerShare > 0 ? `${((annualPerShare / stock.priceOre) * 100).toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %` : "—"}</td>
                    <td>{annualPerShare > 0 ? formatMoney(annualPerShare, language) : "—"}</td>
                    <td>{stock.dividends.length > 0 ? stock.dividends.map((item) => monthName(item.month, language, true)).join(" + ") : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {visibleStocks.length === 0 ? <p className="investment-empty">{labels.noMatches}</p> : null}
        </div>
      </section>

      {selectedStocks.length === 0 ? <div className="investment-empty large">{labels.noSelected}</div> : (
        <>
          <section className="investment-panel holdings-panel" aria-labelledby="holdings-title">
            <div className="investment-panel-heading">
              <div><p className="panel-label">{labels.currentPortfolio}</p><h2 id="holdings-title">{labels.holdingsTitle}</h2><p>{labels.holdingsLead}</p></div>
              <div className="yield-callout"><span>{labels.expectedDividend}</span><strong>{formatMoney(annualDividendOre, language, false)}</strong><small>{weightedYield.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} % · {labels.weightedYield}</small></div>
            </div>
            <div className="investment-table-scroll holdings-table-scroll">
              <table className="investment-table holdings-table" aria-label={labels.holdingsTitle}>
                <thead><tr><th>{labels.company}</th><th>{labels.owned}</th><th>{labels.price}</th><th>{labels.value}</th><th>{labels.dividendShare}</th><th>{labels.annualDividend}</th></tr></thead>
                <tbody>
                  {selectedStocks.map((stock) => {
                    const shares = parsePositiveInteger(holdings[stock.ticker] ?? "0");
                    return <tr key={stock.ticker}><td><strong>{stock.name}</strong><span>{stock.ticker}</span></td><td><input className="table-number-input" type="number" min="0" step="1" inputMode="numeric" aria-label={`${labels.owned} · ${stock.name}`} value={holdings[stock.ticker] ?? ""} placeholder="0" onChange={(event) => { setHoldings((current) => ({ ...current, [stock.ticker]: event.target.value.replace(/[^\d]/g, "") })); markDirty(); }} /></td><td>{formatMoney(stock.priceOre, language)}</td><td>{formatMoney(stock.priceOre * shares, language)}</td><td>{formatMoney(dividendPerShare(stock), language)}</td><td className="strong-cell">{formatMoney(dividendPerShare(stock) * shares, language)}</td></tr>;
                  })}
                </tbody>
                <tfoot><tr><th>{labels.total}</th><td></td><td></td><td>{formatMoney(portfolioValueOre, language)}</td><td></td><td>{formatMoney(annualDividendOre, language)}</td></tr></tfoot>
              </table>
            </div>

            <div className="dividend-calendar">
              <div className="calendar-heading"><div><h3>{labels.dividendCalendar}</h3><p>{labels.dividendCalendarLead}</p></div><strong>{formatMoney(annualDividendOre, language, false)} <small>{labels.perYear}</small></strong></div>
              <div className="calendar-chart" aria-label={labels.dividendCalendar}>
                {monthlyDividends.map((amountOre, index) => <div className="calendar-month" key={index}><div className="calendar-value">{amountOre > 0 ? formatMoney(amountOre, language, false) : "—"}</div><div className="calendar-bar-track"><span style={{ height: `${Math.max(amountOre > 0 ? 8 : 0, (amountOre / maxMonthlyDividend) * 100)}%` }} /></div><span>{monthName(index + 1, language, true)}</span></div>)}
              </div>
              {annualDividendOre === 0 ? <p className="calendar-empty">{labels.noHoldings}</p> : null}
            </div>
          </section>

          <section className="investment-panel purchase-panel" aria-labelledby="purchase-title">
            <div className="investment-panel-heading purchase-heading">
              <div><p className="panel-label">{labels.planning}</p><h2 id="purchase-title">{labels.purchaseTitle}</h2><p>{labels.purchaseLead}</p></div>
              <label className="budget-field"><span>{labels.budget}</span><div className="money-input large"><input aria-label={labels.budget} inputMode="decimal" value={budget} onChange={(event) => { setBudget(event.target.value); markDirty(); }} /><span>kr</span></div></label>
            </div>

            <div className="allocation-status">
              <div className="allocation-copy"><span>{labels.allocation}</span><strong className={totalBasisPoints > 10_000 ? "over" : undefined}>{(totalBasisPoints / 100).toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { maximumFractionDigits: 2 })} %</strong><span>{totalBasisPoints === 10_000 ? labels.allocationExact : totalBasisPoints > 10_000 ? labels.allocationHigh : `${((10_000 - totalBasisPoints) / 100).toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { maximumFractionDigits: 2 })} % ${labels.allocationLow}`}</span></div>
              <div className="allocation-actions"><button className="quiet-button" type="button" onClick={distributeEqually}>{labels.equal}</button><button className="ghost-button" type="button" onClick={() => { setAllocations((current) => ({ ...current, ...Object.fromEntries(selectedStocks.map((stock) => [stock.ticker, "0"])) })); markDirty(); }}>{labels.reset}</button></div>
              <div className="allocation-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, totalBasisPoints / 100)}><span className={totalBasisPoints > 10_000 ? "over" : undefined} style={{ width: `${Math.min(100, totalBasisPoints / 100)}%` }} /></div>
            </div>

            <div className="investment-table-scroll purchase-table-scroll">
              <table className="investment-table purchase-table" aria-label={labels.purchaseTitle}>
                <thead><tr><th>{labels.company}</th><th>{labels.percentage}</th><th>{labels.budgetShare}</th><th>{labels.price}</th><th>{labels.sharesToBuy}</th><th>{labels.purchaseCost}</th><th>{labels.cashLeft}</th></tr></thead>
                <tbody>{purchaseRows.map((row) => <tr key={row.stock.ticker}><td><strong>{row.stock.name}</strong><span>{row.stock.ticker}</span></td><td><div className="percent-input"><input type="number" min="0" max="100" step="0.1" inputMode="decimal" aria-label={`${labels.percentage} · ${row.stock.name}`} value={allocations[row.stock.ticker] ?? ""} onChange={(event) => { setAllocations((current) => ({ ...current, [row.stock.ticker]: event.target.value })); markDirty(); }} /><span>%</span></div></td><td>{formatMoney(row.allocatedOre, language)}</td><td>{formatMoney(row.stock.priceOre, language)}</td><td className="share-count"><strong>{row.shareCount}</strong></td><td className="strong-cell">{formatMoney(row.costOre, language)}</td><td>{formatMoney(row.remainingOre, language)}</td></tr>)}</tbody>
              </table>
            </div>
            <div className="purchase-totals">
              <div><span>{labels.allocatedBudget}</span><strong>{formatMoney(totalAllocatedOre, language)}</strong></div>
              <div className="featured"><span>{labels.actualCost}</span><strong>{formatMoney(totalPurchaseCostOre, language)}</strong></div>
              <div><span>{labels.remainingCash}</span><strong>{formatMoney(remainingBudgetOre, language)}</strong></div>
            </div>
          </section>
        </>
      )}
    </section>
  );
}
