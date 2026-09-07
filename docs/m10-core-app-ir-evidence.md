# M10 Core app Canonical IR evidence

This focused closure records executable evidence for the already implemented Core `app` projection without widening syntax, validation, generation, runtime, or editor support.

`tools/test_core_app_ir_semantics.py` proves that accepted Petstore app semantics are preserved deterministically in Canonical IR: stable app identity, `systemId`, `apiIds`, `defaultDeploymentId`, explicit profile `id`/`major` selections, and the existing global auth metadata (`provider`, `subjectClaim`, `roles`, `scopes`, and `serviceIdentities`). The same generated document is required to satisfy the closed Draft 2020-12 Canonical IR schema.

Negative evidence covers missing required `system`/`defaultDeployment` clauses, unresolved system/API/deployment references at IR construction, and malformed closed-schema app/profile/auth contracts including missing required app fields, unknown properties, malformed declaration IDs, invalid profile majors, and invalid service-identity values.

`decl.app/ir` remains `partial`. The focused evidence exhausts the facts currently emitted by `_app`, but the broader Core app contract is not yet exhaustively closed at validation: the current IR builder can default an omitted explicit profile selection to `core@1`, and app auth projection only materializes auth when the required auth inputs are all present. This block does not establish stable compiler diagnostics for every omitted, duplicate, or partially malformed app/profile/auth clause, so promoting the whole App IR cell would overstate the accepted-source boundary.

M10 acceptance criteria 1 and 3 therefore remain open. Criteria 2 and 4 remain complete. No generator, runtime, IDE, Ruleset, tag, release, or project `.ai/**` state is changed by this evidence block.
