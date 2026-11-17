# ADR 0019: Household roles, personal My Share and attributed changes

**Status:** Accepted
**Date:** 2026-11-16
**Supersedes:** the role and registration parts of ADR 0015

## Context

ADR 0015 made the Ledger shared household data and gave every account full
read and write access, including backup creation, download and upload. With
self-registration enabled by default, anyone who could reach an installation
could join and read or change the whole household economy. "My Share" depended
on one global `is_self` sharing party, so it could only be correct for one
member, and audit events did not record who made a change.

## Decision

- A data plane is one household with one shared Ledger. Access is governed by a
  role per account:
  - **owner**: everything a member can do, plus member administration, backups,
    validation, download and upload, and the Demo/Test reset;
  - **member**: reads and changes the Ledger, budgets, imports and recurring
    items;
  - **viewer**: reads everything, changes only their own password, settings and
    personal investment plan.
- The migration turns administrators into owners and other accounts into
  members. A household always keeps at least one owner.
- `ALLOW_SELF_REGISTRATION` is `false` by default. When enabled, registration
  creates members, never owners.
- A sharing party may be linked to one household member (`sharing_parties.user_id`,
  unique among active parties). "My Share" for a request is the portion
  allocated to the party linked to the requesting member. A member without a
  linked party owns no share of allocated splits; splits without allocations
  belong fully to every perspective, as before. The former `is_self` party is
  linked to the oldest owner during migration.
- The Total / My Share rules live in one module (`app/sharing.py`) used by
  summaries, analysis and budgets.
- Every audit event records `actor_user_id`, taken from the authenticated
  session of the request.
- Sign-in has a per-account lockout: five consecutive failures lock the account
  for 15 minutes (HTTP 429). An unknown username still costs one Argon2
  verification. The gateway additionally rate-limits sign-in, registration and
  setup per client address.

## Consequences

Upgrading installations keep their data. An installation that relied on open
registration must enable it explicitly. A temporary lockout can be triggered by
someone who knows a username; this is accepted for a household application
because it expires on its own and protects against password guessing behind a
shared tunnel address, where per-address limits cannot distinguish users.
