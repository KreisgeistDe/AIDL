import unittest
from pathlib import Path

from tools.aidl_parser import parse_text


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"


def oracle_signature(source: str) -> str:
    program, diagnostics, _tokens = parse_text(source)
    if diagnostics:
        raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
    module = ""
    imports: list[str] = []
    declarations: list[str] = []
    for child in program.children:
        if child.kind == "module":
            module = child.name or ""
        elif child.kind == "import":
            imports.append(child.name or "")
        else:
            declarations.append(
                f"{child.kind}:{child.name or ''}:{str(bool(child.attrs.get('exported'))).lower()}"
            )
    return (
        f"module={module}\n"
        f"imports={','.join(imports)}\n"
        f"declarations={','.join(declarations)}"
    )


class KotlinParserProjectionParityTest(unittest.TestCase):
    def test_shared_fixtures_are_pinned_to_python_oracle(self) -> None:
        cases = sorted(PARITY.glob("*.source"))
        self.assertEqual([path.stem for path in cases], ["canonical-data", "legacy-data"])
        for source_path in cases:
            with self.subTest(case=source_path.stem):
                expected_path = source_path.with_suffix(".signature")
                expected = expected_path.read_text(encoding="utf-8").rstrip("\n")
                actual = oracle_signature(source_path.read_text(encoding="utf-8"))
                self.assertEqual(expected, actual)

    def test_fixture_signatures_are_deterministic(self) -> None:
        for source_path in sorted(PARITY.glob("*.source")):
            source = source_path.read_text(encoding="utf-8")
            self.assertEqual(oracle_signature(source), oracle_signature(source))


if __name__ == "__main__":
    unittest.main()
