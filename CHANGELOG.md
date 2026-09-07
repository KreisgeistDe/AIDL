# Changelog

## 0.1.0rc1 — scoped toolchain pre-release

This release candidate is intentionally scoped to repository surfaces whose conformance status is `implemented`. It is a pre-1.0 toolchain release and does not promote broader language-profile maturity.

### Supported scope

- `tooling.cli`: installable Python 3.12 `aidl` CLI with its registered command surface and versioned JSON output contracts.
- `contract.canonical-ir`: deterministic Canonical IR for the implemented compiler subset at `irVersion` 0.3.0.
- `runtime.m4-petstore`: bounded TypeScript/Fastify/PostgreSQL Petstore vertical slice; this is not a general runtime.
- `release.bundle`: deterministic release bundle, tracked JSON contracts, manifest and SHA-256 integrity metadata.

### Explicit non-claims

No stability or production-completeness promise is made for `profile.cloud`, `profile.core`, `profile.distributed`, `profile.media`, `profile.offline`, `profile.realtime`, or `profile.web`; their conformance status remains `partial` or `specified`. `tooling.intellij` remains `partial`, `tooling.lsp` remains `experimental`, and native `main` protection remains administratively blocked/open.

The release also does not claim signatures, attestations, an SBOM, a transparency log, or general runtime support beyond the bounded surfaces above.

## 0.0.0 — unreleased toolchain baseline

### Added

- Generic-Werttypen, Generic-Views und Generic-Komponenten
- versionierte API-Surfaces mit explizitem Exposure und Rate Limits
- Unions, strukturierte Fehler und Effect Sets
- revision als standardisierter Concurrency-Token
- Service-, System-, Resource- und Deployment-Deklarationen
- Topics, Consumer, Projektionen und atomare Outbox-Semantik
- Sagas mit Kompensation
- Sync-Deklarationen für Offline- und Multi-Writer-Szenarien
- Medien-, Realtime- und Cloud-Profile
- Kompatibilitäts- und Expand/Backfill/Contract-Migrationen

### Changed

- mutation benötigt einen vollständigen Idempotenzvertrag, sobald Retries
  oder externe Aufrufer möglich sind.
- ref ist nur innerhalb derselben Ownership-Grenze zulässig.
- Event-Publikation nennt Topic und Delivery-Pfad explizit.
- Native Erweiterungen deklarieren neben Capabilities auch Effects,
  Retry-Sicherheit und Kostenbudget.

### Fixed

- Die Grammatik umfasst jetzt view, union, error, native, auth, a11y,
  Generic-Anwendungen, Inline-Records und alle Systemdeklarationen.
- Das Petstore verhindert parallele doppelte Reservierung eines Tiers.
- AdoptionRequested besitzt einen Consumer, der den Review-Workflow startet.
- Antragstellerdaten werden konsistent gespeichert; die lokale User-Entität
  wurde durch den OIDC-Subject-Vertrag ersetzt.
- Mutationen geben ihr Ergebnis explizit zurück.
- Ein abgelaufener Adoptionsreview gibt Tier und Anfrage transaktional frei.
