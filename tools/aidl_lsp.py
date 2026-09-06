"""Thin LSP adapter over compiler-owned incremental workspace analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from tools.compiler_incremental import CancellationToken, CompilerCancelled, IncrementalCompilerState
from tools.compiler_snapshot import CompilerSnapshot
from tools.compiler_snapshot_editing import (
    authorized_snapshot_fixes,
    find_snapshot_usages,
    plan_snapshot_rename,
)
from tools.compiler_workspace import CompilerWorkspace, create_compiler_workspace

JSONRPC_VERSION = "2.0"
REQUEST_CANCELLED = -32800


class LspProtocolError(ValueError):
    pass


def file_uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file" or parsed.params or parsed.query or parsed.fragment:
        raise LspProtocolError("only plain file:// URIs are supported")
    if parsed.netloc not in {"", "localhost"}:
        raise LspProtocolError("remote file URI authorities are unsupported")
    return Path(url2pathname(unquote(parsed.path))).absolute().resolve(strict=False)


def path_to_file_uri(path: Path) -> str:
    return path.absolute().resolve(strict=False).as_uri()


def lsp_position_to_offset(text: str, line: int, character: int) -> int:
    if line < 0 or character < 0:
        raise LspProtocolError("negative LSP position")
    lines = text.splitlines(keepends=True)
    if line >= len(lines):
        if line == len(lines) and text.endswith(("\n", "\r")) and character == 0:
            return len(text)
        raise LspProtocolError("LSP line is outside the document")
    content = lines[line].rstrip("\r\n")
    line_start = sum(len(item) for item in lines[:line])
    units = 0
    for index, char in enumerate(content):
        if units == character:
            return line_start + index
        units += len(char.encode("utf-16-le")) // 2
        if units > character:
            raise LspProtocolError("LSP character splits a UTF-16 surrogate pair")
    if units == character:
        return line_start + len(content)
    raise LspProtocolError("LSP character is outside the line")


def offset_to_lsp_position(text: str, offset: int) -> dict[str, int]:
    if offset < 0 or offset > len(text):
        raise LspProtocolError("source offset is outside the document")
    prefix = text[:offset]
    line = prefix.count("\n")
    line_start = prefix.rfind("\n") + 1
    segment = text[line_start:offset]
    return {"line": line, "character": len(segment.encode("utf-16-le")) // 2}


def _range(text: str, offset: int, length: int = 0) -> dict[str, Any]:
    start = offset_to_lsp_position(text, offset)
    end = offset_to_lsp_position(text, offset + length)
    return {"start": start, "end": end}


def _diagnostic_to_lsp(diagnostic, text: str) -> dict[str, Any]:
    severity = {"error": 1, "warning": 2, "info": 3}.get(diagnostic.severity.value)
    payload: dict[str, Any] = {
        "range": _range(text, diagnostic.location.offset),
        "code": diagnostic.code.value,
        "source": "aidl",
        "message": diagnostic.message,
        "data": diagnostic.to_json(),
    }
    if severity is not None:
        payload["severity"] = severity
    return payload


def _root_tuple(project_paths: Path | Iterable[Path]) -> tuple[Path, ...]:
    return (project_paths,) if isinstance(project_paths, Path) else tuple(project_paths)


class AidlLspAdapter:
    def __init__(self, project_paths: Path | Iterable[Path]):
        roots = tuple(path.absolute().resolve(strict=False) for path in _root_tuple(project_paths))
        self.state = IncrementalCompilerState(roots)
        self.project_paths = self.state.roots

    def set_override(self, uri: str, text: str) -> None:
        self.state.set_override(file_uri_to_path(uri), text)

    def clear_override(self, uri: str) -> None:
        self.state.clear_override(file_uri_to_path(uri))

    def watched_files_changed(self, uris: Iterable[str]) -> tuple[Path, ...]:
        return self.state.invalidate_paths(file_uri_to_path(uri) for uri in uris)

    def workspace(self) -> CompilerWorkspace:
        return create_compiler_workspace(self.project_paths, self.state.overrides)

    def snapshot(self, source_path: Path | None = None, token: CancellationToken | None = None) -> CompilerSnapshot:
        if source_path is not None:
            snapshot = self.state.snapshot_for(source_path, token)
            if snapshot is None:
                raise ValueError(f"source is not owned by workspace: {source_path}")
            return snapshot
        if len(self.project_paths) != 1:
            raise ValueError("source path is required for a multi-root workspace")
        return self.state.snapshot_for_root(self.project_paths[0], token)

    def _snapshot_and_offset(self, uri: str, line: int, character: int, token: CancellationToken | None = None):
        source_path = file_uri_to_path(uri)
        snapshot = self.state.snapshot_for(source_path, token)
        if snapshot is None:
            return source_path, None, None, None
        text = snapshot.text(source_path)
        offset = lsp_position_to_offset(text, line, character)
        if token is not None:
            token.check()
        return source_path, snapshot, text, offset

    def diagnostics(self, uri: str, token: CancellationToken | None = None) -> list[dict[str, Any]]:
        source_path = file_uri_to_path(uri)
        snapshot = self.state.snapshot_for(source_path, token)
        if snapshot is None:
            return []
        try:
            text = snapshot.text(source_path)
        except ValueError:
            return []
        if token is not None:
            token.check()
        return [_diagnostic_to_lsp(item, text) for item in snapshot.diagnostics(source_path)]

    def definition(self, uri: str, line: int, character: int, token: CancellationToken | None = None):
        source_path, snapshot, _text, offset = self._snapshot_and_offset(uri, line, character, token)
        if snapshot is None:
            return None
        resolution = snapshot.resolve(source_path, offset)
        if token is not None:
            token.check()
        if resolution.status != "resolved" or resolution.target is None:
            return None
        target = resolution.target
        target_text = snapshot.text(target.source_path)
        return {"uri": path_to_file_uri(target.source_path), "range": _range(target_text, target.location.offset)}

    def completion(self, uri: str, line: int, character: int, token: CancellationToken | None = None):
        source_path, snapshot, _text, offset = self._snapshot_and_offset(uri, line, character, token)
        if snapshot is None:
            return []
        result = snapshot.complete(source_path, offset)
        if token is not None:
            token.check()
        if result.status != "resolved":
            return []
        return [
            {
                "label": candidate.display_text,
                "insertText": candidate.insert_text,
                "detail": candidate.fully_qualified_name,
                "data": candidate.to_json(),
            }
            for candidate in result.candidates
        ]

    def hover(self, uri: str, line: int, character: int, token: CancellationToken | None = None):
        source_path, snapshot, _text, offset = self._snapshot_and_offset(uri, line, character, token)
        if snapshot is None:
            return None
        result = snapshot.document(source_path, offset)
        if token is not None:
            token.check()
        if result.status != "resolved":
            return None
        parts: list[str] = []
        if result.declaration is not None:
            parts.append(f"`{result.declaration.representation}`\n\n{result.declaration.fully_qualified_name}")
        for diagnostic in result.diagnostics:
            parts.append(f"**{diagnostic.code.value}** {diagnostic.message}")
        if not parts:
            return None
        return {"contents": {"kind": "markdown", "value": "\n\n".join(parts)}}

    def references(self, uri: str, line: int, character: int, token: CancellationToken | None = None):
        source_path, snapshot, _text, offset = self._snapshot_and_offset(uri, line, character, token)
        if snapshot is None:
            return []
        result = find_snapshot_usages(snapshot, source_path, offset)
        if token is not None:
            token.check()
        if result.status != "resolved":
            return []
        locations = []
        for usage in result.usages:
            text = snapshot.text(usage.source_path)
            locations.append({"uri": path_to_file_uri(usage.source_path), "range": _range(text, usage.location.offset, usage.length)})
        return locations

    def prepare_rename(self, uri: str, line: int, character: int, token: CancellationToken | None = None):
        source_path, snapshot, text, offset = self._snapshot_and_offset(uri, line, character, token)
        if snapshot is None:
            return None
        resolution = snapshot.resolve(source_path, offset)
        if resolution.status != "resolved" or resolution.target is None:
            return None
        old_name = resolution.target.fully_qualified_name.rsplit(".", 1)[-1]
        token_start = text.rfind(old_name, 0, offset + len(old_name) + 1)
        if token_start < 0 or not (token_start <= offset <= token_start + len(old_name)):
            return None
        return {"range": _range(text, token_start, len(old_name)), "placeholder": old_name}

    def rename(self, uri: str, line: int, character: int, new_name: str, token: CancellationToken | None = None):
        source_path, snapshot, _text, offset = self._snapshot_and_offset(uri, line, character, token)
        if snapshot is None:
            return None
        result = plan_snapshot_rename(snapshot, source_path, offset, new_name)
        if token is not None:
            token.check()
        if result.status != "ready":
            raise LspProtocolError(result.message or f"rename unavailable: {result.status}")
        changes: dict[str, list[dict[str, Any]]] = {}
        for edit in result.edits:
            text = snapshot.text(edit.source_path)
            changes.setdefault(path_to_file_uri(edit.source_path), []).append(
                {"range": _range(text, edit.offset, edit.length), "newText": edit.replacement}
            )
        return {"changes": changes}

    def code_actions(self, uri: str, diagnostic_codes: Iterable[str] | None = None, token: CancellationToken | None = None):
        source_path = file_uri_to_path(uri)
        snapshot = self.state.snapshot_for(source_path, token)
        if snapshot is None:
            return []
        fixes = authorized_snapshot_fixes(snapshot, source_path, diagnostic_codes=diagnostic_codes)
        if token is not None:
            token.check()
        actions = []
        for fix in fixes:
            text = snapshot.text(fix.edit.source_path)
            actions.append(
                {
                    "title": fix.title,
                    "kind": "quickfix",
                    "diagnostics": [{"code": fix.diagnostic_code}],
                    "edit": {
                        "changes": {
                            path_to_file_uri(fix.edit.source_path): [
                                {"range": _range(text, fix.edit.offset, fix.edit.length), "newText": fix.edit.replacement}
                            ]
                        }
                    },
                }
            )
        return actions


class AidlLspServer:
    def __init__(self, project_paths: Path | Iterable[Path]):
        self.adapter = AidlLspAdapter(project_paths)
        self.shutdown_requested = False
        self._active_requests: dict[Any, CancellationToken] = {}
        self._pre_cancelled: set[Any] = set()
        self._open_uris: set[str] = set()

    def _publish_diagnostics(self, uri: str, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": diagnostics}}

    def _progress(self, token: Any, kind: str, message: str) -> dict[str, Any]:
        value: dict[str, Any] = {"kind": kind}
        if kind == "begin":
            value["title"] = message
            value["cancellable"] = True
        else:
            value["message"] = message
        return {"jsonrpc": JSONRPC_VERSION, "method": "$/progress", "params": {"token": token, "value": value}}

    def _request_token(self, request_id: Any) -> CancellationToken:
        token = CancellationToken()
        if request_id in self._pre_cancelled:
            self._pre_cancelled.remove(request_id)
            token.cancel()
        self._active_requests[request_id] = token
        return token

    def cancel_request(self, request_id: Any) -> None:
        token = self._active_requests.get(request_id)
        if token is not None:
            token.cancel()
        else:
            self._pre_cancelled.add(request_id)

    def _semantic_request(self, request_id: Any, params: dict[str, Any], title: str, callback: Callable[[CancellationToken], Any]):
        token = self._request_token(request_id)
        work_done = params.get("workDoneToken")
        responses: list[dict[str, Any]] = []
        if work_done is not None:
            responses.append(self._progress(work_done, "begin", title))
        try:
            result = callback(token)
            responses.append(self._result(request_id, result))
            if work_done is not None:
                responses.append(self._progress(work_done, "end", "complete"))
            return responses
        except CompilerCancelled:
            responses.append(self._error(request_id, REQUEST_CANCELLED, "request cancelled"))
            if work_done is not None:
                responses.append(self._progress(work_done, "end", "cancelled"))
            return responses
        finally:
            self._active_requests.pop(request_id, None)

    def handle(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        if message.get("jsonrpc") != JSONRPC_VERSION:
            return [self._error(message.get("id"), -32600, "invalid JSON-RPC version")]
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}
        if self.shutdown_requested and method not in {"exit", "$/cancelRequest"}:
            return [self._error(request_id, -32600, "server is shutting down")] if request_id is not None else []
        try:
            if method == "initialize":
                return [self._result(request_id, {
                    "capabilities": {
                        "textDocumentSync": {"openClose": True, "change": 1, "save": {"includeText": False}},
                        "definitionProvider": True,
                        "completionProvider": {},
                        "hoverProvider": True,
                        "referencesProvider": True,
                        "renameProvider": {"prepareProvider": True},
                        "codeActionProvider": True,
                        "workspace": {"workspaceFolders": {"supported": False, "changeNotifications": False}},
                    },
                    "serverInfo": {"name": "aidl-lsp-proof", "version": "0.5"},
                })]
            if method == "initialized":
                return []
            if method == "shutdown":
                self.shutdown_requested = True
                return [self._result(request_id, None)]
            if method == "exit":
                return []
            if method == "$/cancelRequest":
                self.cancel_request(params["id"])
                return []
            if method == "textDocument/didOpen":
                document = params["textDocument"]
                uri = document["uri"]
                self._open_uris.add(uri)
                self.adapter.set_override(uri, document["text"])
                return [self._publish_diagnostics(uri, self.adapter.diagnostics(uri))]
            if method == "textDocument/didChange":
                uri = params["textDocument"]["uri"]
                changes = params["contentChanges"]
                if len(changes) != 1 or "range" in changes[0]:
                    raise LspProtocolError("full-document didChange text is required")
                self.adapter.set_override(uri, changes[0]["text"])
                return [self._publish_diagnostics(uri, self.adapter.diagnostics(uri))]
            if method == "textDocument/didSave":
                uri = params["textDocument"]["uri"]
                self.adapter.clear_override(uri)
                return [self._publish_diagnostics(uri, self.adapter.diagnostics(uri))]
            if method == "textDocument/didClose":
                uri = params["textDocument"]["uri"]
                self._open_uris.discard(uri)
                self.adapter.clear_override(uri)
                return [self._publish_diagnostics(uri, [])]
            if method == "workspace/didChangeWatchedFiles":
                affected = set(self.adapter.watched_files_changed(change["uri"] for change in params["changes"]))
                responses = []
                for uri in sorted(self._open_uris):
                    if self.adapter.state.owner(file_uri_to_path(uri)) in affected:
                        responses.append(self._publish_diagnostics(uri, self.adapter.diagnostics(uri)))
                return responses

            if method in {
                "textDocument/definition",
                "textDocument/completion",
                "textDocument/hover",
                "textDocument/references",
                "textDocument/prepareRename",
                "textDocument/rename",
                "textDocument/codeAction",
            }:
                document = params["textDocument"]
                uri = document["uri"]
                position = params.get("position", {"line": 0, "character": 0})
                line = int(position["line"])
                character = int(position["character"])
                callbacks = {
                    "textDocument/definition": lambda token: self.adapter.definition(uri, line, character, token),
                    "textDocument/completion": lambda token: self.adapter.completion(uri, line, character, token),
                    "textDocument/hover": lambda token: self.adapter.hover(uri, line, character, token),
                    "textDocument/references": lambda token: self.adapter.references(uri, line, character, token),
                    "textDocument/prepareRename": lambda token: self.adapter.prepare_rename(uri, line, character, token),
                    "textDocument/rename": lambda token: self.adapter.rename(uri, line, character, params["newName"], token),
                    "textDocument/codeAction": lambda token: self.adapter.code_actions(
                        uri,
                        [item.get("code") for item in params.get("context", {}).get("diagnostics", []) if item.get("code")],
                        token,
                    ),
                }
                return self._semantic_request(request_id, params, f"AIDL {method.rsplit('/', 1)[-1]}", callbacks[method])

            if request_id is not None:
                return [self._error(request_id, -32601, f"method not supported: {method}")]
            return []
        except CompilerCancelled:
            return [self._error(request_id, REQUEST_CANCELLED, "request cancelled")] if request_id is not None else []
        except (KeyError, TypeError, ValueError, OSError) as exc:
            return [self._error(request_id, -32602, str(exc))] if request_id is not None else []
        except Exception as exc:
            return [self._error(request_id, -32603, f"compiler adapter failure: {type(exc).__name__}: {exc}")] if request_id is not None else []

    @staticmethod
    def _result(request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": code, "message": message}}


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if line == b"":
            return None
        if line in {b"\r\n", b"\n"}:
            break
        try:
            name, value = line.decode("ascii").split(":", 1)
        except ValueError as exc:
            raise LspProtocolError("malformed LSP header") from exc
        headers[name.strip().lower()] = value.strip()
    if "content-length" not in headers:
        raise LspProtocolError("missing Content-Length")
    length = int(headers["content-length"])
    if length < 0:
        raise LspProtocolError("negative Content-Length")
    body = stream.read(length)
    if len(body) != length:
        raise LspProtocolError("truncated LSP body")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise LspProtocolError("LSP message body must be an object")
    return payload


def write_message(stream: BinaryIO, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    stream.write(body)
    stream.flush()


def run_stdio(project_paths: Path | Iterable[Path], stdin: BinaryIO | None = None, stdout: BinaryIO | None = None) -> int:
    input_stream = stdin or sys.stdin.buffer
    output_stream = stdout or sys.stdout.buffer
    server = AidlLspServer(project_paths)
    while True:
        message = read_message(input_stream)
        if message is None:
            return 0 if server.shutdown_requested else 1
        method = message.get("method")
        for response in server.handle(message):
            write_message(output_stream, response)
        if method == "exit":
            return 0 if server.shutdown_requested else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("usage: python -m tools.aidl_lsp <project-root> [<project-root> ...]\n")
        raise SystemExit(2)
    raise SystemExit(run_stdio(tuple(Path(argument) for argument in sys.argv[1:])))
