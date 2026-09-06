# Evolution and Compatibility

## Versioned Artifacts

Independently versioned:

- language and profiles
- application release
- public API
- event schema
- sync protocol
- persisted schema
- native adapters
- deployment adapters

The `app` version does not replace these compatibility declarations.

## Semantic Diff

`aidl plan` and `aidl compatibility` classify changes:

- `compatible`: rollout without coordination.
- `expandable`: additive expand phase required first.
- `coordinated`: producer/consumer overlap required.
- `breaking`: explicit migration or new major required.
- `dataLoss`: separate confirmation and recovery plan required.

Pure formatting does not produce a semantic diff.

## API Compatibility

Usually compatible:

- new optional input field with default
- new output field
- new declared error only in a new API major or when clients allow unknown errors

Usually breaking:

- removing or renaming a field
- narrower input constraint
- broader output nullability
- auth, consistency, or idempotency change
- stable error code change

## Event Compatibility

Events are immutable. New shape means new schema version, optionally with `evolves`.

Upcasters are pure and deterministic. Consumers declare accepted versions. A backward-compatible topic must not lose old messages that can be upcast.

## Database Migration

Zero-downtime flow:

1. `expand`: additive schema or dual-read support.
2. `deployReaders`: new code reads old and new schema.
3. `backfill`: resumable idempotent checkpointed job.
4. `switchWrites`: new canonical write path.
5. `verify`: compare invariants and counts.
6. `contract`: remove old representation after compatibility window.

Destructive steps need breaking-change classification, backup/restore proof, and explicit data-loss classification.

## Projections and Search

Incompatible projection mapping creates a parallel target index:

1. create new index
2. replay event log
3. verify lag and samples
4. atomically switch alias
5. remove old index after rollback window

Projection versions, rebuild strategy, and alias migration must be explicit.

## Offline Clients

Sync changes check min/max client version, new-field readability, old-operation upcasts, tombstone watermark, full-resync need, and expired-client behavior.

Servers reject obsolete clients only with typed `UpgradeRequired`. Unsynced local data must remain exportable or migratable.

## Rolling Deployments

Simultaneously active versions must be compatible across API producers/consumers, event producers/consumers, store readers/writers, workflow steps, idempotency key formats, caches, and projections.

`maxUnavailable 0` is invalid when migration requires an exclusive incompatible schema window.

## Removing Contracts

Public fields, events, and operations move through:

`deprecated -> usageObservedZero -> disabled -> removed`

Observation duration and telemetry source must be declared. Missing telemetry is not zero usage.

