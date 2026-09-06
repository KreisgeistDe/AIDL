# M4 Fastify API generator

## Status

M4-03 generates the first REST API contracts and Fastify route registration from canonical AIDL IR for the M4-01 TypeScript stack.

## Input boundary

`tools/generate_fastify_api.py` accepts canonical IR `0.3.0` mappings only. It does not accept source paths, reparse `.aidl`, invoke compiler analysis, or use IntelliJ PSI. API generation resolves only canonical `api.operations[*].operationId` references to canonical `query` and `mutation` declarations.

The generated file set for this slice is `generated/api.ts`.

## Reuse of M4-02 domain types

M4-03 reuses the M4-02 TypeScript type renderer for query/mutation input and output type references. Supported named domain references therefore resolve to the same generated symbols from `generated/domain.ts`; M4-03 does not create route-local reinterpretations of AIDL domain types.

Unsupported domain type references fail through the existing M4-02 generator boundary rather than being silently widened.

## REST route convention

Canonical API IR identifies the REST surface, API base path, API major, and explicitly exposed logical operations, but does not carry a second source-level HTTP method/path mapping. The first Fastify generator therefore uses one deterministic transport convention without changing AIDL language semantics:

- only `transport: rest` APIs are accepted;
- each exposed query becomes `GET <basePath>/<operationName>`;
- each exposed mutation becomes `POST <basePath>/<operationName>`;
- query input is read from Fastify `request.query`;
- mutation input is read from Fastify `request.body`;
- handler output is sent with `reply.send`;
- only operations explicitly present in `api.operations` are externally registered.

The convention is generator behavior for the selected first stack. It is not a new parser/compiler semantic rule.

## Generated contracts

For every exposed operation, generation emits deterministic `<OperationName>Input` and `<OperationName>Output` aliases using the M4-02 domain type mapping. It also emits an `ApiHandlers` interface and deterministic `apiRoutes` metadata containing API ID, operation ID, operation kind, method, path, inherited API auth mode, and the operation's declared error IDs.

`registerApiRoutes(app, handlers)` registers the Fastify routes and delegates execution to caller-provided handlers. M4-03 does not implement the handler internals.

API declarations are ordered by FQN/declaration ID; generated routes are then ordered by API, path, method, and operation ID. Conflicting generated method/path pairs, missing operation declarations, operation-kind mismatches, unsupported transports, unsupported IR/type capabilities, and TypeScript symbol collisions fail explicitly.

## Deliberate non-goals

M4-03 does not implement PostgreSQL persistence or migrations, transaction boundaries, optimistic concurrency, mutation idempotency behavior, event/outbox integration, generated-code ownership enforcement, dependency manifests, application scaffolding, or build/test/run behavior. Those remain later M4 roadmap items.

The route metadata preserves declared auth/error information but this slice does not invent authentication middleware or typed error-to-wire execution behavior beyond the canonical contracts already present in IR.

## Validation

`tools/test_generate_fastify_api.py` covers canonical-IR-only generation, M4-02 type reuse, explicit exposure, deterministic output, GET/POST route conventions, and explicit failure boundaries. CI runs it with the M3 IR regressions, M4 stack/domain checks, the full Python suite, repository spec lint, and Petstore parser smoke.
