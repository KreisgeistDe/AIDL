# M7-02/M7-03/M7-05 — `aidl diff` CLI contract

M7-02 exposes the M7-01 Canonical-IR semantic diff facts through the production AIDL CLI. M7-03/M7-04 add parallel compatibility classification over those same facts. M7-05 adds parallel migration guidance derived from the authoritative facts and classifications. The CLI remains an adapter only; it defines neither a second diff model nor compatibility or migration semantics.

## Command

```text
aidl diff --old <old-path> [<old-path> ...] --new <new-path> [<new-path> ...] [--format human|json]
```

Each side accepts the same AIDL file/directory inputs used by the existing compiler commands.

## Semantic pipeline

For each side independently, `aidl diff`:

1. calls the existing `load_compiler_analysis()` boundary,
2. rejects compiler errors as an expected side-specific input failure,
3. calls the existing `build_canonical_ir()` boundary,
4. passes the two resulting Canonical IR documents unchanged to `diff_canonical_ir()`,
5. preserves the returned M7-01 facts through `semantic_ir_diff_to_json()`,
6. passes those authoritative facts plus the same old/new Canonical IR states to `classify_ir_diff()`, and
7. passes the same authoritative facts, classifications, and old/new Canonical IR states to `build_ir_migration_guidance()`.

The CLI does not inspect AIDL syntax to infer changes and does not duplicate M7-01 unordered-array/stable-identity rules, M7-03/04 compatibility policy, or M7-05 rollout sequencing. Each layer reuses the previous authoritative boundary.

## JSON output

`--format json` uses the established deterministic CLI envelope:

```json
{"command":"diff","diagnostics":[],"ok":true,"result":{"changes":[],"classifications":[],"guidance":[]}}
```

`result.changes` is exactly the M7-01 fact list. Every item has `kind`, `path`, `oldValue`, and `newValue`.

`result.classifications` is a same-order parallel list with the same `kind`/`path`, exactly one of `safe|conditional|migration-required|breaking`, a stable rule ID, and deterministic reason text.

`result.guidance` is a same-order parallel list. Every item repeats only fact/classification identity and adds:

- `classificationRule`,
- ordered `phases` using only `expand`, `deployReaders`, `backfill`, `switchWrites`, `verify`, and `contract`,
- explicit `preconditions`, and
- a deterministic `note`.

A phase list may be empty. Safe changes need no migration sequence; conditional changes remain review/coordination-only; breaking changes deliberately receive no apparently safe automatic migration sequence.

## Human output

The default human format emits one deterministic line per M7-01 fact and appends the parallel metadata:

```text
<kind> <path> old=<compact-json> new=<compact-json> classification=<class> rule=<rule-id> reason=<json-string> guidance=<compact-json>
```

The compact JSON values are sorted deterministically. No semantic changes produces no human stdout.

## Compatibility and migration ownership

M7-03/M7-04 use exactly four runtime classes: `safe`, `conditional`, `migration-required`, and `breaking`; unknown/unrepresented semantics remain `conditional` rather than being guessed safe. The compatibility model is documented in `docs/m7-compatibility-classification.md` and `docs/m7-compatibility-surfaces.md`.

M7-05 migration guidance is documented in `docs/m7-migration-guidance.md`. It does not add a fifth class, reclassify facts, generate SQL/upcasters/backfill transforms, or execute migrations. Missing implementation evidence remains an explicit precondition or review requirement.

## Exit codes and failures

- `0`: both projects compiled to Canonical IR and the semantic diff/classification/guidance pipeline completed, whether the change list is empty or non-empty.
- `1`: expected compiler, IR-build, or semantic-diff input failure.
- `70`: unexpected internal failure.

Expected failures are side-specific whenever the failing input is attributable to `old` or `new`.

- Compiler failures retain the existing compiler diagnostic payloads in JSON and identify the failing side in `error.side`; human diagnostics are prefixed with `aidl diff old:` or `aidl diff new:`.
- `IrBuildError` is reported as `error.kind = "irBuild"` plus `error.side`.
- `IrDiffError` is reported as `error.kind = "diffInput"`; the M7-01 `old:`/`new:` context is projected into `error.side` rather than interpreted semantically.
- Unexpected exceptions, including impossible fact/classification/guidance authority mismatches in the production path, retain the existing `internal` envelope/error behavior and exit `70`.

## Explicit exclusions

M7-05 does not add new compatibility rules, executable migrations, migration application, compatibility CI/pull-request enforcement, or M8 inspect/dependencies/explain tooling.

`aidl diff` remains the stable CLI projection surface for M7-01 raw semantic facts, M7-03/04 classifications, and M7-05 migration guidance.
