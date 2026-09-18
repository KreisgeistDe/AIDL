from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.compiler_refactoring import rename_project_symbol  # noqa: F401
from tools.compiler_snapshot import create_compiler_snapshot
from tools.compiler_snapshot_editing import authorized_snapshot_fixes


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "compiler" / "kotlin" / "parity" / "authorized-fixes.source"
SIGNATURE = ROOT / "compiler" / "kotlin" / "parity" / "authorized-fixes.signature"


def _render(label, fixes):
    if not fixes:
        return f"{label}|<none>"
    rows = []
    for fix in fixes:
        edit = fix.edit
        replacement = edit.replacement.replace("\n", "\\n")
        rows.append(
            f"{label}|{fix.title}|{fix.diagnostic_code}|"
            f"{edit.source_path.name}:{edit.offset}:{edit.length}:{replacement}"
        )
    return "\n".join(rows)


class KotlinAuthorizedFixParityTest(unittest.TestCase):
    def _matrix(self) -> str:
        source_text = SOURCE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "authorized-fixes.aidl"
            source.write_text(source_text, encoding="utf-8")
            saved = create_compiler_snapshot([root])
            shifted = "\n" + source_text
            memory = create_compiler_snapshot([root], {source: shifted})
            return "\n".join(
                [
                    _render("saved-all", authorized_snapshot_fixes(saved, source)),
                    _render(
                        "saved-filter-match",
                        authorized_snapshot_fixes(
                            saved, source, diagnostic_codes=["AIDL-DIST411"]
                        ),
                    ),
                    _render(
                        "saved-filter-empty",
                        authorized_snapshot_fixes(saved, source, diagnostic_codes=[]),
                    ),
                    _render(
                        "saved-filter-miss",
                        authorized_snapshot_fixes(
                            saved, source, diagnostic_codes=["AIDL-R001"]
                        ),
                    ),
                    _render("memory-shifted", authorized_snapshot_fixes(memory, source)),
                ]
            )

    def test_real_python_snapshot_helper_matches_pinned_signature(self) -> None:
        self.assertEqual(SIGNATURE.read_text(encoding="utf-8").rstrip(), self._matrix())

    def test_real_python_snapshot_helper_is_deterministic(self) -> None:
        self.assertEqual(self._matrix(), self._matrix())


if __name__ == "__main__":
    unittest.main()
