# ADR 0021: Staged CSV/XLSX import with explicit approval

**Status:** Accepted
**Date:** 2026-11-16

## Context

Manual entry was the only way to record transactions. The product
specification (CR-040–CR-047, CR-051–CR-052) requires bank file import that can
never silently create incorrect Production transactions.

## Decision

- An upload is first previewed: headers, sample rows, a suggested column mapping
  for common Swedish and English bank exports, saved import profiles ranked by
  header overlap, and earlier imports of the identical file (SHA-256).
- Staging creates an import batch and one row per source row. Each row keeps the
  raw source values as evidence next to its interpretation (dates, signed
  amount, description, currency, reference). Amounts are parsed with `Decimal`;
  spreadsheet numbers are converted through their shortest decimal
  representation.
- Rows are `ready`, `duplicate`, `invalid`, `skipped` or `committed`. Invalid
  rows can be corrected and are revalidated. Duplicates require an explicit
  approval, which keeps the duplicate evidence.
- Duplicate detection has two independent signals: a row fingerprint (account,
  date, amount, currency, normalized description and occurrence order within
  the file) that recognises a re-imported export, and a match against existing
  active income/expense transactions on the same account within three days,
  with a visible confidence. Identical rows within one file are not flagged
  against each other.
- Commit turns all `ready` rows into ordinary income and expense transactions
  with `source_type = 'import'` through the same service as manual entry, in a
  single database transaction. Any invalid row aborts the whole commit and names
  the row.
- Undo previews the impact and, after the phrase `UNDO IMPORT`, archives exactly
  the transactions the batch created. It is refused while active refunds or
  reimbursements are linked to imported expenses.
- Import profiles store a mapping by header names. Rules (CR-049–CR-050) and
  splitting rows in staging (CR-048) are not part of this decision.

## Consequences

Large files are limited to 10 MB and 20 000 rows per upload. Staged batches keep
source evidence in the database until the data plane is reset.
