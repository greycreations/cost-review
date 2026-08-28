# ADR 0001: Production and Demo/Test data boundary

- **Status:** accepted
- **Date:** 2026-08-28
- **Decision owners:** Cost Review project

## Context

Product Specification v1.0 defines Production and Demo/Test as separate trust
domains. Test data must survive restarts and upgrades, support realistic future
imports and workflows, and be safely erasable without any possibility of
mutating production economic data. A row-level `is_test` flag does not provide
an adequate operational or testable boundary.

## Decision

Cost Review runs two data planes from the same immutable application images:

- `api-prod` connects only to `db-prod`;
- `api-test` connects only to `db-test`;
- each PostgreSQL service has a distinct role, password, database volume, and
  private Docker network;
- each API instance has a distinct environment setting, session namespace, and
  CSRF namespace;
- a persistent database identity records the environment kind and a generated
  data-plane identifier;
- startup fails if the configured environment disagrees with the persistent
  database identity;
- the gateway routes explicitly to one data plane while preserving the
  backend's versioned `/api/v1` contract;
- Demo/Test reset routes exist only in the Test API instance;
- future Production-to-Test configuration copy uses a selective, previewed API
  export/import flow. Neither data plane receives the other's database
  credentials.

Database, attachment, and backup volumes are separate per environment. The
frontend shows a persistent environment label, and Demo/Test is visually
distinct without relying only on color.

## Consequences

- Compose uses more services and memory than a shared-database design.
- Migrations and health checks run independently for both data planes.
- Setup and authentication state are independently persisted and session-scoped.
- Every destructive Demo/Test feature requires an isolation integration test.
- Operational mistakes such as mounting a Production database volume under the
  Test API are detected before the API serves traffic.
- The design favors safety and explainability over the smallest possible local
  deployment.

## Rejected alternatives

- **Single database with `is_test`:** one missing predicate could expose or
  delete production rows.
- **Separate schemas in one database:** credentials and failure domain remain
  shared.
- **Two databases in one PostgreSQL service:** improves logical separation but
  still shares the database service and storage volume.
- **One API holding both credentials:** a Test request or defect could still
  reach Production.
