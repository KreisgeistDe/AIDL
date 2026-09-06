# Distributed Systems

## Services and System

A service is the entity ownership boundary, transaction boundary, deployment/versioning component, and service-to-service identity.

```dsl
service PetstoreService {
  owns [Shelter, Pet, AdoptionRequest]
  uses [PetstoreDb, AdoptionEvents]
  exposes [query listAvailablePets, mutation requestAdoption]
  runs [consumer StartAdoptionReview, workflow ReviewAdoption]
  reliability {
    idempotencyStore PetstoreDb
    inboxStore PetstoreDb
    workflowStore PetstoreDb
  }
}
```

Reliability stores bind runtime state explicitly:

- `idempotencyStore`: keys, input hashes, results, retention.
- `inboxStore`: consumer claims and dedupe.
- `workflowStore`: steps, timers, approvals, compensation.
- `projectionStore`: checkpoints and rebuild generation.
- `syncStore`: operation dedupe, cursors, canonical revisions.

All redundant service instances must share logically consistent reliability stores. In-memory bindings are valid only for local deployments.

## Ownership

1. Every persisted entity has exactly one owner service.
2. Only the owner may directly use the underlying store.
3. `ref` cannot cross owner boundaries.
4. Other services use IDs, immutable snapshots, public operations, or events.
5. Imports grant no data access.
6. Invariants cover only one local transaction boundary.

The compiler builds a data-access graph and rejects hidden shared-database coupling.

## Synchronous Calls

Clients declare timeout, retry, circuit breaker, and bulkhead per call. Retries are valid only for pure queries or idempotent mutations. Timeout covers the entire operation unless `attemptTimeout` is declared.

Synchronous service graphs have budgets for depth, latency, and fan-out. Cycles are invalid.

## Async Messaging

Events are facts. Queue commands are work requests. Topics fan out to independent consumer groups; queues distribute within one worker group.

Every message has `messageId`/`eventId` and `occurredAt`/`enqueuedAt`. `atMostOnce` requires explicit data-loss acceptance. `exactlyOnce` is not an allowed distributed delivery value.

`ordering perPartition` requires `partition by`. Global ordering is only for bounded streams with throughput budget.

## Dedupe

Consumer idempotency stores at least consumer ID, schema version, message ID, status, expiry, and optional side-effect references. Claim and commit must be atomic with local writes or use inbox plus outbox. External APIs need their own idempotency keys or reconciliation.

## Consistency and Projections

Read consistency levels:

- `strong`: committed data visible on next read.
- `session`: own confirmed changes visible in session.
- `boundedStaleness`: maximum known lag.
- `eventual`: convergence without fixed bound.

Cross-service read models are projections and at least eventual. APIs and UIs must expose that behavior.

Projections consume versioned events and write only to their target store. They need deterministic mapping, checkpoint per partition, dedupe, rebuild strategy, max lag, and schema/alias migration plan.

## Redundancy

Horizontal replication is safe only when request state is external, mutations have idempotency/concurrency, schedulers have singleton leases, consumers use inbox/idempotency, workflow steps use stable IDs, and sessions are signed tokens or shared-store state.

Distributed profiles forbid in-memory singletons, local cron jobs, and non-persisted retry counters.

## Realtime

Channels declare transport class, delivery, ordering, resume, backpressure, auth, and fallback. WebSocket, SSE, and push are adapters; semantic guarantees remain transport-neutral.

## Tenancy and Identity

Tenant isolation can be `row`, `schema`, `database`, or `deployment`. Every query, mutation, projection, cache key, and topic partition must propagate the tenant key. Events and cache keys without required tenant context are invalid.

Service-to-service calls use `servicePrincipal`. Delegated user identity must be signed with audience and expiry. A service must not transitively trust unchecked client claims.

