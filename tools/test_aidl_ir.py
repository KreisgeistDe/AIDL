from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.aidl_cli import main
from tools.compiler_diagnostics import load_compiler_analysis
from tools.compiler_ir import build_canonical_ir
from tools.ir_canonical_json import canonical_ir_json_text


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "spec" / "ir.schema.json").read_text(encoding="utf-8"))


_MINIMAL_PROJECT = """module demo

app Demo {
  profile core version 1
  profile distributed version 1
  profile cloud version 1
  system DemoSystem
  api DemoApi
  defaultDeployment local
}

auth {
  provider oidc
  subject claim \"sub\"
  roles [user]
  scopes [pets.read]
  serviceIdentities required
}

export enum Species { dog, cat }

export entity Pet {
  id: uuid primary generated immutable
  name: string(1..80) required mutable
  species: Species required immutable
}

export query getPet(id: Pet.id) -> Pet? {
  auth: authenticated
  read: Pet.byId(id)
  consistency: strong
  errors: []
  timeout: 2s
}

export api DemoApi {
  transport rest
  version 1
  operations [query getPet]
  auth inherit
  errors problemDetails
  compatibility backward
}

export resource Db sql {
  consistency strong
  transactions [readCommitted]
  migrations expandBackfillContract
  encryption required
}

export service DemoService {
  owns [Pet]
  uses [Db]
  exposes [query getPet]
  runs []
}

export system DemoSystem {
  services [DemoService]
  resources [Db]
  apis [DemoApi]
}

export deployment local for DemoSystem {
  environment test
  target process
  colocate services all
  bind Db memory
}
"""


class AidlIrTest(unittest.TestCase):
    def _write_project(self, root: Path, text: str = _MINIMAL_PROJECT) -> Path:
        path = root / "app.aidl"
        path.write_text(text, encoding="utf-8")
        return path

    def _assert_schema_valid(self, document: dict) -> None:
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        errors = sorted(
            validator.iter_errors(document),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        self.assertEqual([], errors, "\n".join(error.message for error in errors))

    def test_source_to_ir_is_schema_valid_deterministic_and_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            first = build_canonical_ir(load_compiler_analysis([source]))
            second = build_canonical_ir(load_compiler_analysis([source]))

        self.assertEqual(first, second)
        self._assert_schema_valid(first)
        self.assertEqual("0.3.0", first["irVersion"])
        self.assertNotEqual("sha256:" + "0" * 64, first["semanticHash"])
        self.assertTrue(first["sourceMap"]["entries"])
        self.assertEqual({}, first["profileExtensions"])

        pet = next(item for item in first["declarations"] if item["name"] == "Pet")
        self.assertNotEqual("sha256:" + "0" * 64, pet["semanticHash"])
        name_field = next(field for field in pet["fields"] if field["name"] == "name")
        self.assertFalse(name_field["primary"])
        self.assertFalse(name_field["concurrencyToken"])
        self.assertEqual("none", name_field["onDelete"])

        text = canonical_ir_json_text(first)
        self.assertTrue(text.endswith("\n"))
        self.assertFalse(text.endswith("\n\n"))

    def test_ir_cli_emits_only_canonical_json_on_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory))
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["ir", str(source)])

        self.assertEqual(0, exit_code)
        self.assertEqual("", stderr.getvalue())
        document = json.loads(stdout.getvalue())
        self._assert_schema_valid(document)
        self.assertEqual(stdout.getvalue(), canonical_ir_json_text(document))

    def test_ir_cli_rejects_compiler_diagnostics_without_ir_stdout(self) -> None:
        invalid = _MINIMAL_PROJECT.replace("module demo\n", "module demo\nimport missing.Type\n", 1)
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_project(Path(directory), invalid)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["ir", str(source)])

        self.assertEqual(1, exit_code)
        self.assertEqual("", stdout.getvalue())
        self.assertIn("AIDL-R001", stderr.getvalue())
        self.assertIn("unresolved import", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
