import { useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  getInvestmentFundData,
  getInvestmentMarketData,
  getInvestmentPortfolio,
  saveInvestmentPortfolio,
  type Environment,
  type InvestmentMarketData,
  type InvestmentMarketStock,
  type InvestmentFund,
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
  change1m: number | null;
  change6m: number | null;
  change1y: number;
  annualDividendOre?: number;
  dividends: DividendPayment[];
  detailLevel?: "summary" | "history";
};

type Fund = {
  isin: string;
  name: string;
  category: string;
  fundType: string;
  fundCompany: string;
  navOre: number;
  changeToday: number;
  change1m: number | null;
  change6m: number | null;
  change1y: number;
  productFee: number;
  managementFee: number;
  risk: number | null;
  rating: number | null;
  indexFund: boolean;
  navDate: string;
};

const STOCK_PAGE_SIZE = 50;

const PREVIEW_STOCKS: Stock[] = [
  {
    ticker: "INVE B",
    name: "Investor B",
    sector: "financial_services",
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
    sector: "industrials",
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
    sector: "financial_services",
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
    sector: "industrials",
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
    sector: "industrials",
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
    sector: "consumer_defensive",
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
    sector: "communication_services",
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
    sector: "industrials",
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

const PREVIEW_FUNDS: Fund[] = [
  { isin: "SE0005188836", name: "Länsförsäkringar Global Index", category: "Global", fundType: "Aktiefond", fundCompany: "Länsförsäkringar Fondförvaltning", navOre: 59729, changeToday: 0.3, change1m: 2.1, change6m: 8.4, change1y: 14.7, productFee: 0.21, managementFee: 0.2, risk: 4, rating: 4, indexFund: true, navDate: "2026-09-10" },
  { isin: "SE0001718388", name: "Avanza Zero", category: "Sverige", fundType: "Aktiefond", fundCompany: "Avanza", navOre: 56161, changeToday: -0.45, change1m: -1.97, change6m: 7.91, change1y: 25.53, productFee: 0, managementFee: 0, risk: 4, rating: 5, indexFund: true, navDate: "2026-09-10" },
  { isin: "SE0012454338", name: "Avanza Emerging Markets", category: "Tillväxtmarknader", fundType: "Aktiefond", fundCompany: "Avanza", navOre: 20002, changeToday: 0.28, change1m: 1.8, change6m: 11.4, change1y: 18.2, productFee: 0.23, managementFee: 0.15, risk: 4, rating: 4, indexFund: true, navDate: "2026-09-10" },
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
    lead: "Sålla bland svenska aktier och fonder, uppskatta årets utdelningar och fördela nästa köp — på en och samma sida.",
    stocksTab: "Aktier",
    fundsTab: "Fonder",
    sample: "Exempeldata · inte live",
    sampleHint: "Kurser och utdelningar är illustrativa i den lokala förhandsvisningen.",
    delayedClosingPrices: "fördröjda slutkurser",
    liveHint: "Kurserna är indikativa och inte handelsunderlag. Utdelning per år bygger på senaste 12 månaderna och kalendermånaderna är historiska, inte bekräftade framtida utbetalningar.",
    liveAsOf: "Senaste handelsdag",
    retrieved: "Hämtad",
    staleData: "Datakällan kunde inte nås. Senast lyckade hämtning visas.",
    saved: "Portföljen sparas i den valda datamiljön.",
    previewSaved: "Dina inmatningar sparas lokalt på den här enheten.",
    savePortfolio: "Spara ändringar",
    saving: "Sparar…",
    saveSuccess: "Portföljen är sparad.",
    unsaved: "Du har osparade ändringar.",
    retry: "Försök igen",
    marketLoading: "Hämtar slutkurser och utdelningshistorik…",
    marketNotConfigured: "Marknadsdata är inte konfigurerad",
    marketNotConfiguredLead: "Den valda marknadsdatakällan saknar nödvändig konfiguration. Kontrollera installationens .env och starta om API-tjänsterna.",
    marketUnavailable: "Marknadsdata kunde inte hämtas just nu.",
    limitedUniverse: "{count} Stockholm-handlade aktier hittades via Yahoo Finance.",
    historyHint: "1 mån, 6 mån och utdelningsmånader hämtas när du väljer en aktie.",
    showMore: "Visa 50 fler",
    selectedShares: "Aktier i innehav",
    portfolioValue: "Portföljvärde",
    expectedDividend: "Beräknad utdelning",
    nextPurchase: "Planerat köp",
    perYear: "/ år",
    addHoldings: "Fyll i dina innehav nedan",
    noPurchase: "Ange en köpbudget nedan",
    screener: "Aktiescreener",
    fundScreener: "Fondsök",
    fundMarket: "Fonder på svenska fondmarknaden",
    fundLead: "Sök på fondnamn eller ISIN. Träffarna hämtas från Avanzas publika fondinformation.",
    fundSearch: "Sök fond eller ISIN",
    fundSearchHint: "Skriv minst två tecken för att söka i fondutbudet.",
    fundSearching: "Söker fonder…",
    fundError: "Fonddata kunde inte hämtas just nu.",
    fundHoldingsUnavailable: "Några sparade fondinnehav kunde inte prisuppdateras just nu. De ligger kvar sparade och kan fortfarande tas bort här.",
    unavailableFund: "Fonddata saknas tillfälligt",
    fundSource: "Öppna Avanzas fondlista",
    noFundMatches: "Inga fonder matchar sökningen och filtren.",
    fundCategory: "Kategori",
    allCategories: "Alla kategorier",
    fundKind: "Fondtyp",
    fundCompany: "Fondbolag",
    nav: "NAV",
    fee: "Produktavgift",
    maxFee: "Högsta avgift",
    risk: "Risk",
    maxRisk: "Högsta risk",
    rating: "Betyg",
    indexOnly: "Endast indexfonder",
    unitsOwned: "Fondandelar",
    estimatedUnits: "Beräknade andelar",
    instrumentsInHoldings: "Instrument i innehav",
    fundSourceHint: "NAV och utveckling är fördröjda. Avgifter och riskklass kommer från fondinformationen.",
    swipeTable: "Svep i tabellen för att se fler kolumner.",
    exchange: "Stockholmsbörsen",
    exchangeLead: "Markera bolag och lägg till dem i din permanenta innehavslista.",
    screenerSelection: "markerade",
    addSelectedHoldings: "Lägg till innehav",
    addSelectedHoldingsCount: "Lägg till {count} innehav",
    removeFromHoldings: "Ta bort från innehav",
    removeHolding: "Ta bort",
    removeHoldingLabel: "Ta bort {name} från innehav",
    selectHolding: "Markera innehav",
    portfolioActionSuccess: "Innehavslistan är sparad.",
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
    oneYearColumn: "1 år",
    dividendYield: "Direktavk.",
    dividendShare: "Utd./aktie",
    payout: "Utdelningsmånader",
    noMatches: "Inga aktier matchar de valda filtren.",
    currentPortfolio: "Nuvarande portfölj",
    holdingsTitle: "Innehav & utdelningar",
    holdingsLead: "Ange antal aktier eller fondandelar. Utdelningsbeloppen nedan är en årsprognos före skatt.",
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
    purchaseLead: "Budgeten delas enligt dina procenttal. Aktier räknas i heltal och fondköp i beräknade decimalandelar.",
    budget: "Total köpbudget",
    allocation: "Fördelning",
    equal: "Fördela jämnt",
    reset: "Nollställ",
    percentage: "Andel",
    budgetShare: "Budgetandel",
    sharesToBuy: "Antal att köpa",
    quantityToBuy: "Antal / andelar",
    purchaseCost: "Kostnad",
    cashLeft: "Kvar i andel",
    allocationExact: "Hela budgeten är fördelad.",
    allocationLow: "av budgeten är ännu inte fördelad.",
    allocationHigh: "Fördelningen överskrider 100 %. Sänk någon av andelarna.",
    actualCost: "Total köpkostnad",
    remainingCash: "Kvar efter köp",
    allocatedBudget: "Fördelad budget",
    noSelected: "Markera aktier eller fonder i sökningen och välj Lägg till innehav.",
    optimizer: "Utdelningsoptimerare",
    optimizerTitle: "Mest historisk utdelning per investerad krona",
    optimizerLead:
      "Rangordningen jämför utdelning under de senaste 12 månaderna med den senaste slutkursen.",
    optimizerWarning:
      "Detta är ett mekaniskt jämförelseunderlag, inte en rekommendation. Det bedömer inte framtida utdelningsbeslut, extrautdelningar, bolagsrisk, kurstapp, skatt eller avgifter.",
    optimizerRank: "Plats",
    optimizerCapital: "Med köpbudgeten",
    optimizerShares: "Hela aktier",
    optimizerCost: "Investerat",
    optimizerDividend: "Historisk utdelning / år",
    optimizerEmpty: "Inga aktier med registrerad utdelning finns i den aktuella datan.",
    sectors: {
      basic_materials: "Råvaror",
      communication_services: "Kommunikation",
      consumer_cyclical: "Sällanköp",
      consumer_defensive: "Dagligvaror",
      energy: "Energi",
      financial_services: "Finans",
      healthcare: "Hälsovård",
      industrials: "Industri",
      real_estate: "Fastigheter",
      technology: "Teknik",
      utilities: "Samhällsnytta",
    },
  },
  en: {
    eyebrow: "Portfolio workspace",
    title: "Investments",
    lead: "Screen Swedish shares and funds, estimate annual dividends and allocate your next purchase — all on one page.",
    stocksTab: "Stocks",
    fundsTab: "Funds",
    sample: "Sample data · not live",
    sampleHint: "Prices and dividends are illustrative in the local preview.",
    delayedClosingPrices: "delayed closing prices",
    liveHint: "Prices are indicative and not trading data. Annual dividends use the trailing 12 months and calendar months show history, not confirmed future payments.",
    liveAsOf: "Latest trading day",
    retrieved: "Retrieved",
    staleData: "The data source could not be reached. Showing the latest successful retrieval.",
    saved: "The portfolio is stored in the selected data environment.",
    previewSaved: "Your entries are stored locally on this device.",
    savePortfolio: "Save changes",
    saving: "Saving…",
    saveSuccess: "Portfolio saved.",
    unsaved: "You have unsaved changes.",
    retry: "Try again",
    marketLoading: "Loading closing prices and dividend history…",
    marketNotConfigured: "Market data is not configured",
    marketNotConfiguredLead: "The selected market-data source is missing required configuration. Check the installation .env and restart the API services.",
    marketUnavailable: "Market data could not be loaded right now.",
    limitedUniverse: "Yahoo Finance found {count} Stockholm-traded shares.",
    historyHint: "1-month, 6-month and dividend-month history is loaded when you select a share.",
    showMore: "Show 50 more",
    selectedShares: "Shares in holdings",
    portfolioValue: "Portfolio value",
    expectedDividend: "Estimated dividend",
    nextPurchase: "Planned purchase",
    perYear: "/ year",
    addHoldings: "Add your holdings below",
    noPurchase: "Enter a purchase budget below",
    screener: "Stock screener",
    fundScreener: "Fund search",
    fundMarket: "Funds on the Swedish fund market",
    fundLead: "Search by fund name or ISIN. Results are loaded from Avanza's public fund information.",
    fundSearch: "Search fund or ISIN",
    fundSearchHint: "Enter at least two characters to search the fund range.",
    fundSearching: "Searching funds…",
    fundError: "Fund data could not be loaded right now.",
    fundHoldingsUnavailable: "Some saved fund holdings could not be repriced right now. They remain saved and can still be removed here.",
    unavailableFund: "Fund data is temporarily unavailable",
    fundSource: "Open Avanza's fund list",
    noFundMatches: "No funds match the search and filters.",
    fundCategory: "Category",
    allCategories: "All categories",
    fundKind: "Fund type",
    fundCompany: "Fund company",
    nav: "NAV",
    fee: "Product fee",
    maxFee: "Maximum fee",
    risk: "Risk",
    maxRisk: "Maximum risk",
    rating: "Rating",
    indexOnly: "Index funds only",
    unitsOwned: "Fund units",
    estimatedUnits: "Estimated units",
    instrumentsInHoldings: "Instruments held",
    fundSourceHint: "NAV and performance are delayed. Fees and risk class come from the fund information.",
    swipeTable: "Swipe the table to see more columns.",
    exchange: "Stockholm exchange",
    exchangeLead: "Select companies and add them to your permanent holdings list.",
    screenerSelection: "selected",
    addSelectedHoldings: "Add holdings",
    addSelectedHoldingsCount: "Add {count} holdings",
    removeFromHoldings: "Remove from holdings",
    removeHolding: "Remove",
    removeHoldingLabel: "Remove {name} from holdings",
    selectHolding: "Select holding",
    portfolioActionSuccess: "The holdings list has been saved.",
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
    oneYearColumn: "1 yr",
    dividendYield: "Yield",
    dividendShare: "Dividend/share",
    payout: "Dividend months",
    noMatches: "No shares match the selected filters.",
    currentPortfolio: "Current portfolio",
    holdingsTitle: "Holdings & dividends",
    holdingsLead: "Enter the number of shares or fund units held. Dividend amounts are annual estimates before tax.",
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
    purchaseLead: "The budget is divided by your percentages. Stocks use whole shares and fund purchases show estimated fractional units.",
    budget: "Total purchase budget",
    allocation: "Allocation",
    equal: "Split equally",
    reset: "Reset",
    percentage: "Share",
    budgetShare: "Budget allocation",
    sharesToBuy: "Shares to buy",
    quantityToBuy: "Shares / units",
    purchaseCost: "Cost",
    cashLeft: "Left in allocation",
    allocationExact: "The full budget is allocated.",
    allocationLow: "of the budget is not yet allocated.",
    allocationHigh: "The allocation exceeds 100%. Reduce one of the percentages.",
    actualCost: "Total purchase cost",
    remainingCash: "Cash remaining",
    allocatedBudget: "Allocated budget",
    noSelected: "Select shares or funds in search and choose Add holdings.",
    optimizer: "Dividend optimizer",
    optimizerTitle: "Highest historical dividend per invested krona",
    optimizerLead:
      "The ranking compares dividends during the trailing 12 months with the latest closing price.",
    optimizerWarning:
      "This is a mechanical comparison, not a recommendation. It does not assess future dividend decisions, special dividends, company risk, price losses, tax, or fees.",
    optimizerRank: "Rank",
    optimizerCapital: "Using the purchase budget",
    optimizerShares: "Whole shares",
    optimizerCost: "Invested",
    optimizerDividend: "Historical dividend / year",
    optimizerEmpty: "No stocks with a recorded dividend are available in the current data.",
    sectors: {
      basic_materials: "Basic materials",
      communication_services: "Communication services",
      consumer_cyclical: "Consumer cyclical",
      consumer_defensive: "Consumer defensive",
      energy: "Energy",
      financial_services: "Financial services",
      healthcare: "Healthcare",
      industrials: "Industrials",
      real_estate: "Real estate",
      technology: "Technology",
      utilities: "Utilities",
    },
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
    const valid = stored.filter((ticker): ticker is string => typeof ticker === "string" && (PREVIEW_STOCKS.some((stock) => stock.ticker === ticker) || PREVIEW_FUNDS.some((fund) => fund.isin === ticker)));
    return valid;
  } catch {
    return DEFAULT_SELECTED;
  }
}

function dividendPerShare(stock: Stock): number {
  return stock.annualDividendOre ?? stock.dividends.reduce((sum, payment) => sum + payment.amountOre, 0);
}

function parsePositiveInteger(value: string): number {
  if (!/^\d+$/.test(value.trim())) return 0;
  return Math.min(Number(value), 1_000_000_000);
}

function parsePositiveQuantity(value: string): number {
  const normalized = value.trim().replace(",", ".");
  if (!/^\d+(\.\d{0,8})?$/.test(normalized)) return 0;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? Math.min(parsed, 1_000_000_000) : 0;
}

function quantityForApi(value: string, instrumentType: "stock" | "fund"): string {
  const quantity = instrumentType === "stock" ? parsePositiveInteger(value) : parsePositiveQuantity(value);
  return instrumentType === "stock" ? String(quantity) : quantity.toFixed(8);
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

function quantityInputFromDecimal(value: string): string {
  const normalized = value.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
  return Number(normalized) === 0 ? "" : normalized;
}

function apiStockToStock(stock: InvestmentMarketStock): Stock {
  return {
    ticker: stock.ticker,
    name: stock.name,
    sector: stock.sector,
    priceOre: decimalStringToOre(stock.price),
    changeToday: Number(stock.changes.one_day),
    change1m: stock.changes.one_month === null ? null : Number(stock.changes.one_month),
    change6m: stock.changes.six_months === null ? null : Number(stock.changes.six_months),
    change1y: Number(stock.changes.one_year),
    annualDividendOre: decimalStringToOre(stock.annual_dividend_per_share),
    dividends: stock.dividend_pattern.map((payment) => ({
      month: payment.month,
      amountOre: decimalStringToOre(payment.amount),
      dateBasis: payment.date_basis,
    })),
    detailLevel: stock.detail_level ?? "history",
  };
}

function apiFundToFund(fund: InvestmentFund): Fund {
  return {
    isin: fund.isin,
    name: fund.name,
    category: fund.category,
    fundType: fund.fund_type,
    fundCompany: fund.fund_company,
    navOre: decimalStringToOre(fund.nav),
    changeToday: Number(fund.changes.one_day),
    change1m: fund.changes.one_month === null ? null : Number(fund.changes.one_month),
    change6m: fund.changes.six_months === null ? null : Number(fund.changes.six_months),
    change1y: Number(fund.changes.one_year),
    productFee: Number(fund.product_fee),
    managementFee: Number(fund.management_fee),
    risk: fund.risk,
    rating: fund.rating,
    indexFund: fund.index_fund,
    navDate: fund.nav_date,
  };
}

function mergeFunds(current: Fund[], incoming: Fund[]): Fund[] {
  return [...new Map([...current, ...incoming].map((fund) => [fund.isin, fund])).values()];
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

function TrendValue({ value, language }: { value: number | null; language: Language }) {
  if (value === null) return <span aria-label={language === "sv" ? "Hämtas när aktien väljs" : "Loaded when selected"}>—</span>;
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
  const [instrumentView, setInstrumentView] = useState<"stocks" | "funds">("stocks");
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("all");
  const [dividendFilter, setDividendFilter] = useState("all");
  const [performanceFilter, setPerformanceFilter] = useState("all");
  const [maxPrice, setMaxPrice] = useState("");
  const [visibleCount, setVisibleCount] = useState(STOCK_PAGE_SIZE);
  const [stocks, setStocks] = useState<Stock[]>(preview ? PREVIEW_STOCKS : []);
  const [funds, setFunds] = useState<Fund[]>(preview ? PREVIEW_FUNDS : []);
  const [fundQuery, setFundQuery] = useState("");
  const [fundSelection, setFundSelection] = useState<string[]>([]);
  const [fundCategory, setFundCategory] = useState("all");
  const [maxFundFee, setMaxFundFee] = useState("");
  const [maxFundRisk, setMaxFundRisk] = useState("all");
  const [indexFundsOnly, setIndexFundsOnly] = useState(false);
  const [fundSearchState, setFundSearchState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [fundHoldingState, setFundHoldingState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [marketSnapshot, setMarketSnapshot] = useState<InvestmentMarketData | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "not-configured" | "error">(
    preview ? "ready" : "loading",
  );
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [screenerSelection, setScreenerSelection] = useState<string[]>([]);
  const [portfolioTickers, setPortfolioTickers] = useState<string[]>(
    preview ? readStoredSelection() : [],
  );
  const [portfolioTypes, setPortfolioTypes] = useState<Record<string, "stock" | "fund">>(() =>
    Object.fromEntries((preview ? readStoredSelection() : []).map((ticker) => [ticker, PREVIEW_FUNDS.some((fund) => fund.isin === ticker) ? "fund" : "stock"])),
  );
  const [holdingSelection, setHoldingSelection] = useState<string[]>([]);
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
  const detailRequested = useRef(new Set<string>());

  useEffect(() => {
    if (preview) {
      localStorage.setItem("cost-review-selected-stocks", JSON.stringify(portfolioTickers));
    }
  }, [portfolioTickers, preview]);
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
        detailRequested.current.clear();
        setPortfolioTickers(portfolio.positions.map((position) => position.ticker));
        setPortfolioTypes(
          Object.fromEntries(
            portfolio.positions.map((position) => [position.ticker, position.instrument_type]),
          ),
        );
        setScreenerSelection([]);
        setHoldingSelection([]);
        setHoldings(
          Object.fromEntries(
            portfolio.positions.map((position) => [
              position.ticker,
              quantityInputFromDecimal(String(position.shares)),
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
        const fundIsins = portfolio.positions
          .filter((position) => position.instrument_type === "fund")
          .map((position) => position.ticker);
        if (fundIsins.length > 0) {
          setFundHoldingState("loading");
          void getInvestmentFundData(environment, { isins: fundIsins })
            .then((snapshot) => {
              if (active) {
                setFunds((current) => mergeFunds(current, snapshot.funds.map(apiFundToFund)));
                setFundHoldingState(snapshot.unavailable_isins.length > 0 ? "error" : "ready");
              }
            })
            .catch(() => {
              if (active) setFundHoldingState("error");
            });
        } else {
          setFundHoldingState("idle");
        }
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

  useEffect(() => {
    if (preview || fundQuery.trim().length < 2) return;
    const timeout = window.setTimeout(() => {
      setFundSearchState("loading");
      void getInvestmentFundData(environment, { query: fundQuery.trim() })
        .then((snapshot) => {
          setFunds((current) => mergeFunds(
            current.filter((fund) => portfolioTickers.includes(fund.isin)),
            snapshot.funds.map(apiFundToFund),
          ));
          setFundSearchState("ready");
        })
        .catch(() => setFundSearchState("error"));
    }, 350);
    return () => window.clearTimeout(timeout);
  }, [environment, fundQuery, portfolioTickers, preview]);

  useEffect(() => {
    if (preview || loadState !== "ready") return;
    const pending = [...new Set([...portfolioTickers, ...screenerSelection])].filter((ticker) => {
      const stock = stocks.find((item) => item.ticker === ticker);
      return stock?.detailLevel !== "history" && !detailRequested.current.has(ticker);
    });
    if (pending.length === 0) return;
    pending.forEach((ticker) => detailRequested.current.add(ticker));
    let active = true;
    void getInvestmentMarketData(environment, pending)
      .then((market) => {
        if (!active) return;
        const details = new Map(market.stocks.map((stock) => [stock.ticker, apiStockToStock(stock)]));
        setStocks((current) => current.map((stock) => details.get(stock.ticker) ?? stock));
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [environment, loadState, portfolioTickers, preview, screenerSelection, stocks]);

  const markDirty = () => {
    if (!preview) {
      setDirty(true);
      setSaveState("idle");
      setSaveError(null);
    }
  };

  const portfolioStocks = useMemo(
    () => stocks.filter((stock) => portfolioTickers.includes(stock.ticker) && portfolioTypes[stock.ticker] !== "fund"),
    [portfolioTickers, portfolioTypes, stocks],
  );
  const portfolioFunds = useMemo(
    () => funds.filter((fund) => portfolioTickers.includes(fund.isin) && portfolioTypes[fund.isin] === "fund"),
    [funds, portfolioTickers, portfolioTypes],
  );
  const unavailableFundIsins = useMemo(
    () => portfolioTickers.filter(
      (ticker) => portfolioTypes[ticker] === "fund" && !portfolioFunds.some((fund) => fund.isin === ticker),
    ),
    [portfolioFunds, portfolioTickers, portfolioTypes],
  );
  const filteredStocks = useMemo(() => {
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
  const visibleStocks = filteredStocks.slice(0, visibleCount);
  const fundCategories = [...new Set(funds.map((fund) => fund.category))].sort((a, b) => a.localeCompare(b));
  const filteredFunds = useMemo(() => {
    const maximumFee = maxFundFee.trim().replace(",", ".");
    const feeLimit = maximumFee && /^\d+(\.\d+)?$/.test(maximumFee) ? Number(maximumFee) : Number.POSITIVE_INFINITY;
    const riskLimit = maxFundRisk === "all" ? Number.POSITIVE_INFINITY : Number(maxFundRisk);
    const normalizedQuery = preview ? fundQuery.trim().toLocaleLowerCase() : "";
    return funds.filter((fund) =>
      (!normalizedQuery || `${fund.name} ${fund.isin} ${fund.fundCompany}`.toLocaleLowerCase().includes(normalizedQuery))
      && (fundCategory === "all" || fund.category === fundCategory)
      && fund.productFee <= feeLimit
      && (maxFundRisk === "all" || (fund.risk !== null && fund.risk <= riskLimit))
      && (!indexFundsOnly || fund.indexFund),
    );
  }, [fundCategory, fundQuery, funds, indexFundsOnly, maxFundFee, maxFundRisk, preview]);
  const newScreenerTickers = screenerSelection.filter(
    (ticker) => !portfolioTickers.includes(ticker),
  );
  const newFundIsins = fundSelection.filter((isin) => !portfolioTickers.includes(isin));

  const stockPortfolioValueOre = portfolioStocks.reduce((sum, stock) => sum + stock.priceOre * parsePositiveInteger(holdings[stock.ticker] ?? "0"), 0);
  const fundPortfolioValueOre = portfolioFunds.reduce((sum, fund) => sum + Math.round(fund.navOre * parsePositiveQuantity(holdings[fund.isin] ?? "0")), 0);
  const portfolioValueOre = stockPortfolioValueOre + fundPortfolioValueOre;
  const annualDividendOre = portfolioStocks.reduce((sum, stock) => sum + dividendPerShare(stock) * parsePositiveInteger(holdings[stock.ticker] ?? "0"), 0);
  const weightedYield = portfolioValueOre > 0 ? (annualDividendOre / portfolioValueOre) * 100 : 0;
  const monthlyDividends = Array.from({ length: 12 }, (_, index) => portfolioStocks.reduce((sum, stock) => {
    const paymentOre = stock.dividends
      .filter((item) => item.month === index + 1)
      .reduce((paymentSum, item) => paymentSum + item.amountOre, 0);
    return sum + paymentOre * parsePositiveInteger(holdings[stock.ticker] ?? "0");
  }, 0));
  const maxMonthlyDividend = Math.max(...monthlyDividends, 1);

  const budgetOre = parseMoneyToOre(budget);
  const optimizerRows = stocks
    .filter((stock) => stock.priceOre > 0 && dividendPerShare(stock) > 0)
    .map((stock) => {
      const annualPerShareOre = dividendPerShare(stock);
      const yieldPercent = (annualPerShareOre / stock.priceOre) * 100;
      const shares = Math.floor(budgetOre / stock.priceOre);
      return {
        stock,
        annualPerShareOre,
        yieldPercent,
        shares,
        costOre: shares * stock.priceOre,
        annualDividendOre: shares * annualPerShareOre,
      };
    })
    .sort((left, right) =>
      right.yieldPercent === left.yieldPercent
        ? left.stock.name.localeCompare(right.stock.name)
        : right.yieldPercent - left.yieldPercent,
    )
    .slice(0, 10);
  const purchaseRows = [
    ...portfolioStocks.map((stock) => {
      const basisPoints = percentageToBasisPoints(allocations[stock.ticker] ?? "0");
      const allocatedOre = Math.floor((budgetOre * basisPoints) / 10_000);
      const shareCount = Math.floor(allocatedOre / stock.priceOre);
      const costOre = shareCount * stock.priceOre;
      return { identifier: stock.ticker, name: stock.name, instrumentType: "stock" as const, basisPoints, allocatedOre, priceOre: stock.priceOre, quantity: String(shareCount), costOre, remainingOre: allocatedOre - costOre };
    }),
    ...portfolioFunds.map((fund) => {
      const basisPoints = percentageToBasisPoints(allocations[fund.isin] ?? "0");
      const allocatedOre = Math.floor((budgetOre * basisPoints) / 10_000);
      const units = fund.navOre > 0 ? allocatedOre / fund.navOre : 0;
      return { identifier: fund.isin, name: fund.name, instrumentType: "fund" as const, basisPoints, allocatedOre, priceOre: fund.navOre, quantity: units.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 0, maximumFractionDigits: 4 }), costOre: allocatedOre, remainingOre: 0 };
    }),
  ];
  const totalBasisPoints = purchaseRows.reduce((sum, row) => sum + row.basisPoints, 0);
  const totalPurchaseCostOre = purchaseRows.reduce((sum, row) => sum + row.costOre, 0);
  const totalAllocatedOre = purchaseRows.reduce((sum, row) => sum + row.allocatedOre, 0);
  const remainingBudgetOre = Math.max(0, budgetOre - totalPurchaseCostOre);

  const toggleScreenerSelection = (ticker: string) => {
    setScreenerSelection((current) =>
      current.includes(ticker)
        ? current.filter((item) => item !== ticker)
        : [...current, ticker],
    );
  };

  const toggleHoldingSelection = (ticker: string) => {
    setHoldingSelection((current) =>
      current.includes(ticker)
        ? current.filter((item) => item !== ticker)
        : [...current, ticker],
    );
  };

  const toggleFundSelection = (isin: string) => {
    setFundSelection((current) =>
      current.includes(isin) ? current.filter((item) => item !== isin) : [...current, isin],
    );
  };

  const distributeEqually = () => {
    if (portfolioTickers.length === 0) return;
    const base = Math.floor(10_000 / portfolioTickers.length);
    let remainder = 10_000 - base * portfolioTickers.length;
    setAllocations((current) => ({ ...current, ...Object.fromEntries(portfolioTickers.map((ticker) => {
      const value = base + (remainder-- > 0 ? 1 : 0);
      return [ticker, (value / 100).toFixed(2).replace(/\.00$/, "")];
    })) }));
    markDirty();
  };

  const resetFilters = () => {
    setQuery("");
    setSector("all");
    setDividendFilter("all");
    setPerformanceFilter("all");
    setMaxPrice("");
    setVisibleCount(STOCK_PAGE_SIZE);
  };

  const persistPortfolio = async (
    nextTickers: string[],
    nextHoldings = holdings,
    nextAllocations = allocations,
    nextBudget = budget,
    nextTypes = portfolioTypes,
  ): Promise<boolean> => {
    const nextTotalBasisPoints = nextTickers.reduce(
      (sum, ticker) => sum + percentageToBasisPoints(nextAllocations[ticker] ?? "0"),
      0,
    );
    if (nextTotalBasisPoints > 10_000) return false;
    setSaveState("saving");
    setSaveError(null);
    if (preview) {
      setPortfolioTickers(nextTickers);
      setPortfolioTypes(nextTypes);
      setHoldings(nextHoldings);
      setAllocations(nextAllocations);
      setBudget(nextBudget);
      setDirty(false);
      setSaveState("saved");
      return true;
    }
    try {
      const saved = await saveInvestmentPortfolio(environment, {
        purchase_budget: (parseMoneyToOre(nextBudget) / 100).toFixed(2),
        positions: nextTickers.map((ticker) => ({
          instrument_type: nextTypes[ticker] ?? "stock",
          ticker,
          shares: quantityForApi(nextHoldings[ticker] ?? "0", nextTypes[ticker] ?? "stock"),
          target_percentage: (
            percentageToBasisPoints(nextAllocations[ticker] ?? "0") / 100
          ).toFixed(2),
        })),
      });
      setPortfolioTickers(saved.positions.map((position) => position.ticker));
      setPortfolioTypes(
        Object.fromEntries(
          saved.positions.map((position) => [position.ticker, position.instrument_type]),
        ),
      );
      setHoldings(
        Object.fromEntries(
          saved.positions.map((position) => [
            position.ticker,
            quantityInputFromDecimal(String(position.shares)),
          ]),
        ),
      );
      setAllocations(
        Object.fromEntries(
          saved.positions.map((position) => [
            position.ticker,
            percentInputFromDecimal(position.target_percentage),
          ]),
        ),
      );
      setBudget(moneyInputFromDecimal(saved.purchase_budget));
      setDirty(false);
      setSaveState("saved");
      return true;
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : labels.marketUnavailable);
      setSaveState("error");
      return false;
    }
  };

  const savePortfolio = () => persistPortfolio(portfolioTickers);

  const addSelectedHoldings = async () => {
    const nextTickers = [
      ...portfolioTickers,
      ...screenerSelection.filter((ticker) => !portfolioTickers.includes(ticker)),
    ];
    if (nextTickers.length === portfolioTickers.length) return;
    const nextTypes = { ...portfolioTypes, ...Object.fromEntries(newScreenerTickers.map((ticker) => [ticker, "stock" as const])) };
    if (await persistPortfolio(nextTickers, holdings, allocations, budget, nextTypes)) {
      setScreenerSelection([]);
    }
  };

  const addSelectedFunds = async () => {
    const nextTickers = [...portfolioTickers, ...newFundIsins];
    if (nextTickers.length === portfolioTickers.length) return;
    const nextTypes = { ...portfolioTypes, ...Object.fromEntries(newFundIsins.map((isin) => [isin, "fund" as const])) };
    if (await persistPortfolio(nextTickers, holdings, allocations, budget, nextTypes)) {
      setFundSelection([]);
    }
  };

  const removeHoldings = async (identifiers: string[]) => {
    if (identifiers.length === 0) return;
    const identifiersToRemove = new Set(identifiers);
    const nextTickers = portfolioTickers.filter(
      (ticker) => !identifiersToRemove.has(ticker),
    );
    const nextHoldings = Object.fromEntries(
      Object.entries(holdings).filter(([ticker]) => nextTickers.includes(ticker)),
    );
    const nextAllocations = Object.fromEntries(
      Object.entries(allocations).filter(([ticker]) => nextTickers.includes(ticker)),
    );
    const nextTypes = Object.fromEntries(
      Object.entries(portfolioTypes).filter(([ticker]) => nextTickers.includes(ticker)),
    );
    if (await persistPortfolio(nextTickers, nextHoldings, nextAllocations, budget, nextTypes)) {
      setHoldingSelection((current) =>
        current.filter((ticker) => !identifiersToRemove.has(ticker)),
      );
    }
  };

  const removeSelectedHoldings = () => removeHoldings(holdingSelection);

  const removeHoldingLabel = (name: string) =>
    labels.removeHoldingLabel.replace("{name}", name);

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
              {labels.limitedUniverse.replace(
                "{count}",
                String(marketSnapshot.stock_count || marketSnapshot.stocks.length),
              )}
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

      <div className="instrument-tabs" role="tablist" aria-label={language === "sv" ? "Instrumenttyp" : "Instrument type"}>
        <button className={instrumentView === "stocks" ? "active" : undefined} role="tab" aria-selected={instrumentView === "stocks"} type="button" onClick={() => setInstrumentView("stocks")}>{labels.stocksTab}</button>
        <button className={instrumentView === "funds" ? "active" : undefined} role="tab" aria-selected={instrumentView === "funds"} type="button" onClick={() => setInstrumentView("funds")}>{labels.fundsTab}</button>
      </div>

      <div className="investment-summary" aria-label={labels.instrumentsInHoldings}>
        <div>
          <span>{labels.instrumentsInHoldings}</span>
          <strong>{portfolioTickers.length}</strong>
          <p>{preview ? labels.previewSaved : labels.saved}</p>
        </div>
        <div>
          <span>{labels.portfolioValue}</span>
          <strong>{formatMoney(portfolioValueOre, language)}</strong>
          <p>{portfolioValueOre > 0 ? `${portfolioStocks.filter((stock) => parsePositiveInteger(holdings[stock.ticker] ?? "0") > 0).length + portfolioFunds.filter((fund) => parsePositiveQuantity(holdings[fund.isin] ?? "0") > 0).length} ${language === "sv" ? "innehav" : "holdings"}` : labels.addHoldings}</p>
        </div>
        <div className="summary-feature">
          <span>{labels.expectedDividend}</span>
          <strong>{formatMoney(annualDividendOre, language)} <small>{labels.perYear}</small></strong>
          <p>{portfolioValueOre > 0 ? `${weightedYield.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} % ${language === "sv" ? "av portföljvärdet" : "of portfolio value"}` : labels.addHoldings}</p>
        </div>
        <div>
          <span>{labels.nextPurchase}</span>
          <strong>{formatMoney(totalPurchaseCostOre, language)}</strong>
          <p>{budgetOre > 0 ? `${purchaseRows.filter((row) => row.costOre > 0).length} ${language === "sv" ? "köpförslag" : "purchase suggestions"}` : labels.noPurchase}</p>
        </div>
      </div>

      {instrumentView === "stocks" ? (
      <section className="investment-panel screener-panel" aria-labelledby="stock-list-title">
        <div className="investment-panel-heading">
          <div>
            <p className="panel-label">{labels.screener}</p>
            <h2 id="stock-list-title">{labels.exchange}</h2>
            <p>{labels.exchangeLead}</p>
            {!preview ? <p className="investment-history-hint">{labels.historyHint}</p> : null}
          </div>
          <button className="quiet-button" type="button" onClick={resetFilters}>{labels.clear}</button>
        </div>

        <div className="investment-filter-grid">
          <label className="search-filter">
            <span>{labels.search}</span>
            <div className="input-with-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>
              <input value={query} onChange={(event) => { setQuery(event.target.value); setVisibleCount(STOCK_PAGE_SIZE); }} placeholder={language === "sv" ? "t.ex. Investor" : "e.g. Investor"} />
            </div>
          </label>
          <label>
            <span>{labels.sector}</span>
            <select value={sector} onChange={(event) => { setSector(event.target.value); setVisibleCount(STOCK_PAGE_SIZE); }}>
              <option value="all">{labels.allSectors}</option>
              {Object.entries(labels.sectors).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            <span>{labels.dividend}</span>
            <select value={dividendFilter} onChange={(event) => { setDividendFilter(event.target.value); setVisibleCount(STOCK_PAGE_SIZE); }}>
              <option value="all">{labels.all}</option>
              <option value="yes">{labels.paysDividend}</option>
              <option value="no">{labels.noDividend}</option>
            </select>
          </label>
          <label>
            <span>{labels.oneYear}</span>
            <select value={performanceFilter} onChange={(event) => { setPerformanceFilter(event.target.value); setVisibleCount(STOCK_PAGE_SIZE); }}>
              <option value="all">{labels.anyDevelopment}</option>
              <option value="positive">{labels.positive}</option>
              <option value="ten">{labels.overTen}</option>
            </select>
          </label>
          <label>
            <span>{labels.maxPrice}</span>
            <div className="money-input"><input inputMode="decimal" value={maxPrice} onChange={(event) => { setMaxPrice(event.target.value); setVisibleCount(STOCK_PAGE_SIZE); }} placeholder={labels.maxPricePlaceholder} /><span>kr</span></div>
          </label>
        </div>

        <div className="table-meta screener-table-meta">
          <span>{filteredStocks.length} {labels.matches}</span>
          <div>
            <span>{screenerSelection.length} {labels.screenerSelection}</span>
            <button
              className="primary-button"
              disabled={saveState === "saving" || newScreenerTickers.length === 0}
              onClick={() => void addSelectedHoldings()}
              type="button"
            >
              {newScreenerTickers.length > 0
                ? labels.addSelectedHoldingsCount.replace(
                    "{count}",
                    String(newScreenerTickers.length),
                  )
                : labels.addSelectedHoldings}
            </button>
          </div>
        </div>
        <p className="mobile-scroll-hint">{labels.swipeTable}</p>
        <div className="investment-table-scroll">
          <table className="investment-table" aria-label={labels.exchange}>
            <thead>
              <tr><th className="select-column"><span className="sr-only">{labels.select}</span></th><th>{labels.company}</th><th>{labels.price}</th><th>{labels.today}</th><th>{labels.oneMonth}</th><th>{labels.sixMonths}</th><th>{labels.oneYearColumn}</th><th>{labels.dividendYield}</th><th>{labels.dividendShare}</th><th>{labels.payout}</th></tr>
            </thead>
            <tbody>
              {visibleStocks.map((stock) => {
                const annualPerShare = dividendPerShare(stock);
                const isSelected = screenerSelection.includes(stock.ticker);
                return (
                  <tr key={stock.ticker} className={isSelected ? "selected-row" : undefined}>
                    <td className="select-column"><input type="checkbox" aria-label={`${labels.select} ${stock.name}`} checked={isSelected} onChange={() => toggleScreenerSelection(stock.ticker)} /></td>
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
        {visibleStocks.length < filteredStocks.length ? (
          <div className="investment-load-more">
            <button
              className="secondary-button"
              type="button"
              onClick={() => setVisibleCount((current) => current + STOCK_PAGE_SIZE)}
            >
              {labels.showMore}
            </button>
            <span>{visibleStocks.length} / {filteredStocks.length}</span>
          </div>
        ) : null}
      </section>
      ) : (
      <section className="investment-panel screener-panel fund-screener-panel" aria-labelledby="fund-list-title">
        <div className="investment-panel-heading">
          <div>
            <p className="panel-label">{labels.fundScreener}</p>
            <h2 id="fund-list-title">{labels.fundMarket}</h2>
            <p>{labels.fundLead}</p>
            <p className="investment-history-hint">
              {labels.fundSourceHint}{" "}
              <a href="https://www.avanza.se/fonder/lista.html" rel="noreferrer" target="_blank">
                {labels.fundSource}
              </a>
            </p>
          </div>
          <button className="quiet-button" type="button" onClick={() => { setFundQuery(""); setFundCategory("all"); setMaxFundFee(""); setMaxFundRisk("all"); setIndexFundsOnly(false); }}>{labels.clear}</button>
        </div>
        <div className="investment-filter-grid fund-filter-grid">
          <label className="search-filter">
            <span>{labels.fundSearch}</span>
            <div className="input-with-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>
              <input value={fundQuery} onChange={(event) => { const value = event.target.value; setFundQuery(value); if (!preview && value.trim().length < 2) { setFundSearchState("idle"); setFunds((current) => current.filter((fund) => portfolioTickers.includes(fund.isin))); } }} placeholder={language === "sv" ? "t.ex. Avanza Zero" : "e.g. Avanza Zero"} />
            </div>
          </label>
          <label><span>{labels.fundCategory}</span><select value={fundCategory} onChange={(event) => setFundCategory(event.target.value)}><option value="all">{labels.allCategories}</option>{fundCategories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
          <label><span>{labels.maxFee}</span><div className="percent-input"><input inputMode="decimal" value={maxFundFee} onChange={(event) => setMaxFundFee(event.target.value)} placeholder={labels.maxPricePlaceholder} /><span>%</span></div></label>
          <label><span>{labels.maxRisk}</span><select value={maxFundRisk} onChange={(event) => setMaxFundRisk(event.target.value)}><option value="all">{labels.all}</option>{[1,2,3,4,5,6,7].map((risk) => <option key={risk} value={risk}>{risk} / 7</option>)}</select></label>
          <label className="fund-index-filter"><span>{labels.fundKind}</span><span className="checkbox-line"><input type="checkbox" checked={indexFundsOnly} onChange={(event) => setIndexFundsOnly(event.target.checked)} />{labels.indexOnly}</span></label>
        </div>
        <div className="table-meta screener-table-meta">
          <span>{fundSearchState === "loading" ? labels.fundSearching : fundQuery.trim().length < 2 && !preview ? labels.fundSearchHint : `${filteredFunds.length} ${labels.matches}`}</span>
          <div><span>{fundSelection.length} {labels.screenerSelection}</span><button className="primary-button" disabled={saveState === "saving" || newFundIsins.length === 0} onClick={() => void addSelectedFunds()} type="button">{newFundIsins.length > 0 ? labels.addSelectedHoldingsCount.replace("{count}", String(newFundIsins.length)) : labels.addSelectedHoldings}</button></div>
        </div>
        <p className="mobile-scroll-hint">{labels.swipeTable}</p>
        <div className="investment-table-scroll">
          <table className="investment-table fund-table" aria-label={labels.fundMarket}>
            <thead><tr><th className="select-column"><span className="sr-only">{labels.select}</span></th><th>{labels.fundKind}</th><th>{labels.nav}</th><th>{labels.today}</th><th>{labels.oneMonth}</th><th>{labels.sixMonths}</th><th>{labels.oneYearColumn}</th><th>{labels.fee}</th><th>{labels.risk}</th><th>{labels.rating}</th></tr></thead>
            <tbody>{filteredFunds.map((fund) => { const isSelected = fundSelection.includes(fund.isin); return <tr key={fund.isin} className={isSelected ? "selected-row" : undefined}><td className="select-column"><input type="checkbox" aria-label={`${labels.select} ${fund.name}`} checked={isSelected} onChange={() => toggleFundSelection(fund.isin)} /></td><td><strong>{fund.name}</strong><span>{fund.isin} · {fund.fundCompany || fund.fundType} · {fund.category}</span></td><td>{formatMoney(fund.navOre, language)}<span>{fund.navDate}</span></td><td><TrendValue value={fund.changeToday} language={language} /></td><td><TrendValue value={fund.change1m} language={language} /></td><td><TrendValue value={fund.change6m} language={language} /></td><td><TrendValue value={fund.change1y} language={language} /></td><td>{fund.productFee.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %</td><td>{fund.risk === null ? "—" : `${fund.risk} / 7`}</td><td>{fund.rating === null ? "—" : `${fund.rating} / 5`}</td></tr>; })}</tbody>
          </table>
          {fundSearchState === "error" ? <p className="investment-empty">{labels.fundError}</p> : filteredFunds.length === 0 && (preview || fundQuery.trim().length >= 2) && fundSearchState !== "loading" ? <p className="investment-empty">{labels.noFundMatches}</p> : null}
        </div>
      </section>
      )}

      <section className="investment-panel optimizer-panel" aria-labelledby="optimizer-title">
        <div className="investment-panel-heading optimizer-heading">
          <div>
            <p className="panel-label">{labels.optimizer}</p>
            <h2 id="optimizer-title">{labels.optimizerTitle}</h2>
            <p>{labels.optimizerLead}</p>
          </div>
          <div className="optimizer-budget">
            <span>{labels.optimizerCapital}</span>
            <strong>{formatMoney(budgetOre, language)}</strong>
          </div>
        </div>
        <p className="optimizer-warning">{labels.optimizerWarning}</p>
        {optimizerRows.length > 0 ? (
          <div className="investment-table-scroll optimizer-table-scroll">
            <table className="investment-table optimizer-table" aria-label={labels.optimizerTitle}>
              <thead>
                <tr>
                  <th>{labels.optimizerRank}</th>
                  <th>{labels.company}</th>
                  <th>{labels.price}</th>
                  <th>{labels.dividendShare}</th>
                  <th>{labels.dividendYield}</th>
                  <th>{labels.optimizerShares}</th>
                  <th>{labels.optimizerCost}</th>
                  <th>{labels.optimizerDividend}</th>
                </tr>
              </thead>
              <tbody>
                {optimizerRows.map((row, index) => (
                  <tr key={row.stock.ticker}>
                    <td className="optimizer-rank">{index + 1}</td>
                    <td>
                      <strong>{row.stock.name}</strong>
                      <span>
                        {row.stock.ticker} · {(labels.sectors as Record<string, string>)[row.stock.sector] ?? row.stock.sector}
                      </span>
                    </td>
                    <td>{formatMoney(row.stock.priceOre, language)}</td>
                    <td>{formatMoney(row.annualPerShareOre, language)}</td>
                    <td className="strong-cell">
                      {row.yieldPercent.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })} %
                    </td>
                    <td>{row.shares}</td>
                    <td>{formatMoney(row.costOre, language)}</td>
                    <td>{formatMoney(row.annualDividendOre, language)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="investment-empty">{labels.optimizerEmpty}</p>
        )}
      </section>

      <section className="investment-panel holdings-panel" aria-labelledby="holdings-title">
        <div className="investment-panel-heading">
          <div>
            <p className="panel-label">{labels.currentPortfolio}</p>
            <h2 id="holdings-title">{labels.holdingsTitle}</h2>
            <p>{labels.holdingsLead}</p>
          </div>
          <div className="holdings-heading-actions">
            <div className="yield-callout">
              <span>{labels.expectedDividend}</span>
              <strong>{formatMoney(annualDividendOre, language, false)}</strong>
              <small>
                {weightedYield.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })} % · {labels.weightedYield}
              </small>
            </div>
            <button
              className="destructive-button holdings-remove-button"
              disabled={holdingSelection.length === 0 || saveState === "saving"}
              onClick={() => void removeSelectedHoldings()}
              type="button"
            >
              {labels.removeFromHoldings}
            </button>
          </div>
        </div>

        {portfolioTickers.length === 0 ? (
          <p className="investment-empty holdings-empty">{labels.noSelected}</p>
        ) : (
          <>
            {fundHoldingState === "error" && portfolioTickers.some((ticker) => portfolioTypes[ticker] === "fund") ? (
              <p className="optimizer-warning" role="status">{labels.fundHoldingsUnavailable}</p>
            ) : null}
            {portfolioStocks.length > 0 ? (
            <div className="investment-table-scroll holdings-table-scroll">
              <table className="investment-table holdings-table" aria-label={labels.holdingsTitle}>
                <thead>
                  <tr>
                    <th className="select-column"><span className="sr-only">{labels.selectHolding}</span></th>
                    <th>{labels.company}</th>
                    <th>{labels.owned}</th>
                    <th>{labels.price}</th>
                    <th>{labels.today}</th>
                    <th>{labels.oneMonth}</th>
                    <th>{labels.sixMonths}</th>
                    <th>{labels.oneYearColumn}</th>
                    <th>{labels.dividendYield}</th>
                    <th>{labels.dividendShare}</th>
                    <th>{labels.payout}</th>
                    <th>{labels.value}</th>
                    <th>{labels.annualDividend}</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioStocks.map((stock) => {
                    const shares = parsePositiveInteger(holdings[stock.ticker] ?? "0");
                    const annualPerShare = dividendPerShare(stock);
                    const isSelected = holdingSelection.includes(stock.ticker);
                    return (
                      <tr key={stock.ticker} className={isSelected ? "selected-row" : undefined}>
                        <td className="select-column">
                          <input
                            type="checkbox"
                            aria-label={`${labels.selectHolding} ${stock.name}`}
                            checked={isSelected}
                            onChange={() => toggleHoldingSelection(stock.ticker)}
                          />
                        </td>
                        <td className="holding-identity-cell">
                          <strong>{stock.name}</strong>
                          <span>
                            {stock.ticker} · {(labels.sectors as Record<string, string>)[stock.sector] ?? stock.sector}
                          </span>
                          <button
                            aria-label={removeHoldingLabel(stock.name)}
                            className="holding-row-remove"
                            disabled={saveState === "saving"}
                            onClick={() => void removeHoldings([stock.ticker])}
                            type="button"
                          >
                            <svg aria-hidden="true" viewBox="0 0 24 24">
                              <path d="M5 7h14M9 7V4h6v3M8 10v7M12 10v7M16 10v7M7 7l1 13h8l1-13" />
                            </svg>
                            {labels.removeHolding}
                          </button>
                        </td>
                        <td>
                          <input
                            className="table-number-input"
                            type="number"
                            min="0"
                            step="1"
                            inputMode="numeric"
                            aria-label={`${labels.owned} · ${stock.name}`}
                            value={holdings[stock.ticker] ?? ""}
                            placeholder="0"
                            onChange={(event) => {
                              setHoldings((current) => ({
                                ...current,
                                [stock.ticker]: event.target.value.replace(/[^\d]/g, ""),
                              }));
                              markDirty();
                            }}
                          />
                        </td>
                        <td>{formatMoney(stock.priceOre, language)}</td>
                        <td><TrendValue value={stock.changeToday} language={language} /></td>
                        <td><TrendValue value={stock.change1m} language={language} /></td>
                        <td><TrendValue value={stock.change6m} language={language} /></td>
                        <td><TrendValue value={stock.change1y} language={language} /></td>
                        <td>
                          {annualPerShare > 0
                            ? `${((annualPerShare / stock.priceOre) * 100).toLocaleString(
                                language === "sv" ? "sv-SE" : "en-GB",
                                { minimumFractionDigits: 2, maximumFractionDigits: 2 },
                              )} %`
                            : "—"}
                        </td>
                        <td>{annualPerShare > 0 ? formatMoney(annualPerShare, language) : "—"}</td>
                        <td>
                          {stock.dividends.length > 0
                            ? stock.dividends
                                .map((item) => monthName(item.month, language, true))
                                .join(" + ")
                            : "—"}
                        </td>
                        <td>{formatMoney(stock.priceOre * shares, language)}</td>
                        <td className="strong-cell">{formatMoney(annualPerShare * shares, language)}</td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr>
                    <th colSpan={11}>{labels.total}</th>
                    <td>{formatMoney(stockPortfolioValueOre, language)}</td>
                    <td>{formatMoney(annualDividendOre, language)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
            ) : null}

            {portfolioFunds.length > 0 || unavailableFundIsins.length > 0 ? (
              <div className="investment-table-scroll holdings-table-scroll fund-holdings-scroll">
                <table className="investment-table holdings-table fund-holdings-table" aria-label={language === "sv" ? "Fondinnehav" : "Fund holdings"}>
                  <thead><tr><th className="select-column"><span className="sr-only">{labels.selectHolding}</span></th><th>{labels.fundKind}</th><th>{labels.unitsOwned}</th><th>{labels.nav}</th><th>{labels.oneMonth}</th><th>{labels.sixMonths}</th><th>{labels.oneYearColumn}</th><th>{labels.fee}</th><th>{labels.risk}</th><th>{labels.value}</th></tr></thead>
                  <tbody>
                    {portfolioFunds.map((fund) => {
                      const units = parsePositiveQuantity(holdings[fund.isin] ?? "0");
                      const isSelected = holdingSelection.includes(fund.isin);
                      return (
                        <tr key={fund.isin} className={isSelected ? "selected-row" : undefined}>
                          <td className="select-column">
                            <input
                              type="checkbox"
                              aria-label={`${labels.selectHolding} ${fund.name}`}
                              checked={isSelected}
                              onChange={() => toggleHoldingSelection(fund.isin)}
                            />
                          </td>
                          <td className="holding-identity-cell">
                            <strong>{fund.name}</strong>
                            <span>{fund.isin} · {fund.fundCompany || fund.fundType} · {fund.category}</span>
                            <button
                              aria-label={removeHoldingLabel(fund.name)}
                              className="holding-row-remove"
                              disabled={saveState === "saving"}
                              onClick={() => void removeHoldings([fund.isin])}
                              type="button"
                            >
                              <svg aria-hidden="true" viewBox="0 0 24 24">
                                <path d="M5 7h14M9 7V4h6v3M8 10v7M12 10v7M16 10v7M7 7l1 13h8l1-13" />
                              </svg>
                              {labels.removeHolding}
                            </button>
                          </td>
                          <td>
                            <input className="table-number-input" type="text" inputMode="decimal" aria-label={`${labels.unitsOwned} · ${fund.name}`} value={holdings[fund.isin] ?? ""} placeholder="0" onChange={(event) => { setHoldings((current) => ({ ...current, [fund.isin]: event.target.value.replace(/[^\d.,]/g, "") })); markDirty(); }} />
                          </td>
                          <td>{formatMoney(fund.navOre, language)}<span>{fund.navDate}</span></td>
                          <td><TrendValue value={fund.change1m} language={language} /></td>
                          <td><TrendValue value={fund.change6m} language={language} /></td>
                          <td><TrendValue value={fund.change1y} language={language} /></td>
                          <td>{fund.productFee.toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %</td>
                          <td>{fund.risk === null ? "—" : `${fund.risk} / 7`}</td>
                          <td className="strong-cell">{formatMoney(Math.round(fund.navOre * units), language)}</td>
                        </tr>
                      );
                    })}
                    {unavailableFundIsins.map((isin) => {
                      const isSelected = holdingSelection.includes(isin);
                      return (
                        <tr key={isin} className={isSelected ? "selected-row" : undefined}>
                          <td className="select-column">
                            <input type="checkbox" aria-label={`${labels.selectHolding} ${isin}`} checked={isSelected} onChange={() => toggleHoldingSelection(isin)} />
                          </td>
                          <td className="holding-identity-cell">
                            <strong>{isin}</strong>
                            <span>{labels.unavailableFund}</span>
                            <button
                              aria-label={removeHoldingLabel(isin)}
                              className="holding-row-remove"
                              disabled={saveState === "saving"}
                              onClick={() => void removeHoldings([isin])}
                              type="button"
                            >
                              <svg aria-hidden="true" viewBox="0 0 24 24">
                                <path d="M5 7h14M9 7V4h6v3M8 10v7M12 10v7M16 10v7M7 7l1 13h8l1-13" />
                              </svg>
                              {labels.removeHolding}
                            </button>
                          </td>
                          <td>
                            <input className="table-number-input" type="text" inputMode="decimal" aria-label={`${labels.unitsOwned} · ${isin}`} value={holdings[isin] ?? ""} placeholder="0" onChange={(event) => { setHoldings((current) => ({ ...current, [isin]: event.target.value.replace(/[^\d.,]/g, "") })); markDirty(); }} />
                          </td>
                          <td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot><tr><th colSpan={9}>{labels.total}</th><td>{formatMoney(fundPortfolioValueOre, language)}</td></tr></tfoot>
                </table>
              </div>
            ) : null}

            {portfolioStocks.length > 0 ? (
            <div className="dividend-calendar">
              <div className="calendar-heading">
                <div>
                  <h3>{labels.dividendCalendar}</h3>
                  <p>{labels.dividendCalendarLead}</p>
                </div>
                <strong>{formatMoney(annualDividendOre, language, false)} <small>{labels.perYear}</small></strong>
              </div>
              <div className="calendar-chart" aria-label={labels.dividendCalendar}>
                {monthlyDividends.map((amountOre, index) => (
                  <div className="calendar-month" key={index}>
                    <div className="calendar-value">{amountOre > 0 ? formatMoney(amountOre, language, false) : "—"}</div>
                    <div className="calendar-bar-track">
                      <span style={{ height: `${Math.max(amountOre > 0 ? 8 : 0, (amountOre / maxMonthlyDividend) * 100)}%` }} />
                    </div>
                    <span>{monthName(index + 1, language, true)}</span>
                  </div>
                ))}
              </div>
              {annualDividendOre === 0 ? <p className="calendar-empty">{labels.noHoldings}</p> : null}
            </div>
            ) : null}
          </>
        )}
      </section>

      {portfolioTickers.length > 0 ? (
          <section className="investment-panel purchase-panel" aria-labelledby="purchase-title">
            <div className="investment-panel-heading purchase-heading">
              <div><p className="panel-label">{labels.planning}</p><h2 id="purchase-title">{labels.purchaseTitle}</h2><p>{labels.purchaseLead}</p></div>
              <label className="budget-field"><span>{labels.budget}</span><div className="money-input large"><input aria-label={labels.budget} inputMode="decimal" value={budget} onChange={(event) => { setBudget(event.target.value); markDirty(); }} /><span>kr</span></div></label>
            </div>

            <div className="allocation-status">
              <div className="allocation-copy"><span>{labels.allocation}</span><strong className={totalBasisPoints > 10_000 ? "over" : undefined}>{(totalBasisPoints / 100).toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { maximumFractionDigits: 2 })} %</strong><span>{totalBasisPoints === 10_000 ? labels.allocationExact : totalBasisPoints > 10_000 ? labels.allocationHigh : `${((10_000 - totalBasisPoints) / 100).toLocaleString(language === "sv" ? "sv-SE" : "en-GB", { maximumFractionDigits: 2 })} % ${labels.allocationLow}`}</span></div>
              <div className="allocation-actions"><button className="quiet-button" type="button" onClick={distributeEqually}>{labels.equal}</button><button className="ghost-button" type="button" onClick={() => { setAllocations((current) => ({ ...current, ...Object.fromEntries(portfolioTickers.map((ticker) => [ticker, "0"])) })); markDirty(); }}>{labels.reset}</button></div>
              <div className="allocation-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, totalBasisPoints / 100)}><span className={totalBasisPoints > 10_000 ? "over" : undefined} style={{ width: `${Math.min(100, totalBasisPoints / 100)}%` }} /></div>
            </div>

            <div className="investment-table-scroll purchase-table-scroll">
              <table className="investment-table purchase-table" aria-label={labels.purchaseTitle}>
                <thead><tr><th>{labels.company}</th><th>{labels.percentage}</th><th>{labels.budgetShare}</th><th>{labels.price}</th><th>{labels.quantityToBuy}</th><th>{labels.purchaseCost}</th><th>{labels.cashLeft}</th></tr></thead>
                <tbody>{purchaseRows.map((row) => <tr key={`${row.instrumentType}-${row.identifier}`}><td><strong>{row.name}</strong><span>{row.identifier} · {row.instrumentType === "fund" ? labels.fundsTab : labels.stocksTab}</span></td><td><div className="percent-input"><input type="number" min="0" max="100" step="0.1" inputMode="decimal" aria-label={`${labels.percentage} · ${row.name}`} value={allocations[row.identifier] ?? ""} onChange={(event) => { setAllocations((current) => ({ ...current, [row.identifier]: event.target.value })); markDirty(); }} /><span>%</span></div></td><td>{formatMoney(row.allocatedOre, language)}</td><td>{formatMoney(row.priceOre, language)}</td><td className="share-count"><strong>{row.quantity}</strong></td><td className="strong-cell">{formatMoney(row.costOre, language)}</td><td>{formatMoney(row.remainingOre, language)}</td></tr>)}</tbody>
              </table>
            </div>
            <div className="purchase-totals">
              <div><span>{labels.allocatedBudget}</span><strong>{formatMoney(totalAllocatedOre, language)}</strong></div>
              <div className="featured"><span>{labels.actualCost}</span><strong>{formatMoney(totalPurchaseCostOre, language)}</strong></div>
              <div><span>{labels.remainingCash}</span><strong>{formatMoney(remainingBudgetOre, language)}</strong></div>
            </div>
          </section>
      ) : null}
    </section>
  );
}
