# ADR 0009: Pilot data safety and offline restore

## Status

Accepted for the private pilot.

## Context

Real household data must not be accepted until Cost Review can preserve ledger
history, make reconciliation corrections explicit, and prove that a complete
encrypted backup can be restored. Production and Demo/Test are separate trust
domains and may never share database credentials, attachment roots, backup
roots, encryption keys, or scheduled backup processes.

## Decision

- A reconciled balance is stored as an immutable dated observation. If its
  reported balance differs from the calculated balance, the user may create a
  separate `adjustment` transaction after typing a fixed confirmation phrase.
  The adjustment records direction and amount, is idempotently linked to the
  observation, affects later calculated balances, and is excluded from ordinary
  income, expense, budget, and consumption analysis.
- Material Ledger creates and updates append an audit event with changed
  fields, timestamp, and source. Archive remains the default destructive action.
  A central Recycle Bin lists recoverable records. Dependency-aware permanent
  deletion remains unavailable until all dependency and frozen-identity rules
  are implemented.
- Each data plane creates an AES-GCM encrypted `.crbackup` archive containing a
  PostgreSQL custom-format dump, configuration stored in PostgreSQL, attachment
  files, a manifest, and per-file SHA-256 checksums. Scrypt derives the archive
  key from a data-plane-specific installation secret of at least 32 bytes.
- Automatic and manual backups use the same format. Count retention applies
  only to automatic backups. Manual and pre-restore safety backups are exempt.
- Restore is an offline operator action, not an HTTP endpoint. It requires the
  target API and backup scheduler to be stopped, validates format, authenticated
  decryption, checksums, and environment before overwrite, and creates a fresh
  encrypted pre-restore safety backup. Restored sessions are invalidated.
- Separate optional Compose backup services schedule Production and Demo/Test
  backups on their respective private data networks. They have no route or
  credentials to the other data plane and mount attachments read-only.

## Consequences

- A lost installation backup key makes existing backups unrecoverable. The key
  must therefore be stored outside both the repository and Docker host backup
  volume.
- Database dump and encrypted payload creation temporarily require additional
  disk and memory. Pilot operators should monitor free space and download known
  good backups off-host.
- Restore briefly takes one data plane offline. This is intentional: online
  replacement would allow writes to race with restoration and session state.
- The browser can create, validate, and download backups, but an operator must
  use the documented Compose command to restore one.
- Password-per-download archives, age-based retention, dependency-aware
  permanent deletion, bulk-edit audit grouping, and attachments UI remain
  explicit follow-up slices rather than being implied by this pilot control.

## Verification

Release validation must use an isolated Compose project and PostgreSQL. It must
upgrade migrations, check schema drift, run API and isolation tests, create and
validate an encrypted archive, mutate data and attachments, restore offline,
and prove that the backed-up state returns while the later mutation does not.
