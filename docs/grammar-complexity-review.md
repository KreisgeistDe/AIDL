# AIDL Grammar Complexity Review

Status: **non-binding analysis**. This document does not change AIDL syntax, grammar, language semantics, conformance status, roadmap priority, or implementation support. All simplification options below require a separate design decision and compatibility analysis before they could become language changes.

## Executive summary

This review classifies the current AIDL surface as **(b) moderately in need of simplification**.

The evidence does **not** support classifying the language as structurally unmanageable. The language has strong regularities: named declarations are block-oriented, fields and types have recognizable families, the parser has declaration-specific entry points, and a generic clause representation deliberately absorbs many profile-specific leaves for later semantic validation. The problem is instead concentrated in the number of **locally different clause shapes** a human, an LLM, compiler services, and IDE tooling must learn.

The reproducible grammar measurement reports:

- 16 normative EBNF sections,
- 182 productions,
- 456 top-level production alternatives across those productions,
- 349 distinct quoted terminals in the normative grammar,
- 318 non-lexical syntax terminals, including 298 word-shaped contextual terminals and 20 symbolic terminals,
- 48 productions referenced by the top-level `declaration` union and 49 concrete top-level forms because `aliasDecl` covers both `alias` and `opaque`,
- 111 alternatives containing a logical-newline leaf,
- 62 alternatives containing a block,
- 40 alternatives containing `:`,
- 19 alternatives containing list punctuation,
- 30 alternatives delegating to `profileProperty`, 16 to `uiStatement`, and 4 to `testStatement`, and
- 295 deliberately coarse *starter-plus-shape* signatures. That last number is an inventory aid, not a claim that authors must learn 295 independent grammar rules.

A manual construction-oriented normalization collapses the grammar into **16 recurring surface families**. That is a more useful approximation of what an author or model must learn than raw keyword count. Even within those families, however, several concepts recur in different shapes: `auth`, `errors`, `consistency`, `retry`, `timeout`, `idempotency`, invocation, and lifecycle/budget policies. Offline Sync and deployment/resource clauses also contain dense word-order mini-languages. Frontend and tests introduce their own generic statement sublanguages.

The main recommendation is therefore **not** “reduce the number of domain concepts.” It is to consider, in future design work, reducing the number of *ways the same structural idea is written*, especially punctuation, structured policy clauses, invocation forms, and generic profile/UI sublanguages. Any such change would be compatibility-sensitive and is outside this review.

## Scope and method

Evidence was reviewed from the current project base together with:

- `docs/06-grammar.md` as the normative grammar,
- Core, Backend, Frontend, Distributed, Offline Sync, Resource/Deployment, Evolution, and Standard Library documentation,
- `tools/aidl_parser.py`,
- compiler-owned completion behavior,
- representative Petstore sources, and
- the Calendar Offline sync fixture.

`tools/grammar_complexity_metrics.py` provides the deterministic grammar-only counts used here. `tools/test_grammar_complexity_metrics.py` exercises the helper through the generic Python test path and prints its complete JSON inventory in CI. The helper is intentionally read-only and does not parse AIDL source or participate in compiler behavior.

The metrics distinguish **lexical terminals** from **syntax terminals**. The normative text states that quoted terminals are reserved in their applicable context, so the 298 syntax words should not be read as 298 globally reserved lexer keywords. The current parser's explicit lexer `KEYWORDS` set is much smaller (74 entries); many grammar words are contextual and are interpreted by declaration/clause semantics rather than by global lexical reservation. That design reduces global keyword pressure, but shifts more responsibility to context-sensitive parsing, semantic profile validation, completion, and author memory.

No reproducible external LLM benchmark is part of the repository, so this review does **not** invent model-run success rates. Instead it defines an agent-construction task catalog and measurable error taxonomy for a future controlled evaluation.

## Quantitative inventory

| Metric | Result | Interpretation |
| --- | ---: | --- |
| EBNF sections | 16 | The grammar is explicitly partitioned by language area. |
| Productions | 182 | Large but still inspectable as a normative grammar. |
| Production alternatives | 456 | Indicates substantial local branching and special forms. |
| Distinct quoted terminals | 349 | Includes lexical and syntactic literals. |
| Syntax terminals | 318 | Excludes the lexical-terminal set used by the metric. |
| Word-shaped syntax terminals | 298 | Mostly contextual vocabulary, not all global lexer keywords. |
| Symbolic syntax terminals | 20 | Punctuation/operators are comparatively compact. |
| Top-level declaration productions | 48 | The `declaration` union is broad. |
| Concrete top-level forms | 49 | `aliasDecl` has `alias` and `opaque` forms. |
| Leaf alternatives | 111 | Newline-significant leaf clauses are a dominant form. |
| Block alternatives | 62 | Nested blocks are also common. |
| Colon alternatives | 40 | Colon usage is significant but not universal. |
| List alternatives | 19 | Bracket-list forms are a recurring family. |
| `profileProperty` alternatives | 30 | A large profile-like generic sublanguage. |
| `uiStatement` alternatives | 16 | Frontend introduces a separate generic statement family. |
| `testStatement` alternatives | 4 | Tests introduce another generic statement family. |
| Coarse starter-plus-shape signatures | 295 | Useful for hotspot discovery; not a learnability count. |

The largest section-local terminal inventories are also informative: Operations has 70 unique quoted terminals, Frontend 62, Events/Messaging/Processing 56, Offline Sync 49, and Type Declarations 44. This concentration matches the areas where construction requires remembering clause placement and word order rather than just declaration names.

## Construction-oriented pattern taxonomy

The following **16 families** are a manual normalization of the normative grammar and representative source. The taxonomy deliberately groups syntax that an author can plausibly learn as one construction rule.

1. **Named block declarations** — `entity X { ... }`, `event X { ... }`, `service X { ... }`.
2. **Callable/signature declarations** — query, mutation, policy, workflow, component, page, native function forms with parameters/returns.
3. **Relationship-qualified headers** — declarations qualified by `for`, `from`, `on`, `into`, version, resource kind, or similar header context.
4. **Anonymous/profile blocks** — `auth { ... }`, reliability, observability, health, conflict and other named nested policy/configuration blocks.
5. **Alias/opaque assignment declarations** — `alias` / `opaque` with `=` and a type.
6. **Field/type clauses** — `name: Type` plus nullable/type constructors and field modifiers.
7. **Uncolonized keyword leaves** — `transport rest`, `delivery atLeastOnce`, `consistency strong` in resource/profile contexts.
8. **Colonized keyword leaves** — `auth: authenticated`, `timeout: 5s`, `consistency: strong` in operations.
9. **Bracket-list leaves** — `errors: [...]`, `events [...]`, `services [...]`, `resources [...]`.
10. **Nested keyword blocks** — `transaction ... {}`, `step ... {}`, `approval ... {}`, `when ... {}`.
11. **Binding/effect statements** — `x = ...`, `read: ...`, `write: ...`, `emit: ...`, `return ...`, `require ...`.
12. **Inline function/policy forms** — named arguments, calls, retry constructors, constraints and compact policy expressions.
13. **Generic `profileProperty` sublanguage** — property paths with generic values or recursively nested blocks, constrained later by profile/declaration schemas.
14. **Generic `uiStatement` sublanguage** — identifier-led UI atoms with optional nesting.
15. **Generic `testStatement` sublanguage** — arrange/act/assert and test-domain statement forms.
16. **Compound word-order mini-languages** — especially Sync, deployment, workflow/retry and resource policy leaves whose meaning depends on a fixed sequence of several words and values.

This taxonomy explains why the language is learnable despite 298 syntax words: many terms fit recurring families. It also explains the review's “moderate simplification” result: authors still need to know *which* of the similar families a particular semantic concept uses in each context.

## Hotspot matrix

Ratings are relative within AIDL: Low, Medium, High.

| Hotspot | Human Complexity | LLM Construction Risk | Compiler Complexity | Semantic Ambiguity | Simplification Potential | Breaking-Change Risk | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Colonized vs uncolonized leaf clauses | High | High | Medium | Medium | High | High | Operations use `auth:`, `errors:`, `consistency:`, `timeout:` while APIs/resources/frontends often use corresponding words without `:`. |
| Idempotency compact vs structured forms | Medium | High | Medium | Low | High | High | Mutation/consumer/workflow examples use compact `idempotency: expr retain ...`; backend sources also use a structured idempotency block with key/scope/retain. |
| Retry vocabulary and placement | High | High | Medium | Medium | High | High | Error retry class, consumer/task retry clause, workflow `step ... retry ...`, and distributed client retry are structurally different. |
| Auth and error contract forms | High | High | Medium | Medium | High | High | API `auth inherit` / `errors problemDetails`; operation `auth: mode` / `errors: [types]`; frontend route/page auth has another shape. |
| Consistency/timeout/budget policies | Medium | High | Medium | Medium | Medium | High | Similar facts appear as colonized operation clauses, generic profile properties, data modifiers, or header/step policy text. |
| `profileProperty` generic sublanguage | Medium | Medium | High | Medium | Medium | Medium–High | 30 measured alternatives delegate to it; parser preserves generic clauses and later schemas own much of the validation. |
| `uiStatement` generic sublanguage | High | High | High | Medium | Medium | High | 16 measured alternatives delegate to UI statements; many element-specific word sequences are identifier-led rather than globally explicit productions. |
| Offline Sync compound leaves | High | High | Medium | Medium | High | High | Valid fixture includes `push batch max ... retry ...`, `pull cursor ... page ... source ...`, `changes to ... via outbox`, tombstone and rejected-operation sequences. |
| Deployment/resource compound properties | High | High | Medium | Medium | Medium | High | Resource/deployment blocks combine generic property paths and dense sequences for replicas, autoscale, rollout, health, observability, SLOs and bindings. |
| Workflow/saga/task/schedule family | Medium | High | Medium | Medium | Medium | High | Related orchestration concepts use distinct headers and retry/start/approval/compensation forms. |
| Event/topic/queue/channel family | Medium | Medium | Medium | Medium | Medium | High | Related messaging concepts share vocabulary but differ in declaration roles, delivery/partition/replay/channel semantics. |
| Newline significance and continuation | Medium | Medium | Medium | Low | Medium | High | Logical newline terminates fields/leaves; semicolons are invalid; multiline expressions depend on continuation rules. |
| Contextual terminal vocabulary | Medium | Medium | Medium–High | Low | Low | High | 298 measured syntax words versus a much smaller explicit lexer keyword set; broad vocabulary is contextual rather than globally reserved. |
| Documented evolution forms outside top-level grammar | High | High | Medium | High | High | High | Evolution documentation contains an `upcast ... {}` example, while the current normative top-level `declaration` alternatives contain no `upcastDecl`. This is a documentation/grammar gap, not a support claim. |
| Current compiler completion context coverage | Medium | Medium | Medium | Low | Medium | Medium | Compiler-owned completion deliberately supports parser-established project-reference contexts and is conservative elsewhere; heterogeneous non-colon/profile/UI forms expand the future context surface. |

### Highest-risk clusters

The matrix shows four clusters that matter more than raw keyword volume:

1. **Same concept, different punctuation/placement.** `auth`, `errors`, `consistency`, `retry`, `timeout`, and `idempotency` are not expressed through one common structural convention.
2. **Generic nested sublanguages.** `profileProperty`, `uiStatement`, and test statements make the grammar extensible and compact, but transfer correctness and completion burden to context-specific schemas and validators.
3. **Dense compound leaves.** Offline Sync and deployment are readable once known, but they contain several independent semantic facts encoded by word order rather than named fields.
4. **Closely related declaration families.** Workflow/saga/task/schedule; event/topic/queue/channel; value/view/entity/projection are conceptually distinguishable, but models and new authors can choose the right domain concept with the wrong local clause grammar.

## Repeated semantics with different surface forms

The following are syntax-complexity observations only; they do not assert that the corresponding semantics are identical in every context.

### Authentication

- API-level configuration uses an uncolonized clause such as `auth inherit`.
- Query/mutation contracts use `auth: authenticated` or other modes.
- Frontend routing/page guards use `auth authenticated` embedded in route/page clauses.
- Some profile-style configuration is represented through generic property clauses.

The semantic domains differ, but the shared word `auth` invites transfer of the wrong local pattern.

### Errors

- API transport encoding uses an uncolonized `errors` clause.
- Operations expose a typed `errors: [...]` list.
- Failure handling in UI/forms/tests uses still other statement vocabulary.

This is conceptually sound, but construction must know whether `errors` means transport encoding, declared error set, or a failure branch.

### Retry

- Error declarations classify retry behavior.
- Consumers/tasks configure retry policy as a clause.
- Workflow steps put retry policy in the step header.
- Distributed client calls put retry inside a nested call policy.

The same operational dimension is represented by several clause families.

### Idempotency

Representative sources show both compact idempotency clauses and a nested key/scope/retain block. Supporting compact and structured variants improves expressiveness, but raises construction and formatter/completion surface area.

### Consistency and timeout

Operations commonly use colonized clauses; resource/frontend/profile contexts frequently use uncolonized or nested property forms. Again, the semantics are context-specific, but the surface convention is not uniform.

## Profile-like sublanguages

### `profileProperty`

The normative grammar intentionally defines a generic property-path/value-or-block mechanism. Thirty measured alternatives refer to it. The parser similarly keeps many subclauses as generic structured nodes; declaration/profile schemas then determine legal names, values, and nesting.

**Benefit:** avoids exploding the top-level parser into a rule for every provider/profile property and supports closed profile vocabularies outside the basic parser.

**Cost:** source construction and IDE completion require a second source of context: the local profile/declaration schema. A parser-only completion engine cannot infer the full property vocabulary from syntax alone.

### `uiStatement`

Frontend component/page/form bodies are intentionally compact and semantic rather than JSX/CSS. The grammar delegates 16 measured alternatives to generic UI statements. This keeps the normative grammar short relative to the UI vocabulary, but creates an additional identifier-led statement language whose valid atoms depend heavily on context.

### `testStatement`

Tests similarly form a compact scenario language. It is useful for readable acceptance tests but adds another statement catalog (`arrange`, call/visit/fill/assert/failure/concurrency operations) that is structurally distinct from ordinary backend effects.

## Parser and compiler-service implications

The current parser design is a reasonable response to the language breadth rather than evidence of a broken parser architecture:

- top-level declaration starters are dispatched to specialized declaration parsers,
- declaration headers with parameters/returns/relationships are parsed structurally,
- many nested/profile clauses are captured by a generic balanced `parse_clause` mechanism, and
- later compiler phases are expected to validate declaration/profile meaning.

This means grammar complexity is **distributed across phases**. A syntax parser can remain relatively regular even when the full language is not regular from an authoring perspective.

The same distinction matters for IDE support. Compiler-owned completion is intentionally conservative and currently focuses on parser-backed project-reference positions. Its reference-context recognition is not a general schema-aware completion system for all profile/UI/test clauses. Therefore the grammar review should not count a generic parser clause as “free” complexity: every contextual sublanguage still needs semantic diagnostics, completion, documentation, and refactoring support if it is eventually claimed as editor-complete.

## Representative source observations

### Core

Core declarations are among the most regular parts of AIDL. `enum`, `value`, `entity`, `alias`, `opaque`, type constructors, and field modifiers form recognizable patterns. Complexity increases when type expressions, constraints, nullability and modifiers combine, but the basic field shape is stable.

### Backend

Backend operations combine typed signatures with colonized contract clauses and nested effect blocks. A realistic mutation may require remembering typed errors, auth, allow, idempotency, transaction headers, write/expect/else, emit/outbox, audit and timeout. Each is individually readable; construction risk comes from the number of local forms used together.

### Distributed / Sync

The valid Calendar Offline sync fixture is the clearest compound-leaf hotspot. Within one `sync` block it uses simple leaves, colonized scope, nested `operationLog` and `conflict` blocks, fixed word-order push/pull/change/delete clauses, field merge clauses, group merge clauses, rejected-operation behavior and schema-migration flags. This is expressive but has high exact-syntax recall cost.

### Frontend

Frontend adds route arrows, page data declarations, URL state, state/loading/empty/error clauses, form and action statements, and a generic UI element language. It remains more constrained than a general UI programming language, but it has a distinct construction vocabulary that an agent must learn separately from backend clauses.

## Agent-oriented construction evaluation catalog

No controlled LLM result is recorded here. A future benchmark should pin model/version, system instructions, repository commit, sampling parameters, and task text before any score is treated as evidence.

### Task A — Core construction

Prompt target: create a value/entity/view slice with constrained scalar fields, nullable/list/set/map types, references, concurrency metadata and a view.

Expected measurement:

- parse success,
- diagnostics by category,
- correct declaration selection,
- correct field/type/modifier placement,
- invented syntax count,
- semantic omission count,
- number of repair turns,
- AST/Canonical-IR fact coverage where supported.

### Task B — Backend construction

Prompt target: create a mutation with typed errors, authentication/authorization, idempotency, transaction, optimistic revision handling, outbox event publication, audit and timeout.

Particular risk probes:

- API `auth/errors` style incorrectly transferred into mutation clauses,
- compact versus block idempotency confusion,
- retry or timeout placed in the wrong construct,
- transaction/write/emit syntax mixed with workflow statements.

### Task C — Distributed / Sync construction

Prompt target: create a service/topic/consumer plus an offline sync contract with push/pull, tombstones and conflict merge rules.

Particular risk probes:

- topic/queue/channel concept confusion,
- wrong word order in push/pull/change clauses,
- profile property placed at the wrong nesting level,
- `field ... merge` versus `group ... fields [...] merge` confusion,
- invented peer-to-peer semantics outside the specified profile.

### Task D — Frontend construction

Prompt target: create a page with query-backed data, loading/empty/error states, a form action, route/auth behavior and a realtime or refresh path.

Particular risk probes:

- backend colon conventions transferred to frontend data modifiers,
- `uiStatement` element/action nesting errors,
- route versus navigate versus call confusion,
- missing required loading/empty/error contracts,
- persistence/action semantics expressed in an unsupported UI statement.

### Error taxonomy for such a benchmark

Every failed construction should be assigned one or more stable categories:

1. wrong keyword,
2. valid keyword/clause in the wrong declaration,
3. correct concept but wrong clause form or punctuation,
4. confusion between similar declaration concepts,
5. missing required clause/fact,
6. invalid nesting,
7. invented syntax,
8. malformed type/expression,
9. semantic fact silently omitted from the intended contract,
10. parser success but semantic diagnostic failure.

Aggregate metrics should include first-pass parse rate, first-pass semantic-validation rate, diagnostics per 100 source lines, repair-turn count, invented-syntax rate, wrong-placement rate, and semantic-fact recall. Those measurements distinguish grammar construction risk from underlying domain-model difficulty.

## Non-binding simplification options

These are hypotheses for future design work, **not proposed language changes in this PR**.

### 1. Normalize leaf punctuation

Choose a more uniform rule for whether property-like leaves use `name value` or `name: value`.

- Potential benefit: High for humans, models, formatter/completion rules.
- Risk: High; source-breaking and likely broad fixture/documentation impact.
- Preserve semantics: possible, but requires a migration/deprecation strategy.

### 2. Prefer one structured form for multi-field policies

Idempotency, retry, budgets, cache policy, reliability policy and similar concepts could converge on one named-object/block convention when they carry multiple independent facts.

- Potential benefit: High.
- Risk: High for syntax compatibility.
- Important constraint: do not collapse semantically different policy types merely because they share syntax.

### 3. Introduce shared structural conventions for auth/errors/retry/timeout/consistency

A common syntax family could reduce transfer errors while retaining context-specific types and allowed values.

- Potential benefit: High.
- Risk: High.
- Semantic caution: API transport error encoding is not the same fact as an operation's typed error set; uniform syntax must not imply uniform semantics.

### 4. Make contextual property schemas first-class to tooling

Instead of necessarily replacing `profileProperty`, expose each closed property vocabulary to compiler-owned completion, diagnostics and documentation through machine-readable schema metadata.

- Potential benefit: Medium to High for IDE/agents without a source-breaking syntax change.
- Risk: Medium; primarily tooling/schema architecture rather than language syntax.

### 5. Normalize invocation forms

`call`, query invocation, mutation invocation, workflow `start`, UI actions/navigation and test calls could be documented or eventually structured around clearer common invocation conventions.

- Potential benefit: Medium.
- Risk: High if syntax changes; lower if first addressed through documentation/tooling only.

### 6. Reduce avoidable duplicate inline/block spellings

Where compact and block forms encode the same contract, decide whether both are worth the permanent grammar/tooling cost.

- Potential benefit: Medium to High.
- Risk: High; compact forms may be valuable for common cases.

### 7. Clarify conceptual families before renaming them

Workflow/saga/task/schedule and event/topic/queue/channel deserve explicit “choose this when…” guidance and tooling diagnostics before any renaming is considered.

- Potential benefit: Medium.
- Breaking risk: Low for documentation/tooling; very high for renaming.

### 8. Reconcile specification examples with normative productions

Every documented source-form example should map to a normative grammar production or be explicitly labeled pseudocode/future syntax. The current evolution documentation's `upcast` example is a concrete drift hotspot because the top-level grammar has no corresponding `upcastDecl` production.

- Potential benefit: High for language trust and agent construction.
- Risk: Low if resolved by documentation clarification; potentially High if resolved by adding/changing syntax, which would require a separate semantic decision.

## Why the result is not “structurally too complex”

Several counter-signals prevent a category-(c) conclusion:

- Top-level declarations are explicit and mostly keyword-led.
- Blocks, leaves, lists, fields, callable signatures and effect statements recur consistently enough to form a manageable 16-family construction model.
- The parser architecture has clear declaration dispatch and a deliberate generic-clause boundary instead of a unique parser routine for every domain property.
- Representative Petstore and Calendar fixtures are readable as declarative contracts once the local clause vocabulary is known.
- Symbolic punctuation is small relative to domain vocabulary; the language is not dominated by operator ambiguity.

The risk is therefore **breadth plus local irregularity**, not fundamental syntactic undecidability or an absence of recurring structure.

## Why the result is not “adequately regular”

A category-(a) conclusion would understate the evidence:

- 298 word-shaped syntax terminals are distributed across many context-specific vocabularies.
- There are 111 leaf and 62 block alternatives with only partial punctuation regularity.
- Similar operational concepts use visibly different local shapes.
- `profileProperty`, `uiStatement` and `testStatement` create three substantial context-dependent sublanguages.
- Offline Sync and deployment/resource syntax encode many facts in fixed word-order leaves.
- Current compiler completion is intentionally conservative and cannot make all of that contextual vocabulary discoverable from parser syntax alone.
- At least one documented evolution source form (`upcast`) lacks a matching top-level normative production.

Those factors justify targeted simplification or stronger schema-driven tooling before the full specified-language surface is treated as easy to construct reliably.

## Conclusion

**Classification: (b) moderately in need of simplification.**

AIDL's domain breadth is not itself the primary defect. The highest-value future work would regularize recurring structural conventions and make context-specific sublanguages mechanically discoverable. In priority order, the review suggests investigating:

1. schema-aware tooling for generic profile/UI contexts,
2. documentation/grammar drift closure,
3. a consistent clause-punctuation and structured-policy design study,
4. a controlled agent-construction benchmark using the task/error catalog above, and
5. only then, compatibility-planned syntax simplification where measured construction errors justify the breaking cost.

No recommendation in this review changes the language or any support/conformance claim.
