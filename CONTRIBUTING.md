# Contributing to AIDL

AIDL is a pre-1.0 language specification and reference implementation. Contributions should preserve the distinction between specified language surface and behavior that is implemented and covered by executable evidence.

## Start from repository truth

Before changing code or documentation, read `AGENTS.md`, `TODO.md`, `README.md`, and the files relevant to the area you are changing. Current source, tests, machine-readable contracts, and accepted project documentation are authoritative. Operational agent state under `.ai/**` is not project source and must not be changed in a project pull request.

## Change scope

Keep a pull request coherent and reviewable. Couple implementation, tests, machine-readable contracts, and durable documentation when they describe one capability. Do not widen language semantics, support claims, packaging, release behavior, or version contracts implicitly.

For generated files, fix the generator or semantic source rather than manually repairing generated output. For compiler or IDE behavior, the compiler-owned semantic model remains authoritative; IntelliJ PSI must not become a second semantic source of truth.

## Development baseline

The repository CI baseline currently uses:

- Python 3.12 for the compiler, CLI, packaging, compatibility, fixtures, and release tooling;
- Node.js 22 and npm 10 for the supported generated TypeScript/Petstore path;
- PostgreSQL 17 for the Petstore runtime smoke and E2E path;
- Java 17 for the IntelliJ plugin checks.

The installable CLI package itself declares `>=3.12,<3.13` in `pyproject.toml` and exact runtime/build dependency pins. Do not broaden that support range without executable evidence.

## Local validation

Install the validation dependencies before running the Python checks:

```bash
python3 -m pip install -r requirements-validation.txt
```

For a general compiler/CLI/documentation change, run the repository-owned selectors and lint:

```bash
python3 -m tools.ci_required_regressions validate
python3 -m tools.ci_test_selection run
python3 tools/spec_lint.py .
```

Packaging or installed-CLI changes must additionally pass:

```bash
python3 tools/package_smoke.py
```

Release-contract or release-documentation changes must preserve the M9-05 contract and should run:

```bash
python3 -m tools.release_bundle verify-contract
python3 -m tools.release_bundle reproduce --output release-dist
```

Changes to the supported Petstore runtime path should run its focused Python tests and the Node/PostgreSQL path described by `.github/workflows/python-validation.yml`. IntelliJ changes should run, from `plugins/intellij/`:

```bash
./gradlew --no-daemon check
./gradlew --no-daemon buildPlugin
```

GitHub Actions remains the cross-environment validation source for `Compiler / Python`, `Compatibility / Pull Request`, `Golden Fixtures`, `Petstore Runtime / PostgreSQL`, `IntelliJ Plugin`, and the `.ai/**` project-boundary check. Native branch protection for `main` is still a separate open M9 item; documentation must not claim that those checks are already enforced as branch rules.

## Pull requests

Open a normal feature branch and pull request against `main`. In the pull request, explain the intended post-merge state, list relevant validation, and call out any intentionally unsupported surface. Project pull requests must not add, modify, rename, or delete `.ai/**`.

A change is not complete merely because documentation describes it. New support or stability claims require matching implementation and executable tests/CI.

## Security-sensitive contributions

Do not disclose vulnerability details in a normal issue or pull request. Follow `SECURITY.md` for the repository's reporting route and disclosure expectations.

## Support and artifact claims

Before changing public support language, read `SUPPORT.md` and `docs/12-coverage-and-limits.md`. Before changing packaging or release claims, read `docs/m9-cli-packaging.md`, `docs/m9-release-workflow.md`, and `docs/artifact-provenance.md`.
