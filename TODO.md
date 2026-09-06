# AIDL Project Roadmap

This document tracks the next implementation steps required to turn AIDL from a broad language specification into a reliable end-to-end toolchain.

The guiding principle is to finish one deterministic vertical slice before expanding the language surface further.

## Priority legend

- **P0** — required for the first usable end-to-end AIDL workflow
- **P1** — required for a credible developer experience and CI usage
- **P2** — ecosystem and productivity improvements after the core is stable

## Milestone M1 — Language Core

Goal: parse AIDL projects into a stable semantic model and report useful diagnostics.

- [x] **P0** Define the supported AIDL core subset for the first implementation milestone. See [`docs/aidl-core-subset.md`](docs/aidl-core-subset.md).
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

## Milestone M4 — First End-to-End Vertical Slice

Goal: generate and run one real application from AIDL without manually repairing generated files.

Recommended first target: Petstore with a deliberately constrained stack such as TypeScript + REST + PostgreSQL.

- [x] **P0** Select and document the first supported generator/runtime stack. *(M4-01 selects TypeScript 5.9.x + Node.js 22.x LTS + Fastify 5.x + PostgreSQL 17.x/pg 8.x, documented in `docs/m4-generator-runtime-stack.md` with machine contract `spec/m4-stack.json`.)*
- [x] **P0** Generate domain types/entities from IR. *(M4-02 adds deterministic canonical-IR-only TypeScript domain generation in `tools/generate_typescript_domain.py`, documented in `docs/m4-typescript-domain-generator.md`.)*
- [x] **P0** Generate API contracts/routes from `api`, `query`, and `mutation` declarations. *(M4-03 adds deterministic canonical-IR-only Fastify REST contract/route generation in `tools/generate_fastify_api.py`, documented in `docs/m4-fastify-api-generator.md`.)*
- [x] **P0** Generate persistence schema/migrations for the supported entity subset. *(M4-04 adds deterministic canonical-IR-only PostgreSQL schema and initial SQL migration generation in `tools/generate_postgres_persistence.py`, documented in `docs/m4-postgres-persistence-generator.md`.)*
- [x] **P0** Generate transaction boundaries and optimistic-concurrency behavior. *(M4-05 adds deterministic canonical-IR-only PostgreSQL transaction execution and atomic revision compare-and-set generation in `tools/generate_postgres_transactions.py`, documented in `docs/m4-postgres-transaction-generator.md`.)*
- [x] **P0** Generate idempotency plumbing for supported mutations. *(M4-06 adds deterministic canonical-IR-only PostgreSQL idempotency plans/runtime and an idempotency-store migration in `tools/generate_postgres_idempotency.py`, documented in `docs/m4-postgres-idempotency-generator.md`.)*
- [x] **P1** Generate outbox/event integration for the supported subset. *(M4-07 adds deterministic canonical-IR-only PostgreSQL transactional outbox plans/runtime, `0003_outbox.sql`, and atomic publish integration in `tools/generate_postgres_transactions.py`, documented in `docs/m4-postgres-outbox-generator.md`.)*
- [x] **P1** Add generated-code ownership markers and prohibit manual repair as part of the normal workflow. *(M4-08 adds a deterministic checksum-bearing AIDL ownership marker and safe full-set generation/write path in `tools/generate_m4.py` and `tools/generated_ownership.py`, documented in `docs/m4-generated-ownership.md`.)*
- [x] **P0** Add a reproducible build/test/run path for the generated Petstore application. *(M4-09 complete via PR #67: clean-checkout check/plan/canonical IR, normal M4 bundle generation, lockfile-backed `npm ci`, strict NodeNext/ESM build, Node tests and PostgreSQL 17 migration/startup smoke are CI-validated without manual generated-code repair.)*
- [x] **P0** Add an end-to-end test that starts from AIDL and validates generated application behavior. *(M4-10 complete: the production Petstore path generates/builds/applies PostgreSQL migrations and proves generated `POST /createPet` response/entity persistence with initial revision, completed idempotency, exactly one expected outbox event, and duplicate-free identical retry.)*

### M4 acceptance criteria

- [x] A clean checkout can run `aidl check`, `aidl plan`, and generation for Petstore. *(M4-09 CI validates the production CLI path and normal M4 bundle.)*
- [x] Generated code builds and tests successfully without hand editing. *(M4-09 CI validates strict NodeNext/ESM build, Node tests and PostgreSQL startup smoke after normal owned generation.)*
- [x] A small AIDL change produces a deterministic, explainable generated diff. *(M4-09 focused tests validate deterministic bundle output while M4-08 ownership/checksum tests preserve deterministic generated-file contracts.)*

## Milestone M5 — Golden Fixtures and CI

Goal: make language/toolchain behavior safe to evolve.

- [x] **P0** Create `fixtures/valid/` and `fixtures/invalid/` suites. *(M5-01 adds a versioned manifest, representative standalone valid/invalid projects, and a deterministic compiler-diagnostics harness while preserving the separate M2 semantic fixture corpus.)*
- [x] **P0** Snapshot diagnostics, canonical IR, plans, and generated output where appropriate. *(M5-02 upgrades the manifest to explicit snapshot kinds/paths, commits byte-exact production diagnostics for every case, and adds one minimal supported M4 case with canonical IR, plan, and complete per-file generated snapshots guarded by strict deterministic validation.)*
- [x] **P0** Cover Petstore as the primary golden-path fixture. *(M5-03 registers the existing supported M4 Petstore path in the version-2 manifest with byte-exact diagnostics, canonical IR, plan, and complete per-file generated snapshots, while keeping corpus enumeration manifest-driven.)*
- [x] **P1** Cover Calendar Offline for sync/conflict semantics. *(M5-04 adds a valid diagnostics Golden Fixture for the existing compiler-supported server-validated sync core, including operation-log revisions, tombstones, and declared LWW/add-wins/server-wins/manual conflict strategies; unsupported showcase API/UI boundaries are not worked around or snapshotted.)*
- [x] **P1** Cover VideoHub for distributed/media/deployment semantics. *(M5-05 adds a standalone valid diagnostics Golden Fixture for existing separated Catalog/Media ownership, resumable/versioned/encrypted blob storage, rendition/CDN delivery, service topology, and local/global deployments without widening language, IR, generator, media, deployment, or runtime semantics.)*
- [x] **P1** Add compatibility tests for IR/schema evolution. *(M5-06 adds a deterministic reviewable compatibility matrix for the existing IR-version capability boundary and closed Canonical-IR schema, covering minor/patch compatibility, major rejection, explicit additive-field tolerance, independent profile majors, and unknown/structurally incompatible Core-field rejection without adding evolution semantics.)*
- [x] **P1** Add CI jobs for compiler tests, golden fixtures, and IntelliJ plugin checks. *(M5-07 splits CI into independently visible Compiler/Python, Golden Fixtures, Petstore Runtime/PostgreSQL, and IntelliJ Plugin gates while preserving existing regression boundaries.)*
- [x] **P1** Run `./gradlew check` and plugin build in CI. *(M5-07 runs the plugin-local Gradle wrapper with `check` and `buildPlugin` under a reproducible Java 17/Gradle-cache setup.)*

## Milestone M6 — IDE Integration

Goal: expose compiler semantics directly in the editor rather than duplicating language logic in IntelliJ.

- [x] **P1** Make compiler diagnostics consumable by the IntelliJ plugin. *(M6-01 adds a testable plugin-side adapter/data-model boundary over `aidl check --format json`, preserving compiler-owned codes, phases, severities and source locations while separating compiler, process and JSON failures without adding inspections or PSI-local semantics.)*
- [x] **P1** Surface semantic diagnostics as inspections. *(M6-02 registers a compiler-backed AIDL local inspection that filters authoritative compiler diagnostics to the current file, maps severity and source positions to editor problems, preserves diagnostic code/message, and suppresses infrastructure failures without adding PSI-local semantics.)*
- [x] **P1** Add quick fixes for common missing/invalid clauses. *(M6-03 offers IntelliJ Quick Fixes only from compiler-owned `allowedFixes` metadata, currently supporting safely mappable `insertClause` edits with compiler-provided text unchanged while rejecting unknown/unsafe fixes without duplicating language semantics.)*
- [x] **P1** Improve Go to Definition using compiler symbol resolution. *(M6-04 adds a compiler-owned `aidl resolve` source-offset boundary backed by the existing symbol/import tables; IntelliJ accepts only unique compiler-returned file/source targets and no longer uses PSI-local declaration/import matching as semantic resolution.)*
- [x] **P1** Add Find Usages and safe Rename support. *(M6-05 adds compiler-owned project usage discovery and conservative declaration rename with compiler-planned declaration/reference edits, collision/name validation, copied-project preflight, all-file apply/rollback and final compiler revalidation; IntelliJ only maps compiler usages/results back to PSI.)*
- [x] **P1** Add completion based on semantic context. *(M6-06 adds compiler-owned file+offset completion that reuses the existing declaration symbol table and exact/wildcard import resolutions for local/imported/qualified visibility, omits ambiguous or lexically unsafe candidates, and lets IntelliJ render only compiler-returned lookup items.)*
- [x] **P2** Add hover/quick documentation for declarations and diagnostics. *(M6-07 adds compiler-owned `aidl document` file+offset documentation for declarations/references plus unchanged compiler diagnostic metadata; IntelliJ Quick Documentation/Hover only renders compiler-returned FQN/kind/source/representation and diagnostic fields without PSI/Kotlin semantic fallback.)*
- [x] **P2** Evaluate an LSP layer so VS Code, Zed, Neovim, and other editors can reuse the same semantic core. *(M6-08 adds a minimal saved-file stdio LSP proof for compiler diagnostics and Go to Definition, with only URI/UTF-16/JSON-RPC adaptation; the evaluation recommends a future thin production LSP after compiler snapshot/in-memory analysis is available for authoritative unsaved buffers.)*

## Milestone M7 — Evolution and Compatibility

Goal: make architecture/API/schema evolution a first-class AIDL workflow.

- [x] **P1** Implement semantic project diffing at the IR level. *(M7-01 adds `tools/ir_diff.py`: exact-current-schema Canonical IR validation, sourceMap/semanticHash exclusion, reuse of existing canonical set normalization, stable identity matching, and deterministic added/removed/changed semantic paths with old/new values; no CLI or compatibility classification.)*
- [x] **P1** Implement `aidl diff`. *(M7-02 adds a thin production CLI over the M7-01 fact boundary: old/new sources compile independently through existing compiler analysis plus `build_canonical_ir()`, JSON/human output project the same deterministic facts, semantic differences remain exit 0, and expected compiler/IR/diff input failures are side-specific exit 1 while internal failures remain 70.)*
- [x] **P1** Classify changes as safe, conditional, migration-required, or breaking. *(M7-03 adds `tools/ir_compatibility.py` as a compatibility-owned classifier over authoritative M7-01 facts and validated old/new Canonical IR. It uses exactly the four runtime classes with stable rule IDs/reasons, preserves raw `aidl diff` facts, and conservatively maps unknown paths to `conditional` rather than `safe`.)*
- [x] **P1** Cover API, event, persisted-schema, and client compatibility. *(M7-04 expands the same compatibility-owned classifier across Canonical-IR-carried public API/client contracts, immutable event/topic evolution and persisted entity/schema changes, with deterministic strictest-rule precedence, conservative handling of sync/profile semantics not materialized by Core IR, and no change to raw diff facts or CLI exit behavior.)*
- [x] **P2** Produce suggested expand/backfill/contract migration steps. *(M7-05 adds `tools/ir_migration_guidance.py` as a migration-owned layer over authoritative facts/classifications and old/new Canonical IR. It emits only evidence-backed ordered rollout phases, keeps safe/conditional/breaking cases conservative, makes missing backfill/remediation evidence explicit, and lets `aidl diff` project same-order guidance without changing facts, classifications, or exit semantics.)*
- [x] **P2** Integrate compatibility checks into CI/pull requests. *(M7-06 adds a CI-only policy over authoritative `aidl diff` changes/classifications/guidance, maps existing classes conservatively to pass/review/fail, compares actual PR base/head or previous/current main push states, publishes unchanged M7 projections plus decision metadata, and keeps targets/rules out of workflow glue.)*

## Milestone M8 — Agent-First Tooling

Goal: make AIDL efficient and reliable for coding agents without requiring them to scan entire repositories.

- [x] **P1** Provide stable JSON schemas for CLI output. *(M8-01 adds the versioned Draft 2020-12 contract `spec/cli-output.schema.json` for every existing JSON-producing CLI command, validates current success/failure/result shapes in CI, reuses the Canonical IR schema, and preserves existing JSON bytes by versioning the schema artifact rather than changing the envelope.)*
- [x] **P1** Implement `aidl inspect <FQN>` for declaration-level semantic inspection. *(M8-02 resolves exact compiler-owned FQNs, returns compact source identity plus the matching Canonical-IR node in deterministic human/JSON output, defines invalid/unknown/ambiguous/compiler/build failures with stable exit behavior, and advances the current closed CLI schema to v2 without mutating the frozen v1 contract.)*
- [x] **P1** Implement `aidl dependencies <FQN>`. *(M8-03 resolves exact compiler-owned FQNs, derives only direct references already materialized as known Canonical-IR declaration IDs, returns deterministic compact human/JSON identities with explicit failure/exit behavior, and advances the current closed CLI schema to v3 without mutating frozen v1/v2 contracts.)*
- [x] **P1** Implement `aidl explain <FQN>` / diagnostic explanation output. *(M8-04 resolves exact compiler-owned FQNs and projects only existing compiler diagnostic rule/evidence/allowed-fix metadata for that declaration, with deterministic bounded human/JSON output and closed CLI schema v4 while preserving frozen v1-v3 contracts.)*
- [x] **P2** Add compact project summaries for agent context. *(M8-05 adds `aidl summary` as a compiler-project projection of aggregate/module/declaration/import-dependency facts, deterministically bounded to 64 modules, 128 declarations, and 128 module dependencies with explicit totals/truncation metadata, compact human/JSON output, and closed CLI schema v5 while preserving frozen v1-v4 contracts.)*
- [x] **P2** Add change-impact analysis for a declaration or operation. *(M8-06 adds `aidl impact <FQN>` as a bounded compiler/Canonical-IR projection of direct reverse declaration references, materialized public API/topic contract surfaces, impacted entity state, and relevant existing `aidl diff` comparison surfaces; missing per-declaration generated-artifact ownership is reported explicitly as unknown instead of inferred, and the closed CLI schema advances to v6 without mutating v1-v5.)*
- [x] **P2** Document the recommended coding-agent workflow around `check`, `plan`, `inspect`, and tests. *(M8-07 documents the executable compiler-first workflow in `docs/m8-coding-agent-workflow.md` and protects it with `tools/test_m8_agent_workflow.py`, which exercises check/plan/inspect before and after a supported isolated fixture change.)*

### M8 acceptance criteria

- [x] A coding agent can discover the project, inspect one declaration, and retrieve its direct and transitive dependencies through bounded deterministic JSON output. *(M8-08 extends the compiler-authoritative M8-03 declaration-ID relation with cycle-safe transitive reachability, independently bounds direct/transitive JSON identities to 128 with full totals/truncation metadata, and advances the closed CLI contract to v7 without changing frozen v1-v6 schemas.)*
- [x] Diagnostic explanations identify the violated rule, relevant semantic evidence, and only compiler-authorized remediation options without requiring a repository-wide source scan. *(M8-04 projects only existing compiler diagnostic metadata for the exact declaration and bounds output to 64 explanations with explicit truncation metadata.)*
- [x] Change-impact output identifies affected declarations, public contracts, persisted state, generated artifacts, and compatibility checks from compiler-owned semantics. *(M8-06 reports direct Canonical-IR impact evidence, explicit public/persisted surfaces, relevant existing `aidl diff` checks, and marks generated-artifact ownership as unknown when no compiler-owned mapping is materialized rather than inventing one.)*
- [x] The documented agent workflow uses only implemented commands and is covered by an end-to-end regression fixture. *(M8-07 runs the documented check/plan/inspect loop against an isolated copy of `fixtures/valid/m4-minimal` in CI and verifies its documented command/test spellings remain available.)*

## Milestone M9 — Release and Quality Baseline

Goal: turn the repository toolchain into a reproducible, installable, and protected pre-release baseline before expanding runtime scope.

- [x] **P1** Make CI test selection complete and drift-proof through deterministic discovery or a validated test manifest. *(M9-01 discovers committed `tools/test_*.py` modules through `git ls-files`, runs every matching test by default, and permits only versioned specialized-job exclusions whose path, owner job, command, and rationale are validated.)*
- [x] **P1** Run every compiler-owned resolution, completion, documentation, refactoring, and CLI regression as a required CI gate. *(M9-02 adds a versioned compiler/CLI regression inventory plus AST-based certification against the M9-01 selector; `Compiler / Python` now rejects missing, excluded, stale, drifted, or unpaired critical regressions before running the full discovered suite.)*
- [x] **P1** Reconcile README, coverage, agent-tooling, schema identifiers, registry versioning, and implemented-command documentation with the actual repository state. *(M9-03 aligns README, agent-tooling, coverage, and the M8 workflow with the registered CLI and proven compiler/IR/M4 surfaces; documents IR 0.3.0, CLI schema v7, and profile registry 0.3.0 as separate version domains; and adds a CI regression tying command tables/help plus schema/registry identities to repository truth.)*
- [x] **P1** Package the AIDL CLI/compiler as an installable artifact with pinned runtime dependencies and a clean-machine smoke test. *(M9-04 adds a PEP-517/setuptools wheel with the existing `aidl` console entry point, Python 3.12 support, exact runtime/build pins, packaged `spec/*.json` contracts, focused packaging regressions, and an isolated fresh-venv smoke that proves installed help/check/diff/error behavior without repository import paths.)*
- [x] **P1** Add a reproducible release workflow for CLI artifacts, JSON schemas, checksums, and release notes. *(M9-05 adds a versioned tag/version contract, deterministic same-commit double-build certification, complete tracked `spec/*.json` contract bundling, machine-readable release manifest, SHA-256 component/archive checksums, committed changelog-derived notes, and a read-only Actions dry run with publication disabled.)*
- [ ] **P1** Protect `main` with required validation, compatibility, fixture, runtime, IntelliJ, and `.ai/**` boundary checks.
- [x] **P2** Add contribution, security-reporting, support-status, and artifact provenance documentation. *(M9-07 adds repository-level contribution and security policies, an evidence-bounded support matrix, and provenance/integrity documentation tied exactly to the M9-05 deterministic bundle, manifest, checksums, source commit and dry-run workflow without claiming publication, signatures, SBOMs, attestations, or branch protection.)*
- [ ] **P1** Publish the first explicitly scoped toolchain pre-release without implying stability for unsupported language profiles.

### M9 acceptance criteria

- [ ] A clean environment can install the released CLI and run `aidl check`, `aidl ir`, `aidl plan`, `aidl diff`, and the completed M8 commands.
- [x] Every committed Python test module is either executed by CI or rejected by a validation rule with an explicit reason. *(M9-01 routes every discovered committed `tools/test_*.py` module to Compiler / Python by default; the only exclusions are versioned entries for the existing Golden Fixtures and Petstore Runtime jobs, and stale or malformed exclusions fail validation.)*
- [ ] Direct changes cannot reach `main` without all required gates.
- [ ] Release artifacts are reproducible from the tagged commit and carry stable versions, checksums, and machine-readable contracts.

## Milestone M10 — Core Conformance Closure

Goal: make support claims mechanically traceable across specification, compiler, IR, generators, fixtures, and editors.

- [x] **P1** Replace the illustrative implementation-policy row with a machine-readable feature/conformance manifest. *(M10-01 adds versioned `spec/conformance-manifest.json` plus its Draft 2020-12 schema, stable surface IDs/statuses/evidence, registry-ID and support-document drift validation, and focused negative regressions without claiming M10-02 per-layer completeness.)*
- [x] **P1** Track every Core declaration and semantic rule across Parse, Resolve, Validate, IR, Generate, and IDE layers. *(M10-02 adds the versioned `spec/core-conformance.json` matrix covering 17 Core declarations and 18 semantic rules across exactly six required layers.)*
- [x] **P1** Complete compiler-owned type checking for the declared Core Supported surface, including type constructors, operation signatures, error contracts, and public serialization. *(M10-03 adds compiler-owned Core type validation with stable `AIDL-T001` through `AIDL-T004` diagnostics for constructors, query/mutation signatures and the sole implicit `int -> decimal` default conversion, exported error contracts, and public serialization. `spec/core-conformance.json` records dedicated executable `validate-types` evidence only on the affected Validate rows; unresolved or unmaterialized nominal rejection remains M10-04.)*
- [x] **P1** Reject every unsupported or unmaterialized semantic construct explicitly instead of accepting and silently dropping it. *(M10-04 adds compiler-owned `AIDL-T005` rejection for resolved Core type facts that current Canonical IR cannot materialize, including unsupported nominal declaration kinds, invalid entity identity targets, generic project type semantics, and undeclared non-standard error names; legacy M2 fixtures use explicit/Core-standard errors so their existing policy diagnostics, ordering, and source locations remain stable.)*
- [x] **P1** Add positive, negative, IR, and compatibility fixtures for every Core Supported feature. *(M10-05 adds versioned `spec/core-fixture-conformance.json` plus its schema, derives the exact Core Supported set from Parse/Resolve/Validate/IR status, binds positive/negative/Canonical-IR/compatibility evidence, and makes missing, stale, or incorrectly promoted coverage fail deterministically in CI without widening language semantics.)*
- [x] **P1** Generate documentation coverage tables from the conformance manifest so status pages cannot drift independently. *(M10-06 adds deterministic generated blocks for `SUPPORT.md` and `docs/12-coverage-and-limits.md`, derives them from the repository manifest and versioned Core conformance contracts, and adds write/check commands plus focused regressions so manual or stale coverage fails CI.)*
- [x] **P2** Add performance baselines and deterministic resource limits for representative small, medium, and large projects. *(M10-07 adds a versioned deterministic compiler-structure workload contract, reproducible small/medium/large synthetic Core projects, exact source/declaration/symbol/import baselines, bounded resource envelopes, focused drift/limit regressions, and an explicit Compiler / Python CI gate without relying on wall-clock thresholds.)*

### M10 acceptance criteria

- [ ] Every Core support claim links to executable evidence at each required implementation layer.
- [ ] All three reference applications either pass full Core type checking or report stable diagnostics for profile capabilities not yet implemented.
- [ ] Canonical IR contains every accepted semantic fact required by downstream tools; no supported source construct is silently discarded.
- [x] Conformance and performance baselines are deterministic and enforced in CI. *(Conformance manifest/core-fixture checks and the M10-07 deterministic performance baseline gate run in repository CI; timing SLAs remain explicitly out of scope.)*

## Milestone M11 — Production Language Server

Goal: provide editor-neutral, compiler-authoritative semantics for unsaved and multi-root workspaces.

- [x] **P1** Introduce an in-memory compiler snapshot API for authoritative unsaved-buffer analysis. *(M11-01 adds immutable compiler snapshots that combine deterministic saved-project discovery with explicit in-memory overrides, reuse the existing parser/project/type/diagnostic pipeline, carry resolve/completion/documentation queries over the same source texts, and make LSP diagnostics/definition authoritative on unsaved full-text buffers without adding workspace-ownership or incremental-state semantics.)*
- [x] **P1** Define deterministic workspace discovery, ownership, and multi-root behavior. *(M11-02 canonicalizes configured root order, assigns every source to the most-specific containing root before analysis, builds isolated per-root compiler snapshots, safely admits owned unsaved new `.aidl` files, and routes LSP diagnostics/definition through the owning snapshot so overlapping or independent roots cannot leak semantics.)*
- [x] **P1** Add incremental analysis, cache invalidation, watched-file handling, cancellation, progress, and lifecycle/load tests. *(M11-03 adds compiler-owned per-root snapshot caching keyed by exact deterministic source fingerprints, conservative root-level invalidation for saved/unsaved and watched-file changes, isolated caches, cancellation without cache/partial-result publication, balanced work-done progress, shutdown/restart state handling, and structural repeated-request load regressions without wall-clock gates.)*
- [ ] **P1** Expose existing compiler-owned completion, documentation, references, rename, and authorized fixes through LSP.
- [ ] **P1** Preserve compiler diagnostic codes, semantic identities, and edit preconditions across the protocol boundary.
- [ ] **P2** Select and pin an LSP protocol library only if it reduces protocol-maintenance risk without owning language semantics.
- [ ] **P1** Add packaged server launchers and smoke tests for VS Code plus at least one of Zed or Neovim.

### M11 acceptance criteria

- [ ] Diagnostics, navigation, completion, references, rename, and fixes operate correctly on unsaved buffers.
- [x] Multiple workspace roots cannot leak declarations or edits across project boundaries. *(M11-02 assigns each source to exactly one most-specific root and constructs independent compiler snapshots before semantic analysis; cross-root imports/navigation remain unresolved and no cross-root edit authority is exposed.)*
- [ ] Editor clients consume one compiler-owned semantic interpretation with no client-local fallback semantics.
- [ ] Large-workspace latency, cancellation, memory, and restart behavior meet published baselines.

## Milestone M12 — Distributed Runtime Vertical Slice

Goal: prove AIDL's distributed contracts through one locally runnable multi-service application before adding provider-specific deployment.

- [ ] **P1** Define a portable local adapter contract for topics, queues, inbox/outbox stores, and service-to-service transport.
- [ ] **P1** Generate and run at-least-once consumers with deterministic idempotency and dead-letter behavior.
- [ ] **P1** Generate rebuildable projections and explicit replay controls from canonical IR.
- [ ] **P1** Implement one constrained saga/workflow runtime with persisted state, compensation, timeout, and retry semantics.
- [ ] **P1** Extend `aidl plan` with required service, resource, delivery, replay, and failure consequences.
- [ ] **P1** Add deterministic simulations for duplicates, process crashes, delayed delivery, poison messages, and replay.
- [ ] **P1** Add an end-to-end fixture that runs multiple generated services without manual generated-code repair.

### M12 acceptance criteria

- [ ] State plus outbox publication is atomic while external delivery remains explicitly at-least-once.
- [ ] Duplicate delivery, restart, compensation, and projection rebuild scenarios converge to the expected state.
- [ ] Every runtime capability is derived from validated canonical IR and declared adapter capabilities.
- [ ] The distributed fixture builds and passes failure-oriented tests from a clean checkout.

## Milestone M13 — Offline Calendar Vertical Slice

Goal: make the Calendar reference application a working offline and multi-writer proof rather than only a specification fixture.

- [ ] **P1** Implement operation-log, delta-cursor, and client-generated identity runtime contracts.
- [ ] **P1** Generate server-authoritative revision handling, tombstones, and retention behavior.
- [ ] **P1** Implement the declared LWW, add-wins, server-wins, and manual conflict strategies without trusting raw client time.
- [ ] **P1** Revalidate authorization and invariants when queued offline operations reach the server.
- [ ] **P1** Define rejected-operation, local rollback, retry, and client-schema migration behavior.
- [ ] **P1** Add deterministic multi-client partition, reconnect, reordering, and convergence simulations.
- [ ] **P1** Generate and run the Calendar reference application through the normal toolchain path.

### M13 acceptance criteria

- [ ] Multiple offline clients converge deterministically after reconnect under every supported conflict strategy.
- [ ] Deletes cannot be resurrected inside the declared tombstone-retention window.
- [ ] Rejected operations remain observable and recoverable instead of being silently discarded.
- [ ] The Calendar application passes clean-checkout build, runtime, migration, partition, and convergence tests.

## Milestone M14 — Media, Cloud, and Realtime Vertical Slice

Goal: prove the remaining architecture-heavy profiles through a constrained VideoHub deployment.

- [ ] **P2** Generate resumable upload sessions, checksums, blob lifecycle, and rendition contracts.
- [ ] **P2** Run a constrained transcoding worker pipeline with declared retry, idempotency, timeout, and cost budgets.
- [ ] **P2** Generate search projections, signed delivery contracts, and explicit CDN invalidation behavior.
- [ ] **P2** Implement realtime channels with authorization, backpressure, resume, and fallback semantics.
- [ ] **P2** Validate deployment capability requirements, minimum replicas, rollout safety, secrets references, SLO feasibility, and data residency.
- [ ] **P2** Provide a complete local adapter and one provider adapter without introducing provider products into Application or System semantics.
- [ ] **P2** Generate and run the VideoHub reference application through the normal toolchain path.

### M14 acceptance criteria

- [ ] Upload, processing, search projection, delivery, and realtime flows survive retries and component restarts without contract violations.
- [ ] Unsupported provider capabilities fail planning before generation or deployment.
- [ ] Provider bindings remain replaceable and cannot change domain, ownership, delivery, or compatibility semantics.
- [ ] The VideoHub application passes clean-checkout runtime, failure, rollout, and capability tests.

## Milestone M15 — Adapter Ecosystem and 1.0 Readiness

Goal: establish the published compatibility, security, and operational evidence required for a stable AIDL ecosystem.

- [ ] **P1** Publish versioned language, profile, canonical IR, CLI, adapter, generated-manifest, and wire-schema contracts.
- [ ] **P1** Define an adapter SDK and executable conformance suite for resources, delivery, deployment, and failure behavior.
- [ ] **P1** Require two independently implemented cloud adapters to pass the same conformance suite.
- [ ] **P1** Test old clients, APIs, events, persisted schemas, and rolling deployments across supported compatibility windows.
- [ ] **P1** Validate expand/backfill/contract migrations, rollback behavior, projection replay, and disaster recovery end to end.
- [ ] **P1** Complete external security, privacy, threat-model, dependency, and generated-code reviews.
- [ ] **P2** Publish support lifecycles, deprecation policy, reproducible benchmarks, examples, and migration guides.
- [ ] **P1** Define and satisfy the final language/toolchain 1.0 release criteria without conflating independently versioned profiles and adapters.

### M15 acceptance criteria

- [ ] Published compatibility contracts are stable, independently versioned, and backed by executable conformance evidence.
- [ ] Two cloud adapters pass the same application, failure, migration, and rolling-upgrade suites.
- [ ] External security and privacy findings are resolved or documented with explicit release decisions.
- [ ] A 1.0 release can be reproduced from source and upgraded from every supported pre-1.0 compatibility baseline.

## Implementation policy

`spec/conformance-manifest.json` is the authoritative versioned implementation/support source. New or changed support claims must update a stable manifest surface ID, use only the schema-defined status vocabulary, and carry repository-relative evidence that passes `python3 -m tools.conformance_manifest validate`.

M10-01 records repository-level support surfaces only. The still-open M10-02 item owns the exhaustive Parse/Resolve/Validate/IR/Generate/IDE matrix for every Core declaration and semantic rule; absence of that matrix must not be interpreted as full layer completeness. Public wording in `SUPPORT.md` is drift-checked against each manifest `supportStatement`.

A feature should not be described as fully supported until the applicable manifest scope and its required semantic validation, IR representation, and executable evidence justify that claim.

## Definition of Done for core features

A core language feature is considered complete when:

- [ ] syntax is documented,
- [ ] parser behavior is tested,
- [ ] semantic rules are implemented,
- [ ] invalid combinations have stable diagnostics,
- [ ] canonical IR representation is defined,
- [ ] positive and negative fixtures exist,
- [ ] generator/runtime behavior is defined if applicable,
- [ ] IDE support does not require a conflicting interpretation of the language.

## Recommended execution order

1. Complete M8 — Agent-first tooling
2. M9 — Release and quality baseline
3. M10 — Core conformance closure
4. M11 — Production language server
5. M12 — Distributed runtime vertical slice
6. M13 — Offline Calendar vertical slice
7. M14 — Media, cloud, and realtime vertical slice
8. M15 — Adapter ecosystem and 1.0 readiness

Do not expand the language surface merely to advance a later milestone. Promote a capability only when its required parser, semantic, IR, fixture, runtime or explicit capability-failure, and editor boundaries can advance coherently.

The next success criterion is intentionally agent-focused:

> Given only an AIDL project and a fully qualified declaration name, a coding agent can discover the relevant semantic context, explain dependencies and diagnostics, assess change impact, validate the change, and consume deterministic bounded output without scanning the entire repository.

The next release criterion is equally concrete:

> A clean environment can install a tagged AIDL toolchain artifact, reproduce its schemas and generated output, execute every required CI gate, and run the supported Petstore workflow without modifying generated files.
