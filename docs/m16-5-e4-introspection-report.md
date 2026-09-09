# M16.5 E4 — compiler schema/introspection prototype

Status: **experimental E4 evidence only**. Base: `49c1552a4a0f620b4de4bc12fac87ecb395aac01` (`main`). This package is read-only metadata. It does not parse AIDL, change `docs/06-grammar.md`, alter accepted syntax/parser acceptance, change AST/Canonical-IR meaning, implement formatter/migration or IDE completion, roll out diagnostics, change compatibility/support/conformance, or affect generator/runtime behavior.

## Surface and authority

`tools/m16_5_e4_introspection.py` exposes a transport-neutral `CompilerSchemaService` over immutable dataclasses. There are no registration/update/mutation methods and no imports from the production parser or the E3 candidate parser.

The bounded introspection schema uses the exact immutable tuple:

- schema ID: `urn:aidl:schema:meta:m16.5-e4-introspection`
- semantic version: `0.1.0-e4`
- content fingerprint: `sha256:1c870ed29b4621ae108a64c6fd8ffecd48e7b984d38afee393c23a33cc5da542`

The fingerprint is computed from canonical JSON over the complete unsigned E4 metadata payload, including the pinned project base and normative grammar blob SHA `834629dab9198c1e78090e31a5ce2a29180a05f1`. Clients first obtain the compiler-embedded exact tuple through `schema_ref()` / `schema-ref`; every catalog query then requires that complete tuple. Unknown IDs, stale versions, and fingerprint mismatches fail closed. There is no `latest`, semver substitution, source sniffing, or client-selected fallback.

This tuple identifies the **experimental introspection schema**, not a new source-language version. E2 source-language selection remains unchanged.

## Representative declaration discovery

The service exposes the current accepted grammar shape for four representative families:

| Family | Declaration | Discoverable construction facts |
| --- | --- | --- |
| App | `app` | starter, `typeName` identity, `profile/system/frontend/api/defaultDeployment/compatibility` body slots and value shapes |
| Core | `entity` | starter, `typeName` identity, keywordless named field entries, `index`/`invariant`, field modifier vocabulary and modifier value shapes |
| Backend | `service` | `owns/uses/exposes/runs/dependsOn`, typed list shapes, nested `reliability` profile properties, telemetry |
| Sync | `sync` | `for <type>` header argument, all current `syncClause` slots, compound `changes to <typeName> via outbox` and tombstone forms, nested operation-log/profile and conflict-rule schemas |

Each declaration returns starter tokens, identity shape, header arguments, body slot IDs and visible tokens, cardinality, value/type shape references, modifier IDs, documentation references, nesting targets, and conservative `semantic_order=preserve` metadata. Value shapes are separately queryable so a completion/agent client does not need to reconstruct type/list/enum/compound syntax from declaration-specific branches.

The exported legal declaration kinds intentionally do **not** include E3 candidate-only pseudo-kinds such as `queue_deadletter`, `schedule_lease`, or `sync_outbox`. In particular, Sync exports the current accepted `changes to Target via outbox` compound value; E4 adopts no candidate spelling.

## Generic sublanguage discoverability

The generic structural surfaces requested by the M16.5 roadmap are mechanically queryable without making their vocabularies open:

- `profileProperty`: path/value and recursive path/block alternatives, with closed vocabulary owned by the compiler profile schema for the enclosing declaration/profile;
- `uiStatement`: identifier + typed atom structure plus optional recursive children, with closed vocabulary owned by the compiler web profile schema;
- `testStatement`: explicit leaf/block alternatives with recursive test children, with closed vocabulary owned by the compiler test profile schema.

E4 also exposes `conflictRule` as a bounded nested Sync schema. The generic descriptors state the vocabulary authority and closed-vocabulary contract. They do not invent profile/UI/test words or make unknown identifiers legal.

## Focused evidence

Fixture `fixtures/m16-5/e4-introspection-cases.json` models a consumer contract rather than source syntax. `tools/test_m16_5_e4_introspection.py` proves:

- exact deterministic schema ID/version/fingerprint and pinned grammar/base provenance;
- fail-closed unknown/stale/mismatched schema references;
- App/Core/Backend/Sync discovery with no client-side grammar reconstruction;
- keywordless Entity-field shape plus all current field modifiers and valued modifier shapes;
- current Sync compound syntax and exclusion of E3 candidate pseudo-kinds;
- nested-schema discovery;
- closed generic `profileProperty`, `uiStatement`, and `testStatement` discoverability;
- immutable/read-only catalog behavior and deterministic export;
- explicit failures for unknown declaration/sublanguage/value/modifier IDs;
- no production-parser or E3-parser dependency.

Executed targeted validation:

```text
python3 -m compileall -q tools/m16_5_e4_introspection.py tools/test_m16_5_e4_introspection.py
# exit 0

python3 -m unittest -v tools.test_m16_5_e4_introspection
# 12 tests, OK

python3 -m tools.m16_5_e4_introspection schema-ref
# exact tuple above
```

Repository-wide regression validation remains the existing PR GitHub Actions suite; its exact-head results are part of the completion evidence rather than duplicated by this isolated local prototype workspace.

## Later E6/E7 reliance boundary

Later authorized consumers may rely on these E4 facts only:

1. the service is read-only and compiler-owned;
2. schema lookup is exact-tuple and fail-closed;
3. declaration metadata distinguishes starter/identity/header/body/value/modifier/nesting/documentation facts;
4. generic profile/UI/test sublanguages are closed and expose their structural alternatives plus vocabulary authority;
5. absent `semantic_order=unordered` evidence means preserve source order;
6. candidate E3 spellings are not legal E4 declaration metadata.

E6 may consume this metadata but must not add adapter-local semantic fallback. E7 may use the schema facts to frame expected-slot/value diagnostics only after separate authorization; E4 introduces no new production diagnostic behavior.

## Omissions and failure modes

This bounded E4 package is **not** a complete 49-form declaration-corpus schema and therefore does not satisfy the E3 production-promotion gate by itself. It does not enumerate every profile-specific property path, every web UI keyword, or every typed test verb. Those vocabularies remain compiler/profile authorities and must be exported from their authoritative data before a full E6 consumer can claim complete coverage.

The package also does not prove recursive selection/control-flow parity, unchanged-invalid recovery parity, sidecar edit/anchor stress behavior, M7 semantic equivalence for rewrites, or full-corpus schema/parser equivalence. Those remain gates for later work. A client presenting an unknown/stale schema tuple or requesting an unmodeled declaration/value/sublanguage receives an explicit failure and must not reconstruct or guess a fallback schema.

## Recommendation

Proceed to E5/E6 only under their existing dependency gates. E4 evidence supports the compiler-owned introspection direction for representative families and generic sublanguage structure, but full declaration/profile vocabulary coverage remains required before production completion can rely exclusively on this surface.
