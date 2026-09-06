# M9 Python CI test selection

M9-01 makes Python test selection complete by default and explicit only where a specialized CI owner is intentional.

## Contract

`.github/python-test-selection.json` is the versioned repository policy. Version 1 declares:

- repository roots that contain Python tests;
- the committed test-module filename pattern;
- the small set of tests intentionally excluded from the generic `Compiler / Python` job;
- for every exclusion, the independently visible CI job, exact command, and durable reason that owns it.

`tools/ci_test_selection.py` enumerates committed files with `git ls-files`, discovers matching Python test modules, validates the policy, sorts paths deterministically, and selects every discovered test except a valid explicit exclusion. A newly committed matching test therefore runs automatically without adding its filename to workflow YAML or to the policy.

An exclusion is valid only when its path is itself a committed discovered test module and its entry has the exact version-1 fields `path`, `ciJob`, `command`, and `reason`. Exclusion paths must be unique and sorted, and each command must name its excluded test path. Stale, malformed, duplicated, unsorted, or unsupported-version policy data fails before tests run.

## CI ownership

The generic `Compiler / Python` job runs:

```bash
python3 -m tools.ci_test_selection run
```

The specialized jobs remain separate and retain their existing responsibilities:

- `Golden Fixtures` owns `tools/test_ir_compatibility.py` and `tools/test_m5_fixture_corpus.py`;
- `Petstore Runtime / PostgreSQL` owns `tools/test_m4_petstore.py` together with generation, Node, PostgreSQL smoke, and HTTP E2E validation;
- `Compatibility / Pull Request` continues to evaluate the repository compatibility policy against the actual PR base/head;
- `IntelliJ Plugin` continues to run the Gradle checks and plugin build.

The specialized Python modules stay in discovery: they are excluded from only the generic job, not hidden from the selection contract.

## Determinism and exits

`python3 -m tools.ci_test_selection list` prints the generic selected test paths in lexical repository order. `validate` prints discovered/selected/excluded counts without running tests. `run` executes the same ordered selection through `python -m unittest`.

Exit behavior is stable:

- `0`: selection is valid, and for `run` all selected tests pass;
- `1`: propagated normal `unittest` failure;
- `2`: test-selection policy, committed-file discovery, or selection validation failed.

`tools/test_ci_test_selection.py` protects default execution for unregistered new tests, explicit exclusions, stale exclusion rejection, version/rationale validation, deterministic ordering, and exit propagation.

## Scope boundary

M9-01 removes filename-list drift and establishes the invariant that every committed matching Python test module is either executed by CI or has an explicit versioned specialized-job rationale. It does not itself redefine compiler semantics, compatibility policy, fixture semantics, runtime coverage, or IntelliJ behavior.

The separate M9 roadmap item about certifying every compiler-owned resolution, completion, documentation, refactoring, and CLI regression as a required gate remains a distinct inventory/coverage claim even though deterministic discovery causes currently committed generic tests in those areas to run automatically.
