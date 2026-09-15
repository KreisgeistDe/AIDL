# M10.5-04 bounded Canonical-IR document/envelope slice

This package extends the integrated first Gate-04 domain-declaration projector to a complete, schema-shaped Canonical IR document for the same bounded enum/value/entity parity corpus.

The Kotlin common-core path composes the existing domain declaration projection with the shared `canonical-ir-envelope.source` fixture and owns only the already exercised minimal envelope facts: one app/profile/auth block, services that own bounded domain entities, one system, and one deployment with colocated services. Unsupported envelope facts fail closed instead of being defaulted or dropped. The existing `spec/ir.schema.json` remains unchanged.

Python remains the migration reference/conformance implementation and direct Core remains permanent semantic authority. The Python oracle builds the real full Canonical IR through the production compiler path, validates it against the unchanged schema, removes only `semanticHash` fields from the differential comparison surface, and pins the remaining complete document structure in `compiler/kotlin/parity/canonical-ir-document.signature`.

Semantic-hash computation is deliberately not migrated in this slice. Kotlin carries schema-valid zero-hash placeholders only so the bounded document has the complete versioned shape; those placeholders are excluded from differential equality. Semantic hashes, semantic queries, M10.5-05+, default-compiler cutover, Native operational parity, runtime/public support, and IDE/LSP migration remain outside this package.

Gate 04 remains incomplete after this slice. Fresh independent exact-head validation is required before integration.
