import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  backupDownloadUrl,
  createBackup,
  getAuditEvents,
  getBackups,
  getRecycleBin,
  importBackup,
  validateBackup,
  type AuditEvent,
  type Backup,
  type Environment,
  type Language,
  type RecycleBinItem,
} from "../api";
import { type Labels } from "../i18n/app";

export function OperationalSafetyPanel({
  canManageBackups,
  environment,
  labels,
  language,
}: {
  canManageBackups: boolean;
  environment: Environment;
  labels: Labels;
  language: Language;
}) {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [archived, setArchived] = useState<RecycleBinItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const importInputId = `backup-import-${environment}`;
  const importInputRef = useRef<HTMLInputElement>(null);

  const loadBackups = useCallback(
    () => (canManageBackups ? getBackups(environment) : Promise.resolve([] as Backup[])),
    [canManageBackups, environment],
  );

  const refresh = () =>
    Promise.all([loadBackups(), getRecycleBin(environment), getAuditEvents(environment)])
      .then(([backupItems, recycleItems, auditPage]) => {
        setBackups(backupItems);
        setArchived(recycleItems);
        setAuditEvents(auditPage.items);
      });

  useEffect(() => {
    let active = true;
    void Promise.all([loadBackups(), getRecycleBin(environment), getAuditEvents(environment)])
      .then(([backupItems, recycleItems, auditPage]) => {
        if (!active) return;
        setBackups(backupItems);
        setArchived(recycleItems);
        setAuditEvents(auditPage.items);
      })
      .catch((error) => {
        if (active) setMessage(error instanceof Error ? error.message : "Could not load safety data.");
      });
    return () => {
      active = false;
    };
  }, [environment, loadBackups]);

  return (
    <div className="operations-grid">
      {canManageBackups ? (
      <section className="settings-section operations-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Backup</p>
            <h2>{labels.backups}</h2>
            <p className="quiet-copy">{labels.backupsLead}</p>
          </div>
          <div className="backup-actions">
            <button
              className="primary-button"
              disabled={working}
              onClick={() => {
                setWorking(true);
                setMessage(null);
                void createBackup(environment)
                  .then((created) => refresh().then(() => setMessage(created.filename)))
                  .catch((error) => setMessage(error instanceof Error ? error.message : "Backup failed."))
                  .finally(() => setWorking(false));
              }}
              type="button"
            >
              {labels.createBackup}
            </button>
          </div>
        </div>
        <div className="backup-import-panel">
          <div>
            <h3>{labels.restoreBackup}</h3>
            <p className="quiet-copy">{labels.importBackupLead}</p>
          </div>
          <button
            className="secondary-button"
            disabled={working}
            onClick={() => importInputRef.current?.click()}
            type="button"
          >
            {labels.importBackup}
          </button>
          <input
            accept=".crbackup,application/octet-stream"
            data-testid="backup-file-input"
            disabled={working}
            hidden
            id={importInputId}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              event.currentTarget.value = "";
              if (!file) return;
              setWorking(true);
              setMessage(null);
              void importBackup(environment, file)
                .then((validation) =>
                  refresh().then(() =>
                    setMessage(`${labels.importComplete}: ${validation.filename}`),
                  ),
                )
                .catch((error) =>
                  setMessage(error instanceof Error ? error.message : "Backup import failed."),
                )
                .finally(() => setWorking(false));
            }}
            ref={importInputRef}
            type="file"
          />
        </div>
        <p className="backup-key-hint">{labels.importBackupKeyHint}</p>
        {backups.length === 0 ? <p className="resource-empty">{labels.noBackups}</p> : null}
        <div className="operations-list">
          {backups.map((backup) => (
            <div className="operation-row" key={backup.filename}>
              <div>
                <strong>{new Date(backup.created_at).toLocaleString(language === "sv" ? "sv-SE" : "en-US")}</strong>
                <span>{backup.kind.replace("_", " ")} · {(backup.size_bytes / 1024).toFixed(1)} kB</span>
              </div>
              <div className="row-actions">
                <button
                  className="ghost-button"
                  onClick={() => {
                    setMessage(null);
                    void validateBackup(environment, backup.filename)
                      .then(() => setMessage(`${labels.validate}: ${backup.filename}`))
                      .catch((error) => setMessage(error instanceof Error ? error.message : "Validation failed."));
                  }}
                  type="button"
                >
                  {labels.validate}
                </button>
                <a className="ghost-button button-link" href={backupDownloadUrl(environment, backup.filename)}>
                  {labels.download}
                </a>
              </div>
            </div>
          ))}
        </div>
        {message ? <p className="form-message" role="status">{message}</p> : null}
      </section>
      ) : null}

      <section className="settings-section operations-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Ledger safety</p>
            <h2>{labels.lifecycle}</h2>
            <p className="quiet-copy">{labels.lifecycleLead}</p>
          </div>
        </div>
        <div className="lifecycle-columns">
          <div>
            <h3>{labels.recycleBin}</h3>
            {archived.length === 0 ? <p className="resource-empty">{labels.noArchived}</p> : null}
            <div className="operations-list compact-list">
              {archived.slice(0, 8).map((item) => (
                <div className="operation-row" key={`${item.entity_type}:${item.entity_id}`}>
                  <div><strong>{item.label}</strong><span>{item.entity_type}</span></div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3>{labels.auditTrail}</h3>
            {auditEvents.length === 0 ? <p className="resource-empty">{labels.noAudit}</p> : null}
            <div className="operations-list compact-list">
              {auditEvents.map((event) => (
                <div className="operation-row" key={event.audit_event_id}>
                  <div><strong>{event.action.replace("_", " ")}</strong><span>{event.entity_type} #{event.entity_id ?? "—"}</span></div>
                  <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleDateString(language === "sv" ? "sv-SE" : "en-US")}</time>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
