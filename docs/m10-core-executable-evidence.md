# M10 Core executable evidence

The Core conformance matrix remains authoritative for Parse, Resolve, Validate, IR, Generate, and IDE status. Status promotion is allowed only when the repository contains executable evidence for the complete claimed layer behavior; evidence must not manufacture support that the implementation does not provide.

`spec/core-executable-evidence.json` is a deterministic companion registry for cells marked `implemented` in `spec/core-conformance.json`. A matrix cell reaches the executable-evidence gate only when at least one of its existing `layerEvidence` IDs resolves through the companion registry to a committed focused test file. `python3 -m tools.core_executable_evidence validate` checks that chain offline and rejects unknown, stale, missing, unsorted, or non-test evidence.

The registry deliberately reuses existing executable regressions where they exercise the claimed layer:

- Parse: `tools/test_aidl_parser.py`
- Resolve: `tools/test_compiler_project.py`
- Validate: `tools/test_core_domain_type_ir_semantics.py`, `tools/test_m5_fixture_corpus.py`, `tools/test_core_enum_ir_semantics.py`, `tools/test_core_event_ir_semantics.py`, `tools/test_core_topic_materialization_contract.py`, `tools/test_core_typecheck.py`, and `tools/test_core_value_ir_semantics.py`
- Canonical IR: `tools/test_aidl_ir.py`, `tools/test_core_api_contract_semantics.py`, `tools/test_core_consumer_idempotency_semantics.py`, `tools/test_core_domain_type_ir_semantics.py`, `tools/test_core_entity_ownership_semantics.py`, `tools/test_core_enum_ir_semantics.py`, `tools/test_core_error_contract_ir_semantics.py`, `tools/test_core_event_ir_semantics.py`, `tools/test_core_topic_delivery_ir_semantics.py`, `tools/test_core_topic_materialization_contract.py`, `tools/test_core_transaction_semantics.py`, `tools/test_core_value_ir_semantics.py`, and `tools/test_ir_schema.py`
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

## Alias/Opaque Validate/IR closure

The closed Core Alias/Opaque IR contract stores exactly one target typeRef as `target` for `alias` and `representation` for `opaque`. Before this closure, unresolved or ambiguous project nominal targets could reach `_type_ref()` and be widened into synthetic `aidl.std.*` identities, while source forms not represented by the current typeRef contract could otherwise be accepted or normalized before IR.

`tools/compiler_alias_opaque_materialization.py` now adds a shared pre-IR boundary for both declarations. Missing targets, unresolved or ambiguous nominal targets, fake standard-qualified names, and entity-identity targets whose source identity would be erased are rejected with stable `AIDL-T005`. The existing shared Core materialization boundary continues to own resolved wrong-kind and generic project declarations/uses without duplicate diagnostics. The existing type constructor checker already rejects inline-enum and unsupported constraint forms with `AIDL-T001`, so those facts also stop before Canonical IR rather than being widened. Synthetic standard identities remain allowed only for the explicit closed Core standard-type allowlist.

`tools/test_core_domain_type_ir_semantics.py` proves the complete accepted projection for scalar Alias/Opaque targets, nested nullable/list/set/map shapes, uniquely resolved project nominal types, and explicit Core standard types. It checks deterministic declaration/FQN identity and exact target/representation objects across repeated builds and validates the resulting full document against `spec/ir.schema.json`. Its negative cases prove pre-IR rejection for missing, unresolved, ambiguous, wrong-kind, generic, inline-enum, identity-erasing, malformed-constructor, and unsupported-constraint source forms. `tools/test_core_typecheck.py` and `tools/test_aidl_check.py` now also assert the stable unresolved-Alias materialization diagnostic instead of the former permissive expectation.

This executable evidence justifies promoting exactly these four cells from `partial` to `implemented`:

- `decl.alias`: Validate
- `decl.alias`: IR
- `decl.opaque`: Validate
- `decl.opaque`: IR

Alias/Opaque Generate and IDE remain `partial`. No grammar, IR schema/version, Value, Error, Consumer, App, Module/Import, generator/runtime, M16.5, release/protection workflow, or IDE behavior is widened by this closure.

## Value Validate/IR closure

The closed Core Value IR stores an ordered `fields` array whose field contract preserves `name`, canonical `type`, requiredness, `mutable`, `sensitive`, `generated`, and the already represented optional `primary` and `concurrencyToken` flags. Before this closure, the generic field projector could ignore non-field body entries such as invariants, collapse duplicate field names into an ambiguous semantic surface, treat nullable-plus-`required` source as optional, and accept grammar-level modifiers whose meaning is not represented by the closed Value IR.

`tools/compiler_value_materialization.py` now places a Value-specific pre-IR boundary in front of that projector. It rejects invariants, malformed/non-field body entries, duplicate fields, nullable fields marked `required`, repeated source modifiers that cannot be preserved as distinct facts, and the currently non-materialized `clientGenerated`, `immutable`, `unique`, `default`, `onDelete`, and `via` modifiers with source-located `AIDL-T005`. Existing Core type diagnostics remain authoritative for malformed type constructors and the previously established generic/unsupported type-materialization boundary, avoiding duplicate diagnostics.

`tools/test_core_value_ir_semantics.py` proves deterministic Source-to-Validate-to-IR behavior for ordered scalar and nested nullable/list/set/map fields, supported string constraints, a uniquely resolved project nominal type, and the represented required/mutable/sensitive/generated/primary/concurrency-token metadata. Repeated builds produce the same canonical identities and Value object, and the full emitted document validates against `spec/ir.schema.json`. Its negative matrix proves every unsupported Value body fact above is rejected before IR and separately proves malformed constructors remain owned by `AIDL-T001`.

This executable evidence justifies promoting exactly these two cells from `partial` to `implemented`:

- `decl.value`: Validate
- `decl.value`: IR

`decl.value/generate` and `decl.value/ide` remain `partial`. No grammar, IR schema/version, Error, Consumer, App, Module/Import, runtime/generator, M16.5, release/protection workflow, or IDE behavior is widened by this closure.

## Enum Validate/IR closure

The normative enum grammar permits a case identifier with an optional `= string` assignment, while the closed Core Enum IR stores only an ordered `values` array of case names. Before this closure, `parse_enum` collected identifiers and skipped every other token in the enum body, so an assigned wire value or malformed case syntax could be accepted while its source fact disappeared before validation and IR.

`tools/aidl_parser.py` now retains deterministic per-case parser state in addition to the existing `cases` projection. Unassigned cases remain source-compatible and continue to project as ordered names. Grammar-valid assigned string values are retained only so the existing `AIDL-T005` materialization boundary can reject them until Canonical IR has a wire-value representation; no wire-value meaning is invented. The same materialization boundary rejects empty enums, duplicate case identities, malformed assignments or extra tokens, and a trailing comma rather than allowing those facts to collapse into the `values` array.

`tools/test_aidl_parser.py` proves deterministic retention of assigned and malformed case state. `tools/test_core_enum_ir_semantics.py` proves the accepted path from source through validation to Canonical IR: stable FQN/declaration identity, ordered unassigned case names, repeated-build equality, and full `spec/ir.schema.json` validity. Its negative matrix proves stable pre-IR `AIDL-T005` rejection for empty, duplicate, assigned-wire-value, malformed-assignment, malformed-extra-token, and trailing-comma forms. Existing schema mutation checks continue to prove that empty, duplicate, or missing `values` are invalid IR.

This executable evidence justifies promoting exactly these two cells from `partial` to `implemented`:

- `decl.enum`: Validate
- `decl.enum`: IR

`decl.enum/generate` and `decl.enum/ide` remain `partial`. No grammar, IR schema, wire-value semantics, generator/runtime behavior, unrelated domain declaration, Consumer, App, Module/Import, M16.5, or IDE surface is widened by this closure.

## Event Validate/IR closure

The accepted Core event contract requires versioned event declarations together with event identity/schema metadata. Before this closure, the parser allowed an event without `version`, allowed non-positive or otherwise malformed version tokens, and also recorded an optional `evolves` clause; `tools/compiler_ir.py` then defaulted an absent or invalid source version to `majorVersion=1` and did not project `evolves`. Generic event-body nodes that were not recognized as fields could likewise be skipped by the IR field projection. Those behaviors prevented a whole-cell Core Event claim because accepted source facts could be defaulted or dropped.

`tools/compiler_event_materialization.py` now places the existing `AIDL-T005` materialization boundary in front of every event in the closed Core project context. A Core event must carry an explicit positive major version, must not use `evolves` until event-evolution IR semantics are implemented, must contain at least one materializable field, and every body entry must be a losslessly projectable field. Duplicate field names, nullable-plus-required contradictions, malformed body entries, and field modifiers that Canonical IR would drop are rejected before IR rather than silently normalized away.

`tools/test_core_event_ir_semantics.py` proves the boundary directly from source. Its positive case uses an explicit version 2 and proves deterministic `majorVersion`, canonical FQN/declaration identity, ordered field names, materialized field types, requiredness, and full-document validity against `spec/ir.schema.json`. Its negative matrix proves stable `AIDL-T005` rejection for missing, zero, malformed version, `evolves`, malformed body entries, and dropped field modifiers. The existing closed-schema mutations continue to prove that zero versions, empty event schemas, and empty field names are invalid IR.

This executable evidence justifies promoting exactly these two cells from `partial` to `implemented`:

- `decl.event`: Validate
- `decl.event`: IR

`decl.event/generate` and `decl.event/ide` remain `partial`. No grammar, IR schema shape, event-evolution semantics, generator/runtime behavior, Consumer semantics, Module/Import/App claim model, M16.5 work, or IDE behavior is widened by this closure.

## Topic Validate/IR closure

The closed Core Topic IR contract contains exactly these source-derived facts: one or more canonical event IDs, `delivery`, `partitionField`, `ordering`, `retentionMs`, `compatibility`, and `deadLetterAttempts`. Before this closure, `tools/compiler_ir.py` could supply defaults for absent singleton clauses and could flatten an arbitrary partition expression into the string-valued `partitionField`, while event resolution could be deferred until IR construction. Those behaviors made the existing downstream Topic-IR evidence insufficient for a whole-cell claim.

`tools/compiler_topic_materialization.py` now puts the existing `AIDL-T005` materialization boundary in front of every full Core Topic. Each accepted Topic must declare exactly one explicit `events`, `delivery`, `partition`, `ordering`, `retention`, `compatibility`, and `deadLetter` clause. The event list must be non-empty, every reference must resolve uniquely to an event declaration, and two source references may not collapse to the same canonical event identity. Delivery is restricted to the closed Core `atLeastOnce` contract; ordering is restricted to `none` or `perPartition`; compatibility is restricted to `none`, `backward`, `forward`, or `full`; retention and dead-letter attempts must be positive; and partitioning must be a simple symbol path that can be preserved losslessly as `partitionField`. Missing, repeated, malformed, unsupported, unresolved, wrong-kind, duplicate-event, or complex-expression forms therefore fail before Canonical IR instead of receiving defaults or widened representations.

`tools/test_core_topic_materialization_contract.py` proves the complete boundary directly from source. Its positive cases build the explicit M4 Topic repeatedly, prove exact canonical event-ID preservation and all six delivery metadata fields, exercise supported non-default values, and validate the full resulting document against `spec/ir.schema.json`. Its negative cases prove stable pre-IR rejection for missing and repeated singletons, unresolved/wrong-kind/duplicate events, at-most-once delivery, global ordering, unsupported compatibility, complex partition expressions, and non-positive retention/dead-letter values. `tools/test_core_topic_delivery_ir_semantics.py` remains the focused downstream schema regression for the same closed Topic IR shape.

This executable evidence justifies promoting exactly these two cells from `partial` to `implemented`:

- `decl.topic`: Validate
- `decl.topic`: IR

`decl.topic/generate` and `decl.topic/ide` remain `partial`. No grammar, IR schema shape, generator/runtime behavior, Consumer semantics, or IDE behavior is widened by this closure.

No IDE cell is currently marked `implemented`, so the registry does not manufacture IDE completeness from workflow or documentation evidence. The same rule applies to every remaining `partial` or `missing` cell in any layer: executable tests may exist for a subset of behavior, but status remains open until the matrix can truthfully claim layer completeness.

The transaction block reduced the first M10 acceptance gap by four partial layer cells and the third acceptance gap by preserving two required transaction semantic facts in Canonical IR. The entity ownership block reduced the first gap by three additional IR cells and extended the third acceptance evidence to canonical owner-service, owner-local access, and ref-owner facts. The API block reduced the first gap by one additional IR cell and extended the third acceptance evidence to canonical transport, major-version, operation-exposure, and compatibility facts. The consumer-idempotency block reduced the first gap by one additional IR cell and extended the third acceptance evidence to canonical idempotency key, scope, and retention facts. The error-contract block adds focused evidence without claiming whole-cell completeness. The Alias/Opaque block closes both Validate and IR for `decl.alias` and `decl.opaque`, adds both declarations to the Core Supported fixture set, and removes unresolved/ambiguous nominal widening plus unsupported target-form loss from the remaining Canonical-IR preservation gap. The Value block closes both `decl.value/validate` and `decl.value/ir`, adds Value to the Core Supported fixture set, and removes invariant/body/modifier dropping from the Canonical-IR preservation gap. The Enum block closes both `decl.enum/validate` and `decl.enum/ir`, adds the declaration to the Core Supported fixture set, and removes enum assignment/malformed-token dropping from the Canonical-IR preservation gap. The Event block closes both `decl.event/validate` and `decl.event/ir`, adds the declaration to the Core Supported fixture set, and removes Event version defaulting and unsupported body/evolution dropping from the Canonical-IR preservation gap. The Topic block closes both `decl.topic/validate` and `decl.topic/ir`, adds the declaration to the Core Supported fixture set, and removes Topic defaulting/widening from the remaining Canonical-IR preservation gap. M10 criteria 1 and 3 remain open only for unrelated partial Core rows that require independent closure or explicit claim-model decisions.
