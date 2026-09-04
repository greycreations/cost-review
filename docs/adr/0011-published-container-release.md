# ADR 0011: Published container release for self-hosting

## Status

Accepted for Release 1 pilot deployment.

## Context

The development Compose project builds images from the repository and is useful
for CI and contributor workflows. It is not an appropriate installation path
for a household Ubuntu server: the operator should not need a Git checkout,
Node.js, Python, or build tooling, and a deployment must be pinned to a known
application version.

Production and Demo/Test must still remain separate trust domains after the
application is packaged. Persistent databases, attachments, backups, secrets,
credentials, networks, session-cookie namespaces, and API processes may not be
collapsed merely to simplify installation.

## Decision

- A semantic version tag (`vMAJOR.MINOR.PATCH`) publishes API and frontend
  images to GitHub Container Registry for `linux/amd64` and `linux/arm64`.
- Published images include OCI source metadata, provenance, and an SBOM.
- The tag workflow creates a GitHub release containing `compose.yaml`, an
  `.env.example` template, and SHA-256 checksums.
- The standalone Compose file pulls a fixed `COST_REVIEW_VERSION`. Operators
  upgrade by changing that value deliberately and pulling the new images.
- The standalone project preserves two PostgreSQL services, two API services,
  two scheduled backup services, separate credentials, internal data networks,
  volumes, encryption keys, and session namespaces.
- The gateway is the only service that publishes a host port. Database and API
  services remain private to their Compose networks.
- Release configuration is validated in CI. Source-built Compose remains the
  integration-test and contributor path; it is not the production artifact.

## Consequences

An Ubuntu operator can install Cost Review from two small release files and a
Docker Registry login when the package is private. The application can be
upgraded and rolled back without rebuilding it on the server, while database,
attachment, and backup volumes remain persistent.

Publishing a release now requires version alignment in the backend package,
frontend package, and deployment environment template. Image visibility and
registry access remain an explicit repository-owner decision. Secrets and real
financial data never enter release assets or source control.
