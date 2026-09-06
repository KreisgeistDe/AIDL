# Core Language

## Intent

AIDL minimizes the solution space for coding agents by making system semantics explicit in source and IR. A capability is first-class only if the IR represents it, invalid combinations are statically diagnosed, generators get deterministic plans, and failures/retries/evolution are testable.

Architecture layers:

- Application model: domain types, invariants, operations, policies, workflows, UI, quality requirements.
- System model: services, data ownership, allowed dependencies, topics, consumers, projections, consistency, replication.
- Deployment model: environments, placement, replicas, scaling, rollout, failover, resources, data residency, SLOs.

## Project Shape

```aidl
module petstore.domain.pets

import aidl.std.Page
import petstore.common.Money

export entity Pet { ... }
```

- Files end in `.aidl`, use UTF-8, and are named lowercase-kebab-case.
- Type and component names use PascalCase.
- Operation and field names use camelCase.
- Imports use project namespaces, never relative file paths.
- Cyclic module dependencies are invalid.
- `generated/` must not be edited by coding agents.

The `app` block activates profiles and pins their versions in the lockfile:

```aidl
app Petstore {
  profile core version 1
  profile web version 1
  profile distributed version 1
  profile cloud version 1
  system PetstoreSystem
  frontend PetstoreWeb
}
```

## Types

Scalars: `string`, `int`, `decimal`, `bool`, `uuid`, `date`, `datetime`, `duration`, `revision`, `email`, `url`, `bytes`, `json<S>`.

Collections and wrappers:

- `T?`: nullable.
- `[T]`: ordered list.
- `set<T>`: unique unordered set.
- `map<K,V>`: map with scalar or value keys.
- `ref Entity`: local owner-bounded entity reference.
- Large files use `BlobHandle<S>` from the media profile, not `bytes`.

Implicit conversions are forbidden except lossless `int` to `decimal`. Null, absence, and empty collection are distinct.

## Generics

Allowed on `value`, `union`, `view`, `component`, and `native function`. Persisted `entity` and `error` declarations cannot be generic.

Allowed bounds: `serializable`, `scalar`, `value`, `entityView`, `ErrorValue`, `comparable`, `hashable`. Multiple bounds use `&`.

Generics are invariant, compile-time resolved, monomorphized for stable schema output, and have no runtime reflection, higher-kinded types, conditional types, or mapped types.

## Declarations

- `enum` defines stable cases.
- `alias` does not create a new type.
- `opaque` creates a nominally distinct type with explicit adapter-boundary conversion.
- `union` variants have stable tags and default wire shape `{ kind: "<variant>", ...fields }`.
- `error` is a nominal serializable public contract with stable code, transport mapping, retry class, safe message/localization, and only public fields.
- Unknown internal failures crossing public boundaries become `InternalFailure`.

## Entities and Views

Entity rules:

- Exactly one primary key.
- Concurrent mutable entities should have a `revision generated concurrencyToken`.
- `generated`, `primary`, and `immutable` fields are omitted from generated patch types.
- `ref` is only valid between entities owned by the same service.
- Cross-service references use nominal IDs, snapshots, APIs, or events.
- Invariants are checked on every local commit.
- A service may directly read/write only its own entities.

Views are immutable serializable projections. They may navigate only local `ref` relationships. Cross-service read models are `projection` declarations.

## Field Semantics

- `required`: value required at creation.
- `T?`: stored/transmitted value may be null.
- `immutable`: cannot change after creation.
- `mutable`: can change through explicit mutations.
- `sensitive`: triggers redaction, audit, storage, and deletion rules.
- `generated`: assigned by runtime/store.

## Expressions and Effects

Expressions are pure. Effects exist only in declared contexts:

- `read`: query, policy, mutation, workflow step, consumer.
- `write`: mutation, consumer through mutation, workflow through mutation.
- `publish`: local transaction via outbox or explicit consumer.
- `external`: native function with capability.
- `clock`: operation with nondeterministic clock effect.
- `random`: operation with nondeterministic random effect.

`now()` and `uuid()` are not hidden pure functions. Clock and random source are injected and recorded for deterministic tests.

## Hard Limits

No overloads, custom operators, implicit semicolons, unbound `dynamic`/`any`, hidden network or DB access, duplicate canonical definitions, or unstable public declaration IDs.
