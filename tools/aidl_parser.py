#!/usr/bin/env python3
"""Fault-tolerant parser for AIDL examples and specification tooling.

The parser builds a concrete-enough AST for tooling, linting, indexing, and
smoke-checking before a full compiler exists. It intentionally preserves many
subclauses as structured generic nodes instead of trying to type-check profile
schemas. Semantic validation belongs in the compiler or in spec_lint.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


KEYWORDS = {
    "a11y",
    "action",
    "alias",
    "and",
    "api",
    "app",
    "as",
    "auth",
    "boundedStaleness",
    "cache",
    "call",
    "channel",
    "client",
    "component",
    "config",
    "consumer",
    "deployment",
    "else",
    "emit",
    "entity",
    "enum",
    "error",
    "event",
    "export",
    "false",
    "fixture",
    "for",
    "form",
    "from",
    "frontend",
    "if",
    "import",
    "in",
    "isolation",
    "migration",
    "module",
    "mutation",
    "native",
    "not",
    "null",
    "on",
    "opaque",
    "or",
    "page",
    "policy",
    "privacy",
    "projection",
    "query",
    "queue",
    "ref",
    "rendition",
    "resource",
    "return",
    "saga",
    "scenario",
    "schedule",
    "secret",
    "seo",
    "service",
    "sync",
    "syncStatus",
    "system",
    "task",
    "tenant",
    "test",
    "theme",
    "to",
    "transaction",
    "true",
    "union",
    "value",
    "version",
    "view",
    "workflow",
}

SCALAR_TYPES = {
    "string",
    "int",
    "decimal",
    "bool",
    "uuid",
    "date",
    "datetime",
    "duration",
    "revision",
    "email",
    "url",
    "bytes",
}

DECLARATION_STARTERS = {
    "app",
    "auth",
    "a11y",
    "privacy",
    "enum",
    "alias",
    "opaque",
    "value",
    "union",
    "error",
    "entity",
    "view",
    "api",
    "policy",
    "query",
    "mutation",
    "event",
    "topic",
    "queue",
    "consumer",
    "projection",
    "workflow",
    "saga",
    "task",
    "schedule",
    "system",
    "service",
    "client",
    "tenant",
    "channel",
    "resource",
    "media",
    "rendition",
    "sync",
    "migration",
    "deployment",
    "frontend",
    "theme",
    "component",
    "page",
    "form",
    "action",
    "syncStatus",
    "seo",
    "native",
    "fixture",
    "test",
    "scenario",
}

RESOURCE_KINDS = {
    "sql",
    "document",
    "keyValue",
    "timeSeries",
    "blob",
    "cdn",
    "cache",
    "stream",
    "search",
    "counter",
    "secretRef",
    "configRef",
    "localStore",
}

TWO_CHAR_SYMBOLS = {"->", "==", "!=", "<=", ">=", ".."}
SINGLE_SYMBOLS = set("{}[]()<>,:.*+-/%=?")


@dataclass(frozen=True)
class Span:
    line: int
    column: int
    offset: int

    def to_json(self) -> dict[str, int]:
        return {"line": self.line, "column": self.column, "offset": self.offset}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: Span
    end: Span

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            "start": self.start.to_json(),
            "end": self.end.to_json(),
        }


@dataclass
class Diagnostic:
    message: str
    start: Span
    severity: str = "error"

    def to_json(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "message": self.message,
            "location": self.start.to_json(),
        }


@dataclass
class Node:
    kind: str
    name: str | None = None
    span: Span | None = None
    end: Span | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind}
        if self.name is not None:
            result["name"] = self.name
        if self.span is not None:
            result["span"] = self.span.to_json()
        if self.end is not None:
            result["end"] = self.end.to_json()
        result.update(self.attrs)
        if self.children:
            result["children"] = [child.to_json() for child in self.children]
        return result


class Lexer:
    def __init__(self, text: str) -> None:
        self.text = text
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self.diagnostics: list[Diagnostic] = []

    def tokenize(self) -> tuple[list[Token], list[Diagnostic]]:
        while not self.at_end:
            start = self.span()
            char = self.peek_char()
            nxt = self.peek_char(1)
            if char in " \r\t":
                self.advance()
            elif char == "\n":
                self.add("NEWLINE", self.advance(), start)
            elif char == "/" and nxt == "/":
                self.skip_line_comment()
            elif char == "/" and nxt == "*":
                self.skip_block_comment(start)
            elif char == '"':
                self.lex_string()
            elif char == "@":
                self.lex_annotation()
            elif char.isdigit() or (char == "-" and self.peek_char(1).isdigit()):
                self.lex_number_or_unit()
            elif self.is_identifier_start(char):
                self.lex_identifier()
            elif self.text[self.index : self.index + 2] in TWO_CHAR_SYMBOLS:
                value = self.advance() + self.advance()
                self.add("SYMBOL", value, start)
            elif char in SINGLE_SYMBOLS:
                self.add("SYMBOL", self.advance(), start)
            else:
                self.diagnostics.append(Diagnostic(f"unexpected character {char!r}", start))
                self.advance()
        eof = self.span()
        self.tokens.append(Token("EOF", "", eof, eof))
        return self.tokens, self.diagnostics

    @property
    def at_end(self) -> bool:
        return self.index >= len(self.text)

    def span(self) -> Span:
        return Span(self.line, self.column, self.index)

    def peek_char(self, distance: int = 0) -> str:
        index = self.index + distance
        if index >= len(self.text):
            return ""
        return self.text[index]

    def advance(self) -> str:
        char = self.text[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def add(self, kind: str, value: str, start: Span) -> None:
        self.tokens.append(Token(kind, value, start, self.span()))

    def skip_line_comment(self) -> None:
        while not self.at_end and self.peek_char() != "\n":
            self.advance()

    def skip_block_comment(self, start: Span) -> None:
        self.advance()
        self.advance()
        while not self.at_end:
            if self.peek_char() == "*" and self.peek_char(1) == "/":
                self.advance()
                self.advance()
                return
            self.advance()
        self.diagnostics.append(Diagnostic("unterminated block comment", start))

    def lex_string(self) -> None:
        start = self.span()
        value = self.advance()
        while not self.at_end:
            char = self.advance()
            value += char
            if char == "\\" and not self.at_end:
                value += self.advance()
            elif char == '"':
                self.add("STRING", value, start)
                return
            elif char == "\n":
                self.diagnostics.append(Diagnostic("newline in string literal", start))
                self.add("STRING", value, start)
                return
        self.diagnostics.append(Diagnostic("unterminated string literal", start))
        self.add("STRING", value, start)

    def lex_annotation(self) -> None:
        start = self.span()
        value = self.advance()
        while self.is_identifier_part(self.peek_char()):
            value += self.advance()
        self.add("ANNOTATION", value, start)

    def lex_number_or_unit(self) -> None:
        start = self.span()
        value = ""
        if self.peek_char() == "-":
            value += self.advance()
        while self.peek_char().isdigit():
            value += self.advance()
        if self.peek_char() == "." and self.peek_char(1).isdigit():
            value += self.advance()
            while self.peek_char().isdigit():
                value += self.advance()
        if self.peek_char() == "%":
            value += self.advance()
            self.add("PERCENTAGE", value, start)
            return
        while self.peek_char().isalpha():
            value += self.advance()
        self.add("NUMBER", value, start)

    def lex_identifier(self) -> None:
        start = self.span()
        value = self.advance()
        while self.is_identifier_part(self.peek_char()):
            value += self.advance()
        kind = "KEYWORD" if value in KEYWORDS else "IDENT"
        self.add(kind, value, start)

    @staticmethod
    def is_identifier_start(char: str) -> bool:
        return char == "_" or char.isalpha()

    @staticmethod
    def is_identifier_part(char: str) -> bool:
        return char == "_" or char.isalpha() or char.isdigit()


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0
        self.diagnostics: list[Diagnostic] = []

    def parse_program(self) -> Node:
        program = Node("program", span=self.current.start)
        while not self.check_kind("EOF"):
            self.skip_newlines()
            if self.check_kind("EOF"):
                break
            if self.match_value("module"):
                program.children.append(self.parse_module(self.previous))
            elif self.match_value("import"):
                program.children.append(self.parse_import(self.previous))
            else:
                program.children.append(self.parse_declaration())
        program.end = self.current.end
        return program

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    @property
    def previous(self) -> Token:
        return self.tokens[self.index - 1]

    def advance(self) -> Token:
        if not self.check_kind("EOF"):
            self.index += 1
        return self.previous

    def match_value(self, *values: str) -> bool:
        if self.current.value in values:
            self.advance()
            return True
        return False

    def match_symbol(self, *values: str) -> bool:
        if self.current.kind == "SYMBOL" and self.current.value in values:
            self.advance()
            return True
        return False

    def check_value(self, value: str) -> bool:
        return self.current.value == value

    def check_kind(self, kind: str) -> bool:
        return self.current.kind == kind

    def skip_newlines(self) -> None:
        while self.check_kind("NEWLINE"):
            self.advance()

    def consume_value(self, value: str, message: str) -> Token | None:
        if self.match_value(value):
            return self.previous
        self.error(message)
        return None

    def consume_symbol(self, value: str, message: str) -> Token | None:
        if self.match_symbol(value):
            return self.previous
        self.error(message)
        return None

    def consume_name(self, message: str) -> Token | None:
        if self.current.kind in {"IDENT", "KEYWORD"}:
            return self.advance()
        self.error(message)
        return None

    def error(self, message: str) -> None:
        self.diagnostics.append(Diagnostic(message, self.current.start))

    def parse_module(self, start: Token) -> Node:
        name = self.parse_qualified_name()
        self.consume_line_end()
        return Node("module", name=name, span=start.start, end=self.previous.end)

    def parse_import(self, start: Token) -> Node:
        name = self.parse_qualified_name(allow_wildcard=True)
        self.consume_line_end()
        return Node("import", name=name, span=start.start, end=self.previous.end)

    def parse_declaration(self) -> Node:
        annotations = self.parse_annotations()
        exported = self.match_value("export")
        start = self.current
        if self.match_value("native"):
            node = self.parse_native(start)
        elif self.current.value in DECLARATION_STARTERS:
            kind = self.advance().value
            node = self.parse_known_declaration(kind, start)
        else:
            self.error("expected declaration")
            skipped = self.synchronize()
            node = Node("unknown", span=start.start, end=skipped.end)
        if annotations:
            node.attrs["annotations"] = annotations
        if exported:
            node.attrs["exported"] = True
        return node

    def parse_annotations(self) -> list[dict[str, Any]]:
        annotations: list[dict[str, Any]] = []
        while self.check_kind("ANNOTATION"):
            token = self.advance()
            annotation: dict[str, Any] = {"name": token.value[1:], "span": token.start.to_json()}
            if self.match_symbol("("):
                annotation["arguments"] = self.collect_balanced("(", ")")
            annotations.append(annotation)
            self.skip_newlines()
        return annotations

    def parse_native(self, start: Token) -> Node:
        if self.match_value("function"):
            kind = "nativeFunction"
            name = self.parse_qualified_name()
        elif self.match_value("component"):
            kind = "nativeComponent"
            name = self.consume_name("expected native component name")
            name = name.value if name else None
        else:
            self.error("expected function or component after native")
            return Node("native", span=start.start, end=self.synchronize().end)
        node = Node(kind, name=name, span=start.start)
        if self.match_symbol("<"):
            node.attrs["typeParameters"] = self.collect_balanced("<", ">")
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_known_declaration(self, kind: str, start: Token) -> Node:
        if kind == "app":
            return self.parse_app(start)
        if kind in {"auth", "a11y", "privacy"}:
            return self.parse_anonymous_block(kind, start)
        if kind in {"alias", "opaque"}:
            return self.parse_alias(kind, start)
        if kind == "enum":
            return self.parse_enum(start)
        if kind in {"value", "union", "error", "entity", "view"}:
            return self.parse_type_like(kind, start)
        if kind == "api":
            return self.parse_named_block(kind, start)
        if kind in {"policy", "query", "mutation", "workflow", "saga", "task"}:
            return self.parse_operation_like(kind, start)
        if kind == "event":
            return self.parse_event(start)
        if kind in {"topic", "queue", "consumer", "projection"}:
            return self.parse_messaging(kind, start)
        if kind in {"system", "service", "client", "tenant", "channel"}:
            return self.parse_system_like(kind, start)
        if kind in {"resource", "media", "rendition"}:
            return self.parse_resource_like(kind, start)
        if kind == "sync":
            return self.parse_sync(start)
        if kind == "migration":
            return self.parse_migration(start)
        if kind == "deployment":
            return self.parse_deployment(start)
        if kind in {"frontend", "theme", "component", "page", "form", "action", "syncStatus", "seo"}:
            return self.parse_ui_like(kind, start)
        if kind in {"fixture", "test", "scenario"}:
            return self.parse_test_like(kind, start)
        node = Node(kind, span=start.start)
        self.parse_declaration_tail(node)
        return node

    def parse_app(self, start: Token) -> Node:
        name = self.consume_name("expected app name")
        node = Node("app", name=name.value if name else None, span=start.start)
        if self.match_value("version"):
            version = self.consume_literal_like("expected app version")
            if version:
                node.attrs["version"] = version.value.strip('"')
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_anonymous_block(self, kind: str, start: Token) -> Node:
        node = Node(kind, span=start.start)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_named_block(self, kind: str, start: Token) -> Node:
        name = self.consume_name(f"expected {kind} name")
        node = Node(kind, name=name.value if name else None, span=start.start)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_alias(self, kind: str, start: Token) -> Node:
        name = self.consume_name(f"expected {kind} name")
        node = Node(kind, name=name.value if name else None, span=start.start)
        if self.match_symbol("<"):
            node.attrs["typeParameters"] = self.collect_balanced("<", ">")
        if self.match_symbol("="):
            node.attrs["type"] = self.collect_until_line_end()
        self.consume_line_end()
        node.end = self.previous.end
        return node

    def parse_enum(self, start: Token) -> Node:
        name = self.consume_name("expected enum name")
        node = Node("enum", name=name.value if name else None, span=start.start)
        if self.match_symbol("{"):
            cases: list[str] = []
            while not self.check_kind("EOF") and not self.match_symbol("}"):
                if self.current.kind in {"IDENT", "KEYWORD"}:
                    cases.append(self.advance().value)
                else:
                    self.advance()
            node.attrs["cases"] = cases
            node.end = self.previous.end
        return node

    def parse_type_like(self, kind: str, start: Token) -> Node:
        name = self.consume_name(f"expected {kind} name")
        node = Node(kind, name=name.value if name else None, span=start.start)
        if self.match_symbol("<"):
            node.attrs["typeParameters"] = self.collect_balanced("<", ">")
        if kind == "view" and self.match_value("from"):
            node.attrs["from"] = self.collect_until("{", stop_before=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_operation_like(self, kind: str, start: Token) -> Node:
        name = self.consume_name(f"expected {kind} name")
        node = Node(kind, name=name.value if name else None, span=start.start)
        if self.match_symbol("<"):
            node.attrs["typeParameters"] = self.collect_balanced("<", ">")
        if self.match_symbol("("):
            node.attrs["parameters"] = self.collect_balanced("(", ")")
        if self.match_symbol("->"):
            node.attrs["returns"] = self.collect_until("{", stop_before=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_event(self, start: Token) -> Node:
        name = self.consume_name("expected event name")
        node = Node("event", name=name.value if name else None, span=start.start)
        if self.match_value("version"):
            version = self.consume_literal_like("expected event version")
            if version:
                node.attrs["version"] = version.value
        if self.match_value("evolves"):
            node.attrs["evolves"] = self.collect_until("{", stop_before=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        return node

    def parse_messaging(self, kind: str, start: Token) -> Node:
        name = self.consume_name(f"expected {kind} name")
        node = Node(kind, name=name.value if name else None, span=start.start)
        self.skip_newlines()
        if kind == "consumer":
            if self.match_value("on"):
                node.attrs["on"] = self.collect_until("from", stop_before=True, allow_newlines=True)
            if self.match_value("from"):
                node.attrs["from"] = self.collect_until("{", stop_before=True, allow_newlines=True)
        elif kind == "projection":
            if self.match_value("from"):
                node.attrs["from"] = self.collect_until("into", stop_before=True, allow_newlines=True)
            if self.match_value("into"):
                node.attrs["into"] = self.collect_until("{", stop_before=True, allow_newlines=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_system_like(self, kind: str, start: Token) -> Node:
        name: str | None = None
        if kind == "tenant" and self.match_value("model"):
            token = self.consume_name("expected tenant model name")
            name = token.value if token else None
        else:
            token = self.consume_name(f"expected {kind} name")
            name = token.value if token else None
        node = Node(kind, name=name, span=start.start)
        if kind == "client" and self.match_value("for"):
            node.attrs["for"] = self.collect_until("{", stop_before=True)
        if kind == "channel" and self.match_symbol("<"):
            node.attrs["typeParameters"] = self.collect_balanced("<", ">")
        if self.match_symbol("{"):
            self.parse_block_into(node)
        return node

    def parse_resource_like(self, kind: str, start: Token) -> Node:
        name = self.consume_name(f"expected {kind} name")
        node = Node(kind, name=name.value if name else None, span=start.start)
        if kind == "resource":
            resource_kind = self.consume_name("expected resource kind")
            if resource_kind:
                node.attrs["resourceKind"] = resource_kind.value
            if self.match_symbol("<"):
                node.attrs["typeArguments"] = self.collect_balanced("<", ">")
        elif kind == "rendition" and self.match_value("from"):
            node.attrs["from"] = self.collect_until("{", stop_before=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        return node

    def parse_sync(self, start: Token) -> Node:
        name = self.consume_name("expected sync name")
        node = Node("sync", name=name.value if name else None, span=start.start)
        if self.match_value("for"):
            node.attrs["for"] = self.collect_until("{", stop_before=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        return node

    def parse_migration(self, start: Token) -> Node:
        name = self.consume_name("expected migration name")
        node = Node("migration", name=name.value if name else None, span=start.start)
        if self.match_value("from"):
            token = self.consume_literal_like("expected source version")
            if token:
                node.attrs["from"] = token.value.strip('"')
        if self.match_value("to"):
            token = self.consume_literal_like("expected target version")
            if token:
                node.attrs["to"] = token.value.strip('"')
        if self.match_symbol("{"):
            self.parse_block_into(node)
        return node

    def parse_deployment(self, start: Token) -> Node:
        name = self.consume_name("expected deployment name")
        node = Node("deployment", name=name.value if name else None, span=start.start)
        if self.match_value("for"):
            node.attrs["for"] = self.collect_until("{", stop_before=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        return node

    def parse_ui_like(self, kind: str, start: Token) -> Node:
        name = self.consume_name(f"expected {kind} name")
        node = Node(kind, name=name.value if name else None, span=start.start)
        if self.match_symbol("<"):
            node.attrs["typeParameters"] = self.collect_balanced("<", ">")
        if self.match_symbol("("):
            node.attrs["parameters"] = self.collect_balanced("(", ")")
        if kind == "form" and self.match_value("for"):
            node.attrs["for"] = self.collect_until("{", stop_before=True)
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            self.consume_line_end()
            node.end = self.previous.end
        return node

    def parse_test_like(self, kind: str, start: Token) -> Node:
        if kind == "test" and self.current.kind == "STRING":
            name = self.advance().value.strip('"')
        else:
            token = self.consume_name(f"expected {kind} name")
            name = token.value if token else None
            if self.match_symbol("("):
                params = self.collect_balanced("(", ")")
            else:
                params = None
        node = Node(kind, name=name, span=start.start)
        if kind != "test" and "params" in locals() and params is not None:
            node.attrs["parameters"] = params
        if kind == "test" and self.match_value("target"):
            target = self.consume_name("expected test target")
            if target:
                node.attrs["target"] = target.value
        if self.match_symbol("{"):
            self.parse_block_into(node)
        return node

    def parse_declaration_tail(self, node: Node) -> None:
        if self.match_symbol("{"):
            self.parse_block_into(node)
        else:
            node.attrs["tail"] = self.collect_until_line_end()
            self.consume_line_end()
            node.end = self.previous.end

    def parse_block_into(self, node: Node) -> None:
        while not self.check_kind("EOF"):
            self.skip_newlines()
            if self.match_symbol("}"):
                node.end = self.previous.end
                return
            node.children.append(self.parse_clause())
        self.error(f"unclosed block for {node.kind}")
        node.end = self.current.end

    def looks_like_declaration(self) -> bool:
        offset = 0
        while self.index + offset < len(self.tokens) and self.tokens[self.index + offset].kind == "ANNOTATION":
            offset += 1
        if self.index + offset < len(self.tokens) and self.tokens[self.index + offset].value == "export":
            offset += 1
        if self.index + offset >= len(self.tokens):
            return False
        first = self.tokens[self.index + offset]
        if first.value == "native":
            return True
        if first.value not in DECLARATION_STARTERS:
            return False
        if first.value in {"auth", "a11y", "privacy"}:
            return True
        nxt = self.tokens[self.index + offset + 1] if self.index + offset + 1 < len(self.tokens) else first
        return nxt.kind in {"IDENT", "KEYWORD", "STRING"}

    def parse_clause(self) -> Node:
        start = self.current
        head_parts: list[str] = []
        while not self.check_kind("EOF"):
            if self.check_kind("NEWLINE"):
                self.advance()
                return Node("clause", name=" ".join(head_parts) or None, span=start.start, end=self.previous.end)
            if self.current.value == "}":
                return Node("clause", name=" ".join(head_parts) or None, span=start.start, end=self.current.start)
            if self.current.value == "{":
                self.advance()
                node = Node("blockClause", name=" ".join(head_parts) or None, span=start.start)
                self.parse_block_into(node)
                return node
            if self.current.value == "[":
                head_parts.append(self.collect_balanced("[", "]", consume_open=True))
                continue
            if self.current.value == "(":
                head_parts.append(self.collect_balanced("(", ")", consume_open=True))
                continue
            head_parts.append(self.advance().value)
        return Node("clause", name=" ".join(head_parts) or None, span=start.start, end=self.current.end)

    def parse_qualified_name(self, allow_wildcard: bool = False) -> str | None:
        token = self.consume_name("expected qualified name")
        if not token:
            return None
        parts = [token.value]
        while self.current.value in {".", "-"}:
            separator = self.advance().value
            if separator == "." and allow_wildcard and self.match_symbol("*"):
                parts.append(".*")
                break
            name = self.consume_name("expected qualified name segment")
            if not name:
                break
            parts.append(separator + name.value)
        return parts[0] + "".join(parts[1:])

    def collect_until(self, value: str, *, stop_before: bool = False, allow_newlines: bool = False) -> str:
        parts: list[str] = []
        depth = 0
        while not self.check_kind("EOF"):
            if depth == 0 and self.current.value == value:
                if not stop_before:
                    parts.append(self.advance().value)
                break
            if depth == 0 and self.check_kind("NEWLINE") and not allow_newlines:
                break
            if self.check_kind("NEWLINE"):
                parts.append(self.advance().value)
                continue
            if self.current.value in {"(", "[", "{", "<"}:
                depth += 1
            elif self.current.value in {")",
                "]",
                "}",
                ">",
            } and depth > 0:
                depth -= 1
            parts.append(self.advance().value)
        return join_tokens(parts).strip()

    def collect_until_line_end(self) -> str:
        parts: list[str] = []
        while not self.check_kind("EOF") and not self.check_kind("NEWLINE"):
            parts.append(self.advance().value)
        return join_tokens(parts).strip()

    def collect_balanced(self, open_value: str, close_value: str, *, consume_open: bool = False) -> str:
        parts: list[str] = []
        depth = 1
        if consume_open:
            if self.current.value == open_value:
                parts.append(self.advance().value)
            else:
                self.error(f"expected {open_value}")
        else:
            parts.append(open_value)
        while not self.check_kind("EOF") and depth > 0:
            token = self.advance()
            if token.value == open_value:
                depth += 1
            elif token.value == close_value:
                depth -= 1
            parts.append(token.value)
            if depth == 0:
                break
        if depth != 0:
            self.error(f"unclosed {open_value}")
        return join_tokens(parts).strip()

    def consume_literal_like(self, message: str) -> Token | None:
        if self.current.kind in {"STRING", "NUMBER", "PERCENTAGE", "IDENT", "KEYWORD"}:
            return self.advance()
        self.error(message)
        return None

    def consume_line_end(self) -> None:
        if self.check_kind("NEWLINE"):
            self.advance()
        elif not self.check_kind("EOF") and self.current.value != "}":
            self.error("expected newline")
            self.synchronize()

    def synchronize(self) -> Token:
        last = self.current
        while not self.check_kind("EOF"):
            if self.check_kind("NEWLINE"):
                return self.advance()
            if self.current.value == "}":
                return self.advance()
            last = self.advance()
        return last


def join_tokens(values: Iterable[str]) -> str:
    result = ""
    previous = ""
    no_space_before = {
        ")",
        "]",
        "}",
        ",",
        ".",
        ":",
        ">",
    }
    no_space_after = {"(", "[", "{", ".", "<", ":"}
    for value in values:
        if not result:
            result = value
        elif value in no_space_before or previous in no_space_after:
            result += value
        else:
            result += " " + value
        previous = value
    return result


def parse_text(text: str) -> tuple[Node, list[Diagnostic], list[Token]]:
    lexer = Lexer(text)
    tokens, lexer_diagnostics = lexer.tokenize()
    parser = Parser(tokens)
    program = parser.parse_program()
    return program, lexer_diagnostics + parser.diagnostics, tokens


def parse_file(path: Path, *, include_tokens: bool = False) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    ast, diagnostics, tokens = parse_text(text)
    result: dict[str, Any] = {
        "path": str(path),
        "ast": ast.to_json(),
        "diagnostics": [diagnostic.to_json() for diagnostic in diagnostics],
    }
    if include_tokens:
        result["tokens"] = [
            token.to_json()
            for token in tokens
            if token.kind not in {"EOF", "NEWLINE"}
        ]
    return result


def iter_aidl_files(paths: list[Path]) -> list[Path]:
    files_by_resolved_path: dict[Path, Path] = {}
    for path in paths:
        if path.is_dir():
            candidates = (
                candidate
                for candidate in path.rglob("*.aidl")
                if candidate.is_file()
            )
        else:
            candidates = (path,) if path.suffix == ".aidl" else ()
        for candidate in candidates:
            files_by_resolved_path.setdefault(candidate.resolve(), candidate)
    return sorted(files_by_resolved_path.values(), key=lambda candidate: candidate.as_posix())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="AIDL files or directories")
    parser.add_argument("--tokens", action="store_true", help="include tokens in JSON output")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    parser.add_argument(
        "--fail-on-diagnostics",
        action="store_true",
        help="exit non-zero if parser diagnostics are produced",
    )
    args = parser.parse_args(argv)

    files = iter_aidl_files(args.paths)
    documents = [parse_file(path, include_tokens=args.tokens) for path in files]
    payload = {"files": documents}
    json.dump(payload, sys.stdout, indent=2 if args.pretty else None, ensure_ascii=False)
    sys.stdout.write("\n")

    if args.fail_on_diagnostics and any(doc["diagnostics"] for doc in documents):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
