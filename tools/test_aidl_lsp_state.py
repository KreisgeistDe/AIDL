from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.aidl_lsp import AidlLspAdapter, AidlLspServer, offset_to_lsp_position, path_to_file_uri


class AidlLspStateTest(unittest.TestCase):
    def _write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.write_text(text, encoding="utf-8")
        return path

    def _definition_request(self, request_id: int, uri: str, line: int, character: int, work_done=None) -> dict:
        params = {"textDocument": {"uri": uri}, "position": {"line": line, "character": character}}
        if work_done is not None:
            params["workDoneToken"] = work_done
        return {"jsonrpc": "2.0", "id": request_id, "method": "textDocument/definition", "params": params}

    def test_watched_file_change_invalidates_and_republishes_open_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Item {}\n")
            uri = path_to_file_uri(source)
            server = AidlLspServer(root)
            server.handle({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {"uri": uri, "text": source.read_text(encoding="utf-8")}}})
            server.handle({"jsonrpc": "2.0", "method": "textDocument/didSave", "params": {"textDocument": {"uri": uri}}})
            source.write_text("module app\nentity Item {}\nentity Item {}\n", encoding="utf-8")
            responses = server.handle({
                "jsonrpc": "2.0",
                "method": "workspace/didChangeWatchedFiles",
                "params": {"changes": [{"uri": uri, "type": 2}]},
            })
            self.assertEqual(1, len(responses))
            diagnostics = responses[0]["params"]["diagnostics"]
            self.assertTrue(any(item["code"] == "AIDL-R002" for item in diagnostics))

    def test_pre_cancelled_request_returns_no_partial_definition_and_closes_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Item {}\n")
            uri = path_to_file_uri(source)
            server = AidlLspServer(root)
            server.handle({"jsonrpc": "2.0", "method": "$/cancelRequest", "params": {"id": 7}})
            responses = server.handle(self._definition_request(7, uri, 1, 7, work_done="work-7"))
            self.assertEqual("begin", responses[0]["params"]["value"]["kind"])
            self.assertEqual(-32800, responses[1]["error"]["code"])
            self.assertNotIn("result", responses[1])
            self.assertEqual("end", responses[2]["params"]["value"]["kind"])
            self.assertEqual("cancelled", responses[2]["params"]["value"]["message"])
            self.assertEqual(0, server.adapter.state.stats.builds)

    def test_definition_progress_is_balanced_and_cache_is_reused_under_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nimport lib.Item\nentity Uses { value: Item }\n")
            target = self._write(root, "lib.aidl", "module lib\nexport entity Item {}\n")
            text = source.read_text(encoding="utf-8")
            offset = text.index("Item", text.index("value:"))
            position = offset_to_lsp_position(text, offset)
            uri = path_to_file_uri(source)
            server = AidlLspServer(root)
            first = server.handle(self._definition_request(1, uri, position["line"], position["character"], work_done="work-1"))
            self.assertEqual(["begin", None, "end"], [first[0]["params"]["value"]["kind"], first[1].get("method"), first[2]["params"]["value"]["kind"]])
            self.assertEqual(path_to_file_uri(target), first[1]["result"]["uri"])
            for request_id in range(2, 34):
                response = server.handle(self._definition_request(request_id, uri, position["line"], position["character"]))
                self.assertEqual(path_to_file_uri(target), response[0]["result"]["uri"])
            self.assertEqual(1, server.adapter.state.stats.builds)
            self.assertEqual(32, server.adapter.state.stats.hits)

    def test_shutdown_rejects_new_requests_and_restart_starts_with_empty_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self._write(root, "app.aidl", "module app\nentity Item {}\n")
            uri = path_to_file_uri(source)
            server = AidlLspServer(root)
            self.assertEqual(0, server.adapter.state.stats.builds)
            shutdown = server.handle({"jsonrpc": "2.0", "id": 1, "method": "shutdown", "params": {}})
            self.assertIn("result", shutdown[0])
            rejected = server.handle(self._definition_request(2, uri, 1, 7))
            self.assertEqual(-32600, rejected[0]["error"]["code"])
            restarted = AidlLspServer(root)
            self.assertEqual(0, restarted.adapter.state.stats.builds)
            self.assertIsNotNone(restarted.adapter.snapshot(source))
            self.assertEqual(1, restarted.adapter.state.stats.builds)


if __name__ == "__main__":
    unittest.main()
