import { useState } from "react";
import {
  changePassword,
  saveSettings,
  type AppSettings,
  type Environment,
  type Session,
} from "../api";
import { type Labels } from "../i18n/app";

export function SettingsPanel({
  environment,
  labels,
  session,
  onSession,
}: {
  environment: Environment;
  labels: Labels;
  session: Session;
  onSession: (session: Session) => void;
}) {
  const [draft, setDraft] = useState(session.settings);
  const [status, setStatus] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const update = (field: keyof AppSettings, value: string) => {
    setDraft((current) => ({ ...current, [field]: value }) as AppSettings);
  };

  return (
    <section className="settings-section" id="settings">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{environment === "test" ? labels.test : labels.production}</p>
          <h2>{labels.settings}</h2>
        </div>
        {status ? <span className="save-status">{status}</span> : null}
      </div>
      <form
        className="settings-form"
        onSubmit={(event) => {
          event.preventDefault();
          setWorking(true);
          setStatus(null);
          void saveSettings(environment, draft)
            .then((saved) => {
              onSession({ ...session, settings: saved });
              setStatus(labels.saved);
            })
            .catch((error) => setStatus(error instanceof Error ? error.message : "Save failed."))
            .finally(() => setWorking(false));
        }}
      >
        <label>
          {labels.language}
          <select value={draft.language} onChange={(event) => update("language", event.target.value)}>
            <option value="sv">Svenska</option>
            <option value="en">English</option>
          </select>
        </label>
        <label>
          {labels.region}
          <input value={draft.region} onChange={(event) => update("region", event.target.value)} />
        </label>
        <label>
          {labels.currency}
          <input
            maxLength={3}
            value={draft.base_currency}
            onChange={(event) => update("base_currency", event.target.value.toUpperCase())}
          />
        </label>
        <label>
          {labels.timezone}
          <input value={draft.timezone} onChange={(event) => update("timezone", event.target.value)} />
        </label>
        <button className="primary-button" disabled={working} type="submit">
          {labels.save}
        </button>
      </form>
    </section>
  );
}

export function SecurityPanel({
  environment,
  labels,
}: {
  environment: Environment;
  labels: Labels;
}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  return (
    <section className="settings-section security-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Account</p>
          <h2>{labels.security}</h2>
          <p className="quiet-copy">{labels.securityLead}</p>
        </div>
      </div>
      <form
        className="password-form"
        onSubmit={(event) => {
          event.preventDefault();
          setMessage(null);
          if (newPassword !== confirmation) {
            setMessage(labels.passwordMismatch);
            return;
          }
          setWorking(true);
          void changePassword(environment, currentPassword, newPassword)
            .then(() => {
              setCurrentPassword("");
              setNewPassword("");
              setConfirmation("");
              setMessage(labels.passwordChanged);
            })
            .catch((error) =>
              setMessage(error instanceof Error ? error.message : "Password change failed."),
            )
            .finally(() => setWorking(false));
        }}
      >
        <label>
          {labels.currentPassword}
          <input
            autoComplete="current-password"
            onChange={(event) => setCurrentPassword(event.target.value)}
            required
            type="password"
            value={currentPassword}
          />
        </label>
        <label>
          {labels.newPassword}
          <input
            autoComplete="new-password"
            minLength={12}
            onChange={(event) => setNewPassword(event.target.value)}
            required
            type="password"
            value={newPassword}
          />
        </label>
        <label>
          {labels.confirmPassword}
          <input
            autoComplete="new-password"
            minLength={12}
            onChange={(event) => setConfirmation(event.target.value)}
            required
            type="password"
            value={confirmation}
          />
        </label>
        <button className="primary-button" disabled={working} type="submit">
          {labels.changePassword}
        </button>
      </form>
      {message ? <p className="form-message" role="status">{message}</p> : null}
    </section>
  );
}
