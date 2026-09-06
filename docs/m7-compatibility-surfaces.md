# M7-04 Compatibility Surface Matrix

M7-04 extends the M7-03 four-class classifier across the compatibility semantics that Canonical IR `0.3.0` actually carries. It does not change M7-01 fact generation, M7-02 diff construction, CLI exit codes, or the four runtime classes.

## Authority and precedence

`classify_ir_diff(changes, old, new)` still requires `changes` to equal the authoritative `diff_canonical_ir(old, new)` result exactly. The old/new IR states are used only to identify semantic context such as which query/mutation declarations are exposed by an API and which named declarations are reachable from public inputs or outputs.

A single raw fact can affect more than one surface. M7-04 evaluates the applicable rules and chooses the strictest proved class in this order:

`breaking > migration-required > conditional > safe`

Ties use stable rule order. The classifier emits one classification for every raw fact in the same order as M7-01.

## Public API

Rules derived from current `api` IR and the evolution reference include:

- adding an operation to an existing API: `safe`;
- removing or replacing an API operation: `breaking`;
- changing API authentication, transport, error encoding, or an in-place major version: `breaking`;
- changing API rate limits or declared compatibility policy: `conditional`;
- adding/removing API exposure through `app.apiIds` or `system.apiIds`: additive `safe`, removal/replacement `breaking`.

No source syntax is inspected. Only canonical API fields can participate.

## Public client contracts

M7-04 discovers public operation IDs from canonical API `operations`, then follows canonical `named`/`ref` type references from operation inputs and outputs. This lets compatibility rules apply to shared `value`, `entity`, and nested type declarations without duplicating source resolution.

Representative rules:

- required public input field addition/removal/rename: `breaking`;
- public input `required: false -> true`: `breaking`;
- public input `required: true -> false`: `safe`;
- tighter numeric/string input constraints: `breaking`;
- relaxed numeric/string input constraints: `safe`;
- public input/output type changes: `breaking`;
- public output field addition: `safe`;
- public output field removal/rename: `breaking`;
- broader public output nullability: `breaking`;
- narrower public output nullability: `safe`;
- public auth, consistency, or idempotency changes: `breaking`;
- new public declared error: `conditional` because current IR does not prove that every client accepts unknown errors;
- removed/replaced stable public error: `breaking`;
- timeout changes: `conditional`.

The evolution reference says a new optional input field *with a default* is usually compatible. Current operation/value field IR carries `required` but not enough information to prove the default/unknown-field behavior, so an added optional public input field is deliberately `conditional`, not `safe`.

## Events and topics

Current Core IR carries immutable versioned `event` declarations plus `topic` delivery metadata.

- adding a new event declaration/version: `safe` until delivery is added;
- mutating any existing event-version payload field in place: `breaking`;
- adding an event version to an existing topic: `conditional` because accepted consumer versions/overlap are not proved;
- removing or replacing a topic event version: `breaking`;
- changing the topic partition field: `breaking`;
- reducing topic retention: `breaking` because older messages may disappear before consumption/upcast;
- increasing topic retention: `safe`;
- delivery/ordering/compatibility-policy changes: `conditional`.

Consumer and upcaster overlap details not represented by a specific Core IR fact remain conservative rather than guessed.

## Persisted schema

`entity` is the current persisted-schema semantic boundary.

- adding a persisted field: `migration-required` (expand); a required field specifically implies backfill/migration for existing rows;
- removing a persisted field: `breaking` because the change is destructive/data-loss-sensitive;
- changing field requiredness: `migration-required`, unless a stricter public-client rule raises the same fact to `breaking`;
- changing persisted field constraints: `migration-required`;
- changing field type, field name, identity fields, primary/concurrency/generated/delete semantics: `breaking`.

M7-04 classifies the compatibility requirement only. It does not emit expand/backfill/contract steps; migration-step generation remains a later M7 item.

## Cross-surface example

An optional field added to a persisted entity returned by a public API is client-additive, but it still requires a storage expand migration. The single fact therefore becomes `migration-required`, not `safe`.

## Sync/offline applicability boundary

`references/evolution-compatibility.md` also describes min/max client versions, operation upcasts, tombstone watermarks, full-resync requirements, and obsolete-client behavior. Core Canonical IR `0.3.0` does not currently materialize those sync protocol contracts as Core declarations. M7-04 therefore does not invent them from source text, PSI, or profile conventions. Profile-extension or otherwise unmodelled semantic changes remain `conditional` through `unmodelled.review-required` unless a future versioned IR/profile contract provides explicit machine-readable semantics.

## CLI contract

`aidl diff` remains a projection only:

- `result.changes` is the unchanged M7-01 fact list;
- `result.classifications` is the same-order compatibility list;
- human output appends the same classification/rule/reason metadata to the same facts;
- no-diff and non-empty diff remain exit `0`;
- expected compiler/IR/diff input failures remain exit `1`;
- unexpected failures remain exit `70`.

M7-04 adds no migration recommendations, compatibility CI enforcement, or M8 tooling.
