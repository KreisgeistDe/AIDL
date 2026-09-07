# M9–M10 — Release baseline and Core conformance

## Milestone M9 — Release and Quality Baseline

Goal: turn the repository toolchain into a reproducible, installable, and protected pre-release baseline before expanding runtime scope.

- [x] **P1** Make CI test selection complete and drift-proof through deterministic discovery or a validated test manifest. *(M9-01 discovers committed `tools/test_*.py` modules through `git ls-files`, runs every matching test by default, and permits only versioned specialized-job exclusions whose path, owner job, command, and rationale are validated.)*
- [x] **P1** Run every compiler-owned resolution, completion, documentation, refactoring, and CLI regression as a required CI gate. *(M9-02 adds a versioned compiler/CLI regression inventory plus AST-based certification against the M9-01 selector; `Compiler / Python` now rejects missing, excluded, stale, drifted, or unpaired critical regressions before running the full discovered suite.)*
- [x] **P1** Reconcile README, coverage, agent-tooling, schema identifiers, registry versioning, and implemented-command documentation with the actual repository state. *(M9-03 aligns README, agent-tooling, coverage, and the M8 workflow with the registered CLI and proven compiler/IR/M4 surfaces; documents IR 0.3.0, CLI schema v7, and profile registry 0.3.0 as separate version domains; and adds a CI regression tying command tables/help plus schema/registry identities to repository truth.)*
- [x] **P1** Package the AIDL CLI/compiler as an installable artifact with pinned runtime dependencies and a clean-machine smoke test. *(M9-04 adds a PEP-517/setuptools wheel with the existing `aidl` console entry point, Python 3.12 support, exact runtime/build pins, packaged `spec/*.json` contracts, focused packaging regressions, and an isolated fresh-venv smoke that proves installed help/check/diff/error behavior without repository import paths.)*
- [x] **P1** Add a reproducible release workflow for CLI artifacts, JSON schemas, checksums, and release notes. *(M9-05 adds a versioned tag/version contract, deterministic same-commit double-build certification, complete tracked `spec/*.json` contract bundling, machine-readable release manifest, SHA-256 component/archive checksums, committed changelog-derived notes, and a read-only Actions dry run with publication disabled.)*
- [ ] **P1** **M9-06** Protect `main` with required validation, compatibility, fixture, runtime, IntelliJ, and `.ai/**` boundary checks. *(The project-side required-check contract and deterministic drift validation are defined in `spec/m9-main-protection.json` and `docs/m9-main-protection.md`; completion still requires the active GitHub repository ruleset to require every contracted status check.)*
- [x] **P2** Add contribution, security-reporting, support-status, and artifact provenance documentation. *(M9-07 adds repository-level contribution and security policies, an evidence-bounded support matrix, and provenance/integrity documentation tied exactly to the M9-05 deterministic bundle, manifest, checksums, source commit and dry-run workflow without claiming publication, signatures, SBOMs, attestations, or branch protection.)*
- [x] **P1** **M9-08** Publish the first explicitly scoped toolchain pre-release without implying stability for unsupported language profiles. *(M9-08 defines `aidl-toolchain` `0.1.0rc1` / `aidl-toolchain-v0.1.0rc1`, extracts only scoped conformance-bounded notes, keeps PR builds read-only, and permits GitHub pre-release publication only after a verified exact-tag build; actual tag creation/publication is intentionally deferred until this green PR is integrated.)*

### M9-09 — Roadmap and Agent State Consistency

- [ ] **P1** Make `TODO.md` the sole handwritten authority for roadmap order, milestone identity, and completion state; keep conformance manifests as the separate authority for implementation/support claims.
- [ ] **P1** Eliminate independently maintained durable project `.ai/**` milestone/current-state documents, or derive any retained committed projection deterministically from the authoritative roadmap instead of maintaining a second handwritten roadmap.
- [ ] **P1** Add deterministic offline CI validation for any committed project `.ai/**` current-state exposure so lagging, contradictory, or independently edited agent-facing milestone state is rejected without network access.
- [ ] **P1** Reconcile legacy `BACKLOG`, `TASK`, `HANDOFF`, and applicable `CONTEXT` current-state content against `TODO.md` before it is frozen, removed, or replaced by deterministic generation.
- [ ] **P1** Define the policy-safe maintenance path for that reconciliation or migration while preserving the rule that ordinary project PRs targeting `main` must continue to reject every `.ai/**` mutation.

#### M9-09 acceptance criteria

- [ ] `TODO.md` is the sole handwritten roadmap, milestone, and completion authority.
- [ ] No committed agent-facing current-state projection lags or contradicts the authoritative roadmap.
- [ ] Conformance manifests remain the separate implementation/support-claim authority and are not derived from roadmap completion state.
- [ ] Roadmap/agent-state consistency validation is deterministic and offline.

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
