import { useState } from "react";
import { getSession, resetTestEnvironment, type Session } from "../api";
import { type Labels } from "../i18n/app";

export function TestResetPanel({
  labels,
  session,
  onSession,
}: {
  labels: Labels;
  session: Session;
  onSession: (session: Session) => void;
}) {
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const canReset = confirmation === "DELETE ALL TEST DATA";

  return (
    <section className="danger-section" id="attention">
      <div>
        <p className="eyebrow">DEMO / TEST</p>
        <h2>{labels.resetTitle}</h2>
        <p>{labels.resetLead}</p>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setWorking(true);
          setMessage(null);
          void resetTestEnvironment(confirmation)
            .then(async (result) => {
              const refreshed = await getSession("test");
              onSession(refreshed);
              setConfirmation("");
              setMessage(`${result.message} #${result.reset_generation}`);
            })
            .catch((error) => setMessage(error instanceof Error ? error.message : "Reset failed."))
            .finally(() => setWorking(false));
        }}
      >
        <label>
          {labels.resetPhrase}
          <input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
        </label>
        <button className="destructive-button" disabled={!canReset || working} type="submit">
          {labels.resetAction}
        </button>
        {message ? <p className="form-message">{message}</p> : null}
      </form>
      <span className="sr-only">{session.data_plane_id}</span>
    </section>
  );
}
