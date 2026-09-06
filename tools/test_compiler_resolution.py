from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_resolution import resolve_project_reference


class CompilerResolutionTest(unittest.TestCase):
    def _write(self, root: Path, relative: str, text: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_resolves_local_exact_import_and_qualified_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = self._write(
                root,
                "app.aidl",
                "module app\n"
                "import lib.Shared\n"
                "entity Local {\n}\n"
                "entity Uses {\n"
                "  local: Local\n"
                "  imported: Shared\n"
                "  qualified: lib.Shared\n"
                "}\n",
            )
            shared = self._write(root, "lib.aidl", "module lib\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])

            cases = {
                "Local\n": "app.Local",
                "Shared\n": "lib.Shared",
                "lib.Shared\n": "lib.Shared",
            }
            text = local.read_text(encoding="utf-8")
            for marker, expected in cases.items():
                with self.subTest(marker=marker):
                    offset = text.index(marker) + (4 if marker == "lib.Shared\n" else 0)
                    result = resolve_project_reference(analysis.project, local, offset)
                    self.assertEqual("resolved", result.status)
                    self.assertIsNotNone(result.target)
                    self.assertEqual(expected, result.target.fully_qualified_name)
                    self.assertEqual(shared if expected == "lib.Shared" else local, result.target.source_path)

    def test_resolves_wildcard_import_and_rejects_ambiguous_or_invalid_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\n"
                "import one.*\n"
                "import two.*\n"
                "entity Uses {\n"
                "  target: Shared\n"
                "}\n",
            )
            self._write(root, "one.aidl", "module one\nexport entity Shared {\n}\n")
            self._write(root, "two.aidl", "module two\nexport entity Shared {\n}\n")
            analysis = load_compiler_analysis([root])
            text = source.read_text(encoding="utf-8")

            ambiguous = resolve_project_reference(analysis.project, source, text.index("Shared"))
            self.assertEqual("ambiguous", ambiguous.status)
            self.assertIsNone(ambiguous.target)

            invalid = resolve_project_reference(analysis.project, source, len(text) + 10)
            self.assertEqual("invalid", invalid.status)
            self.assertIsNone(invalid.target)

    def test_unresolved_reference_has_no_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nentity Uses {\n  target: Missing\n}\n",
            )
            analysis = load_compiler_analysis([root])
            result = resolve_project_reference(
                analysis.project,
                source,
                source.read_text(encoding="utf-8").index("Missing"),
            )
            self.assertEqual("unresolved", result.status)
            self.assertIsNone(result.target)


if __name__ == "__main__":
    unittest.main()
