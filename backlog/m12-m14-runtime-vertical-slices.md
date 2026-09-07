# M12–M14 — Runtime vertical slices

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
