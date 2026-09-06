# M4-05 PostgreSQL transaction and optimistic-concurrency generator

M4-05 adds the transaction/concurrency slice for the M4-01 PostgreSQL 17 + `pg` stack. The generator is `tools/generate_postgres_transactions.py` and consumes canonical AIDL IR `0.3.0` only. It does not parse `.aidl` source or use compiler/IntelliJ PSI objects as semantic input.

## Generated contract

`generate_postgres_transaction_files()` emits deterministic `generated/transactions.ts`. Transaction mutations are ordered by canonical FQN/declaration ID. The generated module contains deterministic transaction plans, a small `pg`-compatible client contract, an executor, and one operation wrapper per supported transaction mutation.

Each supported canonical `rootEffect.kind == "transaction"`:

- resolves its canonical `resourceId` through `system.resources`;
- requires an SQL resource whose `transactionIsolation` explicitly contains the requested isolation;
- maps `readCommitted`, `repeatableRead`, and `serializable` to PostgreSQL `READ COMMITTED`, `REPEATABLE READ`, and `SERIALIZABLE`;
- executes `BEGIN`, `SET TRANSACTION ISOLATION LEVEL ...`, the generated steps, then `COMMIT`, and attempts `ROLLBACK` on failure.

The supported read shape is one canonical `byId` or `require` step against an M4-04-supported entity with one identity field. Required reads preserve their canonical `elseErrorId`.

## Optimistic concurrency

M4-05 treats canonical `expectedRevision` on `update`/`delete` writes as compare-and-set input. The target entity must expose exactly one `concurrencyToken` field. For an update, the generated PostgreSQL statement combines identity and expected revision in the `WHERE` clause and increments the concurrency-token column in the same statement. Delete combines identity and expected revision in the same `DELETE ... RETURNING` statement. A row count other than one raises `AidlTransactionError` with the canonical write `elseErrorId`.

This is atomic PostgreSQL compare-and-set behavior; there is no read-then-write revision check outside the statement.

Create writes are supported without an expected revision. A concurrency token must not be present in canonical create values: it remains store-owned, and for the supported generated scalar `revision` token M4-04 supplies the deterministic PostgreSQL initial value. `upsert` is outside the M4-05 subset because its concurrency contract is not yet repository-defined.

## Existing persistence contract reuse

Table naming comes from the M4-04 PostgreSQL persistence generator contract. Entity identity and concurrency-token metadata come from canonical IR. M4-05 does not introduce a second persistence type system or reinterpret M4-04 SQL mappings. In particular, create omits the generated concurrency token, while update continues to increment that token atomically in the compare-and-set statement.

## Explicit unsupported boundaries

Generation fails instead of silently weakening semantics for:

- unsupported IR versions, unresolved/non-SQL resources, or undeclared transaction isolation;
- transaction reads other than one `byId`/`require` identity lookup;
- entities without the single-field identity required by the current persistence subset;
- concurrent update/delete without a canonical `expectedRevision`, `elseErrorId`, target binding, or concurrency token;
- direct assignment of the concurrency-token field, including create writes;
- `upsert` and unknown transaction-step kinds;
- transactional publish/outbox steps, which remain the later event slice.

M4-05 intentionally adds no idempotency runtime, event/outbox execution, generated-code ownership enforcement, dependency manifests, application scaffolding, database startup, or build/run path.
