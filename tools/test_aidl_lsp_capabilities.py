from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.aidl_lsp import AidlLspAdapter, AidlLspServer, offset_to_lsp_position, path_to_file_uri


class AidlLspCapabilitiesTest(unittest.TestCase):
    def _write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_initialize_advertises_compiler_backed_semantic_methods(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            response = AidlLspServer(Path(directory)).handle(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
            )[0]["result"]["capabilities"]
            self.assertIn("completionProvider", response)
            self.assertTrue(response["hoverProvider"])
            self.assertTrue(response["referencesProvider"])
            self.assertEqual({"prepareProvider": True}, response["renameProvider"])
            self.assertTrue(response["codeActionProvider"])

    def test_completion_and_hover_use_unsaved_snapshot_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nimport lib.Shared\nentity Uses {\n  value: Sha\n}\n",
            )
            self._write(root, "lib.aidl", "module lib\nexport entity Shared {}\n")
            uri = path_to_file_uri(source)
            adapter = AidlLspAdapter(root)
            unsaved = source.read_text(encoding="utf-8").replace("value: Sha", "value: Shared")
            adapter.set_override(uri, unsaved)

            completion_offset = unsaved.index("Shared", unsaved.index("value:")) + 3
            completion_position = offset_to_lsp_position(unsaved, completion_offset)
            completion = adapter.completion(uri, completion_position["line"], completion_position["character"])
            self.assertTrue(any(item["insertText"] == "Shared" for item in completion))

            hover_offset = unsaved.index("Shared", unsaved.index("value:"))
            hover_position = offset_to_lsp_position(unsaved, hover_offset)
            hover = adapter.hover(uri, hover_position["line"], hover_position["character"])
            self.assertIsNotNone(hover)
            assert hover is not None
            self.assertIn("lib.Shared", hover["contents"]["value"])

    def test_references_and_rename_are_snapshot_owned_and_root_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            left = base / "left"
            right = base / "right"
            left.mkdir()
            right.mkdir()
            target = self._write(left, "lib.aidl", "module lib\nexport enum Shared { one }\n")
            source = self._write(
                left,
                "app.aidl",
                "module app\nimport lib.Shared\nexport value Uses {\n  first: Shared required\n  second: Shared required\n}\n",
            )
            self._write(right, "other.aidl", "module other\nexport enum Shared { two }\n")
            adapter = AidlLspAdapter([left, right])
            uri = path_to_file_uri(source)
            text = source.read_text(encoding="utf-8")
            offset = text.index("Shared", text.index("first:"))
            position = offset_to_lsp_position(text, offset)

            references = adapter.references(uri, position["line"], position["character"])
            self.assertEqual(3, len(references))
            self.assertTrue(all(item["uri"] == uri for item in references))

            edit = adapter.rename(uri, position["line"], position["character"], "Renamed")
            self.assertIsNotNone(edit)
            assert edit is not None
            self.assertIn(path_to_file_uri(target), edit["changes"])
            self.assertIn(uri, edit["changes"])
            self.assertNotIn(path_to_file_uri(right / "other.aidl"), edit["changes"])

    def test_rename_collision_is_rejected_without_workspace_edit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nexport enum First { one }\nexport enum Existing { two }\nexport value Uses {\n  value: First required\n}\n",
            )
            uri = path_to_file_uri(source)
            text = source.read_text(encoding="utf-8")
            offset = text.index("First", text.index("value:"))
            position = offset_to_lsp_position(text, offset)
            with self.assertRaises(ValueError):
                AidlLspAdapter(root).rename(uri, position["line"], position["character"], "Existing")

    def test_unresolved_positions_do_not_synthesize_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nentity Uses {\n  value: Missing\n}\n",
            )
            uri = path_to_file_uri(source)
            text = source.read_text(encoding="utf-8")
            offset = text.index("Missing")
            position = offset_to_lsp_position(text, offset)
            adapter = AidlLspAdapter(root)
            self.assertEqual([], adapter.references(uri, position["line"], position["character"]))
            self.assertIsNone(adapter.hover(uri, position["line"], position["character"]))
            self.assertIsNone(adapter.prepare_rename(uri, position["line"], position["character"]))

    def test_code_actions_emit_only_compiler_authorized_allowed_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "consumer.aidl",
                "module example.orders\nconsumer StartReview {\n  start: workflow ReviewOrder(event.id)\n}\n",
            )
            uri = path_to_file_uri(source)
            adapter = AidlLspAdapter(root)
            diagnostics = adapter.diagnostics(uri)
            authorized = {
                fix["text"]
                for item in diagnostics
                for fix in item["data"].get("allowedFixes", [])
                if fix.get("kind") == "insertClause"
            }
            actions = adapter.code_actions(uri)
            self.assertTrue(actions)
            self.assertTrue(all(action["title"] in authorized for action in actions))
            self.assertTrue(all(action["kind"] == "quickfix" for action in actions))


if __name__ == "__main__":
    unittest.main()
