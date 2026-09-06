# AIDL Golden Fixture Corpus

`fixtures/` is the durable repository-wide corpus used by M5 Golden Fixtures and CI.

## Structure

- `manifest.json` is the single corpus index. Every case has a stable `id`, a `suite` (`valid` or `invalid`), a project-relative `path`, and an `expectedDiagnostics` list.
- `valid/<case>/` contains a standalone AIDL project that must be accepted with no compiler diagnostics.
- `invalid/<case>/` contains a standalone AIDL project whose diagnostics must exactly match the stable code/file/line/column anchors declared in the manifest.
- Each case is loaded independently. Module names therefore only need to be unique inside that project.

`tools/test_m5_fixture_corpus.py` is the focused harness. It exercises only the existing compiler/diagnostics boundary through `compiler_diagnostics.load_compiler_analysis`: once by project directory and once with the same `.aidl` sources supplied in reverse lexical order. Both runs must produce the same deterministic diagnostics JSON and the exact manifest anchors.

The existing `tools/m2_semantic_fixtures/` corpus remains the task-specific M2 regression suite. M5 fixtures may reuse already-supported semantics, but do not replace or rename that corpus.

M5-01 intentionally does not snapshot full diagnostic payloads, canonical IR, plans, or generated output. Those are M5-02 and later concerns; Petstore golden expansion, Calendar/VideoHub coverage, dedicated CI jobs, and IntelliJ work also remain later roadmap tasks.
