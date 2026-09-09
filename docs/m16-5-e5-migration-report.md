# M16.5 E5 — isolated formatter and migration prototype

Status: **experimental evidence only**. Base: `b273f7e17c0c6d1ad7cdab1aa5ee80c1b3f4197c` (`main`).

This package does not change `docs/06-grammar.md`, the production lexer/parser, AST or Canonical IR, the production formatter, IDE/completion, diagnostics rollout, runtime/generators, compatibility/support/conformance claims, or any accepted source syntax. Every target spelling below remains prototype notation. E5 does not authorize E6–E9.

## Boundary and version authority

`tools/m16_5_e5_migration.py` implements only a bounded dry-run-first migrator and same-version candidate formatter.

The prototype requires explicit immutable contexts:

- old schema: `urn:aidl:schema:language:m16.5-e5-current`, version `m16.5-e5-current-v1`, fingerprint `sha256:3964b3c5cf72fb67a0ef17e0ea2e7d7fb288359250e3b1e130db2c021a69f822`;
- target schema: `urn:aidl:schema:language:m16.5-e5-candidate`, version `m16.5-e5-candidate-v1`, fingerprint `sha256:c702262d2f5374d8eda54a028923d00d7d21e45d3980c62f32d472392ccc8c30`.

There is no `latest`, syntax sniffing, fallback, or implicit version selection. `Formatter(target)` rejects legacy spellings and only canonicalizes target-version prototype anchors. `Migrator(old -> target)` requires the explicit old/target versions, both schema fingerprints, and the exact source fingerprint. A second application is a no-op only when the caller explicitly supplies the target source version and target schema fingerprint.

## Covered normalization rows

`fixtures/m16-5/e5-migration-cases.json` provides one current-syntax source and exact canonical target for every E3 normalization row.

| Row | Current source form | E5 canonical prototype form | Preserved bounded facts |
| --- | --- | --- | --- |
| projection relationship | `projection P from [E] into V` | declaration body slots `source: E`, `target: V` | identity, source set member, target |
| client target | `client C for S` | body slot `service: S` | identity, bound service |
| migration source/target | `migration M from "a" to "b"` | body slots `from`, `to` | identity, modeled data versions |
| consumer relationship | `consumer C on T from E` | body slots `topic`, `source` | identity, topic, accepted source |
| entity field | `name: Type modifiers` | `field name: Type modifiers` | field identity/type/modifier order; surrounding annotations are untouched |
| index | `index name(a asc, b desc)` | `index name: (a asc, b desc)` | identity, ordered fields and directions |
| dead letter | `deadLetter after N attempts` | `deadLetter: N attempts` | enclosing topic/queue kind+identity, threshold |
| schedule lease | `singleton lease D` | `singleton: lease D` | enclosing schedule identity, singleton mode, lease |
| Sync outbox | `changes to T via outbox` | `changes: T via outbox` | enclosing Sync identity, target, outbox delivery fact |

The projection fixture intentionally uses one source because the integrated E3 parser exposes only one `source` identifier. A current multi-source projection fails closed as `AIDL-S004` rather than dropping or coalescing facts. This is a recorded prototype gap, not a language restriction or migration recommendation.

## Dry run, anchors, losslessness, and rollback

`build_sidecar()` records the immutable source bytes/fingerprint, selected schema fingerprint, and stable row/role/range anchors. `plan_migration()` validates that sidecar before constructing edits. Missing or duplicate anchors and overlapping ranges fail as `AIDL-S005`; stale source/schema/version context fails as `AIDL-S008`.

The edit plan is exposed before application and contains exact old/target versions and fingerprints, the source fingerprint, ordered anchored edits, deterministic old/new relocation ranges, old/target semantic fact projections, the bounded compatibility result, and exact original bytes as `rollback_source`.

`apply_plan()` rechecks the source fingerprint and relocation determinism. Bytes outside edited anchors are copied verbatim. Comments/trivia inside an edited anchor are reproduced at the same local tail position by the canonical replacement. Comments, whitespace, annotations, body clauses, and neighboring declarations outside edited anchors are never reformatted by this prototype.

Rollback is exact-byte restoration from `rollback_source`. The fixture suite also exercises explicit target-version coexistence/no-op behavior; it does **not** claim a production coexistence release or emit `AIDL-S006`, because no candidate version has been adopted.

## Semantic-equivalence evidence

Old fixtures are first passed through the existing production `tools.aidl_parser.parse_text` and migration stops if that parser reports diagnostics. The target remains outside production parser acceptance.

For all nine rows, E5 extracts the named E1-preserved semantic facts from old and target snapshots and requires exact equality. Any mismatch fails as `AIDL-S004`; there is no `unknown` or `dataLoss` success state.

E5 additionally reuses `tools.m16_5_e3_prototype.parse_candidate` for the rows whose integrated E3 explicit shape can carry the exact bounded facts without translation loss: projection (single source), client, migration, consumer, and an unmodified-field replay wrapper. E3's current explicit index/dead-letter/schedule/Sync shapes do not encode every E1 fact needed by this E5 rewrite, so E5 does not manufacture an E3 success for those rows. Their fact equality is checked by the E5 bounded projection and the limitation remains explicit.

This is an M7-shaped syntax-only compatibility gate, not a production Canonical-IR comparison. A later adoption decision still requires real old/target compilation and M7 Canonical-IR evidence under separately authorized language versions.

## Ordering and formatting

`format_candidate()` only rebuilds recognized E5 target anchors and never sorts declarations, fields, index entries, clauses, control flow, effects, workflow steps, UI/test statements, or any other sequence. Index field order and explicit `asc`/`desc` direction are preserved. Representative unchanged App and ordered Workflow fixtures remain byte-identical. Absence of explicit semantic-unordered authority therefore means preserve source order, matching E1 `S051` discipline.

The migrator applies `Formatter(target)` only after target construction and requires that the migrator already emitted canonical target text. If formatting would introduce another edit, migration fails closed as `AIDL-S005`.

## Deterministic diagnostics

The bounded prototype uses only E2 structural codes where it introduces a new failure surface:

- `AIDL-S004`: bounded target/value/fact shape cannot preserve required semantics;
- `AIDL-S005`: invalid/missing/ambiguous/overlapping anchor, non-deterministic relocation, or non-canonical migrator output;
- `AIDL-S007`: target formatter sees a legacy spelling;
- `AIDL-S008`: source/version/schema/fingerprint context mismatch or staleness.

Existing production diagnostics are not recoded or reordered.

## Focused validation

The committed test module is intended to run with:

```text
python3 -m compileall -q tools/m16_5_e5_migration.py tools/test_m16_5_e5_migration.py
python3 -m unittest -v tools.test_m16_5_e5_migration
python3 -m unittest -q tools.test_m16_5_e3_prototype
```

`tools/test_m16_5_e5_migration.py` contains 12 focused tests covering all nine rows, exact canonical output, dry-run determinism, explicit idempotence, byte-exact untouched ranges, modifier/comment/annotation preservation, stale source/schema failures, missing/ambiguous/overlapping anchors, formatter/migrator separation, unchanged ordered source, the multi-source fail-closed gap, rollback, and explicit target-version coexistence/no-op behavior.

Repository-wide regression truth is supplied by the normal project PR validation; this document does not pre-claim CI status.

## Known gaps

This is deliberately not a full migration engine. It does not provide full 49-form declaration coverage, recursive property/view migration, sidecar reattachment after arbitrary concurrent edits, incremental parsing, production Canonical-IR comparison, profile-schema migrations, or an adopted source-language version. The current bounded field-context detector is intentionally limited to simple Entity fixtures. Multi-source projection rewrite remains blocked because the E3 target shape is not fact-complete for that case. E3 shape gaps for index directions and dead-letter threshold remain visible rather than normalized away.

These gaps must be resolved or explicitly superseded before any E6/E7 consumer can treat migration metadata as general language authority, and before E8/E9 can make adoption claims.
