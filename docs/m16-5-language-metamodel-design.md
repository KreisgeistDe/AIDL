# M16.5 Self-Describing Language Metamodel Design Candidate

Status: **non-normative design candidate**. This document does not change `docs/06-grammar.md`, accepted syntax, parser behavior, AST/IR schemas, diagnostics, formatter output, IDE behavior, support/conformance claims, or compatibility classes. It records a design target for later evidence-backed evaluation under M16.5.

## 1. Purpose

AIDL already has a broad but structured language surface. The grammar-complexity review shows that the main construction cost is not the number of domain concepts by itself, but the number of locally different ways declaration headers, leaves, named fields, policy values and nested blocks are written. M16.5 therefore evaluates whether two ideas can be combined:

1. normalize visible source construction around a small number of structural forms, and
2. make those forms compiler-introspectable through a versioned self-describing schema rather than duplicating construction rules across parser, completion, formatter, diagnostics and agent tooling.

The candidate is only useful if it preserves AIDL's semantic distinctions, M7 compatibility discipline and Canonical IR facts. Surface uniformity is not a license to merge concepts whose semantics differ.

## 2. Candidate visible construction model

The target declaration form to evaluate is:

```text
[export] <kind> <name> [<type-params>] [(<named-args>)] [-> <result-type>] { ... }
```

The target body forms to evaluate are:

```text
<keyword>: <value> [<modifiers...>]
<keyword> <name>: <value> [<modifiers...>]
<keyword> [<name>] { ... }
```

These are schema shapes, not approved syntax. A future design may retain existing punctuation in some contexts if compatibility or readability evidence wins.

### Why named declaration arguments are a candidate

Several current declaration headers encode independent semantic facts by fixed word order:

- `projection P from [A, B] into Store`
- `client C for Service`
- `migration M from "1" to "2"`
- `consumer C on Topic from Event`

A common named-argument model could expose these facts as schema-addressable slots rather than declaration-specific parser branches. The design objective is that source ordering becomes a formatting choice while the semantic model has stable names such as `sources`, `target`, `service`, `fromVersion`, `toVersion`, `topic`, or `messageType`.

This must be proven against the existing AST/IR and compatibility system. If any current header position carries semantics not expressible by named slots, the candidate must be revised rather than forcing the source into a lossy common shape.

## 3. Candidate normalization matrix

| Current form | Candidate schema model | Semantic facts | Design notes |
| --- | --- | --- | --- |
| `projection P from [A, B] into X` | declaration `projection P(sources: [A, B], target: X)` | source set/order where semantically relevant; target identity | parser prototype must prove equivalent reference diagnostics and IR projection |
| `client C for Service` | declaration `client C(service: Service)` | bound service | simple single-slot relationship candidate |
| `migration M from "a" to "b"` | declaration `migration M(from: "a", to: "b")` | source/target language or schema versions | M7 migration contract must distinguish language-syntax migration from modeled data migration semantics |
| `consumer C on Topic from Event` | declaration `consumer C(topic: Topic, from: Event)` | subscription target and accepted source | names may need refinement to avoid overloading `from` in introspection APIs |
| Entity field `email: string required unique` | body slot concept `field email: string required unique` | slot kind, field name, type, modifiers | explicit `field` is only a candidate; source terseness must be evaluated against discoverability |
| `index byEmail(email)` | named body slot `index byEmail: [email]` or structured block | name, ordered fields, direction | must preserve composite ordering and `asc`/`desc` |
| `deadLetter after 5 attempts` | typed value for `deadLetter` | threshold, unit/meaning | topic and queue may share a value schema only if semantics truly align |
| `singleton lease 30s` | typed `singleton` policy value | strategy, lease duration | declarative value can still be a tagged union rather than an untyped string |
| `changes to Order via outbox` | typed `changes` value | target, delivery mechanism | preserve target and `via` independently for semantic diff and completion |

## 4. Self-describing metamodel

The candidate metamodel introduces three conceptual declaration classes:

- `declaration` — describes a legal declaration kind and its header/body schema,
- `body` — describes one legal body slot, its visible keyword, cardinality, value schema, modifiers and nesting,
- `type` — describes value/type construction, including meta-types used by the language schema itself.

These are conceptual metamodel entities first. Whether they eventually appear as ordinary AIDL declarations, a compiler-owned schema file, generated bootstrap data, or a hybrid is an implementation decision for later packages.

### 4.1 Declaration schema

A declaration schema minimally needs:

- stable kind ID independent of display keyword,
- visible keyword,
- whether `export` is legal,
- name requirements and name category,
- type-parameter schema,
- named header arguments with cardinality and value/type constraints,
- optional result type,
- legal body schemas,
- allowed annotations/modifiers,
- documentation identifiers,
- compatibility/version metadata,
- semantic ownership hooks for validation and IR projection.

The last item is important: a schema can describe construction without replacing compiler semantics. Semantic ownership remains explicit and compiler-authoritative.

### 4.2 Body schema and visible keyword separation

A body schema should separate the token authors see from the semantic schema identifier. Design notation:

```text
body field: EntityField optional multi
```

Here:

- `body` identifies the metamodel category,
- `field` is the visible keyword candidate,
- `EntityField` is the semantic schema,
- `optional`/`multi` describe cardinality rather than ad-hoc parser branching.

The visible keyword need not equal the internal schema name. That makes renames/migration possible without breaking compiler-service identifiers and lets multiple contexts share a semantic schema while presenting context-appropriate source vocabulary when justified.

### 4.3 `EntityField<T>` candidate

`EntityField<T>` is an example generic semantic schema, not approved syntax. It would describe:

- required field name,
- value type `T` or a type expression constrained by `T`,
- legal modifiers,
- modifier cardinality/conflicts,
- annotation policy,
- default/value-expression policy,
- documentation/completion metadata,
- semantic validation owner,
- IR mapping requirements.

This is intentionally richer than “a parser rule for `identifier : type`”. Compiler services need to answer questions such as which modifiers are legal, which are mutually exclusive, what value shape a modifier expects and which semantic diagnostics own violations.

## 5. Modifiers should not automatically become a fundamental category

A tempting metamodel design is to create a separate universal `modifier` construct. M16.5 should resist that unless evidence shows it is necessary. Many modifiers can instead be represented as typed optional/multi slots attached to another schema:

- flag-like: `required`, `unique`, `immutable`,
- valued: `default <expr>`, `onDelete <action>`, `via <mechanism>`,
- structured policy values where appropriate.

The benefit is one schema mechanism for body slots and modifiers, with cardinality and type constraints shared. A dedicated modifier category remains available if it materially simplifies introspection or formatting, but it should not be introduced only because the current grammar spells some facts after a field type.

## 6. Meta-types and typed expressions

The metamodel must be able to constrain both source-level types and expressions without reducing semantic validation to string matching.

Candidate meta-types include concepts equivalent to:

- `type<T>` — a type expression whose resolved type satisfies `T`,
- declaration references constrained by declaration kind,
- literal categories such as duration/string/integer,
- typed expressions `expr<T>` or equivalent compiler-owned schema constraints,
- lists/records/unions over schema values,
- enum/tagged-policy values,
- name categories and qualified references.

The existing type checker remains authoritative. A metamodel constraint such as “expression of bool” is a construction/introspection contract that delegates to normal semantic resolution; it does not create a second type system.

## 7. Declarative operators: introspectable, not project-exportable

Operators are an attractive candidate for declarative description because completion, diagnostics, formatter precedence and expression tooling all need the same metadata. However, project-defined or exported operators would create a much larger language-design problem involving lexical ambiguity, precedence conflicts, compatibility and security of tooling assumptions.

The stability candidate is therefore:

- operator metadata may be compiler-owned and declaratively represented,
- precedence, associativity, token form and operand/result constraints may be introspectable,
- core operators remain non-exportable and non-redefinable by project source,
- the minimal kernel retains enough operator knowledge to parse the metamodel and ordinary expressions deterministically.

A later language decision could revisit extensible operators, but it is not part of this M16.5 candidate.

## 8. Bootstrap and kernel design

A self-describing language cannot bootstrap from nothing. The trusted kernel must be deliberately small and explicitly versioned.

### 8.1 Minimal hard-coded kernel candidate

The kernel likely needs to own at least:

- lexical tokens and comments/newline continuation,
- braces, delimiters and the minimal declaration/body framing needed to load schema declarations,
- identifiers, qualified names and basic literals,
- minimal type application/generic framing required by meta-types,
- expression operator precedence and associativity,
- schema declaration identities for `declaration`, `body`, `type` or their implementation equivalents,
- bootstrap schema version selection,
- deterministic error recovery/failure rules.

The objective is not zero hard-coded grammar. It is a kernel small enough that the majority of declaration/body construction can be described as data while the boot path remains auditable and deterministic.

### 8.2 Boot sequence candidate

1. Kernel lexes/parses the bootstrap schema using only kernel constructs.
2. Kernel validates bootstrap declarations against built-in meta-schema invariants.
3. A versioned standard language schema is loaded and validated.
4. The compiler derives construction schemas for ordinary declarations/body slots/types.
5. Project source is parsed against the selected language version.
6. Normal name resolution, type checking, profile/schema validation and diagnostics run.
7. Canonical IR construction occurs only after the existing semantic gates succeed.

Cycles, unknown schema versions or invalid bootstrap declarations fail closed. The compiler must never guess its way through a meta-circular dependency.

### 8.3 Trust and versioning

At minimum distinguish:

- **kernel-trusted** definitions shipped with the compiler,
- **standard-language schema** definitions versioned with the language/compiler contract,
- **profile/extension schemas** that may be compiler-distributed but are not kernel primitives,
- **project source** that cannot redefine trusted metamodel identities.

The exact packaging/signing/reproducibility mechanism is a later design decision, but a build must be able to report which kernel/language-schema versions produced its parse, diagnostics and construction-introspection answers.

## 9. Compatibility and migration alignment with M7

M7 remains the sole compatibility authority. A new surface spelling is not “compatible” merely because the formatter can rewrite it.

Every adopted normalization needs:

- language-version introduction point,
- whether old and new syntax coexist,
- deterministic compatibility class for source-version transitions,
- canonical source form per language version,
- deprecation diagnostic policy,
- formatter/rewrite behavior,
- fixture corpus covering comments, multiline expressions and source mapping,
- semantic-diff proof for pure syntax migrations,
- rollback behavior while old syntax is still supported,
- explicit removal criterion and major/version boundary when necessary.

Textually different but semantically equivalent formatting already produces no semantic diff under the compatibility model. A syntax migration must preserve that property only when the old and new forms truly map to the same semantic facts.

## 10. Parser and AST/IR implications

### Parser

The hypothesis to test is that schema-driven declaration/body parsing can reduce declaration-specific header and leaf-shape branches. The prototype must measure this rather than assume it. Generic parsing is only a win if invalid source still gets precise, deterministic diagnostics and if contextual ambiguity does not move into fragile post-parse heuristics.

### AST

A normalized surface suggests AST nodes with explicit stable semantic slots rather than opaque token-order fragments. But production AST changes are outside M16.5 planning. The prototype should map candidate slots onto the current AST and list any missing facts before proposing AST migration.

### Canonical IR

Canonical IR is semantic, not source-shaped. A normalization is acceptable only if:

- all current IR facts are preserved,
- no source fact silently disappears before IR,
- declaration IDs/source-map anchors remain deterministic,
- newly exposed semantic facts do not require undeclared IR changes.

If a candidate reveals missing IR semantics, that is a separate IR/version design problem rather than justification to drop the fact.

## 11. Compiler-service and schema-introspection candidate

A future compiler-owned construction endpoint should be able to answer, for an exact language/profile/snapshot context:

- legal declaration kinds,
- declaration header argument schemas,
- legal body slots and nested blocks,
- required/optional/multi cardinality,
- value/type/expression shape,
- allowed modifiers and conflicts,
- reference target kinds,
- documentation IDs,
- canonical formatting hints,
- deprecated/legacy spellings during migration.

The response should be versioned, deterministic and semantic-authoritative. CLI/LSP/MCP/IDE clients may project it, but they must not own a duplicated language schema.

This directly supports the M16 goal that agents construct source from compiler-owned capabilities rather than repository-wide heuristic scanning.

## 12. Formatter and migration implications

If a normalization is adopted, formatter and migrator are separate responsibilities:

- **formatter:** canonicalizes already-valid source for one selected language version;
- **migrator:** transforms source from an older accepted version/spelling to a newer one under an M7 migration contract.

Required properties:

- deterministic output,
- idempotence,
- comments/trivia preservation policy,
- no semantic changes for syntax-only rewrites,
- stable ordering rules for named arguments/body slots where order is semantically irrelevant,
- explicit preservation where order is semantically relevant,
- source-map/diagnostic relocation policy,
- dry-run semantic diff and compatibility evidence before write.

A formatter must not silently perform a breaking language migration.

## 13. IDE and completion implications

The current compiler-owned completion direction is intentionally conservative. A self-describing construction schema offers a route to broader completion without moving language authority into the IntelliJ PSI or another client.

A prototype should prove that:

- completion queries compiler-owned schema/context,
- snippets are generated from required/optional slots rather than hard-coded per declaration,
- reference-valued slots still use compiler resolution for candidates,
- deprecated syntax can be completed only according to selected language/migration mode,
- documentation links originate from the same schema metadata,
- IDE parsing remains presentation infrastructure, not semantic authority.

## 14. Diagnostics implications

Schema-driven construction can improve diagnostics if messages are expressed in semantic terms:

- missing required slot,
- duplicate single slot,
- unknown slot for declaration/body schema,
- wrong value shape/type,
- invalid modifier for slot,
- unresolved/wrong-kind reference,
- deprecated legacy spelling with migration action.

However, generic diagnostics are not enough. Existing domain-specific semantic diagnostics remain necessary for facts that depend on cross-reference, profile, compatibility or runtime semantics. The schema layer should identify the semantic owner rather than replace it.

During old/new coexistence, the compiler must distinguish:

1. valid legacy syntax,
2. deprecated-but-valid legacy syntax,
3. mechanically migratable syntax error,
4. semantic error independent of spelling.

## 15. Vendor-neutral M16 evaluation

The design should be judged with the same task corpus and semantic end-state checks before and after. Required metrics remain:

- compile success,
- semantic correctness,
- unnecessary edits,
- repair loops,
- regressions,
- first-pass parse rate,
- first-pass semantic-validation rate,
- invented-syntax rate,
- wrong-placement rate,
- diagnostics per 100 source lines,
- semantic-fact recall.

Additional implementation-facing measurements may include parser branch/special-case count, formatter rule count, completion schema coverage and diagnostic-context duplication, but these must be reproducibly defined before being used as evidence.

No model/vendor/runtime is part of the language contract. Model configuration is evaluation metadata only.

## 16. Ordered follow-on packages

The authoritative work breakdown lives in `backlog/m16-5-language-surface-normalization.md`. The intended order is:

1. design decision,
2. compatibility/migration contract,
3. isolated experimental parser/schema prototype,
4. compiler-service/schema-introspection prototype,
5. formatter/migration prototype,
6. IDE/completion prototype,
7. diagnostics prototype,
8. vendor-neutral before/after evaluation,
9. only then a separately authorized breaking implementation proposal.

Packages 1–8 do not authorize a production syntax change. Package 9 requires a new dispatch and explicit language-version decision.

## 17. Decision criteria

The candidate should advance only if evidence shows that it can:

- reduce construction-shape irregularity without erasing semantic distinctions,
- preserve all AST/IR facts or explicitly surface separate required semantic work,
- support deterministic M7 migration and rollback,
- shrink duplicated parser/formatter/completion/diagnostic construction knowledge,
- make compiler-owned construction introspection materially more complete,
- keep the bootstrap kernel small, auditable and deterministic,
- avoid project-defined operator/precedence instability,
- improve or at minimum not regress the vendor-neutral M16 construction metrics.

If those conditions are not met, retaining current syntax plus schema-driven tooling clarification is a valid M16.5 outcome.
