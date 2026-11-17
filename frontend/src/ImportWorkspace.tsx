import { useCallback, useEffect, useMemo, useState } from "react";

import {
  bulkUpdateImportRows,
  commitImport,
  getAccounts,
  getCategories,
  getImportRows,
  getImportUndoPreview,
  getImports,
  getImportProfiles,
  previewImport,
  stageImport,
  undoImport,
  updateImportRow,
  type Account,
  type Category,
  type Environment,
  type ImportBatch,
  type ImportMapping,
  type ImportPreview,
  type ImportProfile,
  type ImportRow,
  type ImportRowChange,
  type ImportRowStatus,
  type ImportUndoPreview,
  type Language,
} from "./api";
import { text, UNDO_CONFIRMATION } from "./i18n/import";

const DATE_FORMATS = ["%Y-%m-%d", "%Y%m%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"];


type Labels = (typeof text)["sv"];
type ColumnKey =
  | "date_column"
  | "posting_date_column"
  | "description_column"
  | "amount_column"
  | "debit_column"
  | "credit_column"
  | "currency_column"
  | "reference_column";

export function ImportWorkspace({
  environment,
  language,
  canWrite,
}: {
  environment: Environment;
  language: Language;
  canWrite: boolean;
}) {
  const labels = text[language];
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [profiles, setProfiles] = useState<ImportProfile[]>([]);
  const [batches, setBatches] = useState<ImportBatch[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [accountId, setAccountId] = useState("");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<ImportMapping | null>(null);
  const [profileName, setProfileName] = useState("");
  const [activeBatch, setActiveBatch] = useState<ImportBatch | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const refreshHistory = useCallback(
    () => getImports(environment).then((page) => setBatches(page.items)),
    [environment],
  );

  useEffect(() => {
    let active = true;
    void Promise.all([
      getAccounts(environment),
      getCategories(environment),
      getImportProfiles(environment),
      getImports(environment),
    ])
      .then(([accountPage, categoryPage, profileItems, batchPage]) => {
        if (!active) return;
        setAccounts(accountPage.items);
        setCategories(categoryPage.items);
        setProfiles(profileItems);
        setBatches(batchPage.items);
      })
      .catch((reason) => {
        if (active) setError(errorText(reason));
      });
    return () => {
      active = false;
    };
  }, [environment]);

  const run = (action: () => Promise<unknown>) => {
    setWorking(true);
    setError(null);
    setMessage(null);
    return action()
      .catch((reason) => setError(errorText(reason)))
      .finally(() => setWorking(false));
  };

  const analyse = () => {
    if (!file) return;
    void run(() =>
      previewImport(environment, file).then((result) => {
        setPreview(result);
        setMapping(mappingFromSuggestion(result));
        const best = result.profile_suggestions[0];
        const profile = best && best.confidence >= 80
          ? profiles.find((item) => item.import_profile_id === best.import_profile_id)
          : undefined;
        if (profile) applyProfile(profile);
      }),
    );
  };

  const applyProfile = (profile: ImportProfile) => {
    setMapping({
      date_column: profile.date_column,
      description_column: profile.description_column,
      amount_column: profile.amount_column,
      debit_column: profile.debit_column,
      credit_column: profile.credit_column,
      posting_date_column: profile.posting_date_column,
      currency_column: profile.currency_column,
      reference_column: profile.reference_column,
      date_format: profile.date_format,
      decimal_separator: profile.decimal_separator,
      amount_sign: profile.amount_sign,
      delimiter: profile.delimiter,
      header_row: profile.header_row,
    });
    if (profile.default_account_id) setAccountId(String(profile.default_account_id));
  };

  const stage = () => {
    if (!file || !mapping || !accountId) return;
    void run(() =>
      stageImport(environment, file, {
        account_id: Number(accountId),
        mapping,
        save_profile_name: profileName.trim() || null,
      }).then((batch) => {
        setActiveBatch(batch);
        setPreview(null);
        setFile(null);
        setProfileName("");
        return Promise.all([refreshHistory(), getImportProfiles(environment).then(setProfiles)]);
      }),
    );
  };

  return (
    <section className="import-workspace" aria-labelledby="import-title">
      <div className="workspace-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1 id="import-title">{labels.title}</h1>
          <p>{labels.lead}</p>
        </div>
      </div>
      {error ? <div className="error-banner" role="alert">{error}</div> : null}
      {message ? <p className="form-message" role="status">{message}</p> : null}

      {!canWrite ? <p className="quiet-copy">{labels.readOnly}</p> : null}

      {canWrite && !activeBatch ? (
        <section className="settings-section import-upload">
          <div className="import-upload-grid">
            <label>
              {labels.file}
              <input
                accept=".csv,.txt,.tsv,.xlsx"
                onChange={(event) => {
                  setFile(event.currentTarget.files?.[0] ?? null);
                  setPreview(null);
                }}
                type="file"
              />
            </label>
            <label>
              {labels.account}
              <select onChange={(event) => setAccountId(event.target.value)} value={accountId}>
                <option value="">{labels.chooseAccount}</option>
                {accounts.map((account) => (
                  <option key={account.account_id} value={account.account_id}>
                    {account.name} · {account.currency}
                  </option>
                ))}
              </select>
            </label>
            <button className="secondary-button" disabled={!file || working} onClick={analyse} type="button">
              {labels.analyse}
            </button>
          </div>

          {preview && mapping ? (
            <>
              {preview.previous_imports.length ? (
                <p className="attention-note">{labels.previousImport}</p>
              ) : null}
              {preview.profile_suggestions.length ? (
                <div className="import-profiles">
                  <h3>{labels.profiles}</h3>
                  {preview.profile_suggestions.map((suggestion) => {
                    const profile = profiles.find(
                      (item) => item.import_profile_id === suggestion.import_profile_id,
                    );
                    return profile ? (
                      <button
                        className="ghost-button"
                        key={suggestion.import_profile_id}
                        onClick={() => applyProfile(profile)}
                        type="button"
                      >
                        {labels.useProfile} {suggestion.name} · {suggestion.confidence}% {labels.match}
                      </button>
                    ) : null;
                  })}
                </div>
              ) : null}
              <MappingForm headers={preview.headers} labels={labels} mapping={mapping} onChange={setMapping} />
              <label className="import-profile-name">
                {labels.saveProfile}
                <input maxLength={120} onChange={(event) => setProfileName(event.target.value)} value={profileName} />
              </label>
              <h3>
                {labels.sample} · {preview.row_count} {labels.rows}
              </h3>
              <div className="table-scroll">
                <table className="import-table" aria-label={labels.sample}>
                  <thead>
                    <tr>
                      {preview.headers.map((header) => (
                        <th key={header} scope="col">{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample_rows.slice(0, 8).map((row, index) => (
                      <tr key={index}>
                        {preview.headers.map((header) => (
                          <td key={header}>{String(row[header] ?? "")}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="editor-actions">
                <button
                  className="primary-button"
                  disabled={working || !accountId || !mapping.date_column || !mapping.description_column}
                  onClick={stage}
                  type="button"
                >
                  {labels.stage}
                </button>
              </div>
            </>
          ) : null}
        </section>
      ) : null}

      {activeBatch ? (
        <ImportReview
          batch={activeBatch}
          canWrite={canWrite}
          categories={categories}
          environment={environment}
          labels={labels}
          language={language}
          onClose={() => {
            setActiveBatch(null);
            void refreshHistory();
          }}
          onCommitted={(batch) => {
            setActiveBatch(null);
            setMessage(labels.done);
            void refreshHistory();
            return batch;
          }}
        />
      ) : null}

      <ImportHistory
        accounts={accounts}
        batches={batches}
        canWrite={canWrite}
        environment={environment}
        labels={labels}
        language={language}
        onOpen={setActiveBatch}
        onUndone={() => {
          setMessage(labels.undone);
          void refreshHistory();
        }}
      />
    </section>
  );
}

function MappingForm({
  headers,
  labels,
  mapping,
  onChange,
}: {
  headers: string[];
  labels: Labels;
  mapping: ImportMapping;
  onChange: (mapping: ImportMapping) => void;
}) {
  const columns: { key: ColumnKey; label: string; required?: boolean }[] = [
    { key: "date_column", label: labels.dateColumn, required: true },
    { key: "description_column", label: labels.descriptionColumn, required: true },
    { key: "amount_column", label: labels.amountColumn },
    { key: "debit_column", label: labels.debitColumn },
    { key: "credit_column", label: labels.creditColumn },
    { key: "posting_date_column", label: labels.postingDateColumn },
    { key: "currency_column", label: labels.currencyColumn },
    { key: "reference_column", label: labels.referenceColumn },
  ];
  const set = (change: Partial<ImportMapping>) => onChange({ ...mapping, ...change });
  return (
    <fieldset className="import-mapping">
      <legend>{labels.mapping}</legend>
      {columns.map((column) => (
        <label key={column.key}>
          {column.label}
          <select
            onChange={(event) => {
              const value = event.target.value || null;
              if (column.key === "amount_column" && value) {
                set({ amount_column: value, debit_column: null, credit_column: null });
              } else if ((column.key === "debit_column" || column.key === "credit_column") && value) {
                set({ [column.key]: value, amount_column: null } as Partial<ImportMapping>);
              } else {
                set({ [column.key]: column.required ? value ?? "" : value } as Partial<ImportMapping>);
              }
            }}
            required={column.required}
            value={mapping[column.key] ?? ""}
          >
            {column.required ? null : <option value="">{labels.none}</option>}
            {headers.map((header) => (
              <option key={header} value={header}>{header}</option>
            ))}
          </select>
        </label>
      ))}
      <label>
        {labels.dateFormat}
        <select onChange={(event) => set({ date_format: event.target.value })} value={mapping.date_format}>
          {DATE_FORMATS.map((format) => (
            <option key={format} value={format}>{dateFormatLabel(format, labels.yearToken)}</option>
          ))}
        </select>
      </label>
      <label>
        {labels.decimalSeparator}
        <select
          onChange={(event) => set({ decimal_separator: event.target.value as "," | "." })}
          value={mapping.decimal_separator}
        >
          <option value=",">1 234,56</option>
          <option value=".">1,234.56</option>
        </select>
      </label>
      <label>
        {labels.amountSign}
        <select
          onChange={(event) => set({ amount_sign: event.target.value as "as_is" | "inverted" })}
          value={mapping.amount_sign}
        >
          <option value="as_is">{labels.asIs}</option>
          <option value="inverted">{labels.inverted}</option>
        </select>
      </label>
    </fieldset>
  );
}

const STATUS_ORDER: ImportRowStatus[] = ["invalid", "duplicate", "ready", "skipped", "committed"];

function ImportReview({
  batch,
  canWrite,
  categories,
  environment,
  labels,
  language,
  onClose,
  onCommitted,
}: {
  batch: ImportBatch;
  canWrite: boolean;
  categories: Category[];
  environment: Environment;
  labels: Labels;
  language: Language;
  onClose: () => void;
  onCommitted: (batch: ImportBatch) => void;
}) {
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [filter, setFilter] = useState<ImportRowStatus | "all">("all");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkCategory, setBulkCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const editable = canWrite && batch.status === "staged";

  const load = useCallback(
    () => getImportRows(environment, batch.import_batch_id).then((page) => setRows(page.items)),
    [environment, batch.import_batch_id],
  );

  useEffect(() => {
    void load().catch((reason) => setError(errorText(reason)));
  }, [load]);

  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const row of rows) result[row.status] = (result[row.status] ?? 0) + 1;
    return result;
  }, [rows]);
  const visible = filter === "all" ? rows : rows.filter((row) => row.status === filter);

  const act = (action: () => Promise<unknown>) => {
    setWorking(true);
    setError(null);
    return action()
      .then(() => load())
      .catch((reason) => setError(errorText(reason)))
      .finally(() => setWorking(false));
  };

  const changeRow = (row: ImportRow, change: ImportRowChange) =>
    act(() => updateImportRow(environment, batch.import_batch_id, row.import_row_id, change));

  const bulk = (change: { status?: "ready" | "skipped"; category_id?: number | null }) =>
    act(() =>
      bulkUpdateImportRows(environment, batch.import_batch_id, [...selected], change).then(() =>
        setSelected(new Set()),
      ),
    );

  return (
    <section className="settings-section import-review" aria-labelledby="import-review-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{labels.status[batch.status]}</p>
          <h2 id="import-review-title">
            {labels.review} · {batch.filename}
          </h2>
        </div>
        <button className="ghost-button" onClick={onClose} type="button">×</button>
      </div>
      {error ? <div className="error-banner" role="alert">{error}</div> : null}
      <div className="import-filters" role="group">
        <button
          aria-pressed={filter === "all"}
          className="ghost-button"
          onClick={() => setFilter("all")}
          type="button"
        >
          {labels.all} · {rows.length}
        </button>
        {STATUS_ORDER.filter((status) => counts[status]).map((status) => (
          <button
            aria-pressed={filter === status}
            className="ghost-button"
            key={status}
            onClick={() => setFilter(status)}
            type="button"
          >
            {labels[status]} · {counts[status]}
          </button>
        ))}
      </div>
      {editable && selected.size ? (
        <div className="import-bulk">
          <span>{selected.size}</span>
          <button className="secondary-button" disabled={working} onClick={() => void bulk({ status: "ready" })} type="button">
            {labels.approve}
          </button>
          <button className="secondary-button" disabled={working} onClick={() => void bulk({ status: "skipped" })} type="button">
            {labels.skip}
          </button>
          <select aria-label={labels.setCategory} onChange={(event) => setBulkCategory(event.target.value)} value={bulkCategory}>
            <option value="">{labels.noCategory}</option>
            {categories.map((category) => (
              <option key={category.category_id} value={category.category_id}>{category.name}</option>
            ))}
          </select>
          <button
            className="secondary-button"
            disabled={working}
            onClick={() => void bulk({ category_id: bulkCategory ? Number(bulkCategory) : null })}
            type="button"
          >
            {labels.setCategory}
          </button>
        </div>
      ) : null}
      <div className="table-scroll">
        <table className="import-table" aria-label={labels.review}>
          <thead>
            <tr>
              {editable ? <th scope="col"><span className="sr-only">{labels.select}</span></th> : null}
              <th scope="col">#</th>
              <th scope="col">{labels.dateColumn}</th>
              <th scope="col">{labels.descriptionColumn}</th>
              <th scope="col">{labels.amountColumn}</th>
              <th scope="col">{labels.category}</th>
              <th scope="col">Status</th>
              {editable ? <th scope="col"><span className="sr-only">{labels.approve}</span></th> : null}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <ImportRowLine
                categories={categories}
                editable={editable && row.status !== "committed"}
                key={row.import_row_id}
                labels={labels}
                language={language}
                onChange={(change) => void changeRow(row, change)}
                onSelect={(checked) =>
                  setSelected((current) => {
                    const next = new Set(current);
                    if (checked) next.add(row.import_row_id);
                    else next.delete(row.import_row_id);
                    return next;
                  })
                }
                row={row}
                selectable={editable}
                selected={selected.has(row.import_row_id)}
                working={working}
              />
            ))}
          </tbody>
        </table>
      </div>
      {editable ? (
        <div className="editor-actions">
          <p className="quiet-copy">
            {counts.ready ?? 0} {labels.commitLead}
          </p>
          <button
            className="primary-button"
            disabled={working || !counts.ready}
            onClick={() =>
              void act(() => commitImport(environment, batch.import_batch_id).then(onCommitted))
            }
            type="button"
          >
            {labels.commit}
          </button>
        </div>
      ) : null}
    </section>
  );
}

function ImportRowLine({
  categories,
  editable,
  labels,
  language,
  onChange,
  onSelect,
  row,
  selectable,
  selected,
  working,
}: {
  categories: Category[];
  editable: boolean;
  labels: Labels;
  language: Language;
  onChange: (change: ImportRowChange) => void;
  onSelect: (checked: boolean) => void;
  row: ImportRow;
  selectable: boolean;
  selected: boolean;
  working: boolean;
}) {
  const [date, setDate] = useState(row.transaction_date ?? "");
  const [description, setDescription] = useState(row.description ?? "");
  const [amount, setAmount] = useState(row.amount ?? "");
  const kind = row.amount && row.amount.startsWith("-") ? "expense" : "income";
  const fitting = categories.filter((category) => category.category_kind === kind);
  return (
    <tr className={`import-row import-row-${row.status}`}>
      {selectable ? (
        <td>
          <input
            aria-label={`${labels.select} ${row.row_number}`}
            checked={selected}
            disabled={!editable}
            onChange={(event) => onSelect(event.target.checked)}
            type="checkbox"
          />
        </td>
      ) : null}
      <td>{row.row_number}</td>
      <td>
        {editable && row.status === "invalid" ? (
          <input aria-label={`${labels.dateColumn} ${row.row_number}`} onChange={(event) => setDate(event.target.value)} type="date" value={date} />
        ) : (
          row.transaction_date ?? String(row.raw ? "—" : "")
        )}
      </td>
      <td>
        {editable && row.status === "invalid" ? (
          <input aria-label={`${labels.descriptionColumn} ${row.row_number}`} maxLength={240} onChange={(event) => setDescription(event.target.value)} value={description} />
        ) : (
          row.description
        )}
        {row.duplicate_reason ? (
          <small className="import-duplicate-note">
            {row.duplicate_reason === "previously_imported" ? labels.previouslyImported : labels.matchingTransaction}
            {row.duplicate_confidence !== null ? ` · ${row.duplicate_confidence}% ${labels.confidence}` : ""}
          </small>
        ) : null}
        {row.errors.length ? (
          <small className="import-error-note">
            {row.errors.map((code) => labels.errors[code] ?? code).join(" · ")}
          </small>
        ) : null}
      </td>
      <td className="numeric">
        {editable && row.status === "invalid" ? (
          <input aria-label={`${labels.amountColumn} ${row.row_number}`} className="table-number-input" inputMode="decimal" onChange={(event) => setAmount(event.target.value)} value={amount} />
        ) : row.amount !== null ? (
          formatAmount(row.amount, row.currency ?? "SEK", language)
        ) : (
          "—"
        )}
      </td>
      <td>
        {editable ? (
          <select
            aria-label={`${labels.category} ${row.row_number}`}
            disabled={working}
            onChange={(event) => onChange({ category_id: event.target.value ? Number(event.target.value) : null })}
            value={row.category_id ?? ""}
          >
            <option value="">{labels.noCategory}</option>
            {fitting.map((category) => (
              <option key={category.category_id} value={category.category_id}>{category.name}</option>
            ))}
          </select>
        ) : (
          categories.find((category) => category.category_id === row.category_id)?.name ?? "—"
        )}
      </td>
      <td>
        <span className={`import-status import-status-${row.status}`}>{labels[row.status]}</span>
      </td>
      {selectable ? (
        <td className="row-actions">
          {editable && row.status === "invalid" ? (
            <button
              className="ghost-button"
              disabled={working}
              onClick={() => {
                const change: ImportRowChange = {};
                if (date) change.transaction_date = date;
                if (description.trim()) change.description = description.trim();
                if (amount) change.amount = amount.replace(",", ".").replace(/\s/g, "");
                onChange(change);
              }}
              type="button"
            >
              {labels.save}
            </button>
          ) : null}
          {editable && row.status !== "ready" && row.status !== "invalid" ? (
            <button className="ghost-button" disabled={working} onClick={() => onChange({ status: "ready" })} type="button">
              {labels.approve}
            </button>
          ) : null}
          {editable && row.status !== "skipped" ? (
            <button className="ghost-button" disabled={working} onClick={() => onChange({ status: "skipped" })} type="button">
              {labels.skip}
            </button>
          ) : null}
        </td>
      ) : null}
    </tr>
  );
}

function ImportHistory({
  accounts,
  batches,
  canWrite,
  environment,
  labels,
  language,
  onOpen,
  onUndone,
}: {
  accounts: Account[];
  batches: ImportBatch[];
  canWrite: boolean;
  environment: Environment;
  labels: Labels;
  language: Language;
  onOpen: (batch: ImportBatch) => void;
  onUndone: () => void;
}) {
  const [undoTarget, setUndoTarget] = useState<ImportUndoPreview | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const accountName = (id: number) => accounts.find((account) => account.account_id === id)?.name ?? `#${id}`;
  return (
    <section className="settings-section import-history" aria-labelledby="import-history-title">
      <h2 id="import-history-title">{labels.history}</h2>
      {error ? <div className="error-banner" role="alert">{error}</div> : null}
      {batches.length === 0 ? <p className="resource-empty">{labels.noHistory}</p> : null}
      <div className="operations-list">
        {batches.map((batch) => (
          <div className="operation-row" key={batch.import_batch_id}>
            <div>
              <strong>{batch.filename}</strong>
              <span>
                {new Date(batch.created_at).toLocaleString(language === "sv" ? "sv-SE" : "en-US")} ·{" "}
                {accountName(batch.account_id)} · {labels.status[batch.status]} · {batch.status_counts.committed}/
                {batch.row_count} {labels.rows}
              </span>
            </div>
            <div className="row-actions">
              <button className="ghost-button" onClick={() => onOpen(batch)} type="button">
                {labels.open}
              </button>
              {canWrite && batch.status === "committed" ? (
                <button
                  className="ghost-button"
                  onClick={() => {
                    setError(null);
                    setConfirmation("");
                    void getImportUndoPreview(environment, batch.import_batch_id)
                      .then(setUndoTarget)
                      .catch((reason) => setError(errorText(reason)));
                  }}
                  type="button"
                >
                  {labels.undo}
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
      {undoTarget ? (
        <form
          className="import-undo"
          onSubmit={(event) => {
            event.preventDefault();
            void undoImport(environment, undoTarget.import_batch_id, confirmation)
              .then(() => {
                setUndoTarget(null);
                onUndone();
              })
              .catch((reason) => setError(errorText(reason)));
          }}
        >
          <h3>{labels.undo}</h3>
          <p className="quiet-copy">{labels.undoLead}</p>
          <p>
            {undoTarget.active_transaction_count} {labels.rows} · {labels.expenses}{" "}
            {formatAmount(undoTarget.expenses, "SEK", language)} · {labels.income}{" "}
            {formatAmount(undoTarget.income, "SEK", language)}
          </p>
          {undoTarget.edited_after_import_count ? (
            <p className="attention-note">
              {undoTarget.edited_after_import_count} {labels.edited}
            </p>
          ) : null}
          {!undoTarget.can_undo ? <p className="attention-note">{labels.undoBlocked}</p> : null}
          <label>
            {labels.undoConfirm}
            <input onChange={(event) => setConfirmation(event.target.value)} value={confirmation} />
          </label>
          <div className="editor-actions">
            <button className="ghost-button" onClick={() => setUndoTarget(null)} type="button">×</button>
            <button
              className="primary-button"
              disabled={!undoTarget.can_undo || confirmation !== UNDO_CONFIRMATION}
              type="submit"
            >
              {labels.undo}
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}

function mappingFromSuggestion(preview: ImportPreview): ImportMapping {
  const suggested = preview.suggested_mapping;
  const column = (key: string) => (typeof suggested[key] === "string" ? (suggested[key] as string) : null);
  return {
    date_column: column("date_column") ?? preview.headers[0] ?? "",
    description_column: column("description_column") ?? preview.headers[1] ?? "",
    amount_column: column("amount_column"),
    debit_column: column("debit_column"),
    credit_column: column("credit_column"),
    posting_date_column: column("posting_date_column"),
    currency_column: column("currency_column"),
    reference_column: column("reference_column"),
    date_format: column("date_format") ?? "%Y-%m-%d",
    decimal_separator: suggested.decimal_separator === "." ? "." : ",",
    amount_sign: "as_is",
    delimiter: preview.delimiter,
    header_row: typeof suggested.header_row === "number" ? suggested.header_row : 1,
  };
}

function dateFormatLabel(format: string, yearToken: string): string {
  return format.replace("%Y", yearToken).replace("%m", "MM").replace("%d", "DD");
}

function formatAmount(value: string, currency: string, language: Language): string {
  return new Intl.NumberFormat(language === "sv" ? "sv-SE" : "en-SE", {
    style: "currency",
    currency,
  }).format(Number(value));
}

function errorText(reason: unknown): string {
  return reason instanceof Error ? reason.message : String(reason);
}
