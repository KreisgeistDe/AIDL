# M7-05 — Migration guidance

M7-05 derives deterministic rollout guidance from already-authoritative M7 evidence. It does not classify compatibility, regenerate diff facts, execute migrations, or invent implementation details that are not represented in Canonical IR.

## Ownership boundary

`tools/ir_migration_guidance.py` consumes exactly four inputs:

1. the M7-01 `IrDiffChange` sequence,
2. the M7-03/04 `IrCompatibilityClassification` sequence,
3. the old Canonical IR document, and
4. the new Canonical IR document.

Before producing guidance, it revalidates that the supplied facts exactly equal `diff_canonical_ir(old,new)` and that the supplied classifications exactly equal `classify_ir_diff(...)`. Any mismatch fails instead of producing advisory output from stale or fabricated evidence.

M7-01 remains the semantic-diff authority. M7-03/04 remain the compatibility-policy authority. M7-05 only sequences rollout guidance from those existing decisions.

## Phase vocabulary and ordering

When evidence supports a staged rollout, phases use only this ordered vocabulary:

1. `expand`
2. `deployReaders`
3. `backfill`
4. `switchWrites`
5. `verify`
6. `contract`

Not every change uses every phase. M7-05 never inserts a phase merely to fill the sequence.

## Four-class behavior

### `safe`

Safe changes emit no migration phases and no preconditions. The classifier has already proved that the represented change does not require a compatibility migration sequence.

### `conditional`

Conditional changes emit no automated migration phases. They emit a deterministic coordination/review precondition containing the authoritative classification rule and reason. This keeps missing deployment/client/profile evidence explicit instead of pretending it is a migration plan.

### `migration-required`

M7-05 emits concrete phases only for migration rules whose sequencing is supported by the existing Canonical-IR evidence.

Current evidence-backed mappings include:

- `entity.required-field-added` and `entity.field-required-tightened`: `expand → deployReaders → backfill → switchWrites → verify → contract`.
- `entity.field-added`: `expand → deployReaders → switchWrites → verify`; no backfill is invented for an optional additive field.
- `entity.constraint-changed`: `expand → verify → contract`, with an explicit precondition that any required data remediation must be designed separately.
- `entity.field-required-relaxed`: `expand → deployReaders → switchWrites → verify`.

For a future `migration-required` rule with no M7-05 sequencing evidence, guidance remains explicit but phase-empty and requires an external migration plan instead of guessing.

### `breaking`

Breaking changes never receive an apparently safe expand/backfill/contract automation sequence. Guidance is phase-empty and deterministically requires:

- explicit compatibility review/approval,
- a tested rollback/recovery procedure, and
- a verified backup or equivalent recovery point when persisted state can be affected.

This applies even when the breaking surface is API/client/event rather than storage: M7-05 does not infer a safe automatic migration from a breaking classification.

## No invented implementation details

Guidance actions describe rollout intent only. M7-05 does **not** generate or infer:

- SQL DDL/DML,
- concrete backfill values or transforms,
- event upcasters,
- client upgrade code,
- traffic-switch configuration,
- deployment commands,
- backup commands, or
- recovery procedures.

For required-field backfills, Canonical IR proves that existing data must satisfy the new required contract, but it does not encode where a value comes from or how to compute it. Guidance therefore names the `backfill` phase and makes the missing value/derivation an explicit precondition.

## `aidl diff` projection

`aidl diff` remains a projection layer. Successful JSON output contains three parallel same-order lists:

```json
{
  "changes": [],
  "classifications": [],
  "guidance": []
}
```

`result.changes` remains byte-for-structure equivalent to `semantic_ir_diff_to_json(changes)`. `result.classifications` remains the existing M7-03/04 projection. `result.guidance` is produced only after both authoritative boundaries succeed.

Human output appends a deterministic compact JSON `guidance=...` field to the same raw fact/classification line.

Exit semantics are unchanged:

- `0` for no-diff and non-empty semantic diff success,
- `1` for expected compiler/IR/diff input failures, and
- `70` for unexpected internal failures, including invariant violations inside guidance construction.

## Scope exclusions

M7-05 does not add new compatibility rules, a fifth compatibility class, CI/pull-request compatibility enforcement, executable migrations, migration application, or M8 agent tooling. Compatibility CI enforcement remains the next M7 roadmap item.
