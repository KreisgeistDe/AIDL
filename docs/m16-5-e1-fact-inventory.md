# M16.5 E1 Semantic Fact and Construction-Exception Inventory

Status: **non-normative E1 design evidence**. Structural Schema may identify the source position carrying a fact, but the authoritative truth below is always Semantic-owned.

Base: `KreisgeistDe/AIDL@36403b0df688ea46205c0ce015f826dd113c51d9`.

## Semantic fact inventory

| ID | Fact | Owner | Scope | Authority statement |
| --- | --- | --- | --- | --- |
| `SEM-001` | symbol identity and qualified-name resolution | `semantic` | all reference-bearing positions | Resolved declaration identity, ambiguity, and missing-name truth. |
| `SEM-002` | reference target-kind validation | `semantic` | schema-marked reference positions | Whether a resolved symbol is a legal target kind. |
| `SEM-003` | type-name/type-expression resolution | `semantic` | type-bearing positions | Resolve named/generic/ref/record component types. |
| `SEM-004` | type checking and assignability | `semantic` | expressions, parameters, results, fields | Resolved type compatibility; Structural Schema only carries value-shape metadata. |
| `SEM-005` | expression typing and operator domain rules | `semantic` | all expressions | Kernel owns precedence/associativity; Semantic owns operand/result validity. |
| `SEM-006` | constraint satisfaction | `semantic` | constrained types/type bounds | Range, bound, and semantic constraint truth after type resolution. |
| `SEM-007` | module/import graph resolution | `semantic` | program/module/import | Import targets, visibility, and graph truth. |
| `SEM-008` | import-cycle/project graph policy | `semantic` | project | Cycle and cross-document project invariants. |
| `SEM-009` | single-app/project-root invariant | `semantic` | app/project | Exactly-one-app or equivalent project-level root rule where required. |
| `SEM-010` | app association resolution | `semantic` | appClause | System/frontend/api/defaultDeployment references and association truth. |
| `SEM-011` | profile key closure | `semantic` | profileProperty/ui/test profile vocabularies | Unknown profile/UI/test semantic keys remain rejected by the owning schema/validator. |
| `SEM-012` | profile version selection/compatibility | `semantic` | app/profile metadata | Profile-version semantics; not source-language version selection. |
| `SEM-013` | field identity/type semantics | `semantic` | fieldDecl | Field semantic identity and resolved type. |
| `SEM-014` | field key/uniqueness/concurrency semantics | `semantic` | field modifiers | Primary/unique/concurrency behavior after structural modifier legality. |
| `SEM-015` | deletion/reference behavior | `semantic` | onDelete/via/ref positions | Delete action, relationship behavior, and target semantics. |
| `SEM-016` | invariant truth typing | `semantic` | invariantDecl | Invariant expression must satisfy semantic boolean/domain rules. |
| `SEM-017` | view source/selection semantics | `semantic` | viewDecl/viewSelection | Resolved source and projected member semantics; recursive source order is preserved. |
| `SEM-018` | API transport contract semantics | `semantic` | apiClause | Transport/version/base path/auth/error encoding meaning. |
| `SEM-019` | operation authentication semantics | `semantic` | authClause | Authentication mode meaning and inheritance after structure. |
| `SEM-020` | operation authorization semantics | `semantic` | allow/authorize | Authorization expression/domain truth. |
| `SEM-021` | typed operation error set | `semantic` | errorsClause | Resolved error types and operation error contract. |
| `SEM-022` | query read/result semantics | `semantic` | queryClause/operationSignature | Read expression and result-type relationship. |
| `SEM-023` | consistency semantics | `semantic` | consistency/data/resource contexts | Context-specific consistency meaning; shared spelling never merges domains. |
| `SEM-024` | cache semantics | `semantic` | cacheClause | Visibility, TTL, vary behavior and domain rules. |
| `SEM-025` | idempotency semantics | `semantic` | idempotencyClause | Key/scope/retention meaning and equivalence of any later spellings. |
| `SEM-026` | transaction/isolation semantics | `semantic` | transactionBlock | Transaction target, isolation, lock/effect domain rules. |
| `SEM-027` | write/effect semantics | `semantic` | writeStatement | Write target/effect, revision expectation, failure semantics. |
| `SEM-028` | emit/delivery semantics | `semantic` | emitStatement | Event/message target and outbox/delivery meaning. |
| `SEM-029` | control-flow semantics | `semantic` | when/require/return/bindings | Branch, failure, binding, and return semantics in ordered statements. |
| `SEM-030` | event evolution semantics | `semantic` | eventDecl | Version/evolves compatibility and resolved predecessor meaning. |
| `SEM-031` | topic/queue delivery semantics | `semantic` | topicClause/queueClause | Delivery, ordering, retention, dead-letter domain meaning. |
| `SEM-032` | consumer binding semantics | `semantic` | consumerDecl | Topic/source/service references, start/call, retry and transaction meaning. |
| `SEM-033` | retry semantics | `semantic` | retryClass/retryPolicy/workflow/task contexts | Context-specific retry behavior; structural similarity is not semantic equivalence. |
| `SEM-034` | projection semantics | `semantic` | projectionDecl | Source set, target, key/map/rebuild/checkpoint semantics. |
| `SEM-035` | workflow semantics | `semantic` | workflow statements | Ordered invocation/approval/budget/return semantics. |
| `SEM-036` | saga compensation semantics | `semantic` | sagaStatement | Ordered steps and compensation semantics. |
| `SEM-037` | task execution semantics | `semantic` | taskClause | Execution backend, queue, resources, errors, timeout semantics. |
| `SEM-038` | schedule semantics | `semantic` | scheduleClause | Cron/timezone/singleton/catch-up/start semantics. |
| `SEM-039` | system/service ownership graph | `semantic` | system/service clauses | Owns/uses/exposes/runs/depends-on and project graph meaning. |
| `SEM-040` | client/service binding | `semantic` | clientDecl | Bound service and call contract semantics. |
| `SEM-041` | tenant model semantics | `semantic` | tenantDecl | Tenant-model association and domain constraints. |
| `SEM-042` | resource/profile semantics | `semantic` | resource/media/rendition/profileProperty | Provider/profile-specific constraints beyond structural shape. |
| `SEM-043` | offline-sync semantics | `semantic` | syncDecl/syncClause | Mode, authority, stores, push/pull, outbox, tombstone, conflict, rejection, schemaMigration meaning. |
| `SEM-044` | conflict/merge semantics | `semantic` | conflictRule/mergeStrategy | Field/group merge domain behavior after structural path/list validation. |
| `SEM-045` | modeled data migration semantics | `semantic` | migrationDecl | From/to modeled versions and ordered migration phase meaning; distinct from source-language migration. |
| `SEM-046` | deployment semantics | `semantic` | deploymentDecl | Service/resource binding, colocation, SLO and profile-specific deployment rules. |
| `SEM-047` | frontend routing/data/state semantics | `semantic` | frontend/page/form/action | Route/auth/data/state/action behavior and typed references. |
| `SEM-048` | UI profile semantics | `semantic` | uiStatement | Closed UI vocabulary, element/action domain rules, and references. |
| `SEM-049` | native binding semantics | `semantic` | native declarations | Binding existence/signature and implementation linkage. |
| `SEM-050` | test/fixture semantics | `semantic` | fixture/test/scenario/testStatement | Closed test verb vocabulary and assertion/execution meaning. |
| `SEM-051` | semantic defaults | `semantic` | all declarations | Defaults not explicitly written in source; never inferred by Structural Schema except by naming the semantic hook. |
| `SEM-052` | compatibility classification | `semantic` | M7 boundary | Compatible/coordinated/breaking classification and migration lifecycle remain M7 authority. |
| `SEM-053` | Canonical-IR projection | `semantic` | post-validation | Projection of resolved semantic facts into versioned Canonical IR. |
| `SEM-054` | support/conformance status | `semantic` | feature/profile support | Discoverability or schema coverage never promotes support/conformance. |
| `SEM-055` | semantic diagnostic mapping | `semantic` | post-structural validation | Domain diagnostic code/severity/message selection after resolution/type/project checks. |
| `SEM-056` | semantic source identity/sourceMap | `semantic` | Canonical IR sourceMap | Stable semantic declaration/source identity; trivia stays outside Canonical IR. |

## Explicit construction-exception census

These are **not validator escape hatches**. E3 must report any residual handwritten construction family after generic combinators are implemented. A row counts as residual only if the common algebra cannot construct it without declaration/body-family-specific handwritten logic.

| ID | Current family | Required combinator(s) | Why the visible normalization forms are insufficient |
| --- | --- | --- | --- |
| EXC-01 | anonymous `auth`/`a11y`/`privacy` identity | `DeclarationEnvelope` | No source name; identity is declaration-kind scoped. |
| EXC-02 | compound `native function` / `native component` starters | `DeclarationEnvelope` | Multiple contextual starter words must not become a Kernel keyword table. |
| EXC-03 | tenant `model` identity spelling | `DeclarationEnvelope` | Identity is introduced by an irregular fixed header word. |
| EXC-04 | string-labelled `test` plus `target` | `DeclarationEnvelope` | Identity is a string label plus a separate target fact. |
| EXC-05 | alias/opaque assignment without body | `DeclarationEnvelope` | Assignment envelope, not block construction. |
| EXC-06 | enum comma-delimited entries with optional assigned string | `DelimitedListEntry` | Comma-delimited body with optional identity value assignment. |
| EXC-07 | callable parameter/result envelopes | `DeclarationEnvelope` + `DelimitedListEntry` | Ordered parameters/type parameters/result are not ordinary keyed body slots. |
| EXC-08 | event version/evolves and relationship-qualified headers | `DeclarationEnvelope` | Multiple fixed-order semantic header facts require named structural metadata. |
| EXC-09 | keywordless fields/union variants/view members | `NamedEntry` / `SelectionItem` | Visible keyword-slot normalization cannot represent keywordless entries. |
| EXC-10 | ordered transaction/workflow/saga/action statements | `OrderedStatement` / `ControlFlowStatement` | Execution order is semantic and cannot be formatter-ranked. |
| EXC-11 | nested `when` control flow | `ControlFlowStatement` + `NestedBlock` | Recursive branches carry ordered statement sequences. |
| EXC-12 | recursive view selections | `SelectionItem` | Recursive, optionally comma/newline-delimited selection tree. |
| EXC-13 | hierarchical `profileProperty` | `RecursivePropertyPath` / `KeyedSlot` / `NestedBlock` | Property path plus optional colon/value or recursive block. |
| EXC-14 | generic UI/test statement sublanguages | `FreeItem` | Closed schema vocabulary but identifier-led/free-form construction shape. |

## Gate denominators

- **Normative-production denominator:** 211 productions, the corrected deterministic output for the pinned base grammar.
- **Construction-production denominator:** 154 Structural-Schema-owned productions (`211 - 57 Kernel`). Use only for construction-scope coverage statistics.
- **Semantic-fact denominator:** 56 enumerated Semantic-owned facts (`SEM-001`…`SEM-056`).
- The Cycle-4 Variant-B reopen rule is unchanged. A percentage relative to normative productions uses 211; construction coverage must say 154; fact coverage must say 56. Never mix denominators.

## Phase-1 boundary

Phase 1 includes the common declaration envelope, Core-relevant forms, `profileProperty`, view selection, and representative Sync/deployment facts. `uiStatement` and `testStatement` remain fully inventoried and schema-described but are outside the first executable E3 construction parser unless separately authorized.
