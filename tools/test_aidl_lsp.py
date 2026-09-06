from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from tools.aidl_lsp import (
    AidlLspAdapter,
    AidlLspServer,
    LspProtocolError,
    file_uri_to_path,
    lsp_position_to_offset,
    offset_to_lsp_position,
    path_to_file_uri,
    read_message,
    run_stdio,
    write_message,
)


class AidlLspTest(unittest.TestCase):
    def _write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _framed(self, *payloads: dict) -> io.BytesIO:
        stream = io.BytesIO()
        for payload in payloads:
            write_message(stream, payload)
        stream.seek(0)
        return stream

    def test_file_uri_and_utf16_position_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "space name.aidl"
            uri = path_to_file_uri(path)
            self.assertEqual(path.resolve(), file_uri_to_path(uri))

        text = "module app\nentity Café {\n  label: 😀Thing\n}\n"
        offset = text.index("Thing")
        position = offset_to_lsp_position(text, offset)
        self.assertEqual(offset, lsp_position_to_offset(text, position["line"], position["character"]))
        emoji_offset = text.index("😀") + 1
        with self.assertRaises(LspProtocolError):
            lsp_position_to_offset(text, 2, offset_to_lsp_position(text, emoji_offset)["character"] - 1)

    def test_lsp_content_length_framing(self) -> None:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        stream = io.BytesIO()
        write_message(stream, payload)
        stream.seek(0)
        self.assertEqual(payload, read_message(stream))

    def test_diagnostics_reuse_compiler_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nentity Shared {\n}\nentity Shared {\n}\n",
            )
            diagnostics = AidlLspAdapter(root).diagnostics(path_to_file_uri(source))
            duplicate = next(item for item in diagnostics if item["code"] == "AIDL-R002")
            self.assertEqual("aidl", duplicate["source"])
            self.assertEqual("AIDL-R002", duplicate["data"]["code"])
            self.assertEqual(duplicate["message"], duplicate["data"]["message"])
            self.assertIn("phase", duplicate["data"])
            self.assertIn("severity", duplicate["data"])
            self.assertEqual(duplicate["range"]["start"], duplicate["range"]["end"])

    def test_definition_reuses_compiler_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nimport lib.Shared\nentity Uses {\n  value: Shared\n}\n",
            )
            target = self._write(root, "lib.aidl", "module lib\nexport entity Shared {\n}\n")
            text = source.read_text(encoding="utf-8")
            offset = text.index("Shared", text.index("value:"))
            position = offset_to_lsp_position(text, offset)
            result = AidlLspAdapter(root).definition(
                path_to_file_uri(source),
                position["line"],
                position["character"],
            )
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(path_to_file_uri(target), result["uri"])
            target_text = target.read_text(encoding="utf-8")
            expected = offset_to_lsp_position(target_text, target_text.index("Shared"))
            self.assertEqual(expected, result["range"]["start"])

    def test_unsaved_override_controls_diagnostics_and_definition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(
                root,
                "app.aidl",
                "module app\nimport lib.Old\nimport lib.New\nentity Uses {\n  value: Old\n}\n",
            )
            target = self._write(
                root,
                "lib.aidl",
                "module lib\nexport entity Old {}\nexport entity New {}\n",
            )
            uri = path_to_file_uri(source)
            adapter = AidlLspAdapter(root)
            unsaved = source.read_text(encoding="utf-8").replace("value: Old", "value: New")
            adapter.set_override(uri, unsaved)
            offset = unsaved.index("New", unsaved.index("value:"))
            position = offset_to_lsp_position(unsaved, offset)
            definition = adapter.definition(uri, position["line"], position["character"])
            self.assertIsNotNone(definition)
            assert definition is not None
            self.assertEqual(path_to_file_uri(target), definition["uri"])

            duplicate = unsaved + "entity Uses {}\n"
            adapter.set_override(uri, duplicate)
            self.assertTrue(any(item["code"] == "AIDL-R002" for item in adapter.diagnostics(uri)))
            self.assertNotIn("entity Uses {}\n", source.read_text(encoding="utf-8"))

    def test_multi_root_definition_cannot_resolve_across_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            left = base / "left"
            right = base / "right"
            left.mkdir()
            right.mkdir()
            source = self._write(
                left,
                "app.aidl",
                "module app\nimport shared.Target\nentity Uses {\n  value: Target\n}\n",
            )
            self._write(right, "shared.aidl", "module shared\nexport entity Target {}\n")
            text = source.read_text(encoding="utf-8")
            offset = text.index("Target", text.index("value:"))
            position = offset_to_lsp_position(text, offset)
            adapter = AidlLspAdapter([right, left])
            self.assertIsNone(
                adapter.definition(path_to_file_uri(source), position["line"], position["character"])
            )
            self.assertTrue(
                any(item["code"] == "AIDL-R001" for item in adapter.diagnostics(path_to_file_uri(source)))
            )

    def test_unsaved_new_file_is_admitted_only_to_owning_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            left = base / "left"
            right = base / "right"
            left.mkdir()
            right.mkdir()
            self._write(right, "target.aidl", "module right\nexport entity Target {}\n")
            unsaved = left / "new.aidl"
            text = "module left\nimport right.Target\nentity Uses {\n  value: Target\n}\n"
            adapter = AidlLspAdapter([left, right])
            uri = path_to_file_uri(unsaved)
            adapter.set_override(uri, text)
            diagnostics = adapter.diagnostics(uri)
            self.assertTrue(any(item["code"] == "AIDL-R001" for item in diagnostics))
            self.assertFalse(unsaved.exists())

    def test_unresolved_and_foreign_definitions_return_null_without_guess(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as foreign_directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Uses {\n  value: Missing\n}\n")
            text = source.read_text(encoding="utf-8")
            offset = text.index("Missing")
            position = offset_to_lsp_position(text, offset)
            adapter = AidlLspAdapter(root)
            self.assertIsNone(
                adapter.definition(path_to_file_uri(source), position["line"], position["character"])
            )
            foreign = self._write(Path(foreign_directory), "foreign.aidl", "module foreign\nentity Hidden {}\n")
            self.assertIsNone(adapter.definition(path_to_file_uri(foreign), 1, 7))

    def test_server_advertises_full_sync_and_publishes_unsaved_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Shared {\n}\n")
            uri = path_to_file_uri(source)
            server = AidlLspServer(root)
            initialized = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            capabilities = initialized[0]["result"]["capabilities"]
            self.assertEqual(
                {
                    "textDocumentSync": {
                        "openClose": True,
                        "change": 1,
                        "save": {"includeText": False},
                    },
                    "definitionProvider": True,
                    "completionProvider": {},
                    "hoverProvider": True,
                    "referencesProvider": True,
                    "renameProvider": {"prepareProvider": True},
                    "codeActionProvider": True,
                    "workspace": {
                        "workspaceFolders": {"supported": False, "changeNotifications": False}
                    },
                },
                capabilities,
            )

            opened = server.handle({
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": {"uri": uri, "text": source.read_text(encoding="utf-8")}},
            })
            self.assertFalse(any(item["code"] == "AIDL-R002" for item in opened[0]["params"]["diagnostics"]))

            unsaved = source.read_text(encoding="utf-8") + "entity Shared {\n}\n"
            changed = server.handle({
                "jsonrpc": "2.0",
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": uri},
                    "contentChanges": [{"text": unsaved}],
                },
            })
            self.assertTrue(any(item["code"] == "AIDL-R002" for item in changed[0]["params"]["diagnostics"]))

            saved = server.handle({
                "jsonrpc": "2.0",
                "method": "textDocument/didSave",
                "params": {"textDocument": {"uri": uri}},
            })
            self.assertFalse(any(item["code"] == "AIDL-R002" for item in saved[0]["params"]["diagnostics"]))

            closed = server.handle({
                "jsonrpc": "2.0",
                "method": "textDocument/didClose",
                "params": {"textDocument": {"uri": uri}},
            })
            self.assertEqual([], closed[0]["params"]["diagnostics"])

    def test_shutdown_exit_sequence_controls_process_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = io.BytesIO()
            clean_input = self._framed(
                {"jsonrpc": "2.0", "id": 1, "method": "shutdown", "params": {}},
                {"jsonrpc": "2.0", "method": "exit", "params": {}},
            )
            self.assertEqual(0, run_stdio(root, clean_input, output))
            unclean_input = self._framed({"jsonrpc": "2.0", "method": "exit", "params": {}})
            self.assertEqual(1, run_stdio(root, unclean_input, io.BytesIO()))

    def test_unsupported_request_returns_method_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            response = AidlLspServer(Path(directory)).handle(
                {"jsonrpc": "2.0", "id": 9, "method": "textDocument/formatting", "params": {}}
            )
            self.assertEqual(-32601, response[0]["error"]["code"])


if __name__ == "__main__":
    unittest.main()
