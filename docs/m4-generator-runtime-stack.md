# M4 reference generator/runtime stack

## Status

M4-01 selects the first supported generator/runtime stack for the Petstore vertical slice. This document is the human-readable companion to the machine-checkable contract in `spec/m4-stack.json`.

## Selected stack

The first production-quality AIDL generator targets:

- TypeScript 5.9.x in strict ESM mode;
- Node.js 22.x LTS on Linux x86_64;
- npm 10.x with a committed lockfile for generated application dependencies;
- REST over JSON using Fastify 5.x;
- PostgreSQL 17.x using the `pg` 8.x driver and generated SQL migrations;
- no ORM in the first vertical slice;
- Petstore under `examples/petstore` as the reference end-to-end application;
- generated output isolated under `generated/`.

These version families are the M4 compatibility target. Later implementation may pin exact patch releases in generated lockfiles, but must not silently move to a different major runtime/framework/database contract.

## Generator boundary

The generator MUST consume canonical AIDL IR only. It MUST NOT reparse `.aidl` source or use IntelliJ PSI as a semantic source. Generated files are outputs and MUST NOT require manual repair. If a supported semantic cannot be generated, generation must fail explicitly rather than silently dropping it.

## Required M4 capability boundary

Later M4 implementation on this stack must cover the Petstore subset needed for:

- domain types and persisted entities;
- REST query and mutation routes;
- PostgreSQL persistence and deterministic SQL migrations;
- owner-local transactions;
- optimistic concurrency/revision checks;
- mutation idempotency;
- transactional outbox event publication.

The following remain outside the first generator/runtime promise unless promoted by a later roadmap item: GraphQL generation, RPC generation, workflow/saga runtime execution, multi-language generators, provider-specific cloud bindings, and multi-region orchestration.

## Rationale and trade-offs

TypeScript matches the repository's existing M4 recommendation and gives one language for generated domain, API, and runtime code. Node.js LTS keeps the runtime broadly deployable while ESM avoids introducing a second module-system target. Fastify provides a narrow REST/JSON server boundary without defining AIDL semantics. PostgreSQL directly matches the first persistence target and provides transactions and concurrency primitives needed by the supported semantic subset.

The first slice deliberately avoids an ORM. Direct generated SQL keeps schema, transaction, revision, idempotency, and outbox behavior explicit and deterministic instead of depending on ORM-specific inference. This increases generator responsibility but reduces hidden runtime semantics and makes generated diffs easier to explain.

A single Linux reference platform, one Node major, one TypeScript family, one REST framework family, and one PostgreSQL major intentionally trade portability for a smaller reproducible compatibility surface. Additional platforms, frameworks, databases, transports, and languages are later expansion work.

## Acceptance conditions for later M4 implementation

A later M4 generator/runtime implementation is acceptable only when all of the following hold:

1. generation starts from canonical IR and does not reparse source;
2. two runs over equivalent canonical IR produce deterministic generated files and dependency manifests;
3. generated application code stays under `generated/` and builds without hand edits;
4. the generated Petstore application exposes the supported REST surface and persists through PostgreSQL on the selected stack;
5. generated transaction, optimistic-concurrency, idempotency, and outbox behavior reflects existing compiler/IR semantics rather than inventing new language rules;
6. unsupported generator capabilities fail explicitly;
7. generated dependency resolution is reproducible through the committed npm lockfile;
8. build/test/run instructions are reproducible on the selected Node/Linux/PostgreSQL contract.

## Non-goals of M4-01

M4-01 does not add a generator command, generated source, runtime libraries, database migrations, containers, application scaffolding, or Petstore execution. Those belong to later M4 roadmap items in order.
