# M16.5 E2 Recovery Addendum — validation-gap closure

Status: **non-normative E2 contract addendum**. This file closes only the three validation gaps recorded by the read-only E2 validation dispatch. It does not change `docs/06-grammar.md`, accepted source syntax or semantics, parser/lexer/AST/Canonical-IR behavior, formatter/migrator implementation, IDE/LSP, generators/runtime, support/conformance, or Variant-B status. E3 and later work remain unauthorized.

This addendum is read together with `docs/m16-5-e2-compatibility-migration-contract.md` and the E1 exception inventory in `docs/m16-5-e1-fact-inventory.md`.

## 1. Bounded E2 migration-fixture scope

Recovery does not broaden the accepted language surface. The fixture-backed migration scope contains **exactly four positive candidate migrations**:

| ID | E1 candidate | E2 status |
| --- | --- | --- |
| `MIG-01` | projection relationship header | candidate-only; no production spelling adopted |
| `MIG-02` | client relationship header | candidate-only; no production spelling adopted |
| `MIG-03` | modeled migration `from`/`to` header | candidate-only; source-language version remains a separate fact |
| `MIG-04` | consumer relationship header | candidate-only; no generic relationship-header rewrite |

The labels `e2-old` and `e2-target` in the CSV are fixture-only version labels. They are not product language-version names, accepted source markers, CLI flags, or manifest syntax.

Every other E1 `normalize-candidate` remains a design candidate under the existing E2 lifecycle but is **not** an executable candidate migration in this recovery fixture set. `keep`, `schema-only/tooling`, `normalize-candidate`, and `defer` retain their E1 classifications.

Fixture registry: `fixtures/m16-5/e2-migration-contract.csv`.

## 2. Construction-exception traceability: EXC-01 through EXC-14

Every E1 construction-exception family has a deterministic negative fixture and an explicit E2 disposition. A generic failure without the exception identity is insufficient.

For all negative rows, `AIDL-R006` means “rewrite not authorized for this construction-exception family”. The diagnostic payload must include the exact `construction_exception_id` from the fixture row; therefore `AIDL-R006` alone is not a complete fixture result.

| Exception | Deterministic E2 disposition |
| --- | --- |
| `EXC-01` anonymous auth/a11y/privacy identity | reject generic rewrite; construction remains schema/envelope-owned |
| `EXC-02` compound native starters | reject generic rewrite; no starter-word normalization |
| `EXC-03` tenant `model` identity | reject generic rewrite |
| `EXC-04` string-labelled test + target | reject generic rewrite |
| `EXC-05` alias/opaque assignment envelope | reject generic rewrite |
| `EXC-06` enum delimited entries | reject generic rewrite |
| `EXC-07` callable parameter/result envelopes | reject generic rewrite |
| `EXC-08` event/relationship-qualified headers | reject any unenumerated generic header rewrite; only `MIG-01`..`MIG-04` are positive E2 candidates |
| `EXC-09` keywordless fields/union/view members | reject generic rewrite in this recovery fixture set |
| `EXC-10` ordered transaction/workflow/saga/action statements | reject rewrite; semantic order is preserved |
| `EXC-11` nested `when` control flow | reject rewrite |
| `EXC-12` recursive view selection | reject rewrite |
| `EXC-13` hierarchical `profileProperty` | reject rewrite |
| `EXC-14` generic UI/test free-item sublanguages | reject rewrite; tooling/schema-only boundary remains |

A later separately authorized package may add evidence for a specific candidate, but it may not reinterpret these negative fixtures as successful generic migrations.

## 3. Diagnostic separation

### 3.1 Structural/version diagnostics

The existing `AIDL-S###` structural family remains construction/version-context owned. The E2 mapping is extended without recoding existing diagnostics:

| Code | Condition |
| --- | --- |
| `AIDL-S006` | deprecated-but-valid legacy spelling in an explicitly selected coexistence version |
| `AIDL-S007` | known mechanically migratable legacy spelling invalid in the selected target version |
| `AIDL-S008` | source-language/schema-context mismatch for one source/schema association |
| `AIDL-S009` | mixed-version import/source graph detected during normal compilation; fail before semantic resolution |
| `AIDL-S010` | candidate spelling is unavailable in the explicitly selected source-language version |

`AIDL-S009` is the mixed-version graph failure and is not a rewriter failure. `AIDL-S006` is coexistence/deprecation and is not a rewriter failure.

### 3.2 Dedicated REWRITER namespace

`AIDL-R###` is reserved for deterministic migration/rewriter failures. These codes are emitted only by an explicitly invoked migration operation; they are never substitutes for structural or semantic diagnostics.

| Code | Rewriter condition |
| --- | --- |
| `AIDL-R001` | stale source fingerprint |
| `AIDL-R002` | stale language/profile schema fingerprint |
| `AIDL-R003` | required rewrite anchor missing |
| `AIDL-R004` | rewrite anchor resolves ambiguously |
| `AIDL-R005` | planned edits overlap without one explicit owning edit |
| `AIDL-R006` | no authorized rewrite rule for the identified construction-exception family; diagnostic data must include `EXC-##` |
| `AIDL-R007` | rewritten target snapshot fails target-version validation; underlying structural/semantic diagnostics remain visible |
| `AIDL-R008` | Canonical-IR/Semantic-Diff or E1 fact-preservation gate fails |
| `AIDL-R009` | second migration pass is not idempotent |
| `AIDL-R010` | promised rollback context/original immutable snapshot is unavailable |

Ordering is deterministic: preserve existing source diagnostics first under their existing ordering contract; rewriter diagnostics are ordered by planned edit/source anchor, then `AIDL-R###` code. No `AIDL-R###` code suppresses an existing structural or semantic diagnostic.

## 4. Fixture-backed contract validation

The CSV is contract evidence, not a production parser or migrator test corpus. It must satisfy all of these deterministic checks:

1. exactly four `positive` rows, `MIG-01` through `MIG-04`;
2. exactly fourteen `negative` rows, one each for `EXC-01` through `EXC-14`;
3. every negative row has a non-empty disposition and `expected_diagnostic=AIDL-R006`;
4. every positive row requires `canonical-ir-equal-zero-fact-loss`;
5. no row claims accepted production syntax, support, conformance, or a production language-version name.

For a future authorized migrator, the positive rows expand into the existing E2 evidence requirements: explicit old/target selection, deterministic rewrite, target validation, idempotence, rollback where promised, Canonical-IR/Semantic-Diff equality, zero E1 fact loss, diagnostic stability, and byte/trivia preservation outside edited anchors.

## 5. Conjunctive E3 entry gate

**E3 remains closed.** Entry is permitted only when **all** conditions below are simultaneously satisfied on one pinned project/fixture state:

- **No legacy fallback path:** the isolated E3 harness has no recoverable legacy fallback parse path for the candidate-version fixtures; legacy remnants outside the explicitly selected version are rejected rather than silently recovered. This requirement does not authorize a production parser change.
- **Version choice/marker finalized:** E3 uses the already chosen out-of-source project/compiler authority. Its fixture/harness marker is the explicit metadata field `source_language_version`; no AIDL source directive, app field, or implicit syntax sniffing is introduced.
- **No recoverable legacy remnants:** validation of the complete E3-entry fixture set proves there is no path that accepts a legacy remnant through fallback, heuristic guessing, or unversioned recovery.
- **E2 fixture contract green:** the checks in Section 4 pass, all `EXC-01`..`EXC-14` negative cases retain deterministic traceability/disposition, and every applicable structural/rewriter diagnostic is stable.
- **E1/E2 authority intact:** 211 productions, 522 alternatives, 57 Kernel, 154 Structural-Schema, 56 Semantic facts, 14 construction-exception families, A-prime prototype-only status, and the Variant-B reopen rule remain unchanged unless separately re-authorized.

The gate is conjunctive: satisfying any strict subset is insufficient. This recovery dispatch does not execute E3 and does not claim the gate is currently satisfied.

## 6. Recovery acceptance accounting

The three blocked validation gaps are closed at contract level when:

1. the CSV validates the exact 4-positive/14-negative cardinalities and EXC traceability;
2. `AIDL-R###` is distinct from `AIDL-S006` coexistence and `AIDL-S009` mixed-version diagnostics;
3. Section 5 is present and E3 remains closed unless every conjunct is proven.

No other E2 boundary changes.
