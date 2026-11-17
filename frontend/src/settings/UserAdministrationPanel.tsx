import { useCallback, useEffect, useState } from "react";
import {
  createUser,
  deleteUser,
  getUsers,
  resetUserPassword,
  updateUser,
  type Environment,
  type Session,
  type UserAccount,
  type UserRole,
} from "../api";
import { type Labels } from "../i18n/app";

type UserDraft = { username: string; role: UserRole; password: string };

function roleLabel(labels: Labels, role: UserRole): string {
  if (role === "owner") return labels.roleOwner;
  if (role === "viewer") return labels.roleViewer;
  return labels.roleMember;
}

function RoleSelect({
  labels,
  onChange,
  value,
}: {
  labels: Labels;
  onChange: (role: UserRole) => void;
  value: UserRole;
}) {
  return (
    <select onChange={(event) => onChange(event.target.value as UserRole)} value={value}>
      <option value="member">{labels.roleMember}</option>
      <option value="viewer">{labels.roleViewer}</option>
      <option value="owner">{labels.roleOwner}</option>
    </select>
  );
}

export function UserAdministrationPanel({
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
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [drafts, setDrafts] = useState<Record<number, UserDraft>>({});
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<UserRole>("member");
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const installUsers = useCallback((items: UserAccount[]) => {
    setUsers(items);
    setDrafts(
      Object.fromEntries(
        items.map((user) => [
          user.user_id,
          { username: user.username, role: user.role, password: "" },
        ]),
      ),
    );
  }, []);

  const refresh = () => getUsers(environment).then(installUsers);

  useEffect(() => {
    let active = true;
    void getUsers(environment)
      .then((items) => {
        if (active) installUsers(items);
      })
      .catch((error) => {
        if (active) setMessage(error instanceof Error ? error.message : "Could not load users.");
      });
    return () => {
      active = false;
    };
  }, [environment, installUsers]);

  const updateDraft = (userId: number, values: Partial<UserDraft>) => {
    setDrafts((current) => ({
      ...current,
      [userId]: { ...current[userId], ...values },
    }));
  };

  return (
    <section className="settings-section user-administration-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{labels.roleOwner}</p>
          <h2>{labels.userAdministration}</h2>
          <p className="quiet-copy">{labels.userAdministrationLead}</p>
        </div>
      </div>

      <form
        className="user-create-form"
        onSubmit={(event) => {
          event.preventDefault();
          setWorking(true);
          setMessage(null);
          void createUser(
            environment,
            newUsername,
            newPassword,
            newRole,
            session.settings,
          )
            .then(() => refresh())
            .then(() => {
              setNewUsername("");
              setNewPassword("");
              setNewRole("member");
              setMessage(labels.accountCreated);
            })
            .catch((error) =>
              setMessage(error instanceof Error ? error.message : "Account creation failed."),
            )
            .finally(() => setWorking(false));
        }}
      >
        <label>
          {labels.username}
          <input
            autoComplete="off"
            minLength={3}
            maxLength={64}
            onChange={(event) => setNewUsername(event.target.value)}
            required
            value={newUsername}
          />
        </label>
        <label>
          {labels.password}
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
          {labels.role}
          <RoleSelect labels={labels} onChange={setNewRole} value={newRole} />
        </label>
        <button className="primary-button" disabled={working} type="submit">
          {labels.addUser}
        </button>
      </form>

      <div className="user-account-list">
        {users.map((user) => {
          const draft = drafts[user.user_id];
          if (!draft) return null;
          const isCurrent = user.username === session.username;
          const confirmingDelete = deleteTarget === user.user_id;
          return (
            <article className="user-account-card" key={user.user_id}>
              <div className="user-account-heading">
                <div>
                  <strong>{user.username}</strong>
                  <span>
                    {roleLabel(labels, user.role)}
                    {isCurrent ? ` · ${labels.you}` : ""}
                  </span>
                </div>
              </div>
              <div className="user-account-fields">
                <label>
                  {labels.username}
                  <input
                    maxLength={64}
                    minLength={3}
                    onChange={(event) => updateDraft(user.user_id, { username: event.target.value })}
                    value={draft.username}
                  />
                </label>
                <label>
                  {labels.role}
                  <RoleSelect
                    labels={labels}
                    onChange={(role) => updateDraft(user.user_id, { role })}
                    value={draft.role}
                  />
                </label>
                <button
                  className="secondary-button"
                  disabled={working}
                  onClick={() => {
                    setWorking(true);
                    setMessage(null);
                    void updateUser(environment, user.user_id, {
                      username: draft.username,
                      role: draft.role,
                    })
                      .then((updated) => {
                        if (isCurrent) {
                          onSession({
                            ...session,
                            username: updated.username,
                            role: updated.role,
                          });
                        }
                        return refresh();
                      })
                      .then(() => setMessage(labels.accountSaved))
                      .catch((error) =>
                        setMessage(error instanceof Error ? error.message : "Account save failed."),
                      )
                      .finally(() => setWorking(false));
                  }}
                  type="button"
                >
                  {labels.saveAccount}
                </button>
              </div>
              {!isCurrent ? (
                <div className="user-account-actions">
                  <label>
                    {labels.newPassword}
                    <input
                      autoComplete="new-password"
                      minLength={12}
                      onChange={(event) => updateDraft(user.user_id, { password: event.target.value })}
                      type="password"
                      value={draft.password}
                    />
                  </label>
                  <button
                    className="secondary-button"
                    disabled={working || draft.password.length < 12}
                    onClick={() => {
                      setWorking(true);
                      setMessage(null);
                      void resetUserPassword(environment, user.user_id, draft.password)
                        .then(() => {
                          updateDraft(user.user_id, { password: "" });
                          setMessage(labels.passwordReset);
                        })
                        .catch((error) =>
                          setMessage(error instanceof Error ? error.message : "Reset failed."),
                        )
                        .finally(() => setWorking(false));
                    }}
                    type="button"
                  >
                    {labels.resetPassword}
                  </button>
                  {!confirmingDelete ? (
                    <button
                      className="destructive-button"
                      disabled={working}
                      onClick={() => {
                        setDeleteTarget(user.user_id);
                        setDeleteConfirmation("");
                      }}
                      type="button"
                    >
                      {labels.removeAccount}
                    </button>
                  ) : null}
                </div>
              ) : null}
              {confirmingDelete ? (
                <div className="user-delete-confirmation">
                  <label>
                    {labels.removeConfirmation}: <code>DELETE {user.username}</code>
                    <input
                      onChange={(event) => setDeleteConfirmation(event.target.value)}
                      value={deleteConfirmation}
                    />
                  </label>
                  <div className="row-actions">
                    <button
                      className="destructive-button"
                      disabled={working || deleteConfirmation !== `DELETE ${user.username}`}
                      onClick={() => {
                        setWorking(true);
                        setMessage(null);
                        void deleteUser(environment, user.user_id, deleteConfirmation)
                          .then(() => refresh())
                          .then(() => {
                            setDeleteTarget(null);
                            setDeleteConfirmation("");
                            setMessage(labels.accountRemoved);
                          })
                          .catch((error) =>
                            setMessage(error instanceof Error ? error.message : "Deletion failed."),
                          )
                          .finally(() => setWorking(false));
                      }}
                      type="button"
                    >
                      {labels.confirmRemoval}
                    </button>
                    <button
                      className="secondary-button"
                      disabled={working}
                      onClick={() => setDeleteTarget(null)}
                      type="button"
                    >
                      {labels.cancel}
                    </button>
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
      {message ? <p className="form-message" role="status">{message}</p> : null}
    </section>
  );
}
