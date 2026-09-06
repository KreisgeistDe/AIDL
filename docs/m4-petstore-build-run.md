# M4-09 Petstore build/test/run path

M4-09 establishes a reproducible Petstore path on the M4-01 stack without changing M4-02 through M4-08 generator semantics. The path is fully validated on PR #67 after integration of the focused M4-06/M4-07 TypeScript-emission recovery. Generated files are never repaired manually.

## Boundary

- Source: `examples/petstore/m4-app/app.aidl`.
- Compiler checks, canonical IR and plan use the existing production compiler/CLI contracts.
- `python3 -m tools.m4_petstore generate` calls the integrated `tools/generate_m4.py` bundle; it does not implement a parallel generator.
- Every generated TypeScript and SQL file receives the M4-08 AIDL ownership/SHA-256 marker and is written through the M4-08 full-set preflight/rollback path.
- Runtime scaffolding under `examples/petstore/m4-app/src/` only wires Fastify, `pg`, generated API routes, generated idempotency and generated transaction execution.
- The application tsconfig uses TypeScript `strict: true`, NodeNext modules/resolution and exact optional-property checking. It intentionally does not add `noUncheckedIndexedAccess`, which is an extra compiler option outside TypeScript `strict` and outside the M4-01/M4-09 contract.
- M4-09 does not assert HTTP endpoint behavior, bind a messaging provider, or replace generated files by hand. HTTP end-to-end behavior remains M4-10.

## Prerequisites

- Python 3.12 plus `requirements-validation.txt`.
- Node.js 22.x LTS and npm 10.x.
- Docker with Compose support for the documented local PostgreSQL 17 path.

The checked-in `package-lock.json` pins the Node dependency graph. `package.json` pins TypeScript 5.9.2, Fastify 5.6.0, `pg` 8.16.3 and matching type packages.

## Clean-checkout path

From the repository root:

```sh
python3 -m pip install -r requirements-validation.txt
python3 -m tools.aidl_cli check examples/petstore/m4-app/app.aidl
python3 -m tools.aidl_cli plan examples/petstore/m4-app/app.aidl > /tmp/petstore-plan.json
python3 -m tools.aidl_cli ir examples/petstore/m4-app/app.aidl > /tmp/petstore-ir.json
python3 -m tools.m4_petstore generate

cd examples/petstore/m4-app
npm ci
npm run build
npm test
```

Generation also writes deterministic local build metadata to `examples/petstore/m4-app/build/`: canonical IR, plan and a generation manifest. These files and generated code are build products, not manually maintained source.

The strict application build uses the generated runtime unchanged. The M4-09 Fastify adapter narrows the generic `unknown` result of the generated idempotency helper to the generated `RunnablePet` handler contract at the scaffold boundary. The independently integrated M4-06/M4-07 recovery remains covered by its own real TypeScript 5.9 strict NodeNext compile regression.

## PostgreSQL migration/startup smoke

From `examples/petstore/m4-app` after generation/build:

```sh
docker compose up -d postgres
DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/petstore npm run smoke
```

The smoke command applies generated SQL migrations in lexical order, verifies PostgreSQL connectivity with `SELECT 1`, creates the Fastify application from the generated route/runtime contracts, waits for Fastify readiness, and closes cleanly. It intentionally does not issue an HTTP request or assert application behavior.

To run the server after migrations:

```sh
DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/petstore npm run migrate
DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/petstore npm start
```

Stop the local database with `docker compose down`.

## CI evidence

GitHub Actions run `33940785852` on PR #67 passed:

- focused M4-09 tests;
- M4-02 through M4-08 focused regressions, including the M4-06/M4-07 recovery compile regression;
- the complete configured Python suite: 245 tests;
- repository spec lint: 1029 checks across 57 AIDL files and 3 projects;
- Petstore parser smoke;
- Node 22.23.2 and npm 10.9.8 setup;
- production `check`, `plan` and canonical IR generation;
- normal M4 bundle generation with ownership validation;
- `npm ci` from the checked-in lockfile;
- strict NodeNext/ESM TypeScript build;
- Node tests;
- PostgreSQL 17 migration/startup smoke.

No generated-file repair step is present or permitted. M4-10 can now build on this path for actual end-to-end HTTP behavior validation.
