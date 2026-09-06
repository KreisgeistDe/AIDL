# M1–M3 — Language, semantics, canonical IR, and CLI

## Milestone M1 — Language Core

Goal: parse AIDL projects into a stable semantic model and report useful diagnostics.

- [x] **P0** Define the supported AIDL core subset for the first implementation milestone. See [`docs/aidl-core-subset.md`](../docs/aidl-core-subset.md).
- [x] **P0** Implement/complete project-level parsing for `.aidl` files. *(Deterministic recursive `.aidl` discovery and project loading are implemented in `tools/aidl_parser.py` and `tools/compiler_project.py`.)*
- [x] **P0** Introduce an explicit AST independent of IntelliJ PSI. *(`tools/compiler_ast.py` projects parser nodes into compiler-owned typed documents/declarations and retains source nodes without depending on IntelliJ.)*
- [x] **P0** Implement module loading and fully qualified name resolution. *(`tools/compiler_project.py` builds module indexes and stable declaration FQNs.)*
- [x] **P0** Implement import and wildcard-import resolution. *(Exact and wildcard imports resolve deterministically through exported project declarations.)*
- [x] **P0** Detect cyclic module dependencies. *(Compiler project dependency SCCs are surfaced by `aidl check` as stable `AIDL-R004` diagnostics.)*
- [x] **P0** Build a symbol table for declarations and operation names. *(The compiler-owned symbol table provides deterministic FQN declaration and module-scoped operation lookup.)*
- [x] **P0** Add source locations to AST/symbol nodes for diagnostics. *(Parser spans are preserved through compiler documents/declarations and all M1 resolution diagnostics.)*
- [x] **P0** Define stable diagnostic codes and severity levels. *(M1 uses `AIDL-P001`, `AIDL-R001` through `AIDL-R004`, and explicit error/warning/info severities.)*
- [x] **P1** Add machine-readable diagnostics via `aidl check --format json`. *(The production CLI emits deterministic source-located diagnostic envelopes.)*
- [x] **P1** Add regression tests for parser, name resolution, contextual keywords, and diagnostics. *(Parser/project/diagnostic suites plus focused `aidl check` unresolved-name and cycle regressions cover the M1 boundary.)*

### M1 acceptance criteria

- [x] `aidl check examples/petstore` parses the project without crashing. *(The production check path is exercised by repository CI and the Petstore parser/compiler regression boundary.)*
- [x] Invalid imports, duplicate declarations, and unresolved names produce stable diagnostics with source locations. *(`AIDL-R001`, `AIDL-R002`, and `AIDL-R003`; module cycles use `AIDL-R004`.)*
- [x] Compiler/parser behavior is independent of the IntelliJ plugin. *(Compiler AST/project/resolution/diagnostic modules live under `tools/`; IntelliJ consumes compiler results instead of owning semantics.)*

## Milestone M2 — Semantic Core

Goal: statically enforce the architectural guarantees that make AIDL useful beyond syntax validation.

- [x] **P0** Validate exactly one owner service for every persisted entity.
- [x] **P0** Reject cross-service `ref` relationships.
- [x] **P0** Reject cross-service / cross-resource transactions.
- [x] **P0** Validate query side-effect freedom.
- [x] **P0** Validate required mutation clauses: `auth`, `allow`, `errors`, `idempotency`, and one root effect.
- [x] **P0** Validate public-write requirements and public-reason annotations where applicable.
- [x] **P0** Validate transaction resource ownership and declared isolation.
- [x] **P0** Validate transactional event publication through an outbox.
- [x] **P0** Validate at-least-once consumer idempotency requirements.
- [x] **P1** Validate API exposure/version/compatibility rules.
- [x] **P1** Validate bounded collection query contracts.
- [x] **P1** Add actionable diagnostics with suggested fixes for common violations.
- [x] **P1** Add negative fixtures for every semantic rule.

### M2 acceptance criteria

- [x] The compiler rejects representative invalid distributed-system designs.
- [x] Every semantic rule has at least one positive and one negative test fixture. *(Negative corpus added by M2-13; positive counterparts already exist in the rule-focused M2 tests.)*
- [x] Diagnostics are stable enough for IDE and CI consumption.

## Milestone M3 — Canonical IR and CLI

Goal: make the versioned JSON IR the stable boundary between language semantics and generators/adapters.

- [x] **P0** Define/finalize the canonical AIDL IR schema. *(M3-01 complete via PR #43.)*
- [x] **P0** Ensure deterministic IR output for identical semantic input. *(M3-02 complete via PR #44 for already semantic, schema-conformant IR structures.)*
- [x] **P0** Encode fully qualified names and stable declaration identifiers in the IR. *(M3-03 complete via PR #45 with explicit declaration major input.)*
- [x] **P0** Materialize semantic defaults in the IR instead of leaving them implicit. *(M3-04 complete.)*
- [x] **P0** Remove source-syntax-only details from canonical IR where they are not semantically relevant. *(M3-05 complete.)*
- [x] **P0** Add an IR version field and compatibility rules. *(M3-06 complete.)*
- [x] **P1** Add a deterministic semantic hash / fingerprint. *(M3-07 complete.)*
- [x] **P0** Implement `aidl ir`. *(M3-08 complete; source-to-canonical-IR producer and CLI are documented in `docs/aidl-ir-cli.md`.)*
- [x] **P0** Implement `aidl plan`. *(M3-09 complete; deterministic canonical-IR-only planning and CLI are documented in `docs/aidl-plan-cli.md`.)*
- [x] **P0** Implement `aidl check` with human-readable output. *(M3-10 complete; production compiler-diagnostic CLI is documented in `docs/aidl-check-cli.md`.)*
- [x] **P1** Implement JSON output for all agent/CI-relevant CLI commands. *(M3-11 complete; shared deterministic `--format json` envelopes for `check`, `ir`, and `plan` are documented in `docs/aidl-json-cli.md`.)*
- [x] **P1** Define exit-code conventions for success, validation failure, and internal errors. *(M3-12 complete; `0` success, `1` expected validation/build failure, and `70` unexpected internal failure are documented in `docs/aidl-exit-codes.md`.)*

### M3 acceptance criteria

- [x] Two runs over the same project produce byte-for-byte equivalent canonical IR after normalization. *(Covered by M3-08 focused source-to-IR tests on supported Core input.)*
- [x] Generators can operate solely on IR without reparsing source files. *(M4-02 adds the first canonical-IR-only TypeScript domain generator and explicitly excludes parser/compiler source inputs.)*
- [x] `aidl check --format json`, `aidl ir`, and `aidl plan` are usable from scripts and coding agents. *(M3-11 adds shared machine-readable success/failure envelopes while preserving existing native contracts.)*
