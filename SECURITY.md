# Security Policy

AIDL is a pre-1.0 reference implementation. Security reports are welcome, especially when they affect the compiler/CLI package, generated code in the supported M4 slice, release-bundle integrity, or repository automation.

## Reporting a vulnerability

Do not publish vulnerability details in a normal GitHub issue, pull request, discussion, commit message, or other public channel.

Use GitHub's repository-scoped private vulnerability reporting flow when the repository's **Security** area exposes **Report a vulnerability**. That route keeps the initial report private to repository maintainers.

This repository does not currently document a dedicated security email address or external reporting service. Do not infer or invent one. If GitHub does not present a private vulnerability-reporting control to you, create only a minimal non-sensitive issue asking the repository owner for a private reporting route; do not include exploit details, proof-of-concept code, affected secrets, or other sensitive material in that issue.

A useful private report includes:

- affected commit, package/version, or artifact identity;
- impacted component and expected security boundary;
- reproduction steps or a minimal proof of concept;
- impact and prerequisites;
- known mitigations or workarounds, if any.

Never include real credentials, private keys, tokens, or unrelated personal data.

## Scope and support expectations

The current support boundary is documented in `SUPPORT.md` and `docs/12-coverage-and-limits.md`. A specified AIDL profile is not automatically an implemented or production-supported runtime surface.

The current M9-05 release workflow is a reproducible, read-only bundle dry run with publication disabled. Its checksums and manifest provide integrity evidence for the generated bundle; they are not digital signatures, attestations, an SBOM, or a provenance service. See `docs/artifact-provenance.md`.

## Disclosure

Please allow maintainers time to reproduce and assess a report before public disclosure. Fixes should follow the normal repository validation and review path. This policy does not promise a specific response or remediation SLA.
