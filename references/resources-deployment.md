# Resources and Deployment

## Portable Resources

Resources describe required semantics. Deployment adapters bind them to local or managed products.

Resource kinds:

- `sql`, `document`, `keyValue`, `timeSeries`
- `blob`, `cdn`
- `cache`
- `queue`, `topic`, `stream`
- `search`
- `counter`
- `secretRef`, `configRef`
- `localStore`

Operations list every used store explicitly. A local transaction may include exactly one transactional owner.

## SQL, Blob, CDN, Cache, Streams, Search

SQL resources declare consistency, supported isolation, migration mode, backup RPO/RTO, and encryption.

Blob resources declare upload mode, max object size, checksum, versioning, encryption, and lifecycle. CDN resources declare origin, access mode, cache semantics, and purge method.

Cache resources declare consistency, entry size, and encryption. Streams declare partitioning, retention, and replay. Search resources declare consistency and rebuild source.

## Media Profile

`BlobHandle<S>` is an opaque serializable reference with store ID, object key, version, hash, size, and media type. It never contains provider credentials.

`UploadSession<S>`, `BlobHandle<S>`, and `RenditionSet<S>` are standard media types. Upload begin validates type, size, quota, and idempotency and returns short-lived upload rights scoped to the declared store.

Delivery handles are credential-free and exchanged by adapters for short-lived signed URLs/cookies per authorized request. Expiring URLs are not domain state.

## Deployment

Deployments declare environment, target, regions, data residency, service replica ranges, availability, autoscaling, resources, health checks, rollout, shutdown, bindings, observability, and SLOs.

The adapter must prove that health, autoscaling, and rollout preserve minimum replica requirements.

Local `colocate services all` changes only physical placement. Service identities, ownership, and contracts still apply.

## Regions and Failover

Multi-region deployment can declare routing, active-active services, primary resources, read replicas, and failover RPO/RTO. Active-active is valid only when writes have compatible concurrency/replication semantics. Multiple replicas do not imply multi-region write safety.

## Serverless and Workers

`target functions` requires no local persistent session, bounded runtime, idempotent event processing, and declared cold-start/concurrency limits. Long-running workflows are persisted by durable workflow adapters, not kept in function memory.

## Secrets and Config

Secret values are never DSL literals. `secret("NAME")` and `config("NAME")` are references. Generators must not put secrets in plans, logs, client bundles, or manifest hashes.

Config is typed and may include non-sensitive public values. Changes declare `restart`, `reload`, or `immutable`.

## Observability

Request, workflow, operation, and message IDs propagate as correlation context.

Telemetry declares logs, metrics, traces, sampling, PII/secret redaction, retention, SLO alerts, and cost budget.

## Adapter Capabilities

Provider adapters have versioned capability matrices. Build fails if isolation, retention, ordering, region, backup, security, auth, secret handling, or data-loss guarantees cannot be met. Silent downgrade is forbidden.

