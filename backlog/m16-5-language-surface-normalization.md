# M16.5 — Language Surface Normalization Gate

Goal: turn the measured grammar-construction hotspots into an evidence-backed normalization decision before broad M17–M20 language-surface implementation, without changing AIDL syntax or semantics in this milestone itself.

Dependencies: M7 remains the sole compatibility-classification authority; M10 provides conformance/evidence discipline; M16 provides the model-independent construction/change evaluation approach; `docs/06-grammar.md`, `docs/grammar-complexity-review.md`, and `tools/grammar_complexity_metrics.py` provide the current deterministic syntax baseline. The focused non-normative design companion is `docs/m16-5-language-metamodel-design.md`.

This milestone is a planning and decision gate. It does not define replacement syntax, change parser behavior, promote support claims, or authorize a breaking change. Any later syntax change requires its own versioned language decision, implementation, compatibility evidence, migration plan, fixtures, conformance updates, formatter/migration support, diagnostics, and IDE/completion treatment.

## Candidate target shape to evaluate

M16.5 evaluates, but does not yet adopt, a deliberately small set of structural forms:

- declaration header candidate: `[export] <kind> <name> [<type-params>] [(<named-args>)] [-> <result-type>] { ... }`,
- body value candidate: `<keyword>: <value> [<modifiers...>]`,
- named body value candidate: `<keyword> <name>: <value> [<modifiers...>]`,
- nested block candidate: `<keyword> [<name>] { ... }`.

The goal is not to make unrelated concepts semantically identical. It is to test whether a smaller number of visible structural rules can carry the same semantic facts while reducing exact-token-order recall, parser-special-case count, formatter branches, completion contexts, and diagnostic ambiguity.

## Concrete normalization matrix

Each row is a design candidate only. M7 compatibility and migration evidence must decide whether a later implementation may be compatible, expandable/coordinated, or breaking.

| Current family | Candidate structural direction | Facts that must remain explicit | Compatibility/migration requirement |
| --- | --- | --- | --- |
| `projection X from [A, B] into Y { ... }` | move `from` and `into` from relationship-qualified header into named arguments or body slots under the common declaration form | source event/type set, target type/resource, projection identity | old/new semantic equivalence fixture, deterministic rewrite, no IR fact loss |
| `client X for Service { ... }` | model `for` as a named declaration argument such as `client X(for: Service)` | bound service identity | preserve reference resolution and source-map identity; M7 classify syntax migration |
| `migration X from "a" to "b" { ... }` | model source/target versions as named declaration arguments | from version, to version, migration identity | versioned syntax boundary, deterministic formatter/rewrite, rollback to old spelling during coexistence |
| `consumer X on Topic from Event { ... }` | model `on` and `from` as named declaration arguments | subscription target, accepted message/event source, consumer identity | preserve reference-kind diagnostics and deployment/compatibility semantics |
| unprefixed Entity fields `name: Type modifiers...` | evaluate explicit self-describing body slot such as `field name: Type modifiers...` | field name, value type, modifier set, annotations | migration must distinguish fields from other body declarations without semantic drift |
| `index name(field asc, ...)` | evaluate `index name: (...)` or a schema-driven named block/slot form | index name, ordered fields, sort direction | preserve order and uniqueness semantics; formatter must be canonical |
| `deadLetter after N attempts` | evaluate `deadLetter: N attempts` or a structured slot with named facts | retry-attempt threshold and dead-letter behavior | do not conflate topic/queue semantics; semantic diff must stay empty after rewrite |
| `singleton lease 30s` | evaluate `singleton: lease 30s` or a typed policy value | singleton mode, lease duration | preserve scheduler semantics and diagnostics for unsupported policy combinations |
| `changes to Target via outbox` | evaluate a named semantic slot such as `changes: Target via outbox` or structured value | change target and delivery mechanism | preserve sync semantics and outbox fact independently |

Additional hotspot families from the grammar-complexity review remain in the decision matrix: colonized versus uncolonized leaves; `auth`, `errors`, `retry`, `timeout`, `consistency`, and `idempotency` variants; compact versus structured policies; `profileProperty`, `uiStatement`, and `testStatement`; and confusable declaration families. Visual normalization alone must never erase context-specific semantic distinctions such as API error encoding versus typed operation errors or error retry class versus execution retry policy.

## Self-describing metamodel candidate

M16.5 also evaluates whether the language surface can become more compiler-introspectable by modeling parts of its own construction schema. The candidate is detailed in `docs/m16-5-language-metamodel-design.md` and has these constraints:

- `declaration`, `body`, and `type` are candidates for modelable declarations, not immediate new syntax.
- A body slot separates the visible keyword from its semantic schema. Example design notation: `body field: EntityField optional multi`.
- `EntityField<T>` conceptually describes the slot name, value type, cardinality and permitted modifiers instead of encoding those facts only in hand-written parser branches.
- Modifiers should reuse typed slot/schema structures where practical; they should not become a second fundamental metamodel category unless evidence requires it.
- `type<T>`/meta-types and typed expressions must be representable without weakening the existing semantic type checker.
- Operator definitions may be made declarative for compiler introspection, but non-exportable built-in operators are the stability candidate so projects cannot redefine precedence or core semantics.

The metamodel is not trusted merely because it is self-describing. A minimal hard-coded kernel must own bootstrap parsing, trusted meta-types, schema validation order, operator precedence, version selection, export boundaries, and failure behavior.

## Bootstrap and kernel questions that must be answered before adoption

1. **Minimal kernel:** Which declaration/type/body constructs are hard-coded strongly enough to parse and validate the metamodel itself?
2. **Meta-circular bootstrap:** What is the deterministic sequence from kernel schema to self-described standard language schema, and how is a bootstrapping cycle rejected rather than guessed through?
3. **Trust boundary:** Which type/schema definitions are compiler-trusted, which are ordinary project declarations, and how are trusted definitions versioned and signed/reproduced?
4. **Operators:** Where are precedence, associativity and tokenization fixed? Can operator metadata be introspected without permitting project export/redefinition?
5. **Export boundary:** Which metamodel declarations may be referenced by project/profile schemas, and which kernel declarations remain non-exportable?
6. **Validation order:** Lexing/parsing, bootstrap schema loading, structural validation, name/type resolution, profile/schema validation, diagnostics and IR construction must have one deterministic ordering.
7. **Versioning:** How are language-schema and metamodel versions selected, and how does M7 classify source accepted by one version but not another?
8. **Migration:** How are old syntax and candidate normalized syntax parsed during coexistence, formatted canonically, rewritten deterministically and eventually retired?

## Cross-surface design gates

Every candidate decision must be checked against all of these surfaces before implementation authorization:

- **M7 compatibility/migration:** source spelling changes are language-version changes; textual rewrites must prove semantic equivalence and deterministic compatibility classification.
- **AST and Canonical IR:** normalized syntax must preserve semantic facts and stable declaration/source-map identity; surface reduction is invalid if IR needs new facts that are not represented.
- **Parser:** the target is fewer declaration/header and leaf-shape special cases, but parser simplification is an outcome to measure, not an assumption.
- **Formatter/migration:** each adopted normalization needs one canonical new spelling and an idempotent old-to-new rewrite with fixtures and rollback/coexistence rules.
- **IDE/completion:** completion should consume compiler-owned declaration/body/type schemas rather than duplicate contextual keyword tables; old/new syntax during migration must remain unambiguous.
- **Diagnostics:** errors should refer to semantic slots and expected schemas while retaining source-localized diagnostics for legacy syntax; migration diagnostics must distinguish deprecated spelling from invalid semantics.
- **Compiler services/schema introspection:** legal declaration kinds, body slots, value shapes, modifiers and documentation must be queryable from a versioned compiler-owned schema rather than reconstructed by clients.
- **M16 before/after evaluation:** use the same model/vendor-neutral task corpus and semantic end-state checks; record raw counts and deltas only after execution.

## Ordered executor packages

These packages are follow-on work. A package may start only when all listed dependencies are complete; none except the final breaking implementation package changes accepted language syntax.

### E1 — Design decision record

**Depends on:** current M16.5 roadmap and grammar-complexity baseline.

**Work:** finalize the target declaration/body forms, the concrete normalization matrix, the metamodel/kernel trust model, and explicit keep/normalize decisions for every hotspot.

**Acceptance:** every hotspot has a disposition; every normalized row identifies preserved semantic facts; bootstrap, operators, export boundaries and validation order have explicit decisions; no parser/code change.

### E2 — Compatibility and migration contract

**Depends on:** E1 and M7 compatibility authority.

**Work:** define language-version boundary, old/new coexistence window, deprecation diagnostics, compatibility classes, deterministic rewrite rules, fixture strategy, rollback and removal criteria.

**Acceptance:** each candidate syntax change has an M7-owned classification rule and migration lifecycle; semantic-equivalent rewrites produce no semantic diff; breaking cases require explicit version/approval.

### E3 — Experimental parser/schema prototype

**Depends on:** E1 and E2.

**Work:** isolated experiment proving whether the proposed common declaration/body schema can parse representative normalized examples and round-trip semantic facts. It must not alter production grammar or support claims.

**Acceptance:** prototype covers every matrix row plus representative existing families, reports parser/special-case deltas, and demonstrates where the common model fails without changing production behavior.

### E4 — Compiler-service and schema-introspection design/prototype

**Depends on:** E1; may run after E3 if parser facts are needed.

**Work:** versioned read-only schema for legal declaration kinds, header arguments, body slots, value/type shapes, modifiers, docs and nesting.

**Acceptance:** completion/agent clients can discover representative App/Core/Backend/Sync shapes from compiler-owned data; no client-side semantic reconstruction is required.

### E5 — Formatter and migration prototype

**Depends on:** E2 and E3.

**Work:** deterministic old-to-candidate rewrite and canonical candidate formatter in an experimental path.

**Acceptance:** rewrite is idempotent, semantic end state matches, comments/source locations have an explicit preservation policy, and rollback/coexistence behavior is fixture-backed.

### E6 — IDE/completion prototype

**Depends on:** E4 and E5.

**Work:** consume compiler-owned schema metadata for candidate declaration/body construction and migration-aware completion.

**Acceptance:** representative completion cases do not hard-code a second language schema; old/new syntax is not mixed incorrectly; no IDE layer becomes semantic authority.

### E7 — Diagnostics prototype

**Depends on:** E2–E4.

**Work:** schema-driven expected-slot/value diagnostics plus migration/deprecation diagnostics.

**Acceptance:** diagnostics remain deterministic and source-localized; equivalent invalid constructs produce consistent semantic messages across old/new spellings; no diagnostic silently changes compatibility class.

### E8 — Vendor-neutral before/after evaluation

**Depends on:** E3–E7 and the M16 evaluation harness/task fixtures.

**Work:** execute identical construction/change tasks against baseline and candidate tooling.

**Acceptance:** report compile success, semantic correctness, unnecessary edits, repair loops, regressions, first-pass parse rate, first-pass semantic-validation rate, invented-syntax rate, wrong-placement rate, diagnostics per 100 source lines, semantic-fact recall, and raw counts/deltas; no benefit claim without measured evidence.

### E9 — Breaking implementation proposal

**Depends on:** reviewed E1–E8 evidence.

**Work:** separate language-version implementation proposal for any adopted normalization.

**Acceptance:** exact grammar/parser/AST/IR/tooling changes, compatibility window, fixtures, conformance impact, migration tooling and release plan are approved before production code changes. M16.5 completion alone never authorizes E9.

## Existing work items retained by the gate

- [ ] **P1** Freeze a reproducible language-surface baseline from `tools/grammar_complexity_metrics.py` and the 16-family construction taxonomy before any normalization design is approved.
- [ ] **P1** Complete the normalization decision matrix for all measured high-risk families without equating semantically different concepts merely because syntax looks similar.
- [ ] **P1** Complete the M7 compatibility and migration contract for every candidate that could change accepted source text.
- [ ] **P1** Make generic `profileProperty`, `uiStatement`, and `testStatement` sublanguages mechanically discoverable through compiler-owned schemas before expanding them.
- [ ] **P1** Decompose compound word-order mini-languages into named semantic facts and map each fact to downstream IR and migration sensitivity.
- [ ] **P2** Add explicit “choose this concept when…” guidance and future diagnostic/completion requirements for confusable declaration families.
- [ ] **P1/P2** Run the M16 model- and vendor-neutral construction evaluation as a true before/after comparison for any adopted normalization or tooling-only discoverability change.
- [ ] **P1** Gate broad M17–M20 surface expansion on a reviewed normalization decision.

## Acceptance criteria

- [ ] The deterministic grammar baseline and 16 construction families remain reproducible and linked without inventing new measurements.
- [ ] The common declaration/body target and every concrete matrix row have an explicit design disposition and preserved-semantic-fact inventory.
- [ ] The self-describing metamodel candidate has a defined minimal kernel, trust/version boundary, bootstrap order, operator policy, export boundary and deterministic validation sequence.
- [ ] Every potentially breaking normalization is blocked on an M7-owned versioned compatibility/migration contract, canonical formatter/rewrite behavior and fixture strategy.
- [ ] Parser, AST/IR, compiler service/schema introspection, formatter/migration, IDE/completion and diagnostics impacts are explicitly evaluated before production syntax implementation.
- [ ] Vendor-neutral M16 construction evaluation uses the same semantic task corpus and records raw before/after evidence only when actually executed.
- [ ] No M16.5 planning/design completion item by itself changes syntax, parser acceptance, semantic meaning, Canonical IR, generator/runtime behavior, IDE support, profile status or conformance claims.
- [ ] Broad M17–M20 implementation proceeds only after the gate establishes stable forms, tooling-only improvements and separately authorized migration candidates.
