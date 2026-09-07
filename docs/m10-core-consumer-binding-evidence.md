# M10 Core consumer binding evidence

This focused closure narrows the remaining Core `consumer` Validate/IR gap without changing syntax, generator/runtime behavior, editor support, or the conformance matrix status.

The normative Core consumer boundary already requires `consumer NAME on EVENT from TOPIC`, Core delivery is at-least-once, and a bound consumer must consume an event declared by its source topic. `AIDL-DIST415` now rejects a missing binding header, unresolved event/topic references, a bound event absent from the topic event contract, and a bound topic that omits explicit `atLeastOnce` delivery or declares a non-Core delivery mode. Diagnostics are deterministic, source-located, and emitted before Canonical IR construction.

`tools/test_core_consumer_binding_semantics.py` provides positive and negative executable evidence. The positive case proves that a valid binding remains diagnostic-free and that the already accepted Canonical IR deterministically preserves the resolved `eventId`, `topicId`, and existing consumer idempotency contract. Negative cases cover every rule added by this closure.

This block intentionally does not claim exhaustive `decl.consumer/validate` or `decl.consumer/ir` coverage. The wider grammar still admits consumer `service`, retry, start/call, and transaction clauses whose complete validation/materialization contract is not closed here. In particular, this work does not invent exactly-once delivery, retry execution guarantees, ordering guarantees beyond the topic contract, or runtime behavior. `decl.consumer/validate` and `decl.consumer/ir` therefore remain `partial`, and M10 acceptance criteria 1 and 3 remain open while criteria 2 and 4 remain complete.
