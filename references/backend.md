# Backend

## API Surfaces

`service.exposes` defines a logical service contract; `api` defines the external transport surface.

```dsl
api PetstoreApi {
  transport rest
  version 1
  basePath "/api/v1"
  operations [
    query listAvailablePets,
    mutation requestAdoption
  ]
  auth inherit
  errors problemDetails
  compatibility backward
  rateLimit principal 300 per 1m burst 50
}
```

Rules:

- Internal operations are not external unless mapped by `api`.
- API surfaces have major version and compatibility mode.
- Supported transports are `rest`, `rpc`, and `graphql`.
- Transport status and wire names derive from typed errors.
- GraphQL must preserve the same nullability, error, and paging semantics as REST/RPC.
- Breaking public changes require a new API major version.

## Queries

Queries are side-effect-free, bounded by default, and may read only owner-local data or declared projections.

Every collection query must have a limit, page contract, or stream contract. Consistency is one of `strong`, `boundedStaleness(max: duration)`, `session`, or `eventual`.

Queries should declare auth, read expression, consistency, cache, errors, and timeout when public or operationally relevant.

## Mutations

Every mutation must declare:

- `auth`
- `allow`
- `errors`
- `idempotency`
- one root effect

`auth: public` requires a `publicReason` annotation.

Allowed root effects:

- one local `transaction`
- one idempotent resource `call`
- start of a workflow or saga

Idempotency stores key, scope, normalized input hash, result or public error, and expiry atomically. Same key with different input is `IdempotencyMismatch`. Expiry is not an exactly-once guarantee.

## Authorization

Policies may read local data but cannot write, publish, or do network I/O. Cross-service authorization uses signed claims or explicit read-only `authorize: remote query ... else Error`. Remote auth failure denies or returns a declared dependency error; it must never silently allow.

Remote authorization is not a distributed invariant. If foreign state must remain reserved until commit, model a reservation or saga.

## Transactions

A transaction has exactly one transactional resource owner. Isolation: `readCommitted`, `repeatableRead`, `serializable`. The adapter must support the declared isolation.

Optimistic writes use atomic compare-and-set:

```dsl
write: pet.update(status: pending)
  expect revision input.expectedPetRevision
  else ConcurrentChange
```

Invariants are checked after writes and before commit. Cross-service and cross-database transactions are forbidden.

## Events and Topics

Events are versioned facts in past tense and must include `eventId`, `occurredAt`, and schema version.

Topics declare:

- event types
- delivery
- partitioning
- ordering
- retention
- compatibility
- dead-letter behavior

Inside a transaction, `emit` must use `via outbox`. State and outbox entry commit atomically. Delivery remains at-least-once.

## Consumers

Consumers are invoked at-least-once. They need an idempotency clause unless proven pure. Ordering assumptions are valid only within the declared partition key. Poison events move to dead-letter after retry budget; replay is a new delivery with the same event ID.

## Workflows, Sagas, Tasks

Workflows persist steps, timers, approvals, and retries in the declared workflow store. Step IDs must be stable.

Sagas model distributed invariants by reservation, command/event, confirmation, and compensation. Every committed reversible step requires an idempotent compensation; irreversible steps require explicit justification.

Tasks declare execution, queue, retry, idempotency, resources, errors, and timeout as needed.

