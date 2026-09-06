# M9-04 CLI packaging contract

M9-04 packages the existing compiler-owned AIDL CLI without widening language,
IR, generator, adapter, or release semantics.

## Distribution boundary

`pyproject.toml` is the authoritative build/install contract. It defines:

- distribution name `aidl-toolchain`;
- repository-local packaging baseline `0.0.0`;
- supported interpreter range `>=3.12,<3.13`;
- console script `aidl = tools.aidl_cli:main`;
- exact build requirements `setuptools==80.9.0` and `wheel==0.45.1`;
- exact runtime dependency pins for `jsonschema` and its runtime dependency
  closure used by this artifact;
- Python package `tools`, which contains the compiler and CLI implementation;
- package `spec` with every root-level `spec/*.json` machine contract.

The `0.0.0` distribution version is deliberately not a release claim and does
not reuse Canonical IR `0.3.0`, CLI schema `7.0.0`, or profile-registry
`0.3.0`. Release versioning and publication remain a separate M9 item.

## Runtime data

The installed `tools.ir_diff` implementation resolves
`Path(__file__).resolve().parents[1] / "spec" / "ir.schema.json"`. The wheel
therefore installs `tools` and `spec` as sibling top-level packages and includes
all root JSON contracts in `spec` as package data. This preserves the existing
runtime lookup while removing the checkout requirement.

The package does not claim that repository-only generators, examples, fixtures,
documentation, Gradle assets, or CI configuration are runtime package data.

## Supported Python and dependencies

The artifact currently supports only CPython/Python 3.12 through the explicit
`>=3.12,<3.13` metadata range because that is the interpreter line validated by
the repository CI baseline. Widening that range requires separate executable
evidence.

Runtime dependencies are exact PEP 508 pins in `pyproject.toml`:

- `attrs==26.1.0`
- `jsonschema==4.25.1`
- `jsonschema-specifications==2025.9.1`
- `referencing==0.37.0`
- `rpds-py==2026.6.3`
- `typing-extensions==4.16.0`

These pins make installation of this repository-local artifact resolve one
explicit runtime dependency set. Updating a pin is a package-contract change and
must pass the clean-machine smoke again.

## Build and install

From a clean checkout with supported Python:

```bash
python3 -m pip wheel --no-deps --wheel-dir dist .
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install dist/aidl_toolchain-0.0.0-py3-none-any.whl
aidl --help
```

This is a local artifact workflow only. M9-04 does not publish the wheel, create
checksums or release notes, tag commits, or introduce a release workflow.

## Clean-machine smoke

`tools/package_smoke.py` is the CI proof for the installed boundary. It:

1. builds a wheel through the PEP-517 metadata in `pyproject.toml`;
2. creates a fresh virtual environment with no system site packages;
3. installs the built wheel and its exact runtime dependencies;
4. removes `PYTHONPATH`, enables `PYTHONNOUSERSITE`, and runs from a temporary
   directory outside the repository;
5. verifies installed `aidl --help`;
6. runs `aidl check` successfully on a copied valid fixture;
7. runs `aidl diff` successfully on equal project states, which exercises the
   packaged Canonical IR schema lookup;
8. verifies a malformed source returns the established expected exit code `1`;
9. imports `tools.aidl_cli` and `spec` with the fresh interpreter and rejects
   any import path that points back into the checkout.

The smoke is a required step of the existing `Compiler / Python` Validation job.
Golden Fixtures, Compatibility, Petstore Runtime/PostgreSQL, and IntelliJ remain
separate unchanged gates.

## Focused regressions

`tools/test_packaging.py` checks the console entry point, Python support range,
exact dependency/build pins, package-data declaration, available IR schema, and
repository launcher parity. Because M9-01 discovers every committed
`tools/test_*.py` module, this regression is automatically part of the generic
Python gate.

## Scope boundary

M9-04 ends at a buildable and installable local artifact plus clean-machine CI
proof. The following remain explicitly out of scope and open in `TODO.md`:

- reproducible release publishing, checksums, schema bundles, and release notes;
- branch protection and required-check configuration;
- contribution/security/support/provenance documentation;
- the first published pre-release;
- language, IR, runtime, generator, adapter, or IDE semantic expansion.
