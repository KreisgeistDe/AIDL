# M7 Compatibility Classification

M7-03 established the compatibility-owned classification layer on top of semantic IR facts produced by M7-01 and exposed by M7-02. M7-04 expands that same layer across the API, event, persisted-schema, and public-client semantics that Canonical IR `0.3.0` actually carries. Neither slice changes fact generation, Canonical IR normalization, or CLI exit-code semantics.

## Boundary

`tools/ir_compatibility.py` accepts:

- the authoritative `IrDiffChange` sequence from `diff_canonical_ir()`;
- the validated old Canonical IR state; and
- the validated new Canonical IR state.

The classifier reuses the existing M7-01 diff boundary to verify that the supplied facts exactly belong to those two IR states. It never reparses AIDL source, never creates another diff algorithm, and never changes `IrDiffChange` values or ordering.

`aidl diff` keeps `result.changes` as the unchanged M7-01 JSON facts and adds a parallel, same-order `result.classifications` list. Human output renders the same raw facts with classification metadata appended.

## Runtime taxonomy

There are exactly four runtime classes:

- `safe` — an explicit rule proves that the change preserves every existing contract relevant to the carried semantic surface.
- `conditional` — compatibility depends on deployment, consumer, client, or domain context, or current Canonical IR does not carry enough evidence to prove a stronger result.
- `migration-required` — persisted state/schema must change before the new contract can be used safely.
- `breaking` — an existing contract is removed, narrowed, destructively changed, or replaced incompatibly.

Older/reference wording maps into these four classes rather than adding another runtime value: `compatible`/`non-breaking` maps to `safe` when proved; `context-dependent`/`review-required` maps to `conditional`; `expandable`/`requires migration` maps to `migration-required`; and `incompatible` maps to `breaking`.

## Conservative base rules

The M7-03 base remains valid:

1. Adding a standalone `alias`, `enum`, `opaque`, `value`, or `view` declaration is `safe`.
2. Removing a top-level declaration is `breaking`.
3. Adding a required persisted entity field is `migration-required`.
4. Tightening an existing persisted entity field from `required=false` to `required=true` is `migration-required` unless a stricter public-client rule makes the same fact `breaking`.
5. Changing an operation `timeoutMs` is `conditional`.
6. Every path not covered by an explicit rule is `conditional`, never `safe`.

Each classification includes a stable rule identifier and deterministic explanation text.

## M7-04 surface coverage

M7-04 adds evidence-based rules for:

- public API operation/exposure changes, auth, transport, error encoding, rate limits and compatibility policy;
- public operation input/output evolution through canonical type-reference reachability, including field requiredness, constraints, types, output nullability, auth/consistency/idempotency and errors;
- immutable event versions and topic version/partition/retention/delivery evolution;
- persisted entity expansion, requiredness/constraints, destructive field/type/identity/storage changes; and
- deterministic cross-surface precedence where one raw fact affects multiple contracts.

When several rules apply, the strictest proved class wins deterministically:

`breaking > migration-required > conditional > safe`.

The detailed matrix and applicability limits are documented in [`m7-compatibility-surfaces.md`](m7-compatibility-surfaces.md).

## Evidence boundary

`references/evolution-compatibility.md` also describes sync/client-version semantics such as min/max client versions, old-operation upcasts, tombstone watermarks, full-resync requirements, and obsolete-client behavior. Core Canonical IR `0.3.0` does not materialize those contracts. M7 does not infer them from source text, PSI, or informal profile conventions. Such unmodelled profile/sync facts remain `conditional` until a versioned IR/profile contract carries explicit machine-readable semantics.

This conservative fallback is important: lack of a rule is evidence for review, not evidence of safety.

## CLI and exit codes

`aidl diff --format json` returns the existing deterministic command envelope. On success:

```json
{
  "result": {
    "changes": ["unchanged M7-01 facts"],
    "classifications": ["parallel compatibility classifications"]
  }
}
```

No-diff and non-empty semantic diffs remain exit `0`. Existing compiler/IR/diff input failures remain exit `1`; unexpected internal failures remain exit `70`. Classification introduces neither another result class nor a new exit-code meaning.

Migration-step generation, compatibility CI/pull-request enforcement, and M8 tooling remain later work.
