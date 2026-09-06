from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

from tools.ci_test_selection import SelectionError, repository_selection, tracked_files


DEFAULT_INVENTORY = ".github/compiler-required-regressions.json"
SUPPORTED_INVENTORY_VERSION = 1
CONFIG_ERROR_EXIT = 2
EXPECTED_AREAS = ("completion", "documentation", "refactoring", "resolution")
EXPECTED_GATE = "Compiler / Python"


class CertificationError(ValueError):
    pass


@dataclass(frozen=True)
class CompilerSuite:
    area: str
    module: str
    source: str
    compiler_tests: tuple[str, ...]
    cli_commands: tuple[str, ...]
    cli_tests: tuple[str, ...]


@dataclass(frozen=True)
class RegressionInventory:
    version: int
    gate: str
    workflow: str
    workflow_job: str
    selection_policy: str
    cli_source: str
    compiler_suites: tuple[CompilerSuite, ...]
    cli_regression_modules: tuple[str, ...]


@dataclass(frozen=True)
class Certification:
    compiler_regressions: int
    cli_regressions: int
    suites: int


def _require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificationError(f"{field} must be a non-empty string")
    return value


def _repo_path(value: object, field: str) -> str:
    text = _require_string(value, field)
    path = PurePosixPath(text)
    if path.is_absolute() or text != path.as_posix() or "." in path.parts or ".." in path.parts:
        raise CertificationError(f"{field} must be a normalized repository-relative POSIX path: {text!r}")
    return text


def _sorted_strings(value: object, field: str, *, nonempty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = "non-empty " if nonempty else ""
        raise CertificationError(f"{field} must be a {suffix}array")
    items = tuple(_require_string(item, f"{field}[]") for item in value)
    if list(items) != sorted(set(items)):
        raise CertificationError(f"{field} must be unique and sorted")
    return items


def _sorted_paths(value: object, field: str, *, nonempty: bool = True) -> tuple[str, ...]:
    items = _sorted_strings(value, field, nonempty=nonempty)
    return tuple(_repo_path(item, f"{field}[]") for item in items)


def load_inventory(path: Path) -> RegressionInventory:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CertificationError(f"cannot read required-regression inventory {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise CertificationError("required-regression inventory must be a JSON object")
    expected = {
        "version",
        "gate",
        "workflow",
        "workflowJob",
        "selectionPolicy",
        "cliSource",
        "compilerSuites",
        "cliRegressionModules",
    }
    if set(raw) != expected:
        raise CertificationError(f"inventory must contain exactly {sorted(expected)}")
    if raw["version"] != SUPPORTED_INVENTORY_VERSION:
        raise CertificationError(
            f"unsupported required-regression inventory version {raw['version']!r}; "
            f"expected {SUPPORTED_INVENTORY_VERSION}"
        )
    gate = _require_string(raw["gate"], "gate")
    if gate != EXPECTED_GATE:
        raise CertificationError(f"gate must remain {EXPECTED_GATE!r}")

    suites_raw = raw["compilerSuites"]
    if not isinstance(suites_raw, list) or not suites_raw:
        raise CertificationError("compilerSuites must be a non-empty array")
    suites: list[CompilerSuite] = []
    for index, item in enumerate(suites_raw):
        if not isinstance(item, dict):
            raise CertificationError(f"compilerSuites[{index}] must be an object")
        suite_fields = {"area", "module", "source", "compilerTests", "cliCommands", "cliTests"}
        if set(item) != suite_fields:
            raise CertificationError(
                f"compilerSuites[{index}] must contain exactly {sorted(suite_fields)}"
            )
        area = _require_string(item["area"], f"compilerSuites[{index}].area")
        module = _require_string(item["module"], f"compilerSuites[{index}].module")
        suites.append(
            CompilerSuite(
                area=area,
                module=module,
                source=_repo_path(item["source"], f"compilerSuites[{index}].source"),
                compiler_tests=_sorted_paths(item["compilerTests"], f"compilerSuites[{index}].compilerTests"),
                cli_commands=_sorted_strings(item["cliCommands"], f"compilerSuites[{index}].cliCommands"),
                cli_tests=_sorted_paths(item["cliTests"], f"compilerSuites[{index}].cliTests"),
            )
        )
    areas = tuple(suite.area for suite in suites)
    if areas != EXPECTED_AREAS:
        raise CertificationError(
            f"compilerSuites areas must be exactly {list(EXPECTED_AREAS)} in deterministic order"
        )
    modules = [suite.module for suite in suites]
    if len(modules) != len(set(modules)):
        raise CertificationError("compilerSuites modules must be unique")

    return RegressionInventory(
        version=SUPPORTED_INVENTORY_VERSION,
        gate=gate,
        workflow=_repo_path(raw["workflow"], "workflow"),
        workflow_job=_require_string(raw["workflowJob"], "workflowJob"),
        selection_policy=_repo_path(raw["selectionPolicy"], "selectionPolicy"),
        cli_source=_repo_path(raw["cliSource"], "cliSource"),
        compiler_suites=tuple(suites),
        cli_regression_modules=_sorted_paths(raw["cliRegressionModules"], "cliRegressionModules"),
    )


def _parse_python(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    except (OSError, SyntaxError) as exc:
        raise CertificationError(f"cannot parse Python evidence {path}: {exc}") from exc


def _imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _references_literal_module(tree: ast.AST, module: str) -> bool:
    if module in _imported_modules(tree):
        return True
    return any(
        isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value == module
        for node in ast.walk(tree)
    )


def _registered_cli_commands(tree: ast.AST) -> set[str]:
    commands: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_parser":
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            commands.add(first.value)
    return commands


def _workflow_job_block(text: str, job: str) -> str:
    lines = text.splitlines()
    start = None
    heading = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
    for index, line in enumerate(lines):
        match = heading.match(line)
        if match and match.group(1) == job:
            start = index
            break
    if start is None:
        raise CertificationError(f"workflow job {job!r} is missing")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if heading.match(lines[index]):
            end = index
            break
    return "\n".join(lines[start:end])


def certify_repository(repo_root: Path, inventory_path: Path) -> Certification:
    inventory = load_inventory(inventory_path)
    try:
        selection = repository_selection(repo_root, repo_root / inventory.selection_policy)
        tracked = set(tracked_files(repo_root))
    except SelectionError as exc:
        raise CertificationError(f"test-selection dependency failed: {exc}") from exc

    excluded = {item.path for item in selection.excluded}
    required_paths = {
        inventory.workflow,
        inventory.selection_policy,
        inventory.cli_source,
        *(suite.source for suite in inventory.compiler_suites),
        *(path for suite in inventory.compiler_suites for path in suite.compiler_tests),
        *(path for suite in inventory.compiler_suites for path in suite.cli_tests),
        *inventory.cli_regression_modules,
    }
    missing = sorted(required_paths - tracked)
    if missing:
        raise CertificationError("required inventory paths are not committed: " + ", ".join(missing))

    required_tests = {
        *(path for suite in inventory.compiler_suites for path in suite.compiler_tests),
        *(path for suite in inventory.compiler_suites for path in suite.cli_tests),
        *inventory.cli_regression_modules,
    }
    undiscovered = sorted(required_tests - set(selection.discovered))
    if undiscovered:
        raise CertificationError(
            "required regressions are not discovered by the M9-01 selector: " + ", ".join(undiscovered)
        )
    excluded_required = sorted(required_tests & excluded)
    if excluded_required:
        raise CertificationError(
            f"required regressions are excluded from {inventory.gate}: " + ", ".join(excluded_required)
        )
    unselected = sorted(required_tests - set(selection.selected))
    if unselected:
        raise CertificationError(
            f"required regressions are not selected for {inventory.gate}: " + ", ".join(unselected)
        )

    cli_tree = _parse_python(repo_root / inventory.cli_source)
    registered_commands = _registered_cli_commands(cli_tree)
    declared_compiler_tests: set[str] = set()
    paired_cli_tests: set[str] = set()
    for suite in inventory.compiler_suites:
        declared_compiler_tests.update(suite.compiler_tests)
        paired_cli_tests.update(suite.cli_tests)
        for test in suite.compiler_tests:
            tree = _parse_python(repo_root / test)
            if suite.module not in _imported_modules(tree):
                raise CertificationError(
                    f"compiler regression {test} no longer imports its certified module {suite.module}"
                )
        absent_commands = sorted(set(suite.cli_commands) - registered_commands)
        if absent_commands:
            raise CertificationError(
                f"{suite.area} CLI commands are no longer registered: " + ", ".join(absent_commands)
            )
        for test in suite.cli_tests:
            tree = _parse_python(repo_root / test)
            if not _references_literal_module(tree, "tools.aidl_cli"):
                raise CertificationError(
                    f"paired CLI regression {test} no longer exercises tools.aidl_cli"
                )

    missing_cli_inventory = sorted(paired_cli_tests - set(inventory.cli_regression_modules))
    if missing_cli_inventory:
        raise CertificationError(
            "paired CLI regressions are absent from cliRegressionModules: " + ", ".join(missing_cli_inventory)
        )

    critical_modules = {suite.module for suite in inventory.compiler_suites}
    detected_compiler_tests: set[str] = set()
    detected_cli_tests: set[str] = set()
    for test in selection.selected:
        tree = _parse_python(repo_root / test)
        imports = _imported_modules(tree)
        if imports & critical_modules:
            detected_compiler_tests.add(test)
        if _references_literal_module(tree, "tools.aidl_cli"):
            detected_cli_tests.add(test)

    unlisted_compiler = sorted(detected_compiler_tests - declared_compiler_tests)
    if unlisted_compiler:
        raise CertificationError(
            "compiler-owned critical regressions are selected but not inventoried: "
            + ", ".join(unlisted_compiler)
        )
    stale_compiler = sorted(declared_compiler_tests - detected_compiler_tests)
    if stale_compiler:
        raise CertificationError(
            "inventoried compiler regressions no longer import a critical compiler module: "
            + ", ".join(stale_compiler)
        )

    declared_cli = set(inventory.cli_regression_modules)
    unlisted_cli = sorted(detected_cli_tests - declared_cli)
    if unlisted_cli:
        raise CertificationError(
            "CLI regressions are selected but not inventoried: " + ", ".join(unlisted_cli)
        )
    stale_cli = sorted(declared_cli - detected_cli_tests)
    if stale_cli:
        raise CertificationError(
            "inventoried CLI regressions no longer exercise tools.aidl_cli: " + ", ".join(stale_cli)
        )

    try:
        workflow_text = (repo_root / inventory.workflow).read_text(encoding="utf-8")
    except OSError as exc:
        raise CertificationError(f"cannot read workflow {inventory.workflow}: {exc}") from exc
    block = _workflow_job_block(workflow_text, inventory.workflow_job)
    required_workflow_markers = (
        f"name: {inventory.gate}",
        "run: python3 -m tools.ci_required_regressions validate",
        "run: python3 -m tools.ci_test_selection run",
    )
    missing_markers = [marker for marker in required_workflow_markers if marker not in block]
    if missing_markers:
        raise CertificationError(
            f"workflow job {inventory.workflow_job!r} no longer certifies and runs the required regression set: "
            + ", ".join(missing_markers)
        )

    return Certification(
        compiler_regressions=len(detected_compiler_tests),
        cli_regressions=len(detected_cli_tests),
        suites=len(inventory.compiler_suites),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Certify required compiler-owned Python regressions")
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--inventory", default=DEFAULT_INVENTORY)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    inventory_path = Path(args.inventory)
    if not inventory_path.is_absolute():
        inventory_path = repo_root / inventory_path
    try:
        result = certify_repository(repo_root, inventory_path)
    except CertificationError as exc:
        print(f"required-regressions: {exc}", file=sys.stderr)
        return CONFIG_ERROR_EXIT
    print(
        f"required regressions: {result.suites} compiler suites, "
        f"{result.compiler_regressions} compiler tests, {result.cli_regressions} CLI tests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
