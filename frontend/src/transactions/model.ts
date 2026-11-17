import {
  type Language,
  type ManualTransactionKind,
  type RecoveryKind,
  type TransferPurpose,
  type TransactionKind,
} from "../api";
import { type Labels } from "../i18n/transactions";

export type Draft = {
  accountId: string;
  providerId: string;
  kind: ManualTransactionKind;
  transactionDate: string;
  postingDate: string;
  description: string;
  amount: string;
  currency: string;
  convertedAmount: string;
  categoryId: string;
  tagIds: number[];
  isBaseCost: boolean;
  sourceReference: string;
  notes: string;
  splitMode: boolean;
  splits: SplitDraft[];
  sharingAllocations: ShareDraft[];
};

export type ShareDraft = { partyId: string; percentage: string };

export type SplitDraft = {
  key: string;
  amount: string;
  categoryId: string;
  tagIds: number[];
  isBaseCost: boolean;
  memo: string;
  sharingAllocations: ShareDraft[];
};

export type TransferDraft = {
  sourceAccountId: string;
  destinationAccountId: string;
  purpose: TransferPurpose;
  transactionDate: string;
  sourcePostingDate: string;
  destinationPostingDate: string;
  description: string;
  sourceAmount: string;
  destinationAmount: string;
  sourceConvertedAmount: string;
  destinationConvertedAmount: string;
  sourceReference: string;
  notes: string;
};

export type EntryKind = TransactionKind | "transfer";

export type RecoveryDraft = {
  kind: RecoveryKind;
  expenseId: number;
  accountId: string;
  providerId: string;
  transactionDate: string;
  postingDate: string;
  description: string;
  amount: string;
  currency: string;
  convertedAmount: string;
  sourceReference: string;
  notes: string;
};

export type Filters = {
  dateFrom: string;
  dateTo: string;
  kind: EntryKind | "";
  accountId: string;
  providerId: string;
  categoryId: string;
  tagId: string;
  baseCostOnly: boolean;
  search: string;
  showArchived: boolean;
};

export function allocationTotal(allocations: ShareDraft[]): number {
  return allocations.reduce(
    (total, allocation) =>
      total + Number(normalizeDecimalInput(allocation.percentage) || 0),
    0,
  );
}

export function shareAllocationPayload(allocations: ShareDraft[]) {
  return allocations
    .filter(
      (allocation) =>
        Number(normalizeDecimalInput(allocation.percentage) || 0) > 0,
    )
    .map((allocation) => ({
      sharing_party_id: Number(allocation.partyId),
      percentage: normalizeDecimalInput(allocation.percentage),
    }));
}

export function allocationsBalanced(allocations: ShareDraft[]): boolean {
  return allocations.length === 0 || Math.abs(allocationTotal(allocations) - 100) < 0.00005;
}

export function emptyDraft(baseCurrency: string): Draft {
  const today = localDate(new Date());
  return { accountId: "", providerId: "", kind: "expense", transactionDate: today, postingDate: today, description: "", amount: "", currency: baseCurrency, convertedAmount: "", categoryId: "", tagIds: [], isBaseCost: false, sourceReference: "", notes: "", splitMode: false, splits: initialSplits(), sharingAllocations: [] };
}

export function initialSplits(): SplitDraft[] {
  return [newSplitDraft(), newSplitDraft()];
}

export function newSplitDraft(): SplitDraft {
  return {
    key: crypto.randomUUID(),
    amount: "",
    categoryId: "",
    tagIds: [],
    isBaseCost: false,
    memo: "",
    sharingAllocations: [],
  };
}

export function emptyTransferDraft(): TransferDraft {
  const today = localDate(new Date());
  return {
    sourceAccountId: "",
    destinationAccountId: "",
    purpose: "internal",
    transactionDate: today,
    sourcePostingDate: today,
    destinationPostingDate: today,
    description: "",
    sourceAmount: "",
    destinationAmount: "",
    sourceConvertedAmount: "",
    destinationConvertedAmount: "",
    sourceReference: "",
    notes: "",
  };
}

export function purposeLabel(purpose: TransferPurpose, labels: Labels): string {
  return {
    internal: labels.purposeInternal,
    savings: labels.purposeSavings,
    investment: labels.purposeInvestment,
    credit_card_payment: labels.purposeCard,
    debt_repayment: labels.purposeDebt,
  }[purpose];
}

export function currentMonth(): { from: string; to: string } {
  const today = new Date();
  return { from: localDate(new Date(today.getFullYear(), today.getMonth(), 1)), to: localDate(new Date(today.getFullYear(), today.getMonth() + 1, 0)) };
}

export function localDate(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

export function numberOrNull(value: string): number | null { return value ? Number(value) : null; }

export function normalizeDecimalInput(value: string): string { return value.replace(",", "."); }

export function formatMoney(value: string, currency: string, language: Language): string { return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", { style: "currency", currency }).format(Number(value)); }

export function formatDate(value: string, language: Language): string { return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-SE", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`)); }
