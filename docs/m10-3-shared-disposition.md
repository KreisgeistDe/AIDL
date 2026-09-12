# M10.3 Shared Canonical Source Foundation

This document records the shared central M10.3-01 foundation required before the Calendar and Petstore app-local migration waves can continue. It does not complete M10.3, widen Production Normalization, change Canonical IR meaning, alter the frozen M10.1 revision-4 contract, or authorize M10.5/Kotlin work.

The machine-readable authority for this shared disposition is `spec/m10-3-shared-disposition.json`; `tools/m10_3_shared_disposition.py` validates its frozen-contract identity, complete shared mismatch set, and fail-closed constraints.

## Canonical source forms now accepted by shared tooling

The repository parser already treated declaration bodies generically enough to read the frozen source forms. The Calendar wave exposed two `spec_lint.py` assumptions that were still legacy-only:

- app profile locking discovered only `profile core version 1`; it now also recognizes the frozen revision-4 `profile core { version 1 }` BodySlot projection and compares both spellings to the same `aidl.lock` profile fact;
- mutable-entity and ref-owner checks recognized only historical unprefixed fields; they now apply identically to frozen `field name: Type ...` slots, including `field revision: revision ... concurrencyToken`.

The revision-4 query/mutation `parameters: [...]` named HeaderArg remains unchanged and parser-covered. Positional operation signatures remain compatibility input rather than canonical target syntax.

These changes are source-form equivalence only. They do not add declaration semantics or Production Normalization admission.

## Shared mismatch disposition

Calendar and Petstore wave-1 evidence contains broader product-story surfaces than the current certified Production Semantic Envelope. M10.3 now gives every shared mismatch class an explicit disposition instead of allowing parser readability, runnable slices, or documentation to imply admission.

`app.links` is the only class in this foundation marked `requires-versioned-admission`: frozen revision 4 admits app profile facts but does not define system/frontend/api/defaultDeployment links as app BodySlots. Those links require a separately versioned language/admission change plus re-freeze and certification before becoming production reference evidence.

The remaining recorded classes are intentionally `non-production-fail-closed` for M10.3 reference evidence: value, union, view, entity invariants; query/mutation auth, cache, consistency, idempotency and transaction clauses; productive generic TypeRef arguments; and the error, event, topic, policy, workflow, api, resource, service, system, deployment, frontend, theme, component, page, form, action, sync, syncStatus, seo and test declaration families used by the reference stories.

This disposition does not remove those families from the frozen language contract and does not claim parser rejection. It states only that M10.3 reference evidence must not treat them as current Production Normalization parity. A future product requirement may move one only through an explicit versioned Python semantic/admission decision and the complete re-freeze/certification path.

## Fail-closed guarantees

The shared manifest validator requires exactly the known Calendar/Petstore shared mismatch set, rejects missing or newly invented un-dispositioned classes, pins frozen M10.1 revision 4, and requires explicit flags that Production Admission, Canonical IR meaning and the frozen contract remain unchanged. Focused regressions also cover canonical app profile blocks, explicit entity field slots, historical compatibility equivalents, invalid profile mismatch behavior, and deterministic parser acceptance of named operation HeaderArgs.

M10.2 classification remains authoritative for support tiers. M10.3-01 remains open. Calendar and Petstore app-local migrations may continue only after this shared foundation is independently validated and durably integrated. VideoHub planning should use the same disposition authority. M10.5 and PR #77 remain deferred until integrated M10.3.
