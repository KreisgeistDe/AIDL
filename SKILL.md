# AIDL Language Engineering Skill

Use this skill when editing, reviewing, generating, or explaining AIDL source files, IntelliJ language support, compiler behavior, examples, diagnostics, IR output, generators, or deployment/runtime adapter contracts.

AIDL describes application, system, deployment, frontend, offline-sync, and quality semantics in a compact, statically analyzable language. The text language is the human-readable projection of a versioned JSON IR. Do not treat it as a general programming language or free-form key/value format.

## First Steps

1. Identify the active profiles from the `app` block and `aidl.lock`.
2. Locate the declaration by fully qualified name, not by filename assumptions.
3. Check owner service, used resources, effects, consistency, auth, idempotency, and compatibility before changing behavior.
4. Make the smallest semantically complete AIDL or parser/highlighting change.
5. Validate with `aidl check --format json`, `aidl plan`, compatibility/failure simulations when relevant, and project tests.

For this IntelliJ plugin, use:

```bash
./gradlew check
./gradlew buildPlugin
```

The plugin ZIP is expected at `build/distributions/intellij-aidl-plugin-0.1.0-SNAPSHOT.zip`.

## Core Rules

- Generated files are not repair targets. Change AIDL, validators, adapters, or generators instead.
- Imports are compile-time namespace dependencies, never implicit remote calls.
- Each persisted entity has exactly one service owner; only that owner may directly access its store.
- Public writes require auth, allow, declared errors, idempotency, and one root effect.
- Distributed delivery defaults to at-least-once; never describe it as exactly-once.
- Cross-service transactions and cross-service `ref` relationships are invalid.
- Offline conflict resolution must use declared server-normalized clocks or deterministic merge, never raw client time as authority.
- Frontend code is semantic UI plus state/data contracts, not arbitrary JSX/CSS.
- Resources describe portable semantics; provider details belong in bindings/adapters.
- Public evolution requires compatibility classification and, when needed, expand/backfill/contract migration.

## Reference Map

- `references/core-language.md`: modules, profiles, types, entities, expressions, effects, naming.
- `references/backend.md`: APIs, queries, mutations, transactions, policies, events, consumers, workflows.
- `references/distributed-systems.md`: services, ownership, sync calls, queues, projections, sagas, tenants, realtime.
- `references/offline-sync.md`: sync modes, operation log, clocks, conflicts, tombstones, rejected operations.
- `references/frontend.md`: frontends, routes, themes, components, pages, forms, optimistic/offline actions, a11y.
- `references/resources-deployment.md`: resources, media, deployment, serverless, secrets, observability, adapters.
- `references/evolution-compatibility.md`: semantic diff, API/event/store/client compatibility, migrations, rolling deploys.
- `references/grammar.md`: compact syntax and lexical rules for AIDL.
- `references/diagnostics.md`: compiler phases, diagnostic codes, tests, agent CLI workflow, IR/adapter contract.

## IntelliJ Plugin Notes

- `de.kreisgeist.aidl.AidlLanguage` registers the language.
- `de.kreisgeist.aidl.AidlFileType` registers `.aidl`.
- `de.kreisgeist.aidl.lexer.AidlLexer` is handwritten and drives highlighting.
- `de.kreisgeist.aidl.parser.AidlParser` is permissive and creates enough PSI for editor features.
- `de.kreisgeist.aidl.psi.AidlTypes` and `AidlTokenSets` define token and element types.
- `de.kreisgeist.aidl.highlighting` contains syntax highlighting and color settings.
- `de.kreisgeist.aidl.references` contains lightweight navigation and resolution.

Lexer policy is contextual: top-level declaration starters are keywords only outside braces; `module`, `import`, and `export` are declaration-level keywords; scalar and expression literals/operators are keywords; profile and clause names inside blocks are `PROPERTY_NAME`; any identifier after `.` remains an identifier/type name.

Keep lexer tests in `src/test/kotlin/de/kreisgeist/aidl/lexer/AidlLexerTest.kt`, especially for qualified imports, declaration-level version syntax where independently defined, and app-block properties.

## Regression Fixtures

Use these examples when changing language behavior:

- `../../examples/petstore/app.aidl`: core transactions, optimistic concurrency, outbox, idempotent consumers, web UI, auth, workflow.
- `../../examples/calendar-offline/app.aidl`: client-generated IDs, operation log, delta cursor, server validation, conflicts, tombstones, offline UX.
- `../../examples/videohub/app.aidl`: multi-service topology, blob upload, transcoding, renditions, topics, queues, projections, search, CDN, realtime, multi-region deployment.
