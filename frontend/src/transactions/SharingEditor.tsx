import { useState } from "react";
import {
  type Category,
  type Language,
  type SharingParty,
  type Tag,
} from "../api";
import { type Labels } from "../i18n/transactions";
import {
  type Draft,
  type ShareDraft,
  type SplitDraft,
  allocationTotal,
  newSplitDraft,
  normalizeDecimalInput,
  formatMoney,
} from "./model";

export function SplitEditor({
  availableCategories,
  currency,
  draft,
  labels,
  language,
  setDraft,
  sharingParties,
  tags,
}: {
  availableCategories: Category[];
  currency: string;
  draft: Draft;
  labels: Labels;
  language: Language;
  setDraft: React.Dispatch<React.SetStateAction<Draft>>;
  sharingParties: SharingParty[];
  tags: Tag[];
}) {
  const allocated = draft.splits.reduce(
    (total, split) => total + Number(normalizeDecimalInput(split.amount) || 0),
    0,
  );
  const remaining = Number(normalizeDecimalInput(draft.amount) || 0) - allocated;
  const updateSplit = (key: string, values: Partial<SplitDraft>) => {
    setDraft((current) => ({
      ...current,
      splits: current.splits.map((split) =>
        split.key === key ? { ...split, ...values } : split,
      ),
    }));
  };
  return (
    <section className="split-editor" aria-labelledby="split-editor-title">
      <div className="split-editor-heading">
        <div>
          <h3 id="split-editor-title">{labels.splitTransaction}</h3>
          <p>{labels.splitLead}</p>
        </div>
        <strong className={Math.abs(remaining) < 0.00005 ? "balanced" : "unbalanced"}>
          {labels.remaining}: {formatMoney(String(remaining), currency || "SEK", language)}
        </strong>
      </div>
      <div className="split-list">
        {draft.splits.map((split, index) => (
          <fieldset className="split-row" key={split.key}>
            <legend>{labels.splitPart} {index + 1}</legend>
            <label>{labels.amount}<input aria-label={`${labels.splitPart} ${index + 1} · ${labels.amount}`} inputMode="decimal" onChange={(event) => updateSplit(split.key, { amount: event.target.value })} pattern="[0-9]+([.,][0-9]{1,4})?" required value={split.amount} /></label>
            <label>{labels.category}<select aria-label={`${labels.splitPart} ${index + 1} · ${labels.category}`} onChange={(event) => updateSplit(split.key, { categoryId: event.target.value })} value={split.categoryId}><option value="">{labels.noCategory}</option>{availableCategories.map((category) => <option key={category.category_id} value={category.category_id}>{category.name}</option>)}</select></label>
            <label>{labels.splitMemo}<input onChange={(event) => updateSplit(split.key, { memo: event.target.value })} value={split.memo} /></label>
            <label className="checkbox-field"><input checked={split.isBaseCost} onChange={(event) => updateSplit(split.key, { isBaseCost: event.target.checked })} type="checkbox" />{labels.baseCost}</label>
            {tags.length ? <details className="split-tags"><summary>{labels.tags}</summary>{tags.map((tag) => <label className="checkbox-field" key={tag.tag_id}><input checked={split.tagIds.includes(tag.tag_id)} onChange={(event) => updateSplit(split.key, { tagIds: event.target.checked ? [...split.tagIds, tag.tag_id] : split.tagIds.filter((id) => id !== tag.tag_id) })} type="checkbox" />{tag.name}</label>)}</details> : null}
            <SharingEditor allocations={split.sharingAllocations} labels={labels} onChange={(sharingAllocations) => updateSplit(split.key, { sharingAllocations })} parties={sharingParties} />
            <button className="ghost-button" disabled={draft.splits.length <= 2} onClick={() => setDraft((current) => ({ ...current, splits: current.splits.filter((item) => item.key !== split.key) }))} type="button">{labels.removeSplit}</button>
          </fieldset>
        ))}
      </div>
      <button className="secondary-button" disabled={draft.splits.length >= 100} onClick={() => setDraft((current) => ({ ...current, splits: [...current.splits, newSplitDraft()] }))} type="button">+ {labels.addSplit}</button>
    </section>
  );
}

export function SharingEditor({
  allocations,
  labels,
  onChange,
  parties,
}: {
  allocations: ShareDraft[];
  labels: Labels;
  onChange: (allocations: ShareDraft[]) => void;
  parties: SharingParty[];
}) {
  const [enabled, setEnabled] = useState(allocations.length > 0);
  if (!parties.length) return null;
  const total = allocationTotal(allocations);
  const setPercentage = (partyId: number, percentage: string) => {
    const withoutParty = allocations.filter(
      (allocation) => allocation.partyId !== String(partyId),
    );
    onChange([...withoutParty, { partyId: String(partyId), percentage }]);
  };
  return (
    <fieldset className="sharing-editor">
      <legend>{labels.sharing}</legend>
      <label className="checkbox-field">
        <input
          checked={enabled}
          onChange={(event) => {
            if (!event.target.checked) {
              setEnabled(false);
              onChange([]);
              return;
            }
            setEnabled(true);
            const initialParty = parties[0];
            onChange([
              { partyId: String(initialParty.sharing_party_id), percentage: "100" },
            ]);
          }}
          type="checkbox"
        />
        {enabled ? labels.sharingLead : labels.notShared}
      </label>
      {enabled ? (
        <div className="sharing-grid">
          {parties.map((party) => (
            <label key={party.sharing_party_id}>
              {party.name}{party.username ? ` · ${party.username}` : ""}
              <span className="percentage-input">
                <input
                  inputMode="decimal"
                  min="0"
                  max="100"
                  onChange={(event) =>
                    setPercentage(party.sharing_party_id, event.target.value)
                  }
                  step="0.0001"
                  type="number"
                  value={
                    allocations.find(
                      (allocation) =>
                        allocation.partyId === String(party.sharing_party_id),
                    )?.percentage ?? ""
                  }
                />
                <span>%</span>
              </span>
            </label>
          ))}
          <strong className={Math.abs(total - 100) < 0.00005 ? "balanced" : "unbalanced"}>
            {labels.allocationTotal}: {total.toLocaleString(undefined, { maximumFractionDigits: 4 })}%
          </strong>
        </div>
      ) : null}
    </fieldset>
  );
}
