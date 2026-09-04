# ADR 0011: Published container release for self-hosting

## Status

Accepted for Release 1 pilot deployment.

## Context

The development Compose project builds images from the repository and is useful
for CI and contributor workflows. It is not an appropriate default installation
path for a household Ubuntu server: the operator should not need Node.js,
Python, or build tooling, and a deployment must be pinned to a known application
version.

Production and Demo/Test must still remain separate trust domains after the
application is packaged. Persistent databases, attachments, backups, secrets,
credentials, networks, session-cookie namespaces, and API processes may not be
collapsed merely to simplify installation.

## Decision

- A semantic version tag (`vMAJOR.MINOR.PATCH`) publishes API and frontend
  images to GitHub Container Registry for `linux/amd64` and `linux/arm64`.
- Published images include OCI source metadata, provenance, and an SBOM.
- The tag workflow creates a GitHub release containing `compose.yaml`, an
  environment template named `cost-review.env.example`, and SHA-256 checksums.
- The repository-root `compose.yaml` is the canonical operator entry point and
  pulls a fixed `COST_REVIEW_VERSION`. Operators upgrade by changing that value
  deliberately and pulling the new images.
- Source builds use the explicitly selected `compose.dev.yaml`; Docker Compose
  never selects it accidentally during an ordinary installation.
- `scripts/init-env.sh` creates `.env` with installation-unique database
  passwords and backup keys, derives trusted host/origin settings from one
  operator-supplied URL, and refuses to overwrite an existing configuration.
- The standalone project preserves two PostgreSQL services, two API services,
  two scheduled backup services, separate credentials, internal data networks,
  volumes, encryption keys, and session namespaces.
- The gateway is the only service that publishes a host port. Database and API
  services remain private to their Compose networks.
- Both Compose configurations are validated in CI. Source-built Compose remains
  the integration-test and contributor path; it is not the production artifact.

## Consequences

An Ubuntu operator can clone the repository, initialize `.env`, and use ordinary
Docker Compose commands without knowing which internal file to select. A
release-asset installation remains available without a Git checkout. The
application can be upgraded and rolled back without rebuilding it on the server,
while database, attachment, and backup volumes remain persistent.

Publishing a release now requires version alignment in the backend package,
frontend package, and deployment environment template. Image visibility and
registry access remain an explicit repository-owner decision. Secrets and real
financial data never enter release assets or source control.
