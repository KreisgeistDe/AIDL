# M4-04 PostgreSQL persistence generator

## Scope

M4-04 adds deterministic PostgreSQL 17 schema and initial SQL migration generation for the supported entity subset. The generator consumes canonical AIDL IR `0.3.0` only and emits:

- `generated/schema.sql`
- `generated/migrations/0001_initial.sql`

It does not parse `.aidl` source, use compiler/parser objects, or depend on IntelliJ PSI.

## Supported persistence subset

The first persistence slice supports canonical `entity` declarations whose persisted fields are representable by:

- Core scalar types: `string`, `int`, `decimal`, `bool`, `uuid`, `date`, `datetime`, `duration`, `revision`, `email`, `url`, and `bytes`;
- nullable wrappers around supported types;
- non-generic named `enum`, `alias`, and `opaque` declarations when aliases/opaque representations ultimately resolve to the supported subset;
- owner-valid canonical `ref` fields whose target entity has exactly one supported identity field.

Canonical entity `identityFields` become PostgreSQL primary keys. Supported scalar constraints are projected to deterministic `CHECK` constraints where the canonical IR carries them. Named enums are stored as `text` with deterministic `CHECK ... IN (...)` constraints rather than PostgreSQL enum types. Canonical `onDelete` values map to PostgreSQL foreign-key actions.

A canonical non-null scalar `revision` field marked both `generated` and `concurrencyToken` is store-owned and emitted as `bigint NOT NULL DEFAULT 1`. The concrete starting value is a deterministic PostgreSQL representation of the existing opaque monotonic generated-token contract; callers do not assign it on create, and no new AIDL source semantics are introduced.

Collection, record/value-object persistence, generic named types, unresolved named/ref targets, multi-field ref identities, and other unsupported type shapes fail explicitly with `PostgresPersistenceGeneratorError`. M4-04 does not silently serialize unsupported values to JSON or drop fields.

## Deterministic naming and output

Table names derive only from canonical entity FQNs by lowercasing and replacing non-alphanumeric separators with `_`. Column names come from canonical field names and are quoted. Entities are emitted in canonical FQN/declaration-ID order; fields preserve canonical IR order. Table/check/foreign-key names are deterministic and collisions are rejected.

The initial migration contains the same generated schema prefixed with a migration header. No timestamp, random ID, branch name, or source-file path participates in generated output.

## Boundary to later M4 work

M4-04 defines storage schema only. It intentionally does not generate transaction execution, isolation handling, compare-and-set/optimistic concurrency behavior, idempotency storage/runtime, outbox/events, generated-code ownership enforcement, package/build configuration, application startup, or database execution tooling. The store-owned initial value for a canonical generated `revision` concurrency token is part of the persistence representation; atomic compare-and-set and increment behavior remain the M4-05 transaction contract.

The generator respects M4-02 domain semantics and M4-03 API contracts without reinterpreting language semantics for persistence.
