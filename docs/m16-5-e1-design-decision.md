# M16.5 E1 — Structural Construction Authority Design Decision

Status: **E1 design decision; non-normative for concrete syntax**.

Base: `KreisgeistDe/AIDL@36403b0df688ea46205c0ce015f826dd113c51d9`.

`docs/06-grammar.md` remains normative. This record does **not** adopt candidate source spelling, change accepted syntax or semantics, modify parser/lexer/AST/Canonical IR/formatter/IDE/LSP/generator/runtime behavior, or promote support/conformance. E2 remains the authority for language-version coexistence and migration lifecycle. E3 remains the first authorized executable construction experiment.

## Decision

E1 selects **A-prime as the design architecture for later prototype work, not as production architecture**.

- **Kernel** owns computational grammar and recovery substrate: lexical/source primitives, type grammar, expression grammar, operator precedence/associativity, delimiter/newline handling and bounded synchronization.
- **Structural Schema** owns document/declaration/sublanguage construction and visible-form metadata: starters, identities, header/body slots, cardinality, local ordering class, value/modifier shape, nesting, reference-position metadata, source-version applicability and formatting metadata.
- **Semantic** owns resolution, target-kind truth, typing, domain/project rules, semantic defaults, compatibility, Canonical-IR projection and support/conformance. Semantic owns no concrete-syntax production.
- Trusted Kernel and standard-language schema identities are compiler-owned and cannot be redefined by project source.
- Operator metadata may be introspectable, but core operators remain compiler-owned, non-exportable and non-redefinable.
- Canonical formatting may reorder only items explicitly marked semantically unordered. Otherwise source order is preserved.
- Variant B is not adopted or reopened by E1. The Cycle-4 reopen rule is unchanged and is evaluated only after an A-prime prototype passes the same hard gates and reports residual handwritten construction exceptions.

The complete traceability inventory is split into `docs/m16-5-e1-production-inventory-kernel.md`, `docs/m16-5-e1-production-inventory-structural-a.md`, `docs/m16-5-e1-production-inventory-structural-b.md`, and `docs/m16-5-e1-fact-inventory.md`.

## Grammar baseline reconciliation

The exact base version of `tools/grammar_complexity_metrics.py` was executed against the exact base `docs/06-grammar.md`. It reproduced the historical non-binding values, including **182 productions** and **456 production alternatives**. That did not prove that 182 was the complete count of named normative definitions.

The extractor recognized only definitions whose production name and `=` occur on the same physical line. The normative grammar has 29 valid definitions whose name is on one line and whose `=` begins the following indented line. The omitted definitions are:

`additiveExpression`, `asyncStateClause`, `bindingStatement`, `capabilityLiteral`, `compatibilityMode`, `constraintArgument`, `constraintArguments`, `deploymentClause`, `equalityExpression`, `idempotencyClause`, `idempotencyInline`, `idempotencyProperty`, `invocationStatement`, `multiplicativeExpression`, `nativeComponentDecl`, `nativeFunctionDecl`, `operationLogBlock`, `operationSignature`, `postfixExpression`, `primaryExpression`, `profilePropertyValue`, `projectionClause`, `relationalExpression`, `requireStatement`, `transactionBlock`, `transactionStatement`, `viewInlineMember`, `workflowInnerStatement`, `workflowStatement`.

The discrepancy is therefore a measurement-definition defect, not grammar ambiguity: **182 + 29 = 211** distinct named normative productions. E1 fixes only the read-only metric extractor; the normative grammar is unchanged.

| Metric | Corrected E1 baseline |
| --- | ---: |
| EBNF sections | 16 |
| Productions | **211** |
| Production alternatives | **522** |
| Distinct quoted terminals | 349 |
| Lexical terminals | 31 |
| Syntax terminals | 318 |
| Word syntax terminals | 298 |
| Symbol syntax terminals | 20 |
| Top-level declaration productions | 48 |
| Concrete top-level forms | 49 |
| Leaf alternatives | **129** |
| Block alternatives | **70** |
| Colon alternatives | **46** |
| Equals alternatives | **6** |
| Arrow alternatives | **3** |
| List alternatives | **20** |
| `profileProperty` alternatives | **39** |
| `uiStatement` alternatives | 16 |
| `testStatement` alternatives | 4 |
| Coarse surface signatures | **321** |

Production-relative percentages use the explicit denominator **211**. A construction-only percentage must instead name the **154 Structural-Schema-owned productions** denominator. Fact-relative percentages must name the fact inventory denominator; E1 materializes **56 Semantic-owned facts**. These denominators must never be mixed.

## Kernel boundary

The Cycle-4 Kernel list was rechecked against the normative grammar: 57/57 are present. Kernel owns exactly:

`letter`, `digit`, `identifier`, `typeName`, `upperLetter`, `qualifiedName`, `integer`, `decimalLiteral`, `percentage`, `durationLiteral`, `byteLiteral`, `cpuLiteral`, `number`, `string`, `regex`, `comment`, `annotation`, `newline`, `type`, `primaryType`, `scalarType`, `namedType`, `constrainedType`, `genericType`, `listType`, `refType`, `recordType`, `recordField`, `inlineEnumType`, `typeArguments`, `typeParameters`, `typeParameter`, `typeBound`, `constraintArguments`, `constraintArgument`, `range`, `expression`, `orExpression`, `andExpression`, `equalityExpression`, `relationalExpression`, `additiveExpression`, `multiplicativeExpression`, `unaryExpression`, `postfixExpression`, `memberAccess`, `callSuffix`, `indexSuffix`, `primaryExpression`, `arguments`, `argument`, `spread`, `listLiteral`, `objectLiteral`, `objectMember`, `capabilityLiteral`, `literal`.

The other 154 normative productions are Structural-Schema-owned. Declaration keywords, declaration-specific header sequences, body-slot vocabularies, profile keys and candidate normalized spellings do not move into Kernel tables. Contextual words remain contextual unless a separately authorized lexical decision proves a reservation change safe.

## A-prime structural-combinator algebra

| Combinator | Authority | Fact capacity | Current coverage |
| --- | --- | --- | --- |
| `DocumentSequence` | Structural Schema | module/import/export/declaration order and cardinality | `program`, module-before-import/declaration |
| `DeclarationEnvelope` | Structural Schema | starter tokens, identity, type params, header slots, params, result, optional assignment, body | all declarations; anonymous, callable, relationship and compound starters |
| `KeyedSlot` | Structural Schema | visible key, cardinality, value/modifier shape, reference position, format rank | colonized/uncolonized leaves and policy/config slots |
| `NamedEntry` | Structural Schema | entry identity, value/type, modifiers, annotations | fields, union variants, index/state/data entries |
| `OrderedStatement` | Structural construction; Semantic meaning | statement kind, source order, effects/references | transaction, workflow, saga, action sequences |
| `ControlFlowStatement` | Structural construction; Semantic branch meaning | condition, then/else, ordered children | recursive `when`, approval/failure branches |
| `NestedBlock` | Structural Schema | key/name, child schema, cardinality/order | transaction, workflow step, conflict, operationLog, policy blocks |
| `SelectionItem` | Structural Schema | selection identity, recursive children, expression branch | view members/selections |
| `FreeItem` | Structural shape; Semantic/profile schema closes vocabulary | identifier-led atoms and optional nested body | `uiStatement`, `testStatement` |
| `DelimitedListEntry` | Structural Schema | delimiters, entry identity/value, order, optional assignment | enum cases, params, type args, index fields, lists |
| `RecursivePropertyPath` | Structural Schema | path segments, optional colon, value/block branch, nesting | `profileProperty` |
| `TaggedValue` | Structural Schema | tag and typed payload | retry/consistency/merge/catch-up/delivery variants |

Each combinator instance is designed to carry stable fact IDs, cardinality, source-order/semantic-order flags, reference-position metadata and optional canonical-format rank. These are design metadata, not new syntax.

The existing three/four visible normalization shapes remain **candidates only**. They are insufficient by themselves for ordered statements, keywordless fields/union/view items, recursive view selections and profile paths, compound `native function`/`native component` starters, anonymous declarations, alias/opaque assignment declarations, string-labelled tests, and irregular declaration identities such as `tenant model`.

## Construction exception census

These cases must be represented explicitly by generic combinators or reported as residual handwritten E3 exceptions; they may not be hidden in validators:

1. anonymous `auth`/`a11y`/`privacy` identity;
2. compound `native function` / `native component` starters;
3. `tenant model` identity spelling;
4. string-labelled tests plus `target`;
5. alias/opaque assignment-without-body;
6. comma-delimited enum entries with optional assigned string;
7. callable parameter/result envelopes;
8. event version/evolves and other relationship-qualified headers;
9. keywordless fields, union variants and view members;
10. ordered transaction/workflow/saga/action statements;
11. nested recursive `when` control flow;
12. recursive view selections;
13. hierarchical recursive `profileProperty`;
14. generic UI/test statement sublanguages.

## Measured hotspot dispositions

Disposition vocabulary is fixed to `keep`, `normalize-candidate`, `schema-only/tooling`, or `defer`.

| Hotspot | E1 disposition | Preserved facts / owner | M7 sensitivity and later gate |
| --- | --- | --- | --- |
| Colonized vs uncolonized leaves | `normalize-candidate` | key, value, context-specific semantics / Structural + Semantic | source spelling is M7-sensitive; parity + deterministic rewrite before adoption |
| Idempotency compact vs structured | `normalize-candidate` | key, scope, retain, semantic equivalence where valid / Semantic | coexistence/rewrite is E2; E3 must prove no fact loss |
| Retry vocabulary/placement | `schema-only/tooling` | error retry class vs execution retry policy vs workflow-step retry / Semantic | do not unify semantics; normalized spelling only if later evidence supports it |
| Auth and error contract forms | `schema-only/tooling` | transport encoding, typed errors, auth mode/inheritance/route policy / Semantic | distinguish concepts before any syntax change |
| Consistency/timeout/budget | `schema-only/tooling` | context-specific policy facts / Semantic | schema discoverability first; syntax remains candidate only |
| `profileProperty` | `schema-only/tooling` | path, nesting, value shape; closed vocabulary / Structural + Semantic | Phase-1 schema case; preserve current syntax |
| `uiStatement` | `schema-only/tooling` | identifier-led UI statement shape and closed web vocabulary | inventoried but outside first E3 construction parser |
| Offline Sync compound leaves | `normalize-candidate` | each ordered token/value fact including target, delivery, tombstone, merge / Semantic | E3 shadow schema + M7 rewrite evidence needed |
| Deployment/resource compound properties | `schema-only/tooling` | deployment/resource identities and policy facts | shadow-schema coverage first; no spelling decision |
| workflow/saga/task/schedule family | `keep` | distinct orchestration identity and ordered semantics / Semantic | improve concept guidance before any rename |
| event/topic/queue/channel family | `keep` | distinct messaging identity/delivery semantics / Semantic | no rename in E1 |
| Newline significance/continuation | `keep` | logical newline and continuation / Kernel | changing it is lexical/grammar work outside E1 |
| Contextual terminal vocabulary | `keep` | contextual reservation / Kernel + Structural | no global keyword reservation change |
| Documented `upcast` outside top-level grammar | `defer` | documentation/grammar consistency fact | separate specification/language authority decision; no syntax added here |
| Current completion context coverage | `schema-only/tooling` | compiler-owned reference/construction contexts | later compiler-service/IDE packages; no IDE authority |

## Concrete normalization matrix

| Current form/family | E1 disposition | Facts preserved | Authority | M7 sensitivity / later gates |
| --- | --- | --- | --- | --- |
| `projection P from [A,B] into X` | `normalize-candidate` | projection identity, sources, target | Structural positions; Semantic reference truth | E2 coexistence/rewrite; E3 semantic/diagnostic parity |
| `client C for Service` | `normalize-candidate` | client identity, bound service | Structural + Semantic | M7 classification, source-map identity, rewrite parity |
| `migration M from "a" to "b"` | `normalize-candidate` | migration identity, from/to modeled versions | Structural + Semantic | must not conflate data migration versions with source-language version |
| `consumer C on Topic from Event` | `normalize-candidate` | consumer, topic, accepted source | Structural + Semantic | preserve wrong-kind/unresolved diagnostics |
| keywordless Entity field | `normalize-candidate` | field name/type/modifiers/annotations | Structural; Semantic typing/rules | explicit `field` remains candidate only; E3 fact parity |
| `index name(field asc, ...)` | `normalize-candidate` | index identity, ordered fields/directions | Structural + Semantic | preserve ordered field semantics and formatter behavior |
| `deadLetter after N attempts` | `normalize-candidate` | threshold and domain-specific behavior | Structural + Semantic | topic/queue semantics must remain distinct |
| `singleton lease 30s` | `normalize-candidate` | singleton policy and lease duration | Structural + Semantic | preserve scheduler diagnostics and meaning |
| `changes to Target via outbox` | `normalize-candidate` | target and delivery mechanism independently | Structural + Semantic | E3 shadow schema; semantic diff must be empty for pure rewrite |

## Trust model, bootstrap, operators and export boundary

### Trust tiers

1. **Kernel-trusted**: compiler-embedded computational grammar/meta invariants; immutable for one compiler/kernel version.
2. **Standard-language schema**: compiler-distributed, immutable version + content fingerprint, validated against Kernel meta-invariants.
3. **Profile/extension schema**: compiler-distributed or explicitly configured, dependency-pinned and fingerprinted; not Kernel authority.
4. **Project source**: untrusted relative to metamodel identities; cannot redefine trusted IDs or operator authority.

Trusted-vs-project ownership is therefore decided for E1. The exact public namespace spelling and source-language coexistence lifecycle remain proposal/E2 questions.

### Bootstrap and validation order

1. Select compiler build and Kernel version.
2. Kernel lexes source/schema bytes and owns delimiter/newline recovery primitives.
3. Decode/load the selected immutable standard-language schema without per-document filesystem reload.
4. Meta-validate schema identities, versions, dependencies and fingerprints; duplicate IDs, cycles, missing dependencies or mismatches fail closed.
5. Materialize Structural-Schema construction tables/combinators.
6. Parse project source structurally against the selected schema version.
7. Emit deterministic structural/syntax diagnostics and bounded recovery.
8. Resolve names/references and target kinds.
9. Run type/domain/project/profile validation and semantic diagnostics.
10. Apply semantic defaults and M7 compatibility classification only in Semantic authority.
11. Build Canonical IR only after required semantic gates succeed.

### Operators

Token form, precedence and associativity stay Kernel-trusted. Read-only operator metadata may be exported for introspection. Project/profile source cannot add, redefine, export, shadow or reorder core operators in A-prime.

### Export boundary

Compiler services may expose read-only versioned metadata for declaration/body/type schemas, allowed modifiers, reference-position kinds, docs IDs, formatting hints, operator metadata and deprecation aliases when later authorized. Kernel bootstrap identities, recovery internals and mutation/redefinition capabilities are non-exportable. Exported introspection is never project authority.

## Canonical formatting vs semantic order

E1 uses a fail-safe rule: **absence of explicit `semantic_order=unordered` means preserve source order**.

| Sequence | Semantic order | E1 formatter rule |
| --- | --- | --- |
| module/import/export/declarations | document constraints plus source identity | preserve; enforce only existing normative document constraints |
| annotations | preserve | never reorder in E1 |
| enum cases | preserve | never reorder |
| record fields, entity/value/error fields | preserve by default | never sort without later semantic proof |
| view selections/members | recursive source order | never reorder |
| parameters/type parameters/type arguments | ordered | never reorder |
| index fields | ordered | never reorder |
| query/mutation contract clauses | semantic sequence not inferred from format rank | only use the existing normative operation canonical order where already applicable; never move ordered effects |
| transaction statements, writes, emits | **ordered** | never reorder |
| `when` then/else children | **ordered** | never reorder |
| workflow steps/inner statements | **ordered** | never reorder |
| saga steps/compensations | **ordered** | never reorder |
| action statements | **ordered** | never reorder |
| policy statements | preserve | never reorder unless later schema proves unordered |
| topic/queue/consumer/projection clauses | preserve by default | no inferred sorting |
| task/schedule clauses | preserve by default | no inferred sorting |
| system/service lists and clauses | preserve by default | no inferred sorting |
| `profileProperty` siblings | preserve by default | no key sorting |
| recursive property-path segments | **ordered path** | never reorder |
| Sync clauses and conflict groups | preserve; field lists preserve unless later proven set-like | no inferred sorting |
| migration steps | **ordered** | never reorder |
| deployment clauses | preserve by default | no inferred sorting |
| UI statements | preserve | never reorder |
| test statements | execution/assertion order preserved | never reorder |

## Phase-1 boundary for later E3

The first executable A-prime construction experiment, when separately authorized, covers the common `DeclarationEnvelope`, Core-relevant forms, `profileProperty`/recursive property paths, recursive view selection, and representative Sync/deployment facts as shadow-schema cases. `uiStatement` and `testStatement` stay inventoried/schema-described but outside the first executable E3 construction parser unless separately authorized. No prototype may promote support or conformance.

## Variant B reopen condition

Variant B remains **not reopened**. The Cycle-4 rule is unchanged. It is evaluated only after A-prime passes identical safety/parity gates and E3 measures residual handwritten construction exceptions. Current legacy parser branches are baseline debt and do not count as residual A-prime exceptions.

For reproducibility, a production-relative arm uses denominator **211**. If an analysis instead reports construction coverage it must say **154**, and fact coverage must say **56**. If Variant B is reopened, it must remove at least half of measured residual exceptions and pass every identical gate. A hard safety/parity failure blocks both variants.

## Hard gates carried forward — not run in E1

E1 has no construction prototype, so these remain **NOT RUN**: valid/negative fixture parity; byte-stable unchanged diagnostics; semantic Canonical-IR equality; zero silently dropped facts; deterministic bounded candidate recovery; lossless untouched source/trivia/comment round-trip; formatter/migrator idempotence; fail-closed schema dependency/version/fingerprint behavior; residual handwritten construction exception count.

## Seven ADR proposal boundaries

### A — Construction authority/combinator algebra

**Options:** A-prime Kernel + Structural Schema algebra; retain declaration-specific handwritten construction; Variant B only if its reopen gate fires. **Invariants:** `docs/06-grammar.md` remains normative, Semantic owns no syntax production, 57-production Kernel boundary, explicit exception census, deterministic recovery. **Gates:** complete traceability, fixture/diagnostic parity, zero fact loss, residual-exception measurement and identical hard gates for any B comparison.

### B — Trusted schema identity/version/fingerprint/dependency/coexistence

**Open identity options:** reserved compiler dotted namespace; URI/URN namespace; opaque immutable IDs with versioned public aliases. **Fixed E1 invariants:** trusted IDs cannot be project-redefined; schema versions are immutable/fingerprinted; dependencies resolve before project semantics; unknown/missing/duplicate/cycle/fingerprint mismatch fails closed; trust tiers stay distinct. **Gates:** deterministic serialization, collision/property tests, dependency DAG checks and snapshot stability. Language-version coexistence/removal remains E2/M7.

### C — Lossless shared CST vs sidecar/refactoring anchors

**Options:** shared lossless CST; sidecar token/trivia/anchor map; hybrid only if one is a derived view of one source authority. **Invariants:** immutable source bytes, token/trivia ranges, logical/physical newlines, stable declaration/header/body/modifier anchors; untouched ranges round-trip byte-identically; stale source/schema fingerprints, overlapping edits or ambiguous anchors fail closed; Canonical IR remains semantic. **Gate:** equal lossless/recovery/refactoring/incremental behavior without duplicate source authority. E3 may start with sidecar as the lower-coupling experiment.

### D — Source-language-version selection / normalized-syntax boundary

**Options:** compiler/project manifest; future file directive; future app-level language selector. **Invariants:** no implicit per-file guessing; one explicit normal-compilation version; app/profile versions are not silently repurposed; mixed-version imports fail closed unless M7 later defines coexistence. **Gates:** deterministic schema fingerprint, mixed-version rejection fixtures, old/new semantic-equivalence fixtures, rollback/removal criteria. E1 chooses no lifecycle or new spelling.

### E — Structural diagnostic namespace/mapping/ordering

**Options:** reserved structural code family; reuse existing syntax codes where semantics are unchanged; hybrid. **Invariants:** unchanged invalid syntax retains code/severity/location/relative order; schema IDs never become ad-hoc codes; structural failures are deterministic; semantic diagnostics stay Semantic-owned. Existing relative order remains document order, source offset, phase, severity, code, message. **Gates:** byte-stable unchanged fixtures, deterministic candidate diagnostics, explicit mapping table and bounded recovery.

### F — Canonical formatting order vs semantic order

**Options:** schema-carried canonical rank for explicitly unordered items; handwritten rank tables; generated rank view. **E1 decision:** only explicitly semantically unordered items may move; ordered transaction/workflow/saga/action/control-flow sequences never move. **Gates:** the complete E1 table above, formatter idempotence, Canonical-IR equality, comment/trivia preservation and negative non-reordering tests.

### G — Controlled startup/benchmark protocol

**Options:** eager process decode; lazy-on-first-use process decode; precompiled immutable bundled schema image, provided all expose the same validated fingerprint/semantics. **E1 budget:** at most one bundled standard-language schema decode/meta-validation/fingerprint per process or immutable schema version; immutable reuse across snapshots; no per-document schema filesystem load; fail closed before semantics on mismatch. **Gate before numeric budgets:** pin workload, compiler/interpreter build, warm/cold condition, machine class, schema size/version, repetitions, baseline variance, and absolute/p50/p95 reporting.

## Acceptance accounting

1. Baseline: complete — exact old extractor reproduced 182; root cause identified; corrected extractor reports 211 and corrected dependent metrics.
2. Production/fact traceability: complete — 211/211 productions with exactly one owner; 56 Semantic facts; 14 explicit construction exception families.
3. Hotspots/matrix: complete — every measured hotspot and concrete normalization row has disposition, preserved facts, authority, M7 sensitivity and later gates.
4. Kernel/trust/bootstrap/operators/export/validation: decided for E1 design.
5. Formatting vs semantic order: complete for the E1 scope, conservatively preserving order unless explicitly unordered.
6. Seven ADR proposal boundaries: review-ready without E2/E3 implementation.
7. Documentation synchronization: E1 truth is recorded without marking E2+ or support/conformance complete.
8. Executable scope: only read-only grammar metrics/tests are changed; no project `.ai/**` path is touched.
