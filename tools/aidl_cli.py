from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from tools.compiler_change_impact import analyze_change_impact
from tools.compiler_completion import complete_project_reference
from tools.compiler_dependencies import collect_project_dependencies
from tools.compiler_diagnostics import CompilerAnalysis, CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_documentation import document_project_source
from tools.compiler_explanation import explain_project_declaration
from tools.compiler_inspection import inspect_project_declaration
from tools.compiler_ir import IrBuildError, build_canonical_ir
from tools.compiler_m1_resolution import collect_m1_resolution_diagnostics
from tools.compiler_refactoring import find_project_usages, rename_project_symbol
from tools.compiler_resolution import resolve_project_reference
from tools.compiler_summary import summarize_project
from tools.ir_canonical_json import canonical_ir_json_text
from tools.ir_compatibility import classify_ir_diff, ir_compatibility_to_json
from tools.ir_diff import IrDiffError, diff_canonical_ir, semantic_ir_diff_to_json
from tools.ir_migration_guidance import build_ir_migration_guidance, ir_migration_guidance_to_json
from tools.ir_plan import PlanBuildError, build_plan, canonical_plan_json_text


EXIT_SUCCESS = 0
EXIT_VALIDATION_FAILURE = 1
EXIT_INTERNAL_ERROR = 70


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aidl", description="AIDL compiler command line interface")
    subcommands = parser.add_subparsers(dest="command", required=True)
    check = subcommands.add_parser("check", help="validate an AIDL project and emit diagnostics")
    check.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    check.add_argument("--format", choices=("human", "json"), default="human", help="diagnostic output format")
    ir = subcommands.add_parser("ir", help="emit canonical AIDL IR")
    ir.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    ir.add_argument("--format", choices=("native", "json"), default="native", help="output format")
    plan = subcommands.add_parser("plan", help="emit a deterministic deployment/runtime plan")
    plan.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    plan.add_argument("--deployment", help="deployment name, FQN, or declaration ID; defaults to app.defaultDeploymentId")
    plan.add_argument("--format", choices=("native", "json"), default="native", help="output format")
    diff = subcommands.add_parser("diff", help="compare two AIDL project states through canonical IR")
    diff.add_argument("--old", nargs="+", required=True, type=Path, help="old AIDL files or directories")
    diff.add_argument("--new", nargs="+", required=True, type=Path, help="new AIDL files or directories")
    diff.add_argument("--format", choices=("human", "json"), default="human", help="diff output format")
    inspect = subcommands.add_parser("inspect", help="inspect one fully qualified declaration through compiler semantics")
    inspect.add_argument("fully_qualified_name", help="fully qualified declaration name")
    inspect.add_argument("paths", nargs="*", type=Path, default=[Path(".")], help="AIDL files or directories; defaults to current directory")
    inspect.add_argument("--format", choices=("human", "json"), default="human", help="output format")
    dependencies = subcommands.add_parser("dependencies", help="list direct compiler-owned declaration dependencies")
    dependencies.add_argument("fully_qualified_name", help="fully qualified declaration name")
    dependencies.add_argument("paths", nargs="*", type=Path, default=[Path(".")], help="AIDL files or directories; defaults to current directory")
    dependencies.add_argument("--format", choices=("human", "json"), default="human", help="output format")
    explain = subcommands.add_parser("explain", help="explain compiler diagnostics for one fully qualified declaration")
    explain.add_argument("fully_qualified_name", help="fully qualified declaration name")
    explain.add_argument("paths", nargs="*", type=Path, default=[Path(".")], help="AIDL files or directories; defaults to current directory")
    explain.add_argument("--format", choices=("human", "json"), default="human", help="output format")
    summary = subcommands.add_parser("summary", help="emit a compact compiler-owned project summary")
    summary.add_argument("paths", nargs="*", type=Path, default=[Path(".")], help="AIDL files or directories; defaults to current directory")
    summary.add_argument("--format", choices=("human", "json"), default="human", help="output format")
    impact = subcommands.add_parser("impact", help="analyze compiler-authoritative change impact for one declaration")
    impact.add_argument("fully_qualified_name", help="fully qualified declaration name")
    impact.add_argument("paths", nargs="*", type=Path, default=[Path(".")], help="AIDL files or directories; defaults to current directory")
    impact.add_argument("--format", choices=("human", "json"), default="human", help="output format")
    resolve = subcommands.add_parser("resolve", help="resolve one source reference through compiler symbols")
    resolve.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    resolve.add_argument("--file", required=True, type=Path, help="source file containing the reference")
    resolve.add_argument("--offset", required=True, type=int, help="zero-based source offset inside the reference")
    resolve.add_argument("--format", choices=("json",), default="json", help="output format")
    complete = subcommands.add_parser("complete", help="complete one source reference through compiler visibility")
    complete.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    complete.add_argument("--file", required=True, type=Path, help="source file containing the completion position")
    complete.add_argument("--offset", required=True, type=int, help="zero-based source offset at the completion position")
    complete.add_argument("--format", choices=("json",), default="json", help="output format")
    document = subcommands.add_parser("document", help="return compiler-owned declaration and diagnostic documentation")
    document.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    document.add_argument("--file", required=True, type=Path, help="source file containing the documentation position")
    document.add_argument("--offset", required=True, type=int, help="zero-based source offset at the documentation position")
    document.add_argument("--format", choices=("json",), default="json", help="output format")
    usages = subcommands.add_parser("usages", help="find semantic usages through compiler reference resolution")
    usages.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    usages.add_argument("--file", required=True, type=Path, help="source file containing the declaration/reference")
    usages.add_argument("--offset", required=True, type=int, help="zero-based source offset inside the target")
    usages.add_argument("--format", choices=("json",), default="json", help="output format")
    rename = subcommands.add_parser("rename", help="safely rename one compiler-resolved declaration")
    rename.add_argument("paths", nargs="+", type=Path, help="single AIDL project directory")
    rename.add_argument("--file", required=True, type=Path, help="source file containing the declaration/reference")
    rename.add_argument("--offset", required=True, type=int, help="zero-based source offset inside the target")
    rename.add_argument("--new-name", required=True, help="new declaration identifier")
    rename.add_argument("--apply", action="store_true", help="apply the compiler-validated rename atomically with rollback")
    rename.add_argument("--format", choices=("json",), default="json", help="output format")
    return parser


def _diagnostics_json(analysis) -> list[dict[str, Any]]:
    return [diagnostic.to_json() for diagnostic in analysis.diagnostics]


def _emit_json(command: str, ok: bool, *, diagnostics=None, result=None, error=None) -> None:
    payload: dict[str, Any] = {
        "command": command,
        "diagnostics": diagnostics if diagnostics is not None else [],
        "ok": ok,
    }
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")


def _emit_diagnostics(analysis) -> None:
    for diagnostic in analysis.diagnostics:
        payload = diagnostic.to_json()
        location = payload["location"]
        sys.stderr.write(
            f"{location['file']}:{location['line']}:{location['column']}: "
            f"{payload['severity']} {payload['code']}: {payload['message']}\n"
        )


def _emit_diff_diagnostics(side: str, analysis) -> None:
    for diagnostic in analysis.diagnostics:
        payload = diagnostic.to_json()
        location = payload["location"]
        sys.stderr.write(
            f"aidl diff {side}: {location['file']}:{location['line']}:{location['column']}: "
            f"{payload['severity']} {payload['code']}: {payload['message']}\n"
        )


def _has_errors(analysis) -> bool:
    return any(
        diagnostic.severity == CompilerDiagnosticSeverity.ERROR
        for diagnostic in analysis.diagnostics
    )


def _with_m1_resolution_diagnostics(analysis: CompilerAnalysis) -> CompilerAnalysis:
    supplemental = collect_m1_resolution_diagnostics(analysis.project)
    if not supplemental:
        return analysis
    document_order = {
        document.source_path: index for index, document in enumerate(analysis.project.documents)
    }
    phase_order = {"parse": 0, "resolve": 1, "policy": 2}
    severity_order = {"error": 0, "warning": 1, "info": 2}
    combined = list(analysis.diagnostics) + list(supplemental)
    combined.sort(
        key=lambda diagnostic: (
            document_order.get(diagnostic.source_path, len(document_order)),
            diagnostic.location.offset,
            phase_order.get(diagnostic.phase, len(phase_order)),
            severity_order.get(diagnostic.severity.value, len(severity_order)),
            diagnostic.code.value,
            diagnostic.message,
        )
    )
    return CompilerAnalysis(project=analysis.project, diagnostics=tuple(combined))


def _run_check(paths: Sequence[Path], output_format: str) -> int:
    analysis = _with_m1_resolution_diagnostics(load_compiler_analysis(paths))
    has_errors = _has_errors(analysis)
    if output_format == "json":
        _emit_json("check", not has_errors, diagnostics=_diagnostics_json(analysis))
    else:
        _emit_diagnostics(analysis)
    return EXIT_VALIDATION_FAILURE if has_errors else EXIT_SUCCESS


def _load_ir(paths: Sequence[Path], command: str, output_format: str):
    analysis = load_compiler_analysis(paths)
    if _has_errors(analysis):
        if output_format == "json":
            _emit_json(command, False, diagnostics=_diagnostics_json(analysis))
        else:
            _emit_diagnostics(analysis)
        return None
    try:
        return build_canonical_ir(analysis)
    except IrBuildError as exc:
        if output_format == "json":
            _emit_json(command, False, error={"kind": "irBuild", "message": str(exc)})
        else:
            sys.stderr.write(f"aidl {command}: {exc}\n")
        return None


def _run_ir(paths: Sequence[Path], output_format: str) -> int:
    document = _load_ir(paths, "ir", output_format)
    if document is None:
        return EXIT_VALIDATION_FAILURE
    if output_format == "json":
        _emit_json("ir", True, result=document)
    else:
        sys.stdout.write(canonical_ir_json_text(document))
    return EXIT_SUCCESS


def _run_plan(paths: Sequence[Path], deployment: str | None, output_format: str) -> int:
    document = _load_ir(paths, "plan", output_format)
    if document is None:
        return EXIT_VALIDATION_FAILURE
    try:
        plan = build_plan(document, deployment=deployment)
    except PlanBuildError as exc:
        if output_format == "json":
            _emit_json(command="plan", ok=False, error={"kind": "planBuild", "message": str(exc)})
        else:
            sys.stderr.write(f"aidl plan: {exc}\n")
        return EXIT_VALIDATION_FAILURE
    if output_format == "json":
        _emit_json("plan", True, result=plan)
    else:
        sys.stdout.write(canonical_plan_json_text(plan))
    return EXIT_SUCCESS


def _load_diff_ir(paths: Sequence[Path], side: str, output_format: str):
    analysis = load_compiler_analysis(paths)
    if _has_errors(analysis):
        if output_format == "json":
            _emit_json(
                "diff",
                False,
                diagnostics=_diagnostics_json(analysis),
                error={
                    "kind": "compiler",
                    "message": f"{side} project has compiler errors",
                    "side": side,
                },
            )
        else:
            _emit_diff_diagnostics(side, analysis)
        return None
    try:
        return build_canonical_ir(analysis)
    except IrBuildError as exc:
        if output_format == "json":
            _emit_json(
                "diff",
                False,
                error={"kind": "irBuild", "message": str(exc), "side": side},
            )
        else:
            sys.stderr.write(f"aidl diff {side}: {exc}\n")
        return None


def _diff_input_error(exc: IrDiffError) -> tuple[str, str]:
    message = str(exc)
    for side in ("old", "new"):
        prefix = f"{side}:"
        if message.startswith(prefix):
            return side, message[len(prefix):].lstrip()
    return "comparison", message


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _emit_diff_human(changes, classifications, guidance) -> None:
    raw = semantic_ir_diff_to_json(changes)
    classified = ir_compatibility_to_json(classifications)
    guided = ir_migration_guidance_to_json(guidance)
    for change, classification, migration in zip(raw, classified, guided, strict=True):
        sys.stdout.write(
            f"{change['kind']} {change['path']} "
            f"old={_compact_json(change['oldValue'])} "
            f"new={_compact_json(change['newValue'])} "
            f"classification={classification['classification']} "
            f"rule={classification['rule']} "
            f"reason={_compact_json(classification['reason'])} "
            f"guidance={_compact_json(migration)}\n"
        )


def _run_diff(old_paths: Sequence[Path], new_paths: Sequence[Path], output_format: str) -> int:
    old_document = _load_diff_ir(old_paths, "old", output_format)
    if old_document is None:
        return EXIT_VALIDATION_FAILURE
    new_document = _load_diff_ir(new_paths, "new", output_format)
    if new_document is None:
        return EXIT_VALIDATION_FAILURE
    try:
        changes = diff_canonical_ir(old_document, new_document)
    except IrDiffError as exc:
        side, message = _diff_input_error(exc)
        if output_format == "json":
            _emit_json(
                "diff",
                False,
                error={"kind": "diffInput", "message": message, "side": side},
            )
        else:
            sys.stderr.write(f"aidl diff {side}: {message}\n")
        return EXIT_VALIDATION_FAILURE
    classifications = classify_ir_diff(changes, old_document, new_document)
    guidance = build_ir_migration_guidance(
        changes,
        classifications,
        old_document,
        new_document,
    )
    if output_format == "json":
        _emit_json(
            "diff",
            True,
            result={
                "changes": semantic_ir_diff_to_json(changes),
                "classifications": ir_compatibility_to_json(classifications),
                "guidance": ir_migration_guidance_to_json(guidance),
            },
        )
    else:
        _emit_diff_human(changes, classifications, guidance)
    return EXIT_SUCCESS


def _emit_inspect_human(result: Mapping[str, object]) -> None:
    declaration = result["declaration"]
    if not isinstance(declaration, Mapping):
        raise ValueError("resolved inspect result has no declaration")
    location = declaration["location"]
    if not isinstance(location, Mapping):
        raise ValueError("resolved inspect declaration has no location")
    sys.stdout.write(f"{declaration['fullyQualifiedName']} ({declaration['kind']})\n")
    sys.stdout.write(f"module: {declaration['module']}\n")
    sys.stdout.write(f"exported: {str(declaration['exported']).lower()}\n")
    sys.stdout.write(
        f"location: {location['file']}:{location['line']}:{location['column']}\n"
    )
    sys.stdout.write(f"representation: {declaration['representation']}\n")
    sys.stdout.write(f"canonical: {_compact_json(declaration['canonical'])}\n")


def _run_inspect(paths: Sequence[Path], fully_qualified_name: str, output_format: str) -> int:
    analysis = _with_m1_resolution_diagnostics(load_compiler_analysis(paths))
    diagnostics = _diagnostics_json(analysis)
    if _has_errors(analysis):
        message = "project has compiler errors"
        if output_format == "json":
            _emit_json("inspect", False, diagnostics=diagnostics, error={"kind": "compiler", "message": message})
        else:
            _emit_diagnostics(analysis)
            sys.stderr.write(f"aidl inspect: {message}\n")
        return EXIT_VALIDATION_FAILURE

    try:
        result = inspect_project_declaration(analysis, fully_qualified_name)
    except IrBuildError as exc:
        if output_format == "json":
            _emit_json("inspect", False, diagnostics=diagnostics, error={"kind": "inspectBuild", "message": str(exc)})
        else:
            sys.stderr.write(f"aidl inspect: {exc}\n")
        return EXIT_VALIDATION_FAILURE

    if result.status == "resolved":
        payload = result.to_json()
        if output_format == "json":
            _emit_json("inspect", True, diagnostics=diagnostics, result=payload)
        else:
            _emit_inspect_human(payload)
        return EXIT_SUCCESS

    error_kind = {
        "invalid": "invalidFqn",
        "unknown": "unknownFqn",
        "ambiguous": "ambiguousFqn",
    }[result.status]
    message = {
        "invalid": f"invalid fully qualified declaration name '{fully_qualified_name}'",
        "unknown": f"unknown fully qualified declaration '{fully_qualified_name}'",
        "ambiguous": f"ambiguous fully qualified declaration '{fully_qualified_name}'",
    }[result.status]
    if output_format == "json":
        _emit_json(
            "inspect",
            False,
            diagnostics=diagnostics,
            result=result.to_json(),
            error={"kind": error_kind, "message": message},
        )
    else:
        sys.stderr.write(f"aidl inspect: {message}\n")
    return EXIT_VALIDATION_FAILURE


def _emit_dependencies_human(result: Mapping[str, object]) -> None:
    declaration = result["declaration"]
    dependencies = result["dependencies"]
    if not isinstance(declaration, Mapping) or not isinstance(dependencies, list):
        raise ValueError("resolved dependencies result is malformed")
    sys.stdout.write(
        f"{declaration['fullyQualifiedName']} ({declaration['kind']}): {len(dependencies)} direct dependencies\n"
    )
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            raise ValueError("resolved dependencies result contains malformed dependency")
        sys.stdout.write(
            f"- {dependency['fullyQualifiedName']} ({dependency['kind']}) [{dependency['declarationId']}]\n"
        )


def _run_dependencies(paths: Sequence[Path], fully_qualified_name: str, output_format: str) -> int:
    analysis = _with_m1_resolution_diagnostics(load_compiler_analysis(paths))
    diagnostics = _diagnostics_json(analysis)
    if _has_errors(analysis):
        message = "project has compiler errors"
        if output_format == "json":
            _emit_json("dependencies", False, diagnostics=diagnostics, error={"kind": "compiler", "message": message})
        else:
            _emit_diagnostics(analysis)
            sys.stderr.write(f"aidl dependencies: {message}\n")
        return EXIT_VALIDATION_FAILURE

    try:
        result = collect_project_dependencies(analysis, fully_qualified_name)
    except IrBuildError as exc:
        if output_format == "json":
            _emit_json("dependencies", False, diagnostics=diagnostics, error={"kind": "dependencyBuild", "message": str(exc)})
        else:
            sys.stderr.write(f"aidl dependencies: {exc}\n")
        return EXIT_VALIDATION_FAILURE

    if result.status == "resolved":
        payload = result.to_json()
        if output_format == "json":
            _emit_json("dependencies", True, diagnostics=diagnostics, result=payload)
        else:
            _emit_dependencies_human(payload)
        return EXIT_SUCCESS

    error_kind = {
        "invalid": "invalidFqn",
        "unknown": "unknownFqn",
        "ambiguous": "ambiguousFqn",
    }[result.status]
    message = {
        "invalid": f"invalid fully qualified declaration name '{fully_qualified_name}'",
        "unknown": f"unknown fully qualified declaration '{fully_qualified_name}'",
        "ambiguous": f"ambiguous fully qualified declaration '{fully_qualified_name}'",
    }[result.status]
    if output_format == "json":
        _emit_json(
            "dependencies",
            False,
            diagnostics=diagnostics,
            result=result.to_json(),
            error={"kind": error_kind, "message": message},
        )
    else:
        sys.stderr.write(f"aidl dependencies: {message}\n")
    return EXIT_VALIDATION_FAILURE


def _emit_explain_human(result: Mapping[str, object]) -> None:
    declaration = result["declaration"]
    explanations = result["explanations"]
    if not isinstance(declaration, Mapping) or not isinstance(explanations, list):
        raise ValueError("resolved explain result is malformed")
    sys.stdout.write(
        f"{declaration['fullyQualifiedName']} ({declaration['kind']}): "
        f"{result['totalDiagnosticCount']} diagnostics"
    )
    if result.get("truncated"):
        sys.stdout.write(f"; showing first {len(explanations)}")
    sys.stdout.write("\n")
    for explanation in explanations:
        if not isinstance(explanation, Mapping):
            raise ValueError("resolved explain result contains malformed explanation")
        rule = explanation["rule"]
        evidence = explanation["evidence"]
        remediation = explanation["remediation"]
        if not isinstance(rule, Mapping) or not isinstance(evidence, Mapping) or not isinstance(remediation, list):
            raise ValueError("resolved explain explanation is malformed")
        location = evidence["location"]
        if not isinstance(location, Mapping):
            raise ValueError("resolved explain evidence has no location")
        sys.stdout.write(f"- {rule['code']}: {rule['message']}\n")
        if "expected" in rule:
            sys.stdout.write(f"  expected: {rule['expected']}\n")
        sys.stdout.write(
            f"  evidence: {location['file']}:{location['line']}:{location['column']}"
        )
        subject = evidence.get("subject")
        if isinstance(subject, Mapping):
            sys.stdout.write(f" {subject['kind']} {subject['name']}")
        sys.stdout.write("\n")
        if remediation:
            for fix in remediation:
                if not isinstance(fix, Mapping):
                    raise ValueError("resolved explain remediation is malformed")
                sys.stdout.write(f"  fix: {fix['kind']} {_compact_json(fix['text'])}\n")
        else:
            sys.stdout.write("  fix: none authorized\n")


def _run_explain(paths: Sequence[Path], fully_qualified_name: str, output_format: str) -> int:
    analysis = _with_m1_resolution_diagnostics(load_compiler_analysis(paths))
    diagnostics = _diagnostics_json(analysis)
    result = explain_project_declaration(analysis, fully_qualified_name)
    if result.status == "resolved":
        payload = result.to_json()
        if output_format == "json":
            _emit_json("explain", True, diagnostics=diagnostics, result=payload)
        else:
            _emit_explain_human(payload)
        return EXIT_SUCCESS

    error_kind = {
        "invalid": "invalidFqn",
        "unknown": "unknownFqn",
        "ambiguous": "ambiguousFqn",
    }[result.status]
    message = {
        "invalid": f"invalid fully qualified declaration name '{fully_qualified_name}'",
        "unknown": f"unknown fully qualified declaration '{fully_qualified_name}'",
        "ambiguous": f"ambiguous fully qualified declaration '{fully_qualified_name}'",
    }[result.status]
    if output_format == "json":
        _emit_json(
            "explain",
            False,
            diagnostics=diagnostics,
            result=result.to_json(),
            error={"kind": error_kind, "message": message},
        )
    else:
        sys.stderr.write(f"aidl explain: {message}\n")
    return EXIT_VALIDATION_FAILURE


def _emit_summary_human(result: Mapping[str, object]) -> None:
    modules = result["modules"]
    declarations = result["declarations"]
    dependencies = result["moduleDependencies"]
    kinds = result["declarationKinds"]
    truncated = result["truncated"]
    if not all(isinstance(value, list) for value in (modules, declarations, dependencies, kinds)) or not isinstance(truncated, Mapping):
        raise ValueError("project summary result is malformed")
    sys.stdout.write(
        f"project: {result['moduleCount']} modules, {result['declarationCount']} declarations "
        f"({result['exportedDeclarationCount']} exported), {result['documentCount']} documents\n"
    )
    if kinds:
        sys.stdout.write(
            "kinds: " + ", ".join(f"{item['kind']}={item['count']}" for item in kinds if isinstance(item, Mapping)) + "\n"
        )
    sys.stdout.write(f"modules: {result['totals']['modules']}")
    if truncated.get("modules"):
        sys.stdout.write(f"; showing first {len(modules)}")
    sys.stdout.write("\n")
    for module in modules:
        if not isinstance(module, Mapping):
            raise ValueError("project summary module is malformed")
        sys.stdout.write(
            f"- {module['name']}: {module['declarationCount']} declarations "
            f"({module['exportedDeclarationCount']} exported)\n"
        )
    sys.stdout.write(f"declarations: {result['totals']['declarations']}")
    if truncated.get("declarations"):
        sys.stdout.write(f"; showing first {len(declarations)}")
    sys.stdout.write("\n")
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            raise ValueError("project summary declaration is malformed")
        exported = " exported" if declaration["exported"] else ""
        sys.stdout.write(f"- {declaration['fullyQualifiedName']} ({declaration['kind']}){exported}\n")
    sys.stdout.write(f"module dependencies: {result['totals']['moduleDependencies']}")
    if truncated.get("moduleDependencies"):
        sys.stdout.write(f"; showing first {len(dependencies)}")
    sys.stdout.write("\n")
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            raise ValueError("project summary dependency is malformed")
        sys.stdout.write(f"- {dependency['sourceModule']} -> {dependency['targetModule']}\n")


def _run_summary(paths: Sequence[Path], output_format: str) -> int:
    analysis = _with_m1_resolution_diagnostics(load_compiler_analysis(paths))
    diagnostics = _diagnostics_json(analysis)
    if _has_errors(analysis):
        message = "project has compiler errors"
        if output_format == "json":
            _emit_json("summary", False, diagnostics=diagnostics, error={"kind": "compiler", "message": message})
        else:
            _emit_diagnostics(analysis)
            sys.stderr.write(f"aidl summary: {message}\n")
        return EXIT_VALIDATION_FAILURE

    payload = summarize_project(analysis).to_json()
    if output_format == "json":
        _emit_json("summary", True, diagnostics=diagnostics, result=payload)
    else:
        _emit_summary_human(payload)
    return EXIT_SUCCESS


def _emit_impact_human(result: Mapping[str, object]) -> None:
    declaration = result["declaration"]
    affected = result["affectedDeclarations"]
    contracts = result["publicContracts"]
    persisted = result["persistedState"]
    checks = result["compatibilityChecks"]
    generated = result["generatedArtifacts"]
    if not isinstance(declaration, Mapping) or not all(isinstance(value, list) for value in (affected, contracts, persisted, checks)) or not isinstance(generated, Mapping):
        raise ValueError("resolved impact result is malformed")
    sys.stdout.write(f"{declaration['fullyQualifiedName']} ({declaration['kind']})\n")
    for label, values in (("affected declarations", affected), ("public contracts", contracts), ("persisted state", persisted)):
        sys.stdout.write(f"{label}: {len(values)}\n")
        for item in values:
            if not isinstance(item, Mapping) or not isinstance(item.get("declaration"), Mapping):
                raise ValueError("resolved impact evidence is malformed")
            identity = item["declaration"]
            sys.stdout.write(f"- {item['category']}: {identity['fullyQualifiedName']} ({identity['kind']}) [{identity['declarationId']}]\n")
    sys.stdout.write(f"generated artifacts: {generated['status']}: {generated['reason']}\n")
    sys.stdout.write(f"compatibility checks: {len(checks)}\n")
    for item in checks:
        if not isinstance(item, Mapping):
            raise ValueError("resolved impact compatibility check is malformed")
        sys.stdout.write(f"- {item['surface']}: {item['command']} ({item['status']})\n")


def _run_impact(paths: Sequence[Path], fully_qualified_name: str, output_format: str) -> int:
    analysis = _with_m1_resolution_diagnostics(load_compiler_analysis(paths))
    diagnostics = _diagnostics_json(analysis)
    if _has_errors(analysis):
        message = "project has compiler errors"
        if output_format == "json":
            _emit_json("impact", False, diagnostics=diagnostics, error={"kind": "compiler", "message": message})
        else:
            _emit_diagnostics(analysis)
            sys.stderr.write(f"aidl impact: {message}\n")
        return EXIT_VALIDATION_FAILURE
    try:
        result = analyze_change_impact(analysis, fully_qualified_name)
    except IrBuildError as exc:
        if output_format == "json":
            _emit_json("impact", False, diagnostics=diagnostics, error={"kind": "impactBuild", "message": str(exc)})
        else:
            sys.stderr.write(f"aidl impact: {exc}\n")
        return EXIT_VALIDATION_FAILURE
    if result.status == "resolved":
        payload = result.to_json()
        if output_format == "json":
            _emit_json("impact", True, diagnostics=diagnostics, result=payload)
        else:
            _emit_impact_human(payload)
        return EXIT_SUCCESS
    error_kind = {
        "invalid": "invalidFqn",
        "unknown": "unknownFqn",
        "ambiguous": "ambiguousFqn",
    }[result.status]
    message = {
        "invalid": f"invalid fully qualified declaration name '{fully_qualified_name}'",
        "unknown": f"unknown fully qualified declaration '{fully_qualified_name}'",
        "ambiguous": f"ambiguous fully qualified declaration '{fully_qualified_name}'",
    }[result.status]
    if output_format == "json":
        _emit_json(
            "impact",
            False,
            diagnostics=diagnostics,
            result=result.to_json(),
            error={"kind": error_kind, "message": message},
        )
    else:
        sys.stderr.write(f"aidl impact: {message}\n")
    return EXIT_VALIDATION_FAILURE


def _run_resolve(paths: Sequence[Path], source_file: Path, offset: int) -> int:
    analysis = load_compiler_analysis(paths)
    resolution = resolve_project_reference(analysis.project, source_file, offset)
    _emit_json(
        "resolve",
        True,
        diagnostics=_diagnostics_json(analysis),
        result=resolution.to_json(),
    )
    return EXIT_SUCCESS


def _run_complete(paths: Sequence[Path], source_file: Path, offset: int) -> int:
    analysis = load_compiler_analysis(paths)
    result = complete_project_reference(analysis.project, source_file, offset)
    _emit_json(
        "complete",
        True,
        diagnostics=_diagnostics_json(analysis),
        result=result.to_json(),
    )
    return EXIT_SUCCESS


def _run_document(paths: Sequence[Path], source_file: Path, offset: int) -> int:
    analysis = load_compiler_analysis(paths)
    result = document_project_source(analysis, source_file, offset)
    _emit_json(
        "document",
        True,
        diagnostics=_diagnostics_json(analysis),
        result=result.to_json(),
    )
    return EXIT_SUCCESS


def _run_usages(paths: Sequence[Path], source_file: Path, offset: int) -> int:
    analysis = load_compiler_analysis(paths)
    result = find_project_usages(analysis, source_file, offset)
    _emit_json(
        "usages",
        True,
        diagnostics=_diagnostics_json(analysis),
        result=result.to_json(),
    )
    return EXIT_SUCCESS


def _run_rename(paths: Sequence[Path], source_file: Path, offset: int, new_name: str, apply: bool) -> int:
    result = rename_project_symbol(paths, source_file, offset, new_name, apply=apply)
    success = result.status in {"ready", "applied"}
    _emit_json("rename", success, result=result.to_json())
    return EXIT_SUCCESS if success else EXIT_VALIDATION_FAILURE


def _emit_internal_error(command: str, output_format: str, exc: Exception) -> None:
    message = f"{type(exc).__name__}: {exc}"
    if output_format == "json":
        _emit_json(command, False, error={"kind": "internal", "message": message})
    else:
        sys.stderr.write(f"aidl {command}: internal error: {message}\n")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            return _run_check(args.paths, args.format)
        if args.command == "ir":
            return _run_ir(args.paths, args.format)
        if args.command == "plan":
            return _run_plan(args.paths, args.deployment, args.format)
        if args.command == "diff":
            return _run_diff(args.old, args.new, args.format)
        if args.command == "inspect":
            return _run_inspect(args.paths, args.fully_qualified_name, args.format)
        if args.command == "dependencies":
            return _run_dependencies(args.paths, args.fully_qualified_name, args.format)
        if args.command == "explain":
            return _run_explain(args.paths, args.fully_qualified_name, args.format)
        if args.command == "summary":
            return _run_summary(args.paths, args.format)
        if args.command == "impact":
            return _run_impact(args.paths, args.fully_qualified_name, args.format)
        if args.command == "resolve":
            return _run_resolve(args.paths, args.file, args.offset)
        if args.command == "complete":
            return _run_complete(args.paths, args.file, args.offset)
        if args.command == "document":
            return _run_document(args.paths, args.file, args.offset)
        if args.command == "usages":
            return _run_usages(args.paths, args.file, args.offset)
        if args.command == "rename":
            return _run_rename(args.paths, args.file, args.offset, args.new_name, args.apply)
        raise AssertionError(f"unhandled command: {args.command}")
    except Exception as exc:
        _emit_internal_error(args.command, args.format, exc)
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
