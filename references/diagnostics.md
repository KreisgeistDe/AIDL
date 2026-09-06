# Diagnostics, Tooling, IR, and Limits

## Agent Workflow

Preferred CLI workflow for AIDL changes:

1. `aidl describe --format json`
2. `aidl explain NAME --format json`
3. Inspect topology, owner, consistency, and profiles.
4. Produce the smallest complete AST patch.
5. `aidl check --format json`
6. `aidl plan`
7. Run compatibility and failure simulations where relevant.
8. `aidl build --locked` and tests.

Prefer `aidl edit` atomic AST operations over textual search/replace. Include preconditions such as schema hash and language version.

## Agent Prohibitions

- Do not edit generated files.
- Do not invent unknown keys, profiles, or libraries.
- Do not disable compiler/profile rules to bypass errors.
- Do not create public writes without auth and idempotency.
- Do not bypass service ownership through direct store access.
- Do not create event consumers without dedupe unless proven pure.
- Do not call external effects exactly-once.
- Do not resolve offline conflicts with client time as authority.
- Do not embed secrets or sensitive sample data.
- Do not use free CSS/design values where tokens are required.
- Do not create destructive migrations without breaking-change plan.

## Compiler Phases

- `parse`: tokens and grammar.
- `resolve`: names, imports, cycles.
- `type`: generics, constraints, nullability.
- `effect`: purity, capabilities, side effects.
- `policy`: auth, ownership, data classification.
- `transaction`: isolation, revisions, outbox.
- `topology`: services, contracts, forbidden store access.
- `delivery`: topics, consumers, ordering, dedupe.
- `sync`: authority, delta, tombstones, conflicts.
- `ui`: bindings, states, a11y, tokens.
- `compatibility`: API, event, store, client evolution.
- `deployment`: resources, regions, SLO, capacity.
- `emit`: generator contract and hashes.

## Diagnostic Shape

Diagnostics include severity, code, message, source location, subject, expected condition, allowed fixes, and docs URI.

Common codes:

- `AIDL-E101`: unknown keyword/profile key.
- `AIDL-E121`: unresolved reference.
- `AIDL-T140`: invalid generic instantiation.
- `AIDL-T162`: non-serializable public type.
- `AIDL-E203`: missing authorization.
- `AIDL-E241`: undeclared capability.
- `AIDL-E260`: undeclared public error.
- `AIDL-TX301`: cross-owner transaction.
- `AIDL-TX312`: unsafe concurrent write.
- `AIDL-TX321`: transaction event without outbox.
- `AIDL-MIG310`: possible data loss.
- `AIDL-COMP340`: incompatible contract change.
- `AIDL-DIST401`: direct foreign entity access.
- `AIDL-DIST411`: non-idempotent consumer.
- `AIDL-DIST421`: ordering without partition.
- `AIDL-DIST431`: projection without rebuild strategy.
- `AIDL-DIST432`: retention insufficient for full rebuild.
- `AIDL-SYNC501`: replicated entity without tombstone rule.
- `AIDL-SYNC511`: ambiguous conflict strategy.
- `AIDL-SYNC521`: client clock as authoritative LWW clock.
- `AIDL-DEP601`: SLO not satisfiable by deployment.
- `AIDL-DEP611`: secret literal.
- `AIDL-UI204`: missing async state.
- `AIDL-UI231`: inaccessible interaction.
- `AIDL-UI252`: free design value.
- `AIDL-UI271`: unhandled sync conflict in UI.

## Tests

Use focused DSL tests matching the touched contract:

- Full-stack: user workflows, stored state, emitted logical events.
- Concurrency: optimistic revision and invariant races.
- Delivery/failure: outbox, crashpoints, duplicate delivery, replay.
- Sync: offline clients, conflicts, convergence, rejected operations.
- Compatibility/migration: old clients, expand/backfill/contract, rolling deploys.

`logical` event assertions count domain events, not physical delivery attempts.

Simulations control clock/random, duplicate/delayed/reordered messages, commit/publish crashes, partitions, failover, offline duration, sync order, and old client/event versions.

Completion means `check`, `plan`, `compatibility`, `build`, and relevant tests pass; new warnings are fixed or justified with verifiable annotations.

## IR Contract

DSL is compiled after resolve/type/effect/policy/topology checks into canonical JSON IR. Generators and runtime/deployment adapters consume IR, not raw source text.

Every public/generated declaration has stable `declarationId`, kind, owner module, optional owner service, source span, and semantic hash. Renames without `evolves`/migration create new identities. Formatting/comments do not change semantic hash.

Types are `TypeRef` objects, not strings: named, list, nullable, ref, or record. Generics are fully bound before generator output unless an adapter declares open generic support.

Operation IR includes auth/allow/authorize plan, public errors, effects, root effect, isolation/concurrency, idempotency, timeout/retry budget, and source map. Generators must not claim stronger guarantees than IR.

System IR includes services, entity ownership, resources, sync dependencies, event/queue/channel edges, consumer groups, projections, and sync surfaces.

## Adapter and Generator Contracts

Deployment adapters publish signed capability manifests. Compiler rejects unknown or weaker capabilities. Security, auth, secret, and data-loss guarantees cannot be overridden.

Generators declare accepted IR/profile versions, artifacts, deterministic parameters, required adapter capabilities, version/hash, and supported evolution paths. Output manifests include IR version, semantic hash, lock hash, generator info, and artifact hashes.

Profile registry entries need profile ID, major version, syntax/IR extension, closed property schemas, diagnostics/allowed fixes, conformance tests, and a local adapter or `contractOnly`.

Unknown IR fields are not silently ignored. Consumers accept only same IR major, known profile majors, and tolerated additive minor fields.

## Coverage and Limits

Core coverage includes CRUD, policies, UI contracts, horizontal replication, microservices with ownership, event processing, CQRS/search projections, sagas/workflows, offline command queue, server-coordinated multi-writer with limited merge strategies, media upload/transcoding/CDN, realtime, multi-region reads/failover, and selected active-active cases.

Not covered as core: arbitrary P2P/consensus, hard realtime, drivers, kernel/system software. Analytics/ML algorithms are orchestrated in DSL but algorithm bodies are native.

Reference apps: Petstore, Offline Calendar, VideoHub.

