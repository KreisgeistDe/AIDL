# M4 PostgreSQL Transactional Outbox Generator

M4-07 adds deterministic transactional outbox/event integration for the first supported TypeScript + PostgreSQL slice. The generator boundary remains canonical AIDL IR `0.3.0` only; source syntax and IntelliJ PSI are never semantic inputs.

## Generated files

`tools/generate_postgres_outbox.py` emits:

- `generated/outbox.ts` — provider-neutral PostgreSQL outbox relay primitives and deterministic publish-plan metadata.
- `generated/migrations/0003_outbox.sql` — the PostgreSQL outbox table and pending-message index.

`tools/generate_postgres_transactions.py` projects canonical transaction `publish` steps into `INSERT INTO "aidl_outbox" ...` statements executed inside the existing M4-05 `BEGIN`/isolation/`COMMIT` boundary. State writes, optimistic-concurrency compare-and-set operations, create-result bindings used by later expressions, and outbox inserts therefore share one PostgreSQL transaction.

## Supported canonical publish contract

The M4-07 slice supports transaction steps with:

- `kind: "publish"` and `via: "outbox"`;
- a resolvable canonical `eventId` declaration with positive `majorVersion`;
- a resolvable canonical `topicId` whose `eventIds` contains the event;
- topic delivery `atLeastOnce`;
- positive canonical topic `retentionMs`;
- a canonical record payload containing every required event field;
- required event fields `eventId` and `occurredAt`;
- the canonical topic `partitionField` present in the payload.

Payload expressions reuse canonical value expressions. The source-to-IR producer normalizes parser-preserved transaction-clause spacing and projects the repository intrinsics `operationId()` and `now()` as canonical zero-argument calls. The generated transaction runtime resolves `operationId()` from the mutation input's existing `operationId` field and resolves `now()` to one stable ISO timestamp per transaction execution. Other function-like producer symbols/calls are rejected instead of guessed.

The current IR schema does not add a new create-binding field. For the supported slice, the transaction generator reconstructs a lost create-result binding only when later publish/result expressions identify it unambiguously; it then stores the `RETURNING *` row under that binding. Ambiguous recovery fails explicitly.

## PostgreSQL outbox contract

`0003_outbox.sql` creates `aidl_outbox` with stable event identity, event type/version, topic, partition key, JSON payload, occurrence time, availability/expiry timestamps, publication timestamp, and delivery-attempt count.

The generated relay surface is intentionally broker-neutral because M4-01 selects PostgreSQL but does not select a messaging provider. It provides:

- ordered pending-message claiming with `FOR UPDATE SKIP LOCKED`;
- attempt accounting;
- explicit successful-publication marking;
- retry release with a caller-provided delay.

The boundary is at-least-once: a relay may publish a message more than once if failure occurs after broker publication but before the local published marker is committed. Consumers remain responsible for deduplication as required by the existing distributed-systems contract.

## Preserved M4 contracts

M4-07 does not replace or weaken earlier behavior:

- M4-04 persistence mappings remain unchanged.
- M4-05 transaction isolation and optimistic-concurrency SQL remain the transaction boundary.
- M4-06 idempotency remains outside and around the mutation executor; M4-07 does not reinterpret its claim/replay contract.
- Transactional event publication is added as another step inside the same PostgreSQL transaction.

## Explicit unsupported boundary

Generation fails instead of guessing when a publish is not `via outbox`, an event/topic is unresolved, a topic does not declare the event, delivery is not `atLeastOnce`, retention/version metadata is invalid, the payload is not a canonical record, required event fields are absent, the partition field is absent, a producer function is outside the executable intrinsic subset, or create-result binding recovery is ambiguous.

M4-07 does not add a broker/provider adapter, generated-code ownership enforcement, dependency manifests, database startup, application scaffolding, or build/run behavior. Those remain later roadmap work.
