# M10.1 Closure Certification

M10.1 is certified complete against frozen language-surface contract revision 4. This certification closes the language-design gate only; it does not change parser, AST, IR, runtime, Canonical IR, CLI schema, formatter defaults, or public support claims.

The executable authority for this closure is `tools/compiler_language_surface_certification.py`. It composes the already-integrated contract-derived evidence instead of defining another semantic inventory. The certification fails closed if the frozen contract revision/status drifts, any coverage/declaration-family/policy/execution audit `schema_version` drifts, coverage loses or duplicates contract facts, any declaration/policy/execution disposition becomes unresolved, an intentional exclusion loses its boundary, formatter and migration operations collapse together, or any M10.1 package is not complete.

## Certified Production Semantic Envelope

The compatibility bridge remains `aidl.m10.1-normalized/v2`; Production Normalization remains `aidl.m10.1-production/v5`; complete coverage remains `aidl.m10.1-language-surface-coverage/v1`. The new `aidl.m10.1-closure-certification/v1` envelope is audit evidence only and does not alter normalized semantic hashes.

All 48 frozen canonical declaration kinds retain explicit production dispositions derived from existing compiler gates. The admitted families remain `alias`, `entity`, `enum`, `migration`, `client`, `consumer`, `projection`, `app`, `query`, and `mutation`; the other 38 remain intentionally non-admitted until separately implemented with complete compiler-owned evidence. Non-admission is not parser rejection or removal from the language contract; it means Production Normalization does not claim complete lossless semantics for that family.

For query/mutation policy semantics, frozen-v1 `allow` remains the contract-owned authorize fact. Legacy `auth`, `cache`, and `consistency` remain explicit exclusions because revision 4 defines no corresponding operation BodySlots. Their existing fail-closed compiler boundary is recorded as `AIDL-N010 -> AIDL-N013`: the body bridge retains the unsupported clause as `AIDL-N010` evidence and the Production Normalization losslessness gate rejects that operation with `AIDL-N013`. For execution semantics, `TypeRef.range` and operation-parameter `default` remain Production-Parity; generic TypeRef arguments, non-range constraints, operation generics, mutation `idempotency`, and mutation `transaction` remain explicit fail-closed exclusions on their existing diagnostic paths.

Every non-example frozen-v1 contract leaf remains covered by the deterministic M10.1-09 audit. TypeRef optional/range and reference-projection evidence continues to come from the executable bridge. Existing differential regressions prove representative legacy/canonical semantic and hash convergence, production stability under formatting/source-order variation, and deterministic rejection of unsupported shapes.

## Acceptance matrix

M10.1 closure is certified because all seven milestone acceptance conditions now have executable evidence:

1. Every frozen semantic fact is covered by contract-derived evidence and any unsupported production shape has an explicit fail-closed disposition rather than heuristic partial admission.
2. Representative legacy and independently constructed canonical facts converge on equal semantics/hashes, and equivalent production sources converge on byte-stable semantic JSON/hashes.
3. Production Normalization remains derived from `spec/language-surface-v1.json` plus compiler-owned resolver/typechecker/bridge evidence; no parallel grammar or semantic table is introduced.
4. `LanguageSurfaceBridge.format_legacy` remains a distinct same-version formatting operation from `LanguageSurfaceBridge.migrate_to_canonical_preview`, and both are deterministic.
5. Query/mutation plus all 48 frozen declaration families have an explicit production parity or intentional non-admission/exclusion disposition.
6. Complete coverage, differential conformance, fail-closed boundaries, roadmap consistency, audit-schema/contract drift, and deterministic output are executable through the repository-owned generic Python selector and broader CI.
7. No unresolved M10.1 language decision remains that M10.5-03 must invent or select.

## M10.5-03 unblock condition

M10.5-03 is unblocked only to implement frozen-v1 revision 4 through bounded Python-versus-Kotlin differential parity slices under the existing M10.5 gates. This is not authorization to modify the frozen language contract or begin a semantic redesign. Any new language meaning, changed canonical fact, changed exclusion, or changed schema requires a separately versioned language decision and compatibility process before it can enter the Kotlin front end.

Python remains the reference/conformance implementation throughout M10.5 until the separately defined exit criteria are satisfied. M10.5-03 must preserve existing accepted/rejected classification, diagnostics, identities, ordering, source locations, and deterministic failure behavior for each migrated slice before expanding scope.
