from pathlib import Path
import re
import unittest

from tools.aidl_parser import parse_text
from tools.compiler_ast import compiler_document_from_ast
from tools.compiler_project import compiler_project_from_documents
from tools.compiler_resolution import _reference_candidates
from tools.compiler_typecheck import TypeSyntaxError, parse_type


ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "compiler" / "kotlin" / "parity"
SOURCE_IDS = ["resolution-consumer", "resolution-provider-a", "resolution-provider-b"]
CASES = [
    ("string", "string"),
    ("[uuid]?", "[uuid]?"),
    ("string(1..80)?", "string(1..80)?"),
    ("Public?", "Public?"),
    ("demo.shared.Public", "demo.shared.Public"),
    ("Local", "Local"),
    ("Duplicate", "Duplicate"),
    ("Missing", "Missing"),
    ("<blank>", ""),
    ("string??", "string??"),
    ("[string", "[string"),
    ("string]", "string]"),
    ("List<string>", "List<string>"),
    ("string(min:1)", "string(min:1)"),
    ("string(1..x)", "string(1..x)"),
    ("string(1..2..3)", "string(1..2..3)"),
]
BUILTINS = {
    "bool", "bytes", "date", "datetime", "decimal", "duration", "email", "float",
    "int", "json", "long", "revision", "string", "time", "url", "uuid",
}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
NUMBER = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")


def _project():
    documents = []
    for source_id in SOURCE_IDS:
        source_path = PARITY / f"{source_id}.source"
        program, diagnostics, _tokens = parse_text(source_path.read_text(encoding="utf-8"))
        if diagnostics:
            raise AssertionError([diagnostic.to_json() for diagnostic in diagnostics])
        documents.append(compiler_document_from_ast(Path(f"{source_id}.source"), program))
    return compiler_project_from_documents(documents)


def _identity(candidate) -> str:
    document = candidate.document
    index = document.declarations.index(candidate.declaration)
    return f"{candidate.fully_qualified_name}@{document.source_path.stem}#{index}"


def _bounded_shape(source: str) -> tuple[str, str | None]:
    text = source.strip()
    if not text or "<" in text or ">" in text:
        raise TypeSyntaxError("outside bounded TypeConstruction slice")
    nullable = text.endswith("?")
    if nullable:
        text = text[:-1].rstrip()
    if text.endswith("?"):
        raise TypeSyntaxError("duplicate optional marker")
    suffix = "?" if nullable else ""
    if text.startswith("["):
        if not text.endswith("]") or not text[1:-1].strip():
            raise TypeSyntaxError("invalid list shape")
        nested_signature, nested_name = _bounded_shape(text[1:-1])
        if nested_signature.endswith("?"):
            # Nested optionality is preserved exactly by the bounded Kotlin shape.
            pass
        parse_type(f"[{nested_signature}]")
        return f"[{nested_signature}]{suffix}", nested_name
    if "[" in text or "]" in text:
        raise TypeSyntaxError("invalid list shape")
    open_index = text.find("(")
    range_suffix = ""
    if open_index >= 0:
        if not text.endswith(")"):
            raise TypeSyntaxError("unterminated range")
        payload = text[open_index + 1:-1].strip()
        parts = payload.split("..")
        if len(parts) != 2 or any(not NUMBER.fullmatch(part.strip()) for part in parts):
            raise TypeSyntaxError("only structured min..max range is in the bounded slice")
        base = text[:open_index].rstrip()
        range_suffix = f"({parts[0].strip()}..{parts[1].strip()})"
    else:
        if any(ch in text for ch in "(),:"):
            raise TypeSyntaxError("non-range constraint outside bounded slice")
        base = text
    if not IDENTIFIER.fullmatch(base):
        raise TypeSyntaxError("invalid type name")
    # Require the current Python compiler to accept the corresponding Core type expression.
    parse_type(f"{base}{range_suffix}{suffix}")
    return f"{base}{range_suffix}{suffix}", base


def oracle_signature() -> str:
    project = _project()
    consumer = project.documents[0]
    lines = []
    for label, source in CASES:
        try:
            signature, base_name = _bounded_shape(source)
        except TypeSyntaxError:
            lines.append(f"{label}|REJECT|||")
            continue
        status = "RESOLVED"
        symbols = []
        if base_name and base_name not in BUILTINS:
            candidates = _reference_candidates(project, consumer, base_name)
            status = "UNRESOLVED" if not candidates else "RESOLVED" if len(candidates) == 1 else "AMBIGUOUS"
            symbols = [_identity(candidate) for candidate in candidates]
        lines.append(f"{label}|ACCEPT|{signature}|{status}|{','.join(symbols)}")
    return "\n".join(lines)


class KotlinTypeConstructionParityTest(unittest.TestCase):
    def test_pinned_signature_matches_current_python_core_oracle(self) -> None:
        expected = (PARITY / "type-construction.signature").read_text(encoding="utf-8").rstrip("\n")
        self.assertEqual(expected, oracle_signature())

    def test_type_construction_signature_is_deterministic(self) -> None:
        self.assertEqual(oracle_signature(), oracle_signature())


if __name__ == "__main__":
    unittest.main()
