# ADR 0020: Streaming backup format 2 and schema compatibility

**Status:** Accepted
**Date:** 2026-11-16
**Amends:** ADR 0009

## Context

Format 1 encrypted the whole archive as one AES-GCM message. Creating,
validating and restoring a backup therefore held the full archive in memory,
and the upload limit of 5 GiB allowed a single request to exhaust the API
container. A backup could also be restored into an older release whose code did
not know its schema.

## Decision

- New backups use format 2: `COSTREVIEW-BACKUP-2` header, scrypt salt, a 7-byte
  nonce prefix and the chunk size, followed by 1 MiB plaintext chunks, each
  sealed with AES-GCM. A chunk nonce is `prefix || counter || final`, and the
  header is the associated data of every chunk. Reordering, removing or
  truncating chunks makes authentication fail.
- Encryption, validation and restore stream between files with constant memory.
- Format 1 archives remain readable, so existing backups can still be restored.
- Restore refuses a backup whose schema revision is not part of the running
  release's migration history (`backup_schema_newer`). Older revisions are
  accepted; the API applies newer migrations when it starts.
- Creating, listing, validating, downloading and uploading backups requires the
  owner role (ADR 0019).

## Consequences

Backups created by 0.9.0 cannot be read by 0.8.0. Restoring into an older
release was never supported, and it is now refused explicitly.
