# M16.5 E2 — Compatibility and Migration Contract

Status: **non-normative design contract**. This document resolves M16.5/E2 only. It does not change `docs/06-grammar.md`, accepted source syntax, parser/lexer behavior, AST or Canonical-IR schemas, formatter/IDE/LSP/runtime behavior, support/conformance claims, or any M7 compatibility result for existing source. E3 and later packages require separate authorization.

Base: `a2209ae4430406a5ccf5e353b7004c38278b1d1c` (`main`). E1 is the binding design input: 211 normative productions, 57 Kernel-owned productions, 154 Structural-Schema-owned productions, 56 Semantic facts, the A-prime combinator model, and the E1 hotspot dispositions in `docs/m16-5-e1-design-decision.md`.

## 1. E2 decisions at a glance

E2 freezes the following contracts for later prototype work:

1. **Source-language version authority:** one explicit project/compiler selection outside AIDL source text. A normal compilation has exactly one source-language version. No per-file guessing, no implicit version inference, and no app-level language selector. Mixed-version import graphs fail closed before semantic analysis. Migration mode may compile old and new snapshots separately and compare their Canonical IR through M7.
2. **Trusted schema identity:** compiler-owned schema identities use the reserved `urn:aidl:` namespace. Identity, semantic version, content fingerprint, dependency set, Kernel version, compiler build, profile versions and Canonical-IR version are independent reportable facts.
3. **Schema loading:** dependencies resolve to exact immutable identity/version/fingerprint tuples, form an acyclic graph, and are decoded/meta-validated/fingerprinted at most once per immutable schema version per compiler-service process. Unknown versions, missing dependencies, duplicate trusted identities, cycles and fingerprint mismatches fail before source semantics.
4. **Lossless source:** E3 uses an immutable-source **sidecar** containing token/trivia/newline ranges and stable structural anchors. Canonical IR remains semantic. Stale fingerprints, overlapping edits, missing/ambiguous anchors or schema mismatch fail closed. A shared lossless CST is not selected for E3.
5. **Structural diagnostics:** new schema-owned structural failures use the reserved `AIDL-S###` family only where no existing code applies. Existing diagnostic code, severity, location and relative ordering are preserved.
6. **Formatter versus migrator:** a formatter canonicalizes valid source within one selected language version; a migrator performs an explicit cross-version rewrite. Formatting never changes language version and never reorders semantically ordered sequences. Migration is anchor-based, idempotent, lossless outside edited ranges, and gated by a dry-run semantic diff.
7. **Startup/benchmark protocol:** no per-document schema filesystem load; immutable schema materialization is reused. Benchmark results are comparable only for a pinned workload, compiler/schema identities, warm/cold mode and machine class. E2 sets no latency threshold because none has been measured.
8. **Normalization lifecycle:** every E1 `normalize-candidate` remains a candidate. E2 defines how a future spelling could be introduced, coexist, migrate, roll back and be removed; it does not select or accept any candidate spelling.

## 2. M7 source-language compatibility model

M7 remains the sole compatibility authority. E2 adds a source-language-version contract around M7 rather than creating a second semantic diff system.

### 2.1 Version selection

The selected source-language version is a required compiler/project input supplied by project configuration or the compiler invocation. It is **not** read from AIDL source text in E2.

Rules:

- a normal project compilation selects exactly one source-language version before source parsing;
- every file in the compilation graph is parsed against that same selected language schema;
- imported source or cached metadata that claims a different source-language version is rejected before semantic resolution;
- absent or unknown source-language versions fail closed; there is no “latest”, heuristic, syntax-sniffing or per-file fallback;
- `app` versions, profile versions, API versions, event versions and migration-declaration data versions are not source-language versions;
- a future file directive or app-level selector would itself be a production-language change and therefore requires a separately authorized language decision.

**Chosen authority:** compiler/project configuration. The exact manifest key, CLI spelling or API field is an implementation detail for a later authorized package; E2 fixes the semantic authority, not a new source syntax.

### 2.2 Normal compilation versus migration mode

Normal compilation is single-version and closed under imports. Migration mode is a separate compiler operation:

1. pin old compiler/Kernel/language/profile schema identities and fingerprints;
2. compile the immutable old source snapshot under the old source-language version;
3. produce an anchored rewrite plan for an explicitly selected target version;
4. materialize a candidate target snapshot without modifying the old snapshot;
5. compile the target snapshot under the target source-language version;
6. compare old and target Canonical IR through M7;
7. permit a syntax-only migration only when the intended semantic end state is `compatible` and no fact is lost;
8. write only after all source, schema, diagnostic and semantic gates pass.

The two versions may be loaded in one compiler-service process as two immutable compilation contexts, but they must never form one mixed-version source graph.

### 2.3 M7 classification rules for source-surface evolution

Canonical-IR diff remains semantic. Source acceptance still needs a release disposition:

| Source-language action | Required M7/release treatment | Semantic evidence |
| --- | --- | --- |
| same-version formatting only | `compatible` | identical Canonical IR; no source-version change |
| add a second accepted spelling while retaining the old spelling in the selected version | `expandable` | both spellings must compile to equivalent Canonical IR for syntax-only aliases |
| explicit project switch between two coexisting language versions where all required source rewrites are deterministic | `coordinated` | old and migrated snapshots must have compatible Canonical IR for syntax-only rewrites |
| remove a previously accepted spelling/version | `breaking` | a successful migrator does not make source removal compatible |
| any rewrite that loses or changes semantic facts | `breaking` or stronger existing M7 class | never allowed to masquerade as syntax-only migration |
| any migration with unknown/unclassifiable semantic result | fail closed | M7 result must not be `unknown` for an automated write |

A syntax-only migrator must never produce `dataLoss`. If it does, the candidate is invalid and the write is blocked.

### 2.4 Coexistence, rollback and removal

A future adopted candidate follows four explicit states; E2 does not move any candidate into them:

1. **old-only:** current production grammar; candidate spelling is not accepted;
2. **coexistence:** an explicitly versioned language release may accept old and candidate spellings, with one canonical target spelling and deterministic diagnostics;
3. **new-canonical:** old spelling may remain deprecated-valid under an explicitly selected version while the migrator rewrites it deterministically;
4. **old-removed:** only after a separately approved breaking source-version boundary.

Rollback is possible only while the old source-language version and its exact schema/compiler support remain available. A migration write retains the original bytes or a reversible patch until commit. Removal requires all of these gates: complete authorized fixture coverage, deterministic rewrite, migration idempotence, compatible Canonical-IR result for syntax-only cases, no unresolved/ambiguous anchors, stable diagnostics, a declared deprecation window, and explicit M7/release approval. Missing evidence keeps the old spelling/version available.

## 3. Trusted schema identity, versions, fingerprints and dependencies — ADR boundary B

### 3.1 Reserved identity namespace

**Decision:** use a reserved URI/URN namespace. Compiler-trusted identities begin with `urn:aidl:` and are not mintable or redefinable by project source.

Canonical identity forms are conceptual identifiers, not AIDL syntax:

- standard language schema: `urn:aidl:schema:language:<name>`;
- construction/meta schema: `urn:aidl:schema:meta:<name>`;
- compiler-distributed profile schema: `urn:aidl:schema:profile:<name>`.

The stable identity excludes the visible source keyword and excludes the semantic version. Version and fingerprint are separate tuple members. This keeps identity stable across compatible metadata changes and spelling aliases while making each immutable schema instance exact.

### 3.2 Immutable schema reference

Every trusted schema instance is addressed by the tuple:

`(schema_id, semantic_version, content_fingerprint)`.

Dependencies name the complete immutable tuple. A dependency resolver must not substitute a “closest”, “latest” or semver-compatible version after compilation context creation.

`content_fingerprint` is an algorithm-qualified digest over the canonical packaged schema bytes. The algorithm choice is implementation-owned but must be explicit in serialized/reportable metadata; equality never relies on an unqualified hash string.

### 3.3 Independent version/reporting fields

Every compilation context reports independently:

- compiler build identity;
- Kernel version;
- selected source-language schema ID, semantic version and content fingerprint;
- every selected profile schema ID, semantic version and content fingerprint;
- complete exact schema dependency tuples;
- Canonical-IR schema/version.

None of these fields may be inferred from another. In particular, a compiler build does not stand in for a language-schema version, and a source-language version does not stand in for Canonical-IR version.

### 3.4 Trust/coexistence rules

The four E1 trust tiers remain unchanged. The resolver enforces:

- trusted IDs in `urn:aidl:` cannot be shadowed by project declarations;
- the dependency graph is acyclic;
- one `(schema_id, semantic_version)` may resolve to only one fingerprint in a process; conflicting fingerprints are fatal;
- immutable schema instances may be cached and reused across compilation snapshots;
- multiple source-language versions may coexist in process cache or migration mode, but one normal compilation selects exactly one;
- profile schemas may coexist only when their exact dependency graph is consistent with the selected language context;
- unknown ID/version, missing dependency, duplicate trusted ID, dependency cycle or fingerprint mismatch fails before source semantics and before Canonical IR.

## 4. Lossless source and refactoring architecture — ADR boundary C

### 4.1 E3 architecture decision

**Decision:** use a lossless sidecar for the E3 experiment. Do not introduce a shared production CST in E2/E3.

The source layer owns:

- immutable original source bytes and source fingerprint;
- every token range;
- every trivia range, including comments and ordinary whitespace;
- physical newline ranges and logical-newline/continuation facts;
- stable anchors for document items, declaration header facts, body items, modifiers and nested structural items;
- the selected language-schema fingerprint used to interpret those anchors.

AST/CompilerDeclaration and Canonical IR remain separate. Canonical IR must not acquire trivia as a side effect of migration work.

### 4.2 Anchor contract

An anchor identifies a source-owned range plus its structural role and immutable fact identity where available. Refactoring/migration resolves semantic identities through the normal compiler, then maps the authorized edit back to source anchors.

Edits fail closed when:

- the source fingerprint differs from the snapshot used to compute the plan;
- the selected language/profile schema fingerprint differs from the plan;
- an anchor is missing or resolves ambiguously;
- planned edits overlap without one explicit owning edit;
- a semantic identity no longer resolves to the expected anchored source item.

Unedited ranges are copied byte-for-byte. A rewrite may alter only its authorized anchored slices plus the minimum required separators inside those slices.

### 4.3 Shared-CST reopen gate

A shared lossless CST remains a later alternative, not the E3 choice. It may replace the sidecar only after evidence shows equal or better losslessness, recovery, refactoring anchors and incremental-update behavior without creating a second source-authority model. This is an architecture reopen, not a syntax decision.

## 5. Structural diagnostics and migration states — ADR boundary E

### 5.1 Namespace

**Decision:** reserve `AIDL-S###` for Structural-Schema-owned construction diagnostics. `S` means structural; severity remains an independent diagnostic field. This family is used only when no existing diagnostic code already owns the failure.

Frozen mapping for later implementation:

| Code | Structural condition |
| --- | --- |
| `AIDL-S001` | missing required structural slot/item |
| `AIDL-S002` | duplicate single-cardinality structural slot/item |
| `AIDL-S003` | unknown structural slot/item for the selected schema |
| `AIDL-S004` | wrong structural value shape or cardinality |
| `AIDL-S005` | invalid structural modifier, nesting or schema-owned local-order constraint |
| `AIDL-S006` | deprecated-but-valid legacy spelling in an explicitly selected coexistence version |
| `AIDL-S007` | known mechanically migratable legacy spelling that is invalid in the selected target version |
| `AIDL-S008` | source-language/schema-context mismatch detected while associating source with a selected structural schema |

Unresolved references, wrong resolved target kind, type errors, project invariants, compatibility failures and other Semantic-owned failures retain their existing code families. E2 does not recode them as structural failures.

### 5.2 Preservation and ordering

For unchanged existing invalid source, code, severity, location and relative order must remain unchanged. Structural diagnostics enter only at new schema-owned failure points. The existing deterministic ordering contract remains: document/source order first, then source offset and compiler phase, followed by the established severity/code/message tie-breakers. Introducing `AIDL-S###` must not reorder two pre-existing diagnostics relative to each other.

### 5.3 Migration diagnostic state machine

For a source construct under an explicit selected language version:

1. **valid current spelling:** no migration diagnostic;
2. **valid legacy spelling under a legacy version:** no migration diagnostic merely for being old;
3. **deprecated-but-valid legacy spelling in a coexistence version:** `AIDL-S006`, anchored to the spelling, with a deterministic migration action;
4. **mechanically migratable legacy spelling rejected by the target version:** `AIDL-S007`, with no semantic guessing and no write until migration mode is explicitly invoked;
5. **semantic error independent of spelling:** keep the original Semantic diagnostic; do not substitute `AIDL-S006/S007`.

A migration tool may surface planned edits, but it must not suppress semantic diagnostics to make a rewrite appear successful.

## 6. Canonical formatting versus migration — ADR boundary F

### 6.1 Separate responsibilities

For source-language version `v`:

- `Formatter(v)` accepts source already valid under `v` and emits the canonical form for `v` only.
- `Migrator(v -> w)` accepts an explicit old/target version pair and plans a cross-version rewrite under this contract.

A formatter must not select a new language version, accept otherwise-invalid legacy syntax, emit deprecation rewrites that cross versions, or change compatibility state.

### 6.2 Formatting order

E1 semantic-order facts remain authoritative. A formatter may reorder an item only when Structural Schema explicitly marks it semantically unordered. Absence of that marker means preserve relative source order.

The following remain non-reorderable regardless of formatter rank: transaction statements and writes/emits, workflow steps and inner statements, saga steps/compensation order, action effects, control-flow branches/statements, test/UI statement sequence when their schema marks execution/source order significant, and every item covered by E1 `S051 semantic ordering guarantee`.

Formatter rank is presentation metadata. It is never a source of semantic order.

### 6.3 Migrator algorithm and gates

A cross-version migrator must:

1. validate old bytes against the explicit old version and fingerprints;
2. produce an edit plan over lossless anchors;
3. reject stale fingerprints, missing/ambiguous anchors and overlapping edits;
4. apply edits to a new buffer, copying untouched ranges byte-identically;
5. validate target source against the explicit target version/fingerprints;
6. optionally apply `Formatter(target)` only after target validity, respecting semantic-order rules;
7. compile old and target snapshots to Canonical IR;
8. run M7 semantic diff and require the candidate's declared compatibility result;
9. verify migration idempotence: a second `Migrator(v -> w)` application to the target must produce no further edit plan;
10. emit deterministic diagnostic/source relocation metadata for changed anchors and preserve unaffected locations exactly.

A dry run reports old/target source versions, schema fingerprints, source fingerprint, planned anchored edits, diagnostic delta and M7 semantic result before any write. Failure at any gate leaves original bytes unchanged.

## 7. Controlled startup and benchmark protocol — ADR boundary G

### 7.1 Structural startup budget

The E1 budget becomes an E2 gate for E3 evidence:

- at most one decode/meta-validation/fingerprint operation for a bundled standard-language schema per immutable schema version per compiler-service process;
- no per-document schema filesystem load;
- immutable schema materializations are reused across document/snapshot compilations;
- fingerprint/dependency/identity failures happen before project source semantics;
- cache reuse must be keyed by exact immutable schema tuple, never by display name alone.

### 7.2 Reproducible benchmark record

Any startup/parser benchmark used for an E3+ decision must pin and publish:

- project commit and exact workload file list plus content fingerprints;
- compiler build, Kernel version, language/profile schema tuples and Canonical-IR version;
- interpreter/runtime/toolchain versions;
- OS and machine class, including CPU architecture/count and memory class;
- cold or warm process mode;
- warmup count, measured repetition count and process reuse policy;
- raw timings and allocation/load counters used to support a claim;
- summary statistics and observed variance.

The controlled default protocol for the first comparable measurement is **10 cold fresh-process runs** and **30 warm runs after 5 warmups in one process** on one pinned machine class. The raw samples are authoritative. Median/p95 or other summaries may be reported, but E2 sets **no pass/fail latency threshold**; thresholds may be proposed only after baseline variance exists.

## 8. Compatibility matrix for every E1 hotspot and normalization row

Legend for lifecycle below:

- **N/A migration:** current source remains authoritative; no spelling migration is permitted or needed.
- **Candidate lifecycle:** old-only now; if later adopted, explicit version introduction -> optional coexistence/deprecation -> coordinated migration -> separately approved breaking removal.
- Every syntax-only rewrite must preserve the named E1 facts and produce compatible Canonical IR. Any mismatch blocks the candidate.

| E1 item | Current source contract | E1 disposition | Version/M7 rule | Rewrite/coexistence and diagnostics | Preserved facts / rollback-removal gate |
| --- | --- | --- | --- | --- | --- |
| projection `from [...] into` header | relationship-qualified ordered header in normative grammar | normalize-candidate | Candidate lifecycle; added alias `expandable`, project switch `coordinated`, old removal `breaking` | deterministic anchored header-slot rewrite only after a future spelling is authorized; `S006/S007` during coexistence/target rejection | projection identity, source set/order where semantic, target (`S027`, resolution facts); rollback to old version; remove only after equivalent IR fixtures |
| client `for Service` | relationship-qualified header | normalize-candidate | Candidate lifecycle | rewrite only the bound-service header anchor; no inference from body | bound service (`S033`) and reference identity; same removal gates |
| migration `from "a" to "b"` | modeled data-migration versions in declaration header | normalize-candidate | Candidate lifecycle; source-language version must remain distinct from modeled migration versions | rewrite named header facts only; diagnostics must never label data versions as language versions | data migration from/to semantics (`S041`); compatible IR required |
| consumer `on Topic from Event` | ordered topic/source relationship header | normalize-candidate | Candidate lifecycle | anchored two-fact rewrite; reject ambiguous target kinds rather than guess | consumer subscription/retry/invocation facts (`S026`) plus target-kind resolution |
| implicit entity/value fields | keywordless `identifier : type modifiers` body entries | normalize-candidate | Candidate lifecycle | future explicit slot spelling may coexist only under explicit version; field anchors retain annotations/modifiers | type/default/modifier/reference facts (`S003`, `S011`, field domain facts); no field may be silently reclassified |
| `index name(field asc, ...)` | named comma-delimited ordered index entry | normalize-candidate | Candidate lifecycle | preserve index-field order; candidate formatter cannot sort fields | index identity, ordered fields/direction and uniqueness semantics; removal gated by ordered fixture parity |
| `deadLetter after N attempts` | compound topic/queue leaf | normalize-candidate | Candidate lifecycle | rewrite only when topic/queue schema owns an unambiguous typed value; keep domain-specific diagnostics | threshold plus topic/queue behavior (`S025`); no cross-domain conflation |
| `singleton lease D` | compound schedule leaf | normalize-candidate | Candidate lifecycle | deterministic typed-value rewrite only; no inferred scheduler defaults | singleton mode/lease/catch-up semantics (`S031`) |
| Sync `changes to T via outbox` | compound Sync leaf | normalize-candidate | Candidate lifecycle | target and delivery mechanism require distinct anchors/facts | target and outbox fact (`S039`), source mapping; rollback on either fact mismatch |
| colonized vs uncolonized leaves | punctuation varies by declaration/context | normalize-candidate | Candidate lifecycle per affected schema; no global alias without context | context-owned punctuation rewrite; `S006/S007` only when candidate is explicitly versioned | preserve context-specific Semantic owner; semantic equality required for every affected fixture |
| idempotency compact vs block | both compact and structured forms exist in current contracts | normalize-candidate | Candidate lifecycle only if one form is later retired; coexistence may already be semantically intentional | migrator must prove all key/scope/retain facts, not just text shape | idempotency (`S020`); removal blocked if forms are not semantically equivalent in a context |
| retry vocabulary/placement | error class, consumer/task policy and workflow-header retry are distinct | normalize-candidate | Candidate lifecycle separately per semantic owner; never one global rewrite | typed/contextual rewrite only; semantic diagnostics retain existing codes | retry class/policy facts (`S004`, `S026`, `S028`, `S030`); no cross-context merge |
| auth and error forms | API transport, operation auth/errors and frontend auth are distinct | schema-only/tooling | N/A migration; current spellings remain | expose construction metadata/completion only; no migration diagnostic | API transport/auth/error (`S016`), operation auth/typed errors (`S017`,`S018`), frontend auth (`S043`) |
| consistency/timeout/budget | context-specific operation/task/workflow/profile shapes | normalize-candidate | Candidate lifecycle only per exact semantic schema | no universal replacement; schema identifies value owner before rewrite | consistency (`S019`), workflow budget (`S028`) and context-specific timeout/resource facts |
| `profileProperty` | recursive property path/value/block sublanguage, closed by profile schema | schema-only/tooling | N/A migration | improve schema discoverability only; current syntax untouched | profile closure/value typing (`S036`) and recursive paths |
| `uiStatement` | recursive identifier-led UI sublanguage | schema-only/tooling; outside first E3 construction parser | N/A migration | no E2 rewrite; tooling must use profile/schema metadata | UI validity/order (`S047`), action/page context facts |
| `testStatement` | identifier-led leaf/block test sublanguage | schema-only/tooling; outside first E3 construction parser | N/A migration | no E2 rewrite | test/fixture/scenario facts (`S049`,`S050`) |
| Offline Sync compound leaves | push/pull/delete/rejected/conflict sequences encode multiple facts | normalize-candidate | Candidate lifecycle per exact compound form | each segment gets an anchor/fact mapping; partial rewrite forbidden | Sync mode/push/pull/change/conflict facts (`S037`-`S040`); zero silently dropped facts |
| deployment/resource compounds | profile and deployment leaves/blocks encode provider facts | normalize-candidate | Candidate lifecycle per exact schema | schema must identify closed value shape before rewrite | resource/deployment semantics (`S035`,`S042`) |
| workflow/saga/task/schedule family | related declarations intentionally have distinct execution semantics | schema-only/tooling | N/A migration | concept guidance/completion only; no rename | orchestration facts (`S028`-`S031`), semantic order (`S051`) |
| event/topic/queue/channel family | related messaging concepts have distinct declaration roles | schema-only/tooling | N/A migration | concept guidance/completion only; no rename | event/messaging facts (`S024`,`S025`) plus resolution |
| value/view/entity/projection family | related data/read-model concepts have distinct identities/shapes | schema-only/tooling | N/A migration | concept guidance/completion only | declaration identity, target-kind, projection and type facts |
| logical newline/continuation | newline is syntactically significant; semicolons invalid | keep | N/A migration | no alternate newline rule in E2; lossless layer records physical/logical newlines | Kernel newline/recovery authority; source byte identity |
| contextual terminals | broad contextual vocabulary, not globally reserved lexer keywords | keep | N/A migration | no global reservation change | Kernel lexical boundary and Structural visible spelling; existing diagnostics unchanged |
| documented `upcast` drift | documentation example lacks a current normative top-level production | defer | N/A migration in E2; grammar/doc resolution requires separate authority | do not create a migration for unsupported/unresolved syntax | no invented support or Canonical-IR fact; fail closed on unsupported source |
| compiler completion surface | currently conservative/context-backed | schema-only/tooling | N/A migration | clients consume selected-version schema metadata; no source rewrite | reference-position/docs/cardinality metadata; Semantic resolution stays authoritative |

## 9. Fixture and acceptance requirements for a future migrator

Before any candidate may leave `old-only`, the authorized prototype must include, for each affected matrix row:

- valid old-source fixture and expected old Canonical IR;
- valid target-source fixture under an explicit target version;
- byte-lossless untouched-comment/whitespace fixture;
- multiline/logical-newline fixture where applicable;
- negative old/target fixtures proving diagnostics and source locations;
- stale source fingerprint, stale schema fingerprint, overlapping-edit and ambiguous-anchor failures;
- migration idempotence fixture;
- semantic equality assertion for syntax-only rewrites;
- rollback proof retaining the old snapshot/version context.

Cross-row compound fixtures must cover at minimum one declaration header migration, one keywordless entry, one recursive selection/property case, one ordered effect/control-flow neighborhood, one Sync compound fact and one deployment/resource fact. `uiStatement` and `testStatement` remain inventory/tooling cases unless a later dispatch explicitly brings them into an executable parser/migrator scope.

## 10. ADR proposal boundaries after E2

The seven E1 boundaries remain separate:

- **A — construction authority/combinator algebra:** inherited unchanged from E1. Reopen only with separate architecture evidence.
- **B — trusted schema identity/version/fingerprint/dependency/coexistence:** resolved by Sections 3 and 7 for E3 gating.
- **C — lossless source shared-CST vs sidecar/refactoring anchors:** sidecar selected for E3; shared-CST reopen gate in Section 4.
- **D — source-language-version selection/normalized-syntax boundary:** project/compiler selection and single-version compilation resolved in Section 2; exact future source spellings remain unadopted.
- **E — structural diagnostic namespace/mapping/ordering:** `AIDL-S###` and migration-state mapping resolved in Section 5.
- **F — canonical formatting order versus semantic order:** formatter/migrator split and semantic-order protection resolved in Section 6.
- **G — controlled startup/benchmark protocol:** structural startup budget and reproducible measurement protocol resolved in Section 7.

These are E2 design decisions, not production implementations. E3 may test them only in the separately authorized experimental boundary.

## 11. E2 completion boundary

E2 is complete at design level when this contract and the M16.5 backlog are reviewed together. Completion means:

- version selection and mixed-version failure behavior are deterministic;
- trusted schema identity/version/fingerprint/dependency semantics are stable enough for E3;
- a lossless sidecar and fail-closed anchor contract are selected for E3;
- structural diagnostic mapping is fixed without changing existing diagnostics;
- formatter and migrator responsibilities, ordering and idempotence gates are explicit;
- every E1 matrix/hotspot row has a migration/no-migration contract;
- benchmark methodology is reproducible without an invented performance target.

It does **not** mean any candidate normalized spelling is accepted, any production parser understands a schema, any migration/formatter exists, support has advanced, or Variant B has reopened.