# Changelog

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
