from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import CompilerAnalysis, CompilerDiagnosticFix
from tools.compiler_snapshot import CompilerSnapshot, create_compiler_snapshot
from tools.compiler_snapshot_editing import authorized_snapshot_fixes

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
SOURCE = "module parity.fix\nconsumer Worker {\n  call: downstream\n}\n"


class KotlinAuthorizedFixPlanningParityTest(unittest.TestCase):
    def _snapshot_with(self, snapshot: CompilerSnapshot, source: Path, text: str, diagnostics) -> CompilerSnapshot:
        normalized = source.absolute().resolve(strict=False)
        return CompilerSnapshot(
            roots=snapshot.roots,
            source_texts=MappingProxyType({normalized: text}),
            analysis=CompilerAnalysis(project=snapshot.analysis.project, diagnostics=tuple(diagnostics)),
            overridden_paths=snapshot.overridden_paths,
        )

    def _escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("\n", "\\n")

    def _render(self, label: str, fixes) -> str:
        rendered = ";".join(
            f"{fix.title}~{fix.diagnostic_code}~{fix.edit.source_path.stem}:{fix.edit.offset}:{fix.edit.length}:{self._escape(fix.edit.replacement)}"
            for fix in fixes
        )
        return f"{label}|{rendered}"

    def test_python_snapshot_oracle_matches_pinned_authorized_fix_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fix.aidl"
            source.write_text(SOURCE, encoding="utf-8")
            saved = create_compiler_snapshot([root])
            diagnostics = [d for d in saved.diagnostics(source) if d.code.value == "AIDL-DIST411"]
            self.assertEqual(1, len(diagnostics))
            diagnostic = diagnostics[0]
            self.assertEqual(
                (CompilerDiagnosticFix(kind="insertClause", text="idempotency: event.eventId retain 30d"),),
                diagnostic.allowed_fixes,
            )

            unsaved_text = "\n" + SOURCE
            unsaved = create_compiler_snapshot([root], {source: unsaved_text})
            unsupported = replace(
                diagnostic,
                allowed_fixes=(CompilerDiagnosticFix(kind="replace", text="ignored"),),
            )
            multiple = replace(
                diagnostic,
                allowed_fixes=(
                    CompilerDiagnosticFix(kind="insertClause", text="first"),
                    CompilerDiagnosticFix(kind="insertClause", text="second"),
                ),
            )
            no_brace_text = SOURCE.replace("consumer Worker {", "consumer Worker  ")
            no_line_terminator = "module parity.fix\nconsumer Worker {"
            missing_source = CompilerSnapshot(
                roots=saved.roots,
                source_texts=MappingProxyType({}),
                analysis=saved.analysis,
                overridden_paths=saved.overridden_paths,
            )

            actual = "\n".join(
                (
                    self._render("saved", authorized_snapshot_fixes(saved, source)),
                    self._render("filtered", authorized_snapshot_fixes(saved, source, diagnostic_codes=("OTHER",))),
                    self._render("unsaved", authorized_snapshot_fixes(unsaved, source)),
                    self._render("unsupported", authorized_snapshot_fixes(self._snapshot_with(saved, source, SOURCE, (unsupported,)), source)),
                    self._render("no-brace", authorized_snapshot_fixes(self._snapshot_with(saved, source, no_brace_text, (diagnostic,)), source)),
                    self._render("no-line-terminator", authorized_snapshot_fixes(self._snapshot_with(saved, source, no_line_terminator, (diagnostic,)), source)),
                    self._render("multiple", authorized_snapshot_fixes(self._snapshot_with(saved, source, SOURCE, (multiple,)), source)),
                    self._render("missing-source", authorized_snapshot_fixes(missing_source, source)),
                )
            )
            self.assertEqual((PARITY / "authorized-fix-planning.signature").read_text(encoding="utf-8").rstrip(), actual)

    def test_saved_unsaved_and_root_isolation_use_the_exact_snapshot_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for root_name in ("root-a", "root-b"):
                root = base / root_name
                root.mkdir()
                source = root / "fix.aidl"
                source.write_text(SOURCE, encoding="utf-8")
                saved = create_compiler_snapshot([root])
                saved_fix = authorized_snapshot_fixes(saved, source)
                unsaved_text = "\n" + SOURCE
                unsaved = create_compiler_snapshot([root], {source: unsaved_text})
                unsaved_fix = authorized_snapshot_fixes(unsaved, source)
                self.assertEqual(source, saved_fix[0].edit.source_path)
                self.assertEqual(source, unsaved_fix[0].edit.source_path)
                self.assertEqual(saved_fix[0].edit.offset + 1, unsaved_fix[0].edit.offset)


if __name__ == "__main__":
    unittest.main()
