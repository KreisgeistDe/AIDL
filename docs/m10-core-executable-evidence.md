# M10 Core executable evidence

The Core conformance matrix remains authoritative for Parse, Resolve, Validate, IR, Generate, and IDE status. Status promotion is allowed only when the repository contains executable evidence for the complete claimed layer behavior; evidence must not manufacture support that the implementation does not provide.

`spec/core-executable-evidence.json` is a deterministic companion registry for cells marked `implemented` in `spec/core-conformance.json`. A matrix cell reaches the executable-evidence gate only when at least one of its existing `layerEvidence` IDs resolves through the companion registry to a committed focused test file. `python3 -m tools.core_executable_evidence validate` checks that chain offline and rejects unknown, stale, missing, unsorted, or non-test evidence.

The registry deliberately reuses existing executable regressions where they exercise the claimed layer:

- Parse: `tools/test_aidl_parser.py`
- Resolve: `tools/test_compiler_project.py`
- Validate: `tools/test_m5_fixture_corpus.py` and `tools/test_core_typecheck.py`
- Canonical IR: `tools/test_aidl_ir.py`, `tools/test_core_api_contract_semantics.py`, `tools/test_core_consumer_idempotency_semantics.py`, `tools/test_core_entity_ownership_semantics.py`, `tools/test_core_error_contract_ir_semantics.py`, `tools/test_core_event_ir_semantics.py`, `tools/test_core_topic_delivery_ir_semantics.py`, `tools/test_core_transaction_semantics.py`, and `tools/test_ir_schema.py`
- Generate: `tools/test_core_transaction_semantics.py` and `tools/test_m4_petstore.py`

## Transaction resource/outbox closure

The Core transaction contract already requires one transaction resource owner and transactional event publication through an outbox. Canonical IR preserves the selected resource as `rootEffect.resourceId` and preserves transactional publication as a `publish` step with `via: outbox`. The PostgreSQL transaction generator resolves that exact resource, rejects an unresolved resource, requires canonical outbox publication, emits the outbox insert as a transaction step, and commits only after all steps have executed.

`tools/test_core_transaction_semantics.py` binds those existing semantics end to end through the Petstore reference source. It proves both canonical IR facts, proves that the PostgreSQL generator consumes the same resource and outbox step inside its generated transaction, and proves negative rejection for an unresolved transaction resource and a non-outbox publish. This justifies promoting only these four cells from `partial` to `implemented`:

- `rule.transaction.resource-owner`: IR and Generate
- `rule.transaction.outbox-atomic`: IR and Generate

No source syntax, language semantic, support surface, or IDE status is widened by this closure.

## Entity ownership IR closure

The Core ownership contract already requires every persisted entity to have exactly one owner service, direct persisted access to stay owner-local, and direct entity `ref` fields not to cross service ownership boundaries. These rules are already enforced by stable compiler diagnostics: owner cardinality is rejected by `AIDL-DIST400`, cross-service refs by `AIDL-DIST401`, and transaction access outside the exposing service's ownership boundary by `AIDL-DIST402`.

Canonical IR already materializes the accepted ownership facts rather than reparsing source: `system.services[].owns` contains the canonical entity declaration IDs, service `exposes` links operations to that same service boundary, write steps carry canonical `entityId` values, and a valid entity `ref` carries both its target `entityId` and `ownerServiceId`. `tools/test_core_entity_ownership_semantics.py` exercises those facts on an owner-local reference variant of the existing M4 Petstore source and proves that an exposed persistent write remains inside the service's canonical `owns` set.

Together with the existing deterministic negative diagnostics, that executable IR materialization evidence justifies promoting only these three cells from `partial` to `implemented`:

- `rule.entity.single-owner`: IR
- `rule.entity.owner-local-access`: IR
- `rule.entity.cross-service-ref-rejected`: IR

No Generate or IDE cell is promoted, and no ownership syntax or policy behavior is changed by this closure.

## API exposure/version/compatibility IR closure

The accepted Core API contract already requires exactly one supported transport (`rest`, `rpc`, or `graphql`), a positive major version, one non-empty operation list whose explicit query/mutation mappings resolve uniquely to the matching declaration kind, and one compatibility mode from `none`, `backward`, `forward`, or `full`. Stable `AIDL-DIST412` diagnostics already reject missing, duplicate, invalid, unresolved, ambiguous, kind-mismatched, or duplicate operation mappings deterministically before Canonical IR is emitted.

Canonical IR materializes those accepted facts directly as `transport`, `majorVersion`, `operations[]` with canonical operation declaration IDs, and `compatibility`. `tools/test_core_api_contract_semantics.py` proves the positive IR materialization using a valid RPC/version-2/full-compatibility variant of the existing M4 Petstore source and directly proves the negative boundary for invalid transport, version, unresolved operation exposure, and compatibility.

That evidence justifies promoting only this one cell from `partial` to `implemented`:

- `rule.api.exposure-version-compatibility`: IR

The API declaration's Generate cell remains `partial`: the existing M4 generator is a deliberately bounded runtime slice and this closure does not manufacture general REST/RPC/GraphQL generation support. No IDE cell, syntax, or API policy behavior changes.

## Consumer idempotency IR closure

The accepted Core consumer contract requires effectful consumers to declare exactly one idempotency clause. Stable `AIDL-DIST411` diagnostics already reject effectful consumers that omit that clause or declare it more than once, while pure consumers may omit it. The existing compiler also carries the accepted idempotency contract into Canonical IR rather than discarding it.

Canonical IR materializes a consumer's idempotency key expression, scope, and retention duration as `idempotency.key`, `idempotency.scope`, and `idempotency.retentionMs`; the closed IR schema requires all three fields whenever the idempotency object is present. `tools/test_core_consumer_idempotency_semantics.py` proves that a valid event/topic-bound consumer preserves its canonical event/topic IDs together with the parsed `event.eventId` key, the consumer idempotency scope literal, and a seven-day retention, and directly proves the existing `AIDL-DIST411` negative boundary for an effectful consumer without idempotency.

That evidence justifies promoting only this one cell from `partial` to `implemented`:

- `rule.consumer.idempotency`: IR

Generate remains `partial`: `tools/generate_postgres_idempotency.py` is deliberately scoped to transactional mutations with a resolved PostgreSQL transaction resource and does not implement consumer runtime idempotency. No consumer runtime, general distributed profile, IDE cell, source syntax, or language semantic is widened by this closure.

## Error contract IR evidence

The accepted Core error contract requires typed exported errors to carry a stable code, public transport status, retry classification, and exactly one safe public message or localization contract. Compiler-owned `AIDL-T003` diagnostics already reject empty codes, invalid public HTTP statuses, invalid retry classes, and missing or empty safe-message/localization contracts deterministically.

Canonical IR materializes the accepted runtime-facing subset directly as `code`, `safeMessage`, `retry`, and `transportStatus`. `tools/test_core_error_contract_ir_semantics.py` proves deterministic source-to-IR preservation of those four facts for a valid exported error added to the existing M4 minimal fixture, proves the existing `AIDL-T003` negative boundary for malformed exported errors, and proves the closed IR schema rejects invalid code, retry, and transport-status values.

This closure intentionally does not promote `decl.error/ir`: it proves the typed error contract metadata subset but does not claim every broader Error Validate/IR/Generate behavior is complete. No source syntax, language semantics, generator behavior, or IDE status is widened.

## Event version/schema IR evidence

The accepted Core event contract requires versioned event declarations together with event identity/schema metadata. Canonical IR already carries the event major version and canonical field schema, including field names, materialized field types, and requiredness; the closed IR schema requires a positive major version and at least one valid event field.

`tools/test_core_event_ir_semantics.py` exercises the existing M4 minimal fixture end to end. It proves deterministic source-to-IR preservation of the event major version and ordered event field schema, and proves the negative IR boundary by showing the closed schema rejects a zero major version, an empty event schema, and an empty field name.

This closure intentionally does not promote `decl.event/ir`: it proves the accepted version/schema metadata subset but does not claim every broader Event Validate/IR/Generate behavior is complete. No syntax, language semantics, generator behavior, or IDE status is widened.

## Topic delivery metadata IR evidence

The accepted Core topic contract requires at-least-once delivery together with partitioning, ordering, retention, compatibility, and dead-letter metadata. Canonical IR already materializes those source facts as `delivery`, `partitionField`, `ordering`, `retentionMs`, `compatibility`, and `deadLetterAttempts`, while the closed IR schema constrains each field to the supported Core contract.

`tools/test_core_topic_delivery_ir_semantics.py` exercises the existing M4 minimal fixture end to end. It proves deterministic source-to-IR materialization of the six delivery metadata fields and proves the negative IR boundary by showing the closed schema rejects exactly-once delivery, an empty partition field, unsupported global ordering, zero retention, an unsupported compatibility value, and zero dead-letter attempts.

This closure intentionally does not promote `decl.topic/ir`: it proves one complete downstream-relevant semantic subset, not every topic declaration fact. Event binding and the broader Topic Validate/IR/Generate cells remain subject to independent closure. No syntax, language semantics, generator behavior, or IDE status is widened.

No IDE cell is currently marked `implemented`, so the registry does not manufacture IDE completeness from workflow or documentation evidence. The same rule applies to every remaining `partial` or `missing` cell in any layer: executable tests may exist for a subset of behavior, but status remains open until the matrix can truthfully claim layer completeness.

The transaction block reduced the first M10 acceptance gap by four partial layer cells and the third acceptance gap by preserving two required transaction semantic facts in Canonical IR. The entity ownership block reduced the first acceptance gap by three additional IR cells and extended the third acceptance evidence to canonical owner-service, owner-local access, and ref-owner facts. The API block reduced the first gap by one additional IR cell and extended the third acceptance evidence to canonical transport, major-version, operation-exposure, and compatibility facts. The consumer-idempotency block reduced the first gap by one additional IR cell and extended the third acceptance evidence to canonical idempotency key, scope, and retention facts. The error-contract block adds focused positive/negative evidence for accepted typed-error runtime contract facts without claiming whole-cell completeness. The event-version/schema block adds focused positive/negative evidence for accepted versioned event schema facts without claiming whole-cell completeness. The topic-delivery block adds focused positive/negative evidence for six accepted downstream-relevant Topic IR facts without claiming whole-cell completeness. Neither acceptance criterion is complete: other Core matrix cells remain `partial` or `missing`, including unrelated IR, generator, and IDE capabilities that require independent implementation or narrower claim decisions before promotion.
