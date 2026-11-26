# Threat Model & Security Boundaries — CONSERVA

## Trust Boundaries
- **TB1 — Role & Tenant Authorization**: API routes enforce `X-Conserva-Role` (`ADMIN`, `AUDITOR`, `RISK_OWNER`, `VIEWER`) and `X-Conserva-Org` scoping. Non-ADMIN identities are blocked (`403`) from reading or mutating another tenant's assessments, evidence, or risk models.
- **TB2 — Evidence Integrity & Provenance**: Every evidence item stores a SHA-256 digest, owner, review status, and expiration date. Non-applicable SoA entries require explicit non-empty justification (`422` otherwise).
- **TB3 — Licensing & Copyright Boundary**: No copyrighted ISO normative text is copied or redistributed. Private standards can be loaded locally by authorized operators via `import_custom_controls()`.

## Residual Risks
- Demonstration authentication uses explicit RBAC headers for local/API testing; production deployments should terminate OIDC/JWT tokens (e.g., via LIMEN Keycloak gateway) upstream of CONSERVA.
