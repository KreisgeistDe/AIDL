# M10-05 Core fixture conformance

M10-05 records fixture coverage only for rows that are already **Core Supported** by the normative implementation contract. It does not promote partial declarations, semantic rules, profiles, syntax, runtime behavior, or generators.

`spec/core-fixture-conformance.json` is the machine-readable coverage index. Its supported feature IDs are not hand-defined policy: `tools/conformance_manifest.py` derives the expected set from `spec/core-conformance.json` by requiring each Parse, Resolve, Validate, and IR layer to be either `implemented` or semantically `not-applicable`, with at least one implemented layer. Any partial or missing required layer therefore excludes the row from M10-05 coverage.

The coverage contract requires four evidence classes for every derived Core Supported row:

- **positive** — accepted source fixture plus executable Golden Fixture coverage;
- **negative** — executable compiler/diagnostic regressions proving stable rejection behavior;
- **ir** — a committed Canonical-IR snapshot plus executable semantic-projection coverage;
- **compatibility** — the committed IR compatibility matrix plus its executable matrix test.

Evidence is catalogued once and referenced through `defaultEvidence`; the stable feature list is checked against the derived supported set. This avoids maintaining a second semantic support policy while still making missing, stale, reordered, or incorrectly promoted fixture evidence fail deterministically.

`tools/test_core_fixture_conformance.py` protects the coverage boundary with negative regressions for missing supported rows, accidental claims for partial rows, unknown evidence IDs, and missing IR/compatibility machine fixtures. The normal generic Python test discovery executes this test, while the existing repository spec-lint path invokes `python3 -m tools.conformance_manifest validate`, so both direct test execution and CI reject drift.

The Enum Validate/IR closure promotes `decl.enum` into the derived Core Supported set. `tools/test_core_enum_ir_semantics.py` supplies focused positive, negative, deterministic identity/case-order, and full `ir.schema.json` proof for the closed Enum contract, while `tools/test_aidl_parser.py` proves assigned and malformed source state is retained instead of silently discarded. Assigned string values remain unsupported and are rejected with `AIDL-T005`; no wire-value semantics, Enum Generate support, or IDE support is inferred from this fixture promotion.

The Event Validate/IR closure promotes `decl.event` into the derived Core Supported set. The existing M4 minimal source and committed IR snapshot provide positive and snapshot evidence; `tools/test_core_event_ir_semantics.py` now supplies focused positive, negative, deterministic identity/schema, and full `ir.schema.json` proof for the closed Event contract. It rejects missing, non-positive or malformed versions, `evolves`, and non-losslessly-projectable body facts before Canonical IR. No Event Generate, evolution, or IDE support is inferred from this fixture promotion.

The Topic Validate/IR closure promotes `decl.topic` into the derived Core Supported set. The existing M4 minimal source and committed IR snapshot provide positive and snapshot evidence; `tools/test_core_topic_materialization_contract.py` supplies the focused positive, negative, and semantic IR proof for the complete closed Topic contract; and the existing IR compatibility matrix/test remains the compatibility authority. No Topic Generate or IDE support is inferred from this fixture promotion.

The existing fixture and compatibility harnesses remain authoritative for behavior. M10-05 only binds their evidence to the current Core Supported rows; it does not reinterpret those tests or add new language semantics.
