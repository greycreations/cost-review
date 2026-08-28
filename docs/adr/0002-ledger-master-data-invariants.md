# ADR 0002: Ledger account and master-data invariants

- Status: Accepted
- Date: 2026-08-28
- Product baseline: Product Specification v1.0

## Context

The first Ledger slice must establish accounts and reusable master data before
transactions exist. It must preserve the hard Production/Demo-Test boundary,
avoid temporary semantics that would later contaminate the economic ledger, and
leave later dependency-aware deletion, sharing allocation, and audit work
possible without rewriting history.

## Decision

- Ledger rows contain no environment discriminator. Production and Demo/Test
  store their rows in separate PostgreSQL services, roles, networks, and volumes.
- Account type is constrained to the eight Product Specification base types.
  Names remain user-defined. Opening balance and effective date are account
  attributes; creating an account never creates an income transaction.
- Master records use `active`/`archived` lifecycle state with explicit archive
  and restore operations. No master-record hard-delete endpoint is exposed in
  this slice.
- Category parentage supports arbitrary depth. The service rejects cycles and a
  PostgreSQL trigger independently prevents cycles from non-API writes. A
  category with active children cannot be archived implicitly.
- Provider aliases are normalized with Unicode NFKC, whitespace folding, and
  case folding. One normalized alias resolves to one canonical provider.
- Provider and category relationships use ordered identifier pairs with a
  unique constraint. Links express analytical relationships and never merge or
  rewrite either master record.
- Tags have a case-insensitive unique normalized name and can be archived and
  restored. A maximum of one active Sharing Party can represent the signed-in
  owner; parties remain metadata rather than application users.
- List contracts are paginated from their first release and archived records
  are opt-in.
- Demo/Test reset truncates all Ledger/master-data tables in the Test database
  and keeps the current Test session plus persistent environment identity. The
  Production API has neither that route nor network/database access to Test.

## Deliberate deferrals

- Tag merge is implemented with transaction/tag assignments so all references
  can move atomically; recording a merge before references exist would be a
  misleading no-op.
- Percentage `ShareAllocation` rows arrive with the first shareable Ledger
  objects. The Sharing Party register and its single-self invariant exist now.
- Recycle Bin, dependency-aware permanent deletion, frozen historical account
  identity, and audit events remain CR-022 and CR-023. Archive/restore in this
  slice is the safe lifecycle foundation, not a claim that those stories are
  complete.

## Consequences

The next Transaction/TransactionSplit migration can reference stable account,
category, provider, tag, and sharing-party identifiers. Production/Test
isolation tests can now prove separation with economic data, not only settings.
Later deletion and merge workflows must preserve these identifiers or create
the frozen/audited replacements required by Product Specification v1.0.
