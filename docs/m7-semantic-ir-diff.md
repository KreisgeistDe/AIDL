# M7-01 Semantic Canonical IR Diff

M7-01 introduces a compiler/IR-owned structural diff boundary for two already-built Canonical IR states. It deliberately does **not** add `aidl diff`, compatibility classification, or migration advice.

## API

`tools.ir_diff.diff_canonical_ir(old_document, new_document)` accepts two Canonical IR mappings and returns an ordered list of `IrDiffChange` values.

Each change contains:

- `kind`: `added`, `removed`, or `changed`;
- `path`: a deterministic canonical semantic path;
- `oldValue`;
- `newValue`.

`semantic_ir_diff_to_json()` projects the same information into JSON-compatible dictionaries. M7-01 does not define a CLI envelope; that remains M7-02.

## Input contract

Both inputs must be valid current Canonical IR `0.3.0` documents under `spec/ir.schema.json`.

The diff boundary rejects rather than rewrites:

- malformed or missing `irVersion`;
- any Canonical IR version other than the current `0.3.0` schema contract;
- closed-schema violations or structurally invalid Core values.

Version/schema failures raise `IrDiffError` with deterministic input (`old`/`new`) and schema-path context. M7-01 does not negotiate, migrate, or normalize incompatible IR versions into a common shape.

## Semantic projection

The diff compares Canonical IR semantics, not source presentation.

Before comparison it removes:

- root/source traceability through `sourceMap`;
- root and nested derived `semanticHash` fields.

It then reuses `tools.ir_canonical_json.canonical_ir_json_text()` so the existing Canonical IR contract remains the only authority for semantically unordered arrays such as profiles, `errorIds`, `eventIds`, service ownership/use/exposure sets, transaction-isolation sets, and the other already-declared canonical set paths.

Consequently source formatting, source spans/files, declaration source-file order, derived hash bytes, and ordering of already-canonical semantic sets do not create a semantic diff.

## Stable identity and paths

IR arrays containing declaration-like objects with stable `declarationId`/`fqn` identity are matched by identity rather than list position. For the top-level `declarations` array the declaration `kind` is also included in the selector.

Examples:

- `/declarations/entity:example.Pet@1/fields/2/mutable`
- `/declarations/api:example.PublicApi@1/rateLimit/requests`
- `/system/resources/example.PrimaryDb@1/transactionIsolation/1`

This avoids positional remove/add noise when declaration/resource/service/deployment order changes. Arrays without an existing stable identity remain positional unless the existing Canonical JSON contract already marks them as semantic sets.

## Change semantics

M7-01 reports structure only:

- an added declaration or value has `kind: added`, `oldValue: null`, and the new semantic value;
- a removed declaration or value has `kind: removed`, its old semantic value, and `newValue: null`;
- a scalar/type/shape change has `kind: changed` with both values.

Changes are sorted deterministically by path and kind. Nested API, event, entity, system/resource, and persistence-relevant fields use the same recursive mechanism; there is no separate compatibility policy hidden in the diff engine.

## Explicit exclusions

M7-01 does not implement:

- `aidl diff` or any other new CLI command;
- `safe`, `conditional`, `migration-required`, or `breaking` classification;
- API/event/schema/client compatibility policy;
- expand/backfill/contract or other migration suggestions;
- M8 inspect/dependencies/explain or agent-tooling features.

Those are later M7/M8 roadmap items layered on top of this deterministic IR-owned fact model.
