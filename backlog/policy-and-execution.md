# Roadmap policy, Definition of Done, and execution order

## Implementation policy

`TODO.md` is the sole handwritten authority for roadmap order, milestone identity, and completion state. Operational execution state remains on `agents/channel`; committed legacy project `.ai/**` current-state files are not a second roadmap authority.

The project tree is intentionally `.ai/**`-free. Every project PR targeting `main` must reject any `.ai/**` endpoint, including additions, modifications, deletions, copies, and renames; the former one-time legacy deletion exceptions are obsolete because those files no longer exist in the project repository. Operational state and any maintenance of the transport workflow belong only in `KreisgeistDe/AIDL_channel@agents/channel`, never in a project PR.

`spec/conformance-manifest.json` is the separate authoritative versioned implementation/support source. New or changed support claims must update a stable manifest surface ID, use only the schema-defined status vocabulary, and carry repository-relative evidence that passes `python3 -m tools.conformance_manifest validate`. Roadmap completion alone never promotes a support claim.

The offline repository-state check `python3 -m tools.validate_repository_state` enforces the `.ai/**`-free project invariant and the roadmap, channel, and conformance authority markers. It requires no network access and runs in standard validation CI.

M10-01 records repository-level support surfaces only. M10-02 provides the exhaustive Parse/Resolve/Validate/IR/Generate/IDE matrix for every Core declaration and semantic rule; incomplete rows or evidence remain explicit in that matrix and must not be interpreted as full layer completeness. Public wording in `SUPPORT.md` is drift-checked against each manifest `supportStatement`.

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

1. M9 — Release and quality baseline
2. M10 — Core conformance closure
3. M11 — Production language server
4. M12 — Distributed runtime vertical slice
5. M13 — Offline Calendar vertical slice
6. M14 — Media, cloud, and realtime vertical slice
7. M15 — Adapter ecosystem and 1.0 readiness
8. M16 — Agent Construction and Verification

Do not expand the language surface merely to advance a later milestone. Promote a capability only when its required parser, semantic, IR, fixture, runtime or explicit capability-failure, and editor boundaries can advance coherently.

The next success criterion is intentionally agent-focused:

> Given an AIDL project and a change request, a model-independent coding agent can obtain bounded compiler-owned context, construct a semantic patch, validate it entirely in memory against a specific snapshot, inspect deterministic diagnostics, impact, and compatibility evidence, and apply it only while the validated preconditions still hold, without repository-wide heuristic scanning.

The next release criterion is equally concrete:

> A clean environment can install a tagged AIDL toolchain artifact, reproduce its schemas and generated output, execute every required CI gate, and run the supported Petstore workflow without modifying generated files.
