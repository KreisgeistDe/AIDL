# M8 — Stable CLI JSON schemas

M8-01 established a versioned JSON Schema contract for AIDL's machine-readable CLI surfaces without changing existing emitted payloads. Later M8 commands extend that contract only through explicit schema-version evolution.

## Schema identity and compatibility

The frozen v1 schema remains `spec/cli-output.schema.json`:

- `$id`: `https://aidl.example/spec/cli/1/cli-output.schema.json`
- schema artifact version: `1.0.0`
- JSON Schema dialect: Draft 2020-12

V1 covers the nine JSON-producing production commands that existed at M8-01 and deliberately uses a closed command set and closed top-level envelope.

M8-02 introduced `aidl inspect`, which v1 rejects by design. Its frozen schema is `spec/cli-output-v2.schema.json`:

- `$id`: `https://aidl.example/spec/cli/2/cli-output.schema.json`
- schema artifact version: `2.0.0`
- JSON Schema dialect: Draft 2020-12

V2 accepts every v1 envelope by reference and adds only the `inspect` envelope.

M8-03 introduced direct-only `aidl dependencies`; its frozen schema is `spec/cli-output-v3.schema.json`:

- `$id`: `https://aidl.example/spec/cli/3/cli-output.schema.json`
- schema artifact version: `3.0.0`
- JSON Schema dialect: Draft 2020-12

V3 accepts every v2 envelope by reference and adds only the direct `dependencies` envelope.

M8-04 introduced `aidl explain`; frozen v4 is `spec/cli-output-v4.schema.json` with `$id` `https://aidl.example/spec/cli/4/cli-output.schema.json`.

M8-05 introduced `aidl summary`; frozen v5 is `spec/cli-output-v5.schema.json` with `$id` `https://aidl.example/spec/cli/5/cli-output.schema.json`.

M8-06 introduced `aidl impact`; frozen v6 is `spec/cli-output-v6.schema.json` with `$id` `https://aidl.example/spec/cli/6/cli-output.schema.json`.

M8-08 extends the existing `aidl dependencies` result with bounded transitive reachability. The current schema is `spec/cli-output-v7.schema.json`:

- `$id`: `https://aidl.example/spec/cli/7/cli-output.schema.json`
- schema artifact version: `7.0.0`
- JSON Schema dialect: Draft 2020-12

V7 accepts the complete frozen v6 contract by reference and adds only the extended current `dependencies` envelope. Frozen v1-v6 schema files are unchanged.

The schema version belongs to the schema artifact rather than the emitted payload. Callers continue to receive the established `command`, `diagnostics`, `ok`, optional `result`, and optional `error` fields without mandatory envelope metadata.

## Covered CLI surfaces

V1 covers `check`, `ir`, `plan`, `diff`, `resolve`, `complete`, `document`, `usages`, and `rename` JSON output.

V2 additionally covers `aidl inspect <FQN> --format json`.

V3 additionally covers the original direct-only `aidl dependencies <FQN> --format json`.

V4 additionally covers `aidl explain <FQN> --format json`.

V5 additionally covers `aidl summary [PATH ...] --format json`.

V6 additionally covers `aidl impact <FQN> [PATH ...] --format json`.

V7 advances `aidl dependencies` without adding another command.

## Contract boundaries

Top-level CLI envelopes remain closed: unknown commands and unknown top-level fields are rejected. Diagnostics retain the existing stable compiler diagnostic shape. Existing command results remain governed by their frozen prior contracts.

The current v7 `dependencies` result preserves `dependencies` as the M8-03 direct relation and adds:

- `transitiveDependencies`: depth-two-or-greater reachability over the same direct Canonical-IR declaration-ID relation;
- `totals.directDependencies` and `totals.transitiveDependencies`: complete pre-bound counts;
- `truncated.directDependencies` and `truncated.transitiveDependencies`: explicit per-list truncation flags.

Direct and transitive identity lists are independently bounded to 128 items, deduplicated, and sorted by FQN, kind, and declaration ID. The target declaration is excluded even when a dependency cycle reaches it. No source scanning, repository heuristic, new language rule, or extra dependency edge is introduced.

The M8-02 `inspect` result remains a declaration-level compiler/Canonical-IR view. M8-04 explanation output remains bounded to 64 explanations. M8-05 summary output remains bounded to 64 modules, 128 declarations, and 128 module dependencies. M8-06 impact evidence remains independently bounded and conservative about generated-artifact ownership.

Failure envelopes and 0/1/70 exit conventions are unchanged.

## Validation

`tools/test_cli_output_schema.py` registers frozen v1-v6 resources, validates real current production output, verifies v7 identity, and confirms that frozen v6 rejects the extended dependencies payload. `tools/test_compiler_dependencies.py` covers direct-edge authority, transitive graph closure, cycles, deterministic sorting/deduplication, and explicit direct/transitive bounds. Existing `tools/test_aidl_exit_codes.py` continues to cover `aidl dependencies` success, validation failures, and internal-error exit 70 in both human and JSON modes.
