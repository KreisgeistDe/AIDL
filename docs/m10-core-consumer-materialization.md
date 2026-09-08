# M10 Core Consumer Validate/IR closure

This closure covers exactly `decl.consumer/validate` and `decl.consumer/ir`. It does not widen Consumer Generate/IDE support, runtime semantics, grammar, Canonical-IR schema/version, App/Module/Import claims, M11, M10.5/Kotlin, M16.5, release/protection, or project `.ai/**` state.

## Closed source boundary

The normative Consumer body contains exactly these clause families: `service`, `idempotency`, `retry`, `start`, `call`, and `transaction`. The existing compiler and Canonical-IR path already give every accepted Consumer fact one of two outcomes: lossless projection or stable rejection before IR.

- `on EVENT from TOPIC` is validated by `AIDL-DIST415`. The event and topic must resolve uniquely, the Topic must contain the Event, and delivery must be `atLeastOnce`. Accepted bindings materialize as canonical `eventId` and `topicId`.
- Effectful Consumer idempotency cardinality remains owned by `AIDL-DIST411`: exactly one idempotency clause is required for effectful Consumers, while pure Consumers may omit it. Accepted idempotency materializes `key`, `scope`, and `retentionMs`.
- `service SERVICE` is accepted only when the service resolves uniquely, lists the Consumer in `runs`, and is included by the canonical System. The binding is preserved through the canonical service `runs` declaration IDs.
- Retry materializes as `none` when absent or explicitly `none`, or as exact exponential `initialDelayMs`, `maxDelayMs`, and positive `attempts`. `immediate` and malformed/non-closed retry forms are rejected by the existing `AIDL-T005` materialization boundary.
- `start` materializes only for one resolved `workflow` or `task` target with one recursively projectable literal/symbol/record input. Mutation, saga, unresolved targets, malformed invocation shapes, and unprojectable inputs are rejected before IR with `AIDL-T005`.
- Consumer `call` and Consumer `transaction` have no closed Core Consumer IR representation and are rejected before IR with `AIDL-T005` rather than silently discarded.

No new diagnostic code is introduced. Existing `AIDL-DIST415` and `AIDL-DIST411` ownership remains authoritative for their respective policy failures; the focused closure regressions verify those failures do not receive a Consumer `AIDL-T005` duplicate.

## Executable evidence

`tools/test_core_consumer_materialization_closure.py` proves the whole Source→Validate→IR boundary directly:

- deterministic full-document builds from the same source;
- stable Consumer FQN and declaration identity;
- exact canonical `eventId` and `topicId`;
- service membership through `system.services[].runs`;
- explicit idempotency key/scope/retention;
- retry `none` and exact exponential projection;
- workflow and task start effects;
- optional retry/start/idempotency defaults for a pure Consumer;
- matching Consumer `sourceMap` identity and node path;
- complete `spec/ir.schema.json` validation;
- stable `AIDL-DIST415` ownership for unresolved/mismatched binding and wrong delivery;
- stable `AIDL-DIST411` ownership for missing/duplicate idempotency on effectful Consumers;
- stable `AIDL-T005` rejection for service mismatch, immediate/malformed retry, mutation/saga/unresolved/unprojectable starts, `call`, and Consumer `transaction`.

The existing focused binding, idempotency, and execution-contract tests remain complementary evidence and are still registered in `spec/core-executable-evidence.json`.

## Conformance promotion

The evidence above justifies only these status changes in `spec/core-conformance.json`:

- `decl.consumer/validate`: `partial` → `implemented`
- `decl.consumer/ir`: `partial` → `implemented`

`decl.consumer/generate` and `decl.consumer/ide` remain `partial`. The resulting Core Supported fixture row is registered in `spec/core-fixture-conformance.json` without changing any language or runtime claim.
