from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.compiler_diagnostics import CompilerDiagnosticSeverity, load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.generate_m4 import generate_and_write_m4
from tools.ir_canonical_json import canonical_ir_json_text
from tools.ir_plan import build_plan, canonical_plan_json_text


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "examples" / "petstore" / "m4-app"
SOURCE = APP_ROOT / "app.aidl"
BUILD_ROOT = APP_ROOT / "build"


def _load_ir() -> dict:
    analysis = load_compiler_analysis([SOURCE])
    errors = [item for item in analysis.diagnostics if item.severity == CompilerDiagnosticSeverity.ERROR]
    if errors:
        for diagnostic in errors:
            payload = diagnostic.to_json()
            location = payload["location"]
            sys.stderr.write(
                f"{location['file']}:{location['line']}:{location['column']}: "
                f"{payload['severity']} {payload['code']}: {payload['message']}\n"
            )
        raise SystemExit(1)
    return build_canonical_ir(analysis)


def _write_build_metadata(ir: dict) -> None:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    (BUILD_ROOT / "canonical-ir.json").write_text(canonical_ir_json_text(ir), encoding="utf-8", newline="")
    plan = build_plan(ir)
    (BUILD_ROOT / "plan.json").write_text(canonical_plan_json_text(plan), encoding="utf-8", newline="")


def command_check() -> int:
    _load_ir()
    return 0


def command_ir() -> int:
    sys.stdout.write(canonical_ir_json_text(_load_ir()))
    return 0


def command_plan() -> int:
    sys.stdout.write(canonical_plan_json_text(build_plan(_load_ir())))
    return 0


def command_generate() -> int:
    ir = _load_ir()
    _write_build_metadata(ir)
    files = generate_and_write_m4(ir, APP_ROOT)
    manifest = {
        "generated": sorted(files),
        "ir": "build/canonical-ir.json",
        "plan": "build/plan.json",
    }
    (BUILD_ROOT / "generation-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproducible M4 Petstore build input driver")
    parser.add_argument("command", choices=("check", "ir", "plan", "generate"))
    args = parser.parse_args(argv)
    if args.command == "check":
        return command_check()
    if args.command == "ir":
        return command_ir()
    if args.command == "plan":
        return command_plan()
    return command_generate()


if __name__ == "__main__":
    raise SystemExit(main())
