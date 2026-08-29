import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  createAnalysisGroup,
  createBudget,
  getAnalysisGroups,
  getBudgetOutcome,
  getBudgets,
  getBudgetTransactions,
  getCategories,
  getTags,
  setBudgetArchived,
  updateBudget,
  type AnalysisGroup,
  type Budget,
  type BudgetInput,
  type BudgetOutcome,
  type BudgetPeriodType,
  type BudgetRolloverMode,
  type BudgetTransaction,
  type Category,
  type Environment,
  type Language,
  type SelectionMode,
  type Tag,
} from "./api";

const text = {
  sv: {
    eyebrow: "Planering och analys",
    title: "Budget",
    lead: "Koppla budgetar till samma kategorier och taggar som används i Ledger-analysen.",
    newBudget: "+ Ny budget",
    month: "Analysmånad",
    empty: "Inga budgetar ännu. Skapa en budget för att börja jämföra utfall.",
    name: "Budgetnamn",
    amount: "Belopp per period",
    period: "Period",
    calendarMonth: "Kalendermånad",
    salaryCycle: "Lön till lön",
    calendarYear: "Kalenderår",
    custom: "Eget intervall",
    starts: "Gäller från",
    ends: "Gäller till",
    anchor: "Startdag i månaden",
    reset: "Återställ varje period",
    rollover: "Rulla över kvarvarande belopp",
    group: "Analysis Group",
    noGroup: "Ingen sparad grupp",
    categories: "Kategorier",
    tags: "Taggar",
    ignore: "Ignorera",
    include: "Inkludera",
    exclude: "Exkludera",
    descendants: "inklusive underkategorier",
    save: "Skapa budget",
    update: "Spara ändringar",
    edit: "Redigera",
    cancel: "Avbryt",
    selectionHelp: "Utan urval räknas alla utgifter. Val inom samma typ matchar valfri post; kategori och tagg måste matcha samma delpost. Exkludering vinner alltid.",
    groupName: "Namn på sparat urval",
    saveGroup: "Spara som Analysis Group",
    target: "Budget",
    actual: "Utfall",
    remaining: "Kvar",
    matched: "matchande poster",
    overlap: "Överlappar en annan budget – summorna är inte additiva.",
    missingFx: "Poster med saknad valutakurs är inte medräknade i utfallet.",
    showRows: "Visa underlag",
    hideRows: "Dölj underlag",
    noRows: "Inga matchande transaktioner i perioden.",
    archive: "Arkivera",
    error: "Budgetdata kunde inte läsas.",
  },
  en: {
    eyebrow: "Planning and analysis",
    title: "Budget",
    lead: "Connect budgets to the same categories and tags used by Ledger analysis.",
    newBudget: "+ New budget",
    month: "Analysis month",
    empty: "No budgets yet. Create one to start comparing actuals.",
    name: "Budget name",
    amount: "Amount per period",
    period: "Period",
    calendarMonth: "Calendar month",
    salaryCycle: "Salary to salary",
    calendarYear: "Calendar year",
    custom: "Custom interval",
    starts: "Effective from",
    ends: "Effective to",
    anchor: "Monthly start day",
    reset: "Reset each period",
    rollover: "Roll remaining amount forward",
    group: "Analysis Group",
    noGroup: "No saved group",
    categories: "Categories",
    tags: "Tags",
    ignore: "Ignore",
    include: "Include",
    exclude: "Exclude",
    descendants: "including descendants",
    save: "Create budget",
    update: "Save changes",
    edit: "Edit",
    cancel: "Cancel",
    selectionHelp: "With no selection, all expenses count. Choices within one type match any item; category and tag must match the same split. Exclusions always win.",
    groupName: "Saved selection name",
    saveGroup: "Save as Analysis Group",
    target: "Budget",
    actual: "Actual",
    remaining: "Remaining",
    matched: "matching entries",
    overlap: "Overlaps another budget – totals are not additive.",
    missingFx: "Entries with a missing exchange rate are excluded from actuals.",
    showRows: "Show underlying entries",
    hideRows: "Hide underlying entries",
    noRows: "No matching transactions in this period.",
    archive: "Archive",
    error: "Budget data could not be loaded.",
  },
} as const;

type Draft = {
  name: string;
  amount: string;
  periodType: BudgetPeriodType;
  rolloverMode: BudgetRolloverMode;
  startsOn: string;
  endsOn: string;
  anchorDay: number;
  analysisGroupId: string;
  categoryModes: Record<number, SelectionMode | "">;
  tagModes: Record<number, SelectionMode | "">;
};

export function BudgetWorkspace({
  baseCurrency,
  environment,
  language,
}: {
  baseCurrency: string;
  environment: Environment;
  language: Language;
}) {
  const labels = text[language];
  const [month, setMonth] = useState(currentMonth());
  const [categories, setCategories] = useState<Category[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [groups, setGroups] = useState<AnalysisGroup[]>([]);
  const [outcomes, setOutcomes] = useState<BudgetOutcome[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingBudgetId, setEditingBudgetId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Draft>(() => emptyDraft());
  const [groupName, setGroupName] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [rows, setRows] = useState<Record<number, BudgetTransaction[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const period = useMemo(() => monthPeriod(month), [month]);

  const load = async () => {
    try {
      const [budgetItems, categoryPage, tagPage, groupItems] = await Promise.all([
        getBudgets(environment),
        getCategories(environment),
        getTags(environment),
        getAnalysisGroups(environment),
      ]);
      const activeCategories = categoryPage.items.filter((item) => item.category_kind === "expense");
      setCategories(activeCategories);
      setTags(tagPage.items);
      setGroups(groupItems);
      setOutcomes(
        await Promise.all(
          budgetItems.map((budget) =>
            getBudgetOutcome(environment, budget.budget_id, period.from, period.to),
          ),
        ),
      );
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : labels.error);
    }
  };

  useEffect(() => {
    // Loading is triggered by the selected data plane and analysis period.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [environment, period.from, period.to]);

  const selections = () => ({
    categories: Object.entries(draft.categoryModes)
      .filter(([, mode]) => mode)
      .map(([categoryId, mode]) => ({
        category_id: Number(categoryId),
        mode: mode as SelectionMode,
        include_descendants: true,
      })),
    tags: Object.entries(draft.tagModes)
      .filter(([, mode]) => mode)
      .map(([tagId, mode]) => ({ tag_id: Number(tagId), mode: mode as SelectionMode })),
  });

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setWorking(true);
    try {
      const payload: BudgetInput = {
        name: draft.name,
        amount: draft.amount.replace(",", "."),
        currency: baseCurrency,
        period_type: draft.periodType,
        rollover_mode: draft.rolloverMode,
        starts_on: draft.startsOn,
        ends_on: draft.periodType === "custom" ? draft.endsOn : null,
        anchor_day: draft.anchorDay,
        analysis_group_id: draft.analysisGroupId ? Number(draft.analysisGroupId) : null,
        notes: null,
        ...selections(),
      };
      if (editingBudgetId === null) {
        await createBudget(environment, payload);
      } else {
        await updateBudget(environment, editingBudgetId, payload);
      }
      setDraft(emptyDraft());
      setEditingBudgetId(null);
      setShowForm(false);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : labels.error);
    } finally {
      setWorking(false);
    }
  };

  const saveGroup = async () => {
    if (!groupName.trim()) return;
    setWorking(true);
    try {
      const group = await createAnalysisGroup(environment, {
        name: groupName.trim(),
        notes: null,
        ...selections(),
      });
      setGroups((current) => [...current, group]);
      setDraft((current) => ({ ...current, analysisGroupId: String(group.analysis_group_id) }));
      setGroupName("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : labels.error);
    } finally {
      setWorking(false);
    }
  };

  const toggleRows = async (budgetId: number) => {
    if (expanded === budgetId) {
      setExpanded(null);
      return;
    }
    setExpanded(budgetId);
    if (!rows[budgetId]) {
      try {
        const items = await getBudgetTransactions(environment, budgetId, period.from, period.to);
        setRows((current) => ({ ...current, [budgetId]: items }));
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : labels.error);
      }
    }
  };

  const beginCreate = () => {
    setEditingBudgetId(null);
    setDraft(emptyDraft());
    setShowForm(true);
  };

  const beginEdit = (budget: Budget) => {
    setEditingBudgetId(budget.budget_id);
    setDraft(draftFromBudget(budget));
    setShowForm(true);
  };

  const closeEditor = () => {
    setEditingBudgetId(null);
    setDraft(emptyDraft());
    setShowForm(false);
  };

  return (
    <section className="budget-workspace" aria-labelledby="budget-title">
      <div className="workspace-heading">
        <div><p className="eyebrow">{labels.eyebrow}</p><h1 id="budget-title">{labels.title}</h1><p>{labels.lead}</p></div>
        <div className="budget-heading-actions"><label>{labels.month}<input aria-label={labels.month} onChange={(event) => setMonth(event.target.value)} type="month" value={month} /></label><button className="primary-button" onClick={beginCreate} type="button">{labels.newBudget}</button></div>
      </div>
      {error ? <div className="error-banner" role="alert">{error}</div> : null}
      {showForm ? (
        <form className="budget-editor" onSubmit={submit}>
          <div className="editor-title"><h2>{editingBudgetId === null ? labels.newBudget.slice(2) : labels.edit}</h2><button className="ghost-button" onClick={closeEditor} type="button">{labels.cancel}</button></div>
          <div className="budget-form-grid">
            <label>{labels.name}<input autoFocus onChange={(event) => setDraft({ ...draft, name: event.target.value })} required value={draft.name} /></label>
            <label>{labels.amount}<input inputMode="decimal" onChange={(event) => setDraft({ ...draft, amount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" required value={draft.amount} /></label>
            <label>{labels.period}<select onChange={(event) => { const periodType = event.target.value as BudgetPeriodType; setDraft({ ...draft, periodType, rolloverMode: periodType === "custom" ? "reset" : draft.rolloverMode }); }} value={draft.periodType}><option value="calendar_month">{labels.calendarMonth}</option><option value="salary_cycle">{labels.salaryCycle}</option><option value="calendar_year">{labels.calendarYear}</option><option value="custom">{labels.custom}</option></select></label>
            <label>{labels.starts}<input onChange={(event) => setDraft({ ...draft, startsOn: event.target.value })} required type="date" value={draft.startsOn} /></label>
            {draft.periodType === "custom" ? <label>{labels.ends}<input onChange={(event) => setDraft({ ...draft, endsOn: event.target.value })} required type="date" value={draft.endsOn} /></label> : null}
            {draft.periodType === "salary_cycle" ? <label>{labels.anchor}<input max="28" min="1" onChange={(event) => setDraft({ ...draft, anchorDay: Number(event.target.value) })} type="number" value={draft.anchorDay} /></label> : null}
            <label>{labels.rollover}<select onChange={(event) => setDraft({ ...draft, rolloverMode: event.target.value as BudgetRolloverMode })} value={draft.rolloverMode}><option value="reset">{labels.reset}</option><option disabled={draft.periodType === "custom"} value="rollover">{labels.rollover}</option></select></label>
            <label>{labels.group}<select onChange={(event) => setDraft({ ...draft, analysisGroupId: event.target.value })} value={draft.analysisGroupId}><option value="">{labels.noGroup}</option>{groups.map((group) => <option key={group.analysis_group_id} value={group.analysis_group_id}>{group.name}</option>)}</select></label>
          </div>
          <p className="quiet-copy">{labels.selectionHelp}</p>
          <div className="budget-selection-grid">
            <SelectionList items={categories} labels={labels} modes={draft.categoryModes} name={(item) => item.name} onMode={(id, mode) => setDraft({ ...draft, categoryModes: { ...draft.categoryModes, [id]: mode } })} title={labels.categories} />
            <SelectionList items={tags} labels={labels} modes={draft.tagModes} name={(item) => item.name} onMode={(id, mode) => setDraft({ ...draft, tagModes: { ...draft.tagModes, [id]: mode } })} title={labels.tags} />
          </div>
          <div className="analysis-group-save"><label>{labels.groupName}<input onChange={(event) => setGroupName(event.target.value)} value={groupName} /></label><button className="secondary-button" disabled={working || !groupName.trim()} onClick={() => void saveGroup()} type="button">{labels.saveGroup}</button></div>
          <div className="editor-actions"><button className="secondary-button" onClick={closeEditor} type="button">{labels.cancel}</button><button className="primary-button" disabled={working} type="submit">{editingBudgetId === null ? labels.save : labels.update}</button></div>
        </form>
      ) : null}
      {outcomes.length === 0 ? <div className="honest-empty"><p>{labels.empty}</p></div> : <div className="budget-cards">{outcomes.map((outcome) => <BudgetCard key={outcome.budget.budget_id} labels={labels} language={language} outcome={outcome} rows={rows[outcome.budget.budget_id] ?? []} expanded={expanded === outcome.budget.budget_id} onArchive={() => void setBudgetArchived(environment, outcome.budget.budget_id, true).then(load)} onEdit={() => beginEdit(outcome.budget)} onToggle={() => void toggleRows(outcome.budget.budget_id)} />)}</div>}
    </section>
  );
}

function SelectionList<T extends { category_id?: number; tag_id?: number }>({ items, labels, modes, name, onMode, title }: { items: T[]; labels: typeof text.sv | typeof text.en; modes: Record<number, SelectionMode | "">; name: (item: T) => string; onMode: (id: number, mode: SelectionMode | "") => void; title: string }) {
  return <fieldset className="budget-selection"><legend>{title}</legend>{items.length === 0 ? <p>—</p> : items.map((item) => { const id = item.category_id ?? item.tag_id ?? 0; return <label key={id}><span>{name(item)}</span><select aria-label={`${title}: ${name(item)}`} onChange={(event) => onMode(id, event.target.value as SelectionMode | "")} value={modes[id] ?? ""}><option value="">{labels.ignore}</option><option value="include">{labels.include}</option><option value="exclude">{labels.exclude}</option></select></label>; })}</fieldset>;
}

function BudgetCard({ outcome, labels, language, expanded, rows, onToggle, onArchive, onEdit }: { outcome: BudgetOutcome; labels: typeof text.sv | typeof text.en; language: Language; expanded: boolean; rows: BudgetTransaction[]; onToggle: () => void; onArchive: () => void; onEdit: () => void }) {
  const consumed = Number(outcome.consumed_percent);
  const progress = Math.max(0, consumed);
  const currency = outcome.base_currency;
  return <article className="budget-card"><div className="budget-card-heading"><div><h2>{outcome.budget.name}</h2><p>{periodLabel(outcome.budget.period_type, labels)} · {outcome.matched_transaction_count} {labels.matched}</p></div><div><button className="ghost-button" onClick={onEdit} type="button">{labels.edit}</button><button className="ghost-button" onClick={onArchive} type="button">{labels.archive}</button></div></div>{outcome.overlapping_budget_ids.length ? <p className="attention-note">{labels.overlap}</p> : null}{outcome.missing_fx_count ? <p className="attention-note">{outcome.missing_fx_count} {labels.missingFx}</p> : null}<div className="budget-metrics"><div><span>{labels.target}</span><strong>{money(outcome.target_amount, currency, language)}</strong></div><div><span>{labels.actual}</span><strong>{money(outcome.actual_amount, currency, language)}</strong></div><div><span>{labels.remaining}</span><strong>{money(outcome.remaining_amount, currency, language)}</strong></div></div><div className="budget-progress" aria-label={`${outcome.consumed_percent}%`}><span style={{ width: `${Math.min(100, progress)}%` }} /></div><p className="budget-progress-label">{new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", { maximumFractionDigits: 1 }).format(consumed)}%</p><button className="secondary-button" onClick={onToggle} type="button">{expanded ? labels.hideRows : labels.showRows}</button>{expanded ? <div className="budget-underlay">{rows.length === 0 ? <p>{labels.noRows}</p> : rows.map((row) => <div className="budget-row" key={row.transaction_id}><time>{dateLabel(row.transaction_date, language)}</time><span>{row.description}</span><strong>{money(row.matched_amount, row.base_currency, language)}</strong></div>)}</div> : null}</article>;
}

function emptyDraft(): Draft {
  const today = localDate(new Date());
  return { name: "", amount: "", periodType: "calendar_month", rolloverMode: "reset", startsOn: today.slice(0, 8) + "01", endsOn: today, anchorDay: 25, analysisGroupId: "", categoryModes: {}, tagModes: {} };
}

function draftFromBudget(budget: Budget): Draft {
  return {
    name: budget.name,
    amount: budget.amount,
    periodType: budget.period_type,
    rolloverMode: budget.rollover_mode,
    startsOn: budget.starts_on,
    endsOn: budget.ends_on ?? budget.starts_on,
    anchorDay: budget.anchor_day,
    analysisGroupId: budget.analysis_group_id ? String(budget.analysis_group_id) : "",
    categoryModes: Object.fromEntries(
      budget.categories.map((item) => [item.category_id, item.mode]),
    ),
    tagModes: Object.fromEntries(budget.tags.map((item) => [item.tag_id, item.mode])),
  };
}

function currentMonth(): string { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`; }
function monthPeriod(month: string) { const [year, monthNumber] = month.split("-").map(Number); return { from: localDate(new Date(year, monthNumber - 1, 1)), to: localDate(new Date(year, monthNumber, 0)) }; }
function localDate(value: Date): string { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`; }
function money(value: string, currency: string, language: Language): string { return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", { style: "currency", currency }).format(Number(value)); }
function dateLabel(value: string, language: Language): string { return new Intl.DateTimeFormat(language === "sv" ? "sv-SE" : "en-SE", { day: "numeric", month: "short" }).format(new Date(`${value}T12:00:00`)); }
function periodLabel(value: BudgetPeriodType, labels: typeof text.sv | typeof text.en): string { return { calendar_month: labels.calendarMonth, salary_cycle: labels.salaryCycle, calendar_year: labels.calendarYear, custom: labels.custom }[value]; }
