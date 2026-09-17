# M10.5-04 authorized diagnostic fix-planning parity slice

This bounded Gate-04 package ports only the existing Python `authorized_snapshot_fixes` / `SnapshotAuthorizedFix` observable contract into Kotlin common compiler core. It is a non-applying semantic query: callers receive edit plans and the planner never mutates source text.

The admitted mapping is intentionally narrow. Only compiler diagnostics that explicitly carry an `insertClause` allowed fix are projected. The plan preserves the fix text as title, diagnostic code, exact source identity, insertion offset, zero edit length, indentation-derived replacement text, optional diagnostic-code filtering, diagnostic/fix order, and fail-closed behavior for missing snapshot text or unusable anchors. Unknown fix kinds are omitted rather than interpreted.

`AuthorizedFixPlanningDifferentialParityTest` consumes `parity/authorized-fix-planning.signature`; `tools/test_m10_5_kotlin_authorized_fix_planning.py` independently regenerates that signature through the real Python `CompilerSnapshot` diagnostic path, including the real `AIDL-DIST411` missing-idempotency authorized fix plus saved/unsaved snapshot coverage. Focused synthetic boundary cases pin unsupported fix kinds, missing source text, invalid insertion anchors, multiple fixes, filtering, determinism, and root isolation without adding language meaning.

This slice does not apply edits, broaden code actions, alter diagnostic generation, change Core language/schema semantics, close Gate 04, authorize M10.5-05+, or change Python's reference/conformance role.
