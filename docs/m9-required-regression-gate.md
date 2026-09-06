# M9 required compiler regression gate

M9-02 certifies the compiler-owned editor/CLI regression boundary on top of the M9-01 committed-test discovery.

## Machine-readable inventory

`.github/compiler-required-regressions.json` is the version-1 certification inventory. It names the required `Compiler / Python` workflow job, the M9-01 selection policy, the production CLI source, and the four compiler-owned capability suites that must remain paired end to end:

- resolution: `tools.compiler_resolution`, its compiler regression, `aidl resolve`, and its CLI regression;
- completion: `tools.compiler_completion`, its compiler regression, `aidl complete`, and its CLI regression;
- documentation: `tools.compiler_documentation`, its compiler regression, `aidl document`, and its CLI regression;
- refactoring: `tools.compiler_refactoring`, its compiler regression, `aidl usages`/`aidl rename`, and their CLI regression.

The same inventory explicitly lists every current generic Python regression that exercises `tools.aidl_cli`, including the shared CLI envelope/schema/exit tests and the M8 compiler-tooling CLI regressions.

## Certification

The `Compiler / Python` job runs this before executing the M9-01 selected test set:

```bash
python3 -m tools.ci_required_regressions validate
python3 -m tools.ci_test_selection run
```

`tools/ci_required_regressions.py` reuses the M9-01 tracked-file selection and then fails certification when any required regression is missing, not discovered, explicitly excluded, or otherwise absent from the generic Compiler / Python selection.

The certification does not trust filenames alone. It parses selected Python tests with the standard-library AST and checks two drift boundaries:

1. every selected regression that imports one of the four critical compiler modules must be represented by the compiler-suite inventory;
2. every selected regression that imports or invokes `tools.aidl_cli` must be present in `cliRegressionModules`, and every inventoried CLI regression must still exercise that module.

It also parses `tools/aidl_cli.py` to verify that every paired CLI command is still registered and checks the workflow job block so the certification command and M9-01 execution command remain in the same `Compiler / Python` gate.

## Determinism and exits

Inventory suites, test arrays, command arrays, and CLI regression modules are unique and lexically ordered. The four suite areas are fixed in `completion`, `documentation`, `refactoring`, `resolution` order for version 1.

`python3 -m tools.ci_required_regressions validate` exits:

- `0` when the inventory, compiler/CLI pairs, M9-01 selection, and workflow ownership are certified;
- `2` for inventory, selection, pairing, drift, missing-path, exclusion, Python-evidence, command-registration, or workflow-assignment errors.

Normal test failures still come from the following `tools.ci_test_selection run` step and keep the established `unittest` exit behavior.

`tools/test_ci_required_regressions.py` covers missing paths, required-test exclusions, compiler and CLI drift, deterministic inventory order, missing pair coverage, successful certification, and the stable configuration-error exit.

## Scope boundary

M9-02 changes no language semantics and no branch protection. Specialized `Compatibility / Pull Request`, `Golden Fixtures`, `Petstore Runtime / PostgreSQL`, and `IntelliJ Plugin` jobs keep their existing ownership and commands. Branch protection remains a later M9 roadmap item.
