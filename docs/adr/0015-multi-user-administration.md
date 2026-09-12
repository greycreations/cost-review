# ADR 0015: Environment-scoped multi-user administration

**Status:** Accepted  
**Date:** 2026-09-12

## Context

Cost Review originally locked first-run setup after creating one local login. A household network
installation now needs personal accounts, self-service password changes and an administrator who
can manage other accounts without weakening the hard Production/Demo-Test boundary.

## Decision

- The first account in each data plane is an administrator. The migration promotes the oldest
  existing account, so an upgrade needs no manual database change.
- Self-registration creates regular accounts only and is controlled by
  `ALLOW_SELF_REGISTRATION`, enabled by default for the documented trusted-network deployment.
- Each user keeps independent locale settings, sessions, investment holdings and purchase-plan
  allocations. Household ledger data remains shared application data; login identities are not
  silently converted into economic Sharing Parties.
- Every authenticated user can change their own password after proving the current password. All
  of that user's other sessions are revoked while the session performing the change remains active.
- Administrator routes require both an authenticated administrator role and valid CSRF proof.
  Administrators can create and rename users, delegate administrator status, reset another user's
  password, and delete another account.
- A password reset revokes all sessions for the affected account. Deletion requires the exact
  phrase `DELETE <username>`, cannot target the active administrator, and cannot remove the final
  administrator. Material account actions are written to the audit trail without password data.
- Production and Demo/Test store users, roles, password hashes and sessions in their already
  separate PostgreSQL services.

## Consequences

Anyone who can reach an installation with self-registration enabled can create a regular account,
so operators exposing Cost Review beyond a trusted network should disable registration or enforce
access at the reverse proxy. Deleting an account also removes its personal settings, sessions and
investment planning data through database cascades; shared household ledger history remains.
