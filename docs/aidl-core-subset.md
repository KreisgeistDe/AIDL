# AIDL Core Implementation Subset

Status: **Normative for the first implementation milestone (M1–M4)**

This document defines the AIDL language surface that the first end-to-end implementation MUST support. It intentionally narrows the full AIDL specification so parser, semantic analysis, canonical IR, CLI tooling, tests, and the first generator can converge on one stable vertical slice.

The full language specification remains the design target. Features marked **Deferred** are not removed from AIDL; they are outside the compatibility promise of the first implementation milestone.

## Goals

The first supported subset MUST be sufficient to describe and validate a non-trivial service application with:

- modules and imports,
- domain types and persisted entities,
- typed errors,
- services and ownership,
- queries and mutations,
- local transactions,
- API exposure,
- events, topics, and consumers,
- explicit authentication/authorization and idempotency semantics.

The primary reference fixture is `examples/petstore`.

## Support levels

Every language feature MUST be tracked independently across these implementation layers:

1. **Parse** — source syntax is accepted and represented in the compiler AST.
2. **Resolve** — names/imports/FQNs are resolved.
3. **Validate** — required semantic rules are enforced with stable diagnostics.
4. **IR** — the semantic representation is emitted in canonical AIDL IR.
5. **Generate** — at least one supported generator consumes the feature without reparsing source.
6. **IDE** — optional for the first milestone; editor support MUST NOT define compiler semantics.

A feature is considered **Core Supported** only when Parse, Resolve, Validate, and IR are implemented. Generator support may lag until M4 and must be reported separately.

## Core Supported language surface

### Project and module structure

The first implementation MUST support:

- UTF-8 `.aidl` source files,
- `module <qualified.name>`,
- `import <qualified.name>`,
- wildcard imports,
- `export` declarations,
- fully qualified names,
- project-level module loading,
- duplicate declaration detection,
- unresolved-name diagnostics,
- cyclic module dependency diagnostics,
- the `app` declaration with profile selection.

Relative filesystem imports are not part of the language model.

### Names and declarations

The implementation MUST support:

- PascalCase declaration/type names,
- camelCase operation and field names,
- contextual keywords as defined by the AIDL grammar,
- stable fully qualified declaration identity independent of file names.

### Types

The first implementation MUST support these scalar types:

- `string`
- `int`
- `decimal`
- `bool`
- `uuid`
- `date`
- `datetime`
- `duration`
- `revision`
- `email`
- `url`
- `bytes`

It MUST support these type constructors:

- nullable `T?`,
- ordered lists `[T]`,
- `set<T>`,
- `map<K,V>`,
- owner-local `ref Entity`.

The only implicit scalar conversion in the core subset is lossless `int` to `decimal`.

### Domain declarations

The first implementation MUST support:

- `enum`,
- `alias`,
- `opaque`,
- `value`,
- persisted `entity`,
- typed `error` declarations.

Entities MUST have a stable identity in the semantic model and MUST participate in service ownership validation.

### Services and ownership

The first implementation MUST support:

- service declarations,
- explicit persisted-entity ownership,
- logical operation exposure by a service,
- validation that every persisted entity has exactly one owner service,
- validation that direct persisted access is owner-local,
- rejection of cross-service `ref` relationships.

Imports MUST remain compile-time namespace dependencies and MUST NOT imply network calls.

### Queries

The first implementation MUST support query declarations with:

- typed input/output,
- authorization/authentication clauses required by the applicable profile,
- read expressions represented semantically,
- declared consistency,
- declared errors,
- timeout metadata where present.

The semantic analyzer MUST reject side effects in queries.

Collection queries MUST eventually be validated for bounded result contracts; enforcement is targeted in M2 and does not block parsing in M1.

### Mutations

The first implementation MUST support mutation declarations with:

- typed input/output,
- `auth`,
- `allow`,
- declared `errors`,
- `idempotency`,
- exactly one root effect.

Supported root effects for the first subset are:

- one owner-local `transaction`,
- one idempotent resource call where the resource semantics are available in the active profile,
- start of a declared workflow/saga only as a parsed/IR construct until the corresponding runtime support exists.

Semantic validation MUST enforce the required mutation clauses before generator support is considered complete.

### Transactions

The first implementation MUST support owner-local transactions with:

- one transactional resource owner,
- declared isolation,
- reads and writes,
- optimistic compare-and-set / revision expectations,
- invariant validation,
- transactional event emission through an outbox.

Cross-service and cross-resource transactions MUST be rejected.

### APIs

The first implementation MUST support external `api` declarations with:

- transport,
- major version,
- base path where applicable,
- explicitly mapped query/mutation operations,
- auth inheritance/selection,
- typed error mapping semantics,
- compatibility mode.

Core transports are:

- `rest`,
- `rpc`,
- `graphql`.

For M4, only one transport needs a production-quality generator. The other core transports may remain Parse/Validate/IR supported until generators are implemented.

### Events, topics, and consumers

The first implementation MUST support:

- versioned event declarations,
- event identity/schema metadata,
- topic declarations,
- delivery mode,
- partitioning/ordering metadata,
- retention metadata,
- compatibility metadata,
- dead-letter metadata,
- consumers,
- consumer idempotency metadata.

Delivery semantics in the core subset are at-least-once. The compiler and documentation MUST NOT promise exactly-once distributed delivery.

Transactional event publication MUST use an outbox and commit state plus outbox entry atomically at the semantic/runtime-contract level.

## Parsed but not required for first generator

The following constructs may be included in the compiler AST/IR during M1–M3 but are not required for the first Petstore generator to be considered complete:

- workflows,
- sagas,
- tasks,
- non-REST API generation,
- generic declarations allowed by the wider AIDL specification.

When present, unsupported generator behavior MUST fail explicitly with a stable diagnostic or capability error. It MUST NOT silently ignore semantics.

## Explicitly deferred from the first core implementation

The following areas are outside the M1–M4 compatibility promise unless a later task promotes them:

- full frontend/UI generation,
- arbitrary component styling/rendering languages,
- offline synchronization runtime,
- operation logs and delta cursors,
- conflict resolution and tombstone runtime behavior,
- multi-region deployment orchestration,
- provider-specific cloud bindings,
- CDN/search/transcoding runtime adapters,
- realtime runtime adapters,
- advanced tenant isolation/runtime provisioning,
- automated expand/backfill/contract migrations,
- semantic compatibility diff tooling (`aidl diff`),
- LSP support,
- multi-language production generators.

Deferred syntax already present in examples/specification may still be accepted by a permissive parser, but acceptance MUST NOT be presented as semantic/runtime support.

## First generator target

M4 SHOULD implement one reference vertical slice with the following target unless superseded by a dedicated architecture decision:

- TypeScript runtime/application code,
- REST API surface,
- PostgreSQL persistence,
- generated code isolated under `generated/`,
- Petstore as the golden end-to-end fixture.

Generated files are outputs, not manual repair targets. Generator defects must be fixed in AIDL, the semantic model, adapters, or generator itself.

## Required CLI behavior for this subset

The implementation roadmap targets these commands:

```bash
aidl check <project>
aidl check <project> --format json
aidl ir <project>
aidl plan <project>
```

For every Core Supported feature, `aidl check` MUST either:

1. accept the construct and preserve its semantics into canonical IR, or
2. reject it with a stable, source-located diagnostic.

Silent dropping of supported semantics is a correctness bug.

## Compatibility rule for the implementation milestone

Until a feature reaches Core Supported status, changes to its syntax or IR representation are not covered by the first implementation compatibility promise.

Once a feature is Core Supported:

- its source semantics require explicit migration notes for breaking changes,
- its canonical IR shape is versioned,
- diagnostics relied upon by CI/IDE tooling should retain stable codes,
- generators must consume semantic IR instead of source syntax.

## Definition of done for the core subset

The first AIDL core subset is complete when:

- `examples/petstore` is parsed as a project,
- names and imports resolve independently of IntelliJ PSI,
- the M2 architectural invariants are enforced,
- canonical IR is deterministic,
- the CLI can check, emit IR, and plan the application,
- one generator can produce a runnable Petstore vertical slice without manual edits to generated files,
- positive and negative golden fixtures cover every Core Supported semantic rule.

## Change policy

Changes to this subset should be made deliberately. A pull request that promotes a deferred feature into Core Supported SHOULD specify:

- syntax/grammar impact,
- AST impact,
- name-resolution impact,
- semantic rules and diagnostics,
- canonical IR representation,
- generator capability impact,
- positive and negative fixtures.

This document is the implementation contract for M1–M4; the wider AIDL specification remains the source of truth for the long-term language design.