from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KERNEL_VERSION = 1


class BootstrapSyntaxError(ValueError):
    """Raised when source is outside the versioned bootstrap-kernel grammar."""


@dataclass(frozen=True)
class TypeRef:
    name: str
    arguments: tuple["TypeRef", ...] = ()
    optional: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": [item.to_json() for item in self.arguments],
            "optional": self.optional,
        }


@dataclass(frozen=True)
class Value:
    kind: str
    value: Any
    raw: str

    def to_json(self) -> Any:
        if self.kind == "typeRef":
            return {"$typeRef": self.value.to_json()}
        return self.value


@dataclass(frozen=True)
class ModifierCall:
    name: str
    arguments: tuple[tuple[str, Value], ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": {name: value.to_json() for name, value in self.arguments},
        }


@dataclass(frozen=True)
class BodyEntry:
    body_type: str
    name: str | None
    value: Value | None
    modifiers: tuple[ModifierCall, ...]
    form: str

    def to_json(self) -> dict[str, Any]:
        return {
            "bodyType": self.body_type,
            "name": self.name,
            "value": None if self.value is None else self.value.to_json(),
            "modifiers": [item.to_json() for item in self.modifiers],
            "form": self.form,
        }


@dataclass(frozen=True)
class Declaration:
    kind: str
    name: str | None
    exported: bool
    arguments: tuple[tuple[str, Value], ...]
    result: TypeRef | None
    body: tuple[BodyEntry, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "exported": self.exported,
            "arguments": {name: value.to_json() for name, value in self.arguments},
            "result": None if self.result is None else self.result.to_json(),
            "body": [item.to_json() for item in self.body],
        }


@dataclass(frozen=True)
class Program:
    module: str | None
    imports: tuple[str, ...]
    declarations: tuple[Declaration, ...]


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


_SYMBOLS = set("{}[]()<>,:?.@")


def _tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1
    while index < len(source):
        char = source[index]
        if char in " \t\r":
            index += 1
            column += 1
            continue
        if char == "\n":
            tokens.append(Token("NEWLINE", "\n", line, column))
            index += 1
            line += 1
            column = 1
            continue
        if source.startswith("//", index):
            while index < len(source) and source[index] != "\n":
                index += 1
                column += 1
            continue
        if source.startswith("->", index):
            tokens.append(Token("SYMBOL", "->", line, column))
            index += 2
            column += 2
            continue
        if char == '"':
            start_line = line
            start_column = column
            raw = char
            index += 1
            column += 1
            escaped = False
            while index < len(source):
                current = source[index]
                raw += current
                index += 1
                column += 1
                if escaped:
                    escaped = False
                    continue
                if current == "\\":
                    escaped = True
                    continue
                if current == '"':
                    break
                if current == "\n":
                    raise BootstrapSyntaxError(
                        f"newline in string at {start_line}:{start_column}"
                    )
            else:
                raise BootstrapSyntaxError(
                    f"unterminated string at {start_line}:{start_column}"
                )
            tokens.append(Token("STRING", raw, start_line, start_column))
            continue
        if char.isdigit() or (
            char == "-" and index + 1 < len(source) and source[index + 1].isdigit()
        ):
            start = index
            start_column = column
            index += 1
            column += 1
            while index < len(source) and (
                source[index].isdigit() or source[index] == "."
            ):
                index += 1
                column += 1
            tokens.append(Token("NUMBER", source[start:index], line, start_column))
            continue
        if char.isalpha() or char == "_":
            start = index
            start_column = column
            index += 1
            column += 1
            while index < len(source) and (
                source[index].isalnum() or source[index] == "_"
            ):
                index += 1
                column += 1
            tokens.append(Token("IDENT", source[start:index], line, start_column))
            continue
        if char in _SYMBOLS:
            tokens.append(Token("SYMBOL", char, line, column))
            index += 1
            column += 1
            continue
        raise BootstrapSyntaxError(
            f"unexpected character {char!r} at {line}:{column}"
        )
    tokens.append(Token("EOF", "", line, column))
    return tokens


class _Parser:
    def __init__(self, source: str) -> None:
        self.tokens = _tokenize(source)
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current
        if token.kind != "EOF":
            self.index += 1
        return token

    def match(self, value: str) -> bool:
        if self.current.value == value:
            self.advance()
            return True
        return False

    def require(self, value: str) -> Token:
        if not self.match(value):
            self.fail(f"expected {value!r}")
        return self.tokens[self.index - 1]

    def name(self) -> str:
        if self.current.kind != "IDENT":
            self.fail("expected identifier")
        return self.advance().value

    def fail(self, message: str) -> None:
        token = self.current
        raise BootstrapSyntaxError(
            f"{message} at {token.line}:{token.column}; found {token.value!r}"
        )

    def skip_newlines(self) -> None:
        while self.current.kind == "NEWLINE":
            self.advance()

    def program(self) -> Program:
        module: str | None = None
        imports: list[str] = []
        declarations: list[Declaration] = []
        self.skip_newlines()
        while self.current.kind != "EOF":
            if self.match("module"):
                if module is not None:
                    self.fail("duplicate module directive")
                module = self.qualified_name()
                self.line_end()
            elif self.match("import"):
                imports.append(self.qualified_name())
                self.line_end()
            else:
                declarations.append(self.declaration())
            self.skip_newlines()
        return Program(module, tuple(imports), tuple(declarations))

    def line_end(self) -> None:
        if self.current.kind == "NEWLINE":
            self.advance()
            return
        if self.current.kind == "EOF":
            return
        self.fail("expected newline")

    def qualified_name(self) -> str:
        parts = [self.name()]
        while self.match("."):
            parts.append(self.name())
        return ".".join(parts)

    def declaration(self) -> Declaration:
        exported = self.match("export")
        kind = self.name()
        candidate_name: str | None = None
        if self.current.kind == "IDENT" and self.current.value not in {
            "true",
            "false",
            "null",
        }:
            candidate_name = self.advance().value
        arguments = self.named_arguments() if self.match("(") else ()
        result = None
        if self.match("->"):
            result = self.type_ref()
        self.require("{")
        if self.current.kind == "NEWLINE":
            self.advance()
        body: list[BodyEntry] = []
        while True:
            self.skip_newlines()
            if self.match("}"):
                break
            if self.current.kind == "EOF":
                self.fail("unclosed declaration body")
            body.append(self.body_entry())
        if self.current.kind == "NEWLINE":
            self.advance()
        return Declaration(
            kind,
            candidate_name,
            exported,
            arguments,
            result,
            tuple(body),
        )

    def named_arguments(self) -> tuple[tuple[str, Value], ...]:
        arguments: list[tuple[str, Value]] = []
        self.skip_newlines()
        if self.match(")"):
            return ()
        while True:
            name = self.name()
            self.require(":")
            value = self.value(stop={",", ")"})
            arguments.append((name, value))
            self.skip_newlines()
            if self.match(")"):
                break
            self.require(",")
            self.skip_newlines()
        return tuple(arguments)

    def type_ref(self) -> TypeRef:
        name = self.qualified_name()
        arguments: list[TypeRef] = []
        if self.match("<"):
            self.skip_newlines()
            if self.match(">"):
                self.fail("generic TypeRef requires at least one argument")
            while True:
                arguments.append(self.type_ref())
                self.skip_newlines()
                if self.match(">"):
                    break
                self.require(",")
                self.skip_newlines()
        optional = self.match("?")
        return TypeRef(name, tuple(arguments), optional)

    def body_entry(self) -> BodyEntry:
        body_type = self.name()
        candidate_name: str | None = None
        if self.current.kind == "IDENT" and self.tokens[self.index + 1].value == ":":
            candidate_name = self.advance().value
        self.require(":")

        # V1 is specifically colon + opening brace + newline. A same-line object
        # literal therefore remains an ordinary value and is not a modifier block.
        if self.current.value == "{" and self.tokens[self.index + 1].kind == "NEWLINE":
            self.advance()
            self.advance()
            value: Value | None = None
            self.skip_newlines()
            if self.current.value not in {"@", "}"}:
                value = self.value(stop={"\n", "@", "}"})
                self.line_end()
            modifiers = self.modifier_block_tail()
            return BodyEntry(
                body_type,
                candidate_name,
                value,
                modifiers,
                "multiline-v1",
            )

        value = None
        if self.current.kind != "NEWLINE" and self.current.value not in {"@", "}"}:
            value = self.value(stop={"\n", "@", "modifier-block"})
        if self.current.value == "{" and self.tokens[self.index + 1].kind == "NEWLINE":
            self.advance()
            self.advance()
            modifiers = self.modifier_block_tail()
            return BodyEntry(
                body_type,
                candidate_name,
                value,
                modifiers,
                "multiline-v2",
            )

        modifiers: list[ModifierCall] = []
        while self.current.value == "@":
            modifiers.append(self.modifier())
        if self.current.kind == "NEWLINE":
            self.advance()
        elif self.current.value != "}":
            self.fail("expected newline or declaration close after body entry")
        return BodyEntry(
            body_type,
            candidate_name,
            value,
            tuple(modifiers),
            "inline",
        )

    def modifier_block_tail(self) -> tuple[ModifierCall, ...]:
        modifiers: list[ModifierCall] = []
        while True:
            self.skip_newlines()
            if self.match("}"):
                if self.current.kind == "NEWLINE":
                    self.advance()
                return tuple(modifiers)
            if self.current.value != "@":
                self.fail("expected modifier line or closing brace")
            modifiers.append(self.modifier())
            if self.current.kind == "NEWLINE":
                self.advance()
            elif self.current.value != "}":
                self.fail("expected newline after modifier")

    def modifier(self) -> ModifierCall:
        self.require("@")
        name = self.name()
        arguments = self.named_arguments() if self.match("(") else ()
        return ModifierCall(name, arguments)

    def value(self, stop: set[str]) -> Value:
        start = self.index
        token = self.current
        if token.kind == "STRING":
            self.advance()
            return Value("string", json.loads(token.value), token.value)
        if token.kind == "NUMBER":
            self.advance()
            number: int | float = (
                float(token.value) if "." in token.value else int(token.value)
            )
            return Value("number", number, token.value)
        if token.value in {"true", "false", "null"}:
            self.advance()
            return Value(
                "literal",
                {"true": True, "false": False, "null": None}[token.value],
                token.value,
            )
        if token.value == "[":
            return self.list_value()
        if token.value == "{":
            return self.object_value()
        if token.kind == "IDENT":
            saved = self.index
            try:
                type_ref = self.type_ref()
                if self._at_stop(stop):
                    return Value(
                        "typeRef",
                        type_ref,
                        self.raw(start, self.index),
                    )
            except BootstrapSyntaxError:
                pass
            self.index = saved

        # I1 deliberately frames but does not semantically interpret expressions or
        # declaration references. Balanced nested delimiters/newlines remain one
        # opaque value until later Core-semantic phases.
        depth: list[str] = []
        pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
        while self.current.kind != "EOF":
            if not depth and self._at_stop(stop):
                break
            if self.current.value in pairs:
                depth.append(pairs[self.current.value])
                self.advance()
                continue
            if depth and self.current.value == depth[-1]:
                depth.pop()
                self.advance()
                continue
            if self.current.kind == "NEWLINE" and depth:
                self.advance()
                continue
            self.advance()
        if depth:
            self.fail("unclosed balanced value")
        if self.index == start:
            self.fail("expected value")
        raw = self.raw(start, self.index)
        return Value("raw", raw, raw)

    def _at_stop(self, stop: set[str]) -> bool:
        if self.current.kind == "NEWLINE" and "\n" in stop:
            return True
        if self.current.value == "@" and "@" in stop:
            return True
        if self.current.value in stop:
            return True
        if (
            "modifier-block" in stop
            and self.current.value == "{"
            and self.tokens[self.index + 1].kind == "NEWLINE"
        ):
            return True
        return False

    def list_value(self) -> Value:
        start = self.index
        self.require("[")
        values: list[Any] = []
        self.skip_newlines()
        if self.match("]"):
            return Value("list", values, self.raw(start, self.index))
        while True:
            values.append(self.value(stop={",", "]"}).to_json())
            self.skip_newlines()
            if self.match("]"):
                break
            self.require(",")
            self.skip_newlines()
        return Value("list", values, self.raw(start, self.index))

    def object_value(self) -> Value:
        start = self.index
        self.require("{")
        result: dict[str, Any] = {}
        self.skip_newlines()
        if self.match("}"):
            return Value("object", result, self.raw(start, self.index))
        while True:
            if self.current.kind == "STRING":
                key = json.loads(self.advance().value)
            else:
                key = self.name()
            self.require(":")
            result[key] = self.value(stop={",", "}"}).to_json()
            self.skip_newlines()
            if self.match("}"):
                break
            self.require(",")
            self.skip_newlines()
        return Value("object", result, self.raw(start, self.index))

    def raw(self, start: int, end: int) -> str:
        output = ""
        previous: Token | None = None
        for token in self.tokens[start:end]:
            if token.kind == "NEWLINE":
                output += "\n"
                previous = token
                continue
            no_space_before = token.value in {")", "]", "}", ",", ":", "?", ">", "."}
            no_space_after_previous = previous is None or previous.value in {
                "(", "[", "{", "<", ".", "@"
            }
            if (
                output
                and not output.endswith(("\n", " "))
                and not no_space_before
                and not no_space_after_previous
            ):
                output += " "
            output += token.value
            previous = token
        return output


def parse_source(source: str) -> Program:
    """Parse source using only the irreducible Bootstrap Kernel v1 grammar."""

    return _Parser(source).program()


def parse_type_ref(source: str) -> TypeRef:
    parser = _Parser(source)
    result = parser.type_ref()
    parser.skip_newlines()
    if parser.current.kind != "EOF":
        parser.fail("unexpected trailing TypeRef input")
    return result


def source_digest(source: str) -> str:
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def generate_projection(source: str) -> dict[str, Any]:
    """Derive the deterministic I1 Core registry projection from core.aidl."""

    program = parse_source(source)
    declarations: list[dict[str, Any]] = []
    for declaration in program.declarations:
        if declaration.kind != "declaration":
            raise BootstrapSyntaxError(
                "core source may only contain declaration meta-definitions, "
                f"found {declaration.kind!r}"
            )
        if declaration.name is None:
            raise BootstrapSyntaxError(
                "core declaration meta-definition requires a candidate name"
            )
        declarations.append(declaration.to_json())
    return {
        "schemaVersion": 1,
        "kernelVersion": KERNEL_VERSION,
        "sourceModule": program.module,
        "sourceSha256": source_digest(source),
        "declarations": declarations,
    }


def projection_text(source: str) -> str:
    return (
        json.dumps(
            generate_projection(source),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def check_projection(core_path: Path, projection_path: Path) -> None:
    expected = projection_text(core_path.read_text(encoding="utf-8"))
    actual = projection_path.read_text(encoding="utf-8")
    if actual != expected:
        raise BootstrapSyntaxError(
            f"Core projection drift: regenerate {projection_path} from {core_path}"
        )
