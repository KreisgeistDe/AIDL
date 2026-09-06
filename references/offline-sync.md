# Offline Sync

## Models

Sync model is chosen per aggregate/scope:

- `serverAuthoritative`: client cannot write offline; server is final authority.
- `queuedCommands`: client queues operations offline, not confirmed state; server is final authority.
- `replicated`: client can write; declared merge plus server validation is final.

Offline-created entities need globally unique `clientGenerated` IDs. `revision` is assigned only by the confirming server or convergence log.

## Sync Contract

A sync declaration defines mode, authority, scope, local/server stores, operation log, push/pull, change feed, tombstones, conflict rules, rejected behavior, and schema migration.

`serverStore` is the atomic commit boundary. `changes to ... via outbox` means confirmed state, new revision, operation dedupe status, and change-feed entry commit together.

Pull streams are at-least-once; local application dedupes by cursor and entity ID.

## Operation Log

Each local operation contains:

- operation ID
- device ID and actor/subject
- entity ID
- base revision or causality context
- typed patch or command
- local ordering
- client schema version
- optional blob tickets

The server deduplicates `operationId` within the declared scope. Confirmed operations receive server revision and canonical state.

## Clocks and Causality

Device time is never authoritative for conflict resolution. Valid clocks:

- `serverSequence`
- `serverHlc`
- `vector` for bounded replica groups

`deviceTime` may be stored as user-facing metadata only.

## Conflict Strategies

- `reject`: sensitive or non-mergeable changes.
- `serverWins`: server-authoritative field.
- `lww(serverSequence/serverHlc)`: independent register.
- `max`/`min`: monotonic numbers or times.
- `addWinsSet`/`removeWinsSet`: sets with declared delete semantics.
- `counter`: commutative counter.
- `manual`: user decision.
- `custom deterministic`: pure checked merge function.

Fields participating in an invariant must be merged as a conflict group. Example: `startsAt` and `endsAt` must not be independent LWW fields.

Custom merge functions must be deterministic, pure, and capability-free.

## Tombstones

Physical deletion before tombstone retention expires can resurrect data from old clients. Retention must cover max offline duration plus maximum sync delay.

After expiry, each client needs full resync, a server snapshot after delete watermark, or verified minimum revision.

## Authorization and Rejection

Offline accepted writes are provisional. On push, server rechecks identity, authorization, tenant, quota, and invariants.

Revoked permissions produce `rejected`, never silent acceptance. Sensitive local data requires encryption at rest and declared deletion on sign-out or device revocation.

Rejected operations include stable error code, canonical server state, affected local operation, and actions such as `discard`, `editAndRetry`, or `requestAccess`. UI must handle all possible outcomes; silently discarding local user data is forbidden.

## Media and Schema Changes

Operations reference blob tickets, not raw bytes. Required blob uploads must be server-bound before operation confirmation. Orphan uploads need TTL and cleanup.

Changes to replicated types classify `serverBackwardCompatible`, `oldClientReadable`, `operationUpcastRequired`, and `fullResyncRequired`. Old clients must not upload operations whose meaning is no longer unambiguous.

Core support covers server-coordinated multi-writer replication, not arbitrary serverless P2P, Byzantine fault tolerance, or custom consensus without a profile/native integration.

