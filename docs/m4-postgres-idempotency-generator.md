# M4-06 PostgreSQL Idempotency Generator

M4-06 adds deterministic idempotency plumbing for the first supported TypeScript + PostgreSQL runtime slice. The generator consumes canonical AIDL IR `0.3.0` only and does not reparse AIDL source or use IntelliJ PSI.

## Generated outputs

`tools/generate_postgres_idempotency.py` emits:

- `generated/idempotency.ts` — idempotency plans plus a small PostgreSQL-backed runtime wrapper;
- `generated/migrations/0002_idempotency.sql` — the deterministic idempotency-record table and expiry index.

## Supported mutation subset

The M4-06 subset is intentionally the same owner-local transaction mutation subset that M4-05 can execute. A generated mutation must:

- have canonical `rootEffect.kind == "transaction"`;
- contain canonical idempotency `key`, `scope`, and positive `retentionMs`;
- be exposed by exactly one canonical service;
- have that service declare `reliability.idempotencyStoreId`;
- use a SQL idempotency store;
- use the same resource for the idempotency store and the mutation transaction, so this first slice does not invent cross-resource atomicity.

Canonical idempotency key/scope expressions are limited to scalar literals or `input.*` symbol paths. Other expression shapes fail explicitly instead of receiving generator-local semantics.

## Runtime behavior

The generated table is keyed by `(operation_id, scope, key)` so two mutation declarations cannot collide merely because they use the same scope/key value. Records expire according to canonical `retentionMs`.

The generated wrapper:

1. resolves canonical key and scope from the mutation input;
2. replays the stored result for an unexpired completed record;
3. atomically claims a new key using PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`;
4. reports `AIDL_IDEMPOTENCY_IN_PROGRESS` when another execution owns the same unexpired key;
5. executes the caller-supplied mutation function;
6. persists the completed JSON result for future replay;
7. removes a still-running claim if execution fails, so a later retry can execute again.

The caller-supplied executor remains the M4-05 transaction/concurrency boundary. M4-06 does not alter optimistic-concurrency SQL or introduce a second transaction interpretation.

## Explicit boundaries

M4-06 does not implement:

- cross-resource idempotency atomicity;
- events or transactional outbox execution;
- generated-code ownership markers;
- database startup/provisioning;
- package/dependency manifests or application scaffolding;
- build/run behavior.

Unsupported canonical shapes fail with `PostgresIdempotencyGeneratorError`.
