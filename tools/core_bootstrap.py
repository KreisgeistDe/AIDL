from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KERNEL_VERSION = 1
KERNEL_META_COMBINATORS = ("name", "args", "body", "cardinal", "modifier")


class BootstrapSyntaxError(ValueError):
    """Raised when source is outside the versioned bootstrap-kernel grammar."""


@dataclass(frozen=True)
class TypeRef:
    name: str
    arguments: tuple["TypeRef", ...] = ()
    optional: bool = False

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": [item.to_json() for item in self.arguments], "optional": self.optional}


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
        return {"name": self.name, "arguments": {name: value.to_json() for name, value in self.arguments}}


@dataclass(frozen=True)
class BodyEntry:
    body_type: str
    name: str | None
    value: Value | None
    modifiers: tuple[ModifierCall, ...]
    form: str

    def to_json(self) -> dict[str, Any]:
        return {"bodyType": self.body_type, "name": self.name, "value": None if self.value is None else self.value.to_json(), "modifiers": [item.to_json() for item in self.modifiers], "form": self.form}


@dataclass(frozen=True)
class NamedArgument:
    name: str
    type_ref: TypeRef
    optional: bool = False
    default: Value | None = None


@dataclass(frozen=True)
class GenericParameter:
    name: str
    constraint: TypeRef | None = None


@dataclass(frozen=True)
class Declaration:
    kind: str
    name: str | None
    exported: bool
    arguments: tuple[tuple[str, Value], ...]
    arguments_present: bool
    result: TypeRef | None
    body: tuple[BodyEntry, ...]
    declaration_type: TypeRef | None = None
    generic_parameters: tuple[GenericParameter, ...] = ()
    argument_specs: tuple[NamedArgument, ...] = ()
    open_arguments_binder: str | None = None

    def to_json(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "name": self.name,
            "exported": self.exported,
            "arguments": ({name: value.to_json() for name, value in self.arguments} if self.arguments_present else None),
            "result": None if self.result is None else self.result.to_json(),
            "body": [item.to_json() for item in self.body],
        }
        if self.declaration_type is not None and (self.declaration_type.arguments or self.declaration_type.optional):
            result["declarationType"] = self.declaration_type.to_json()
        if self.generic_parameters:
            result["genericParameters"] = [{"name": item.name, "constraint": None if item.constraint is None else item.constraint.to_json()} for item in self.generic_parameters]
        if self.open_arguments_binder is not None:
            result["openArgumentsBinder"] = self.open_arguments_binder
        return result


@dataclass(frozen=True)
class Program:
    module: str | None
    imports: tuple[str, ...]
    declarations: tuple[Declaration, ...]
    import_aliases: tuple[tuple[str, str | None], ...] = ()


@dataclass(frozen=True)
class KernelTerm:
    name: str
    arguments: tuple["KernelTerm | str | int | float | bool | None", ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": [item.to_json() if isinstance(item, KernelTerm) else item for item in self.arguments]}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


_MULTI = ("...", "->", "..", "||", "&&", "==", "!=", "<=", ">=")
_SINGLE = set("{}[]()<>,:?.@;=+-*/%!$")
_LEVELS: tuple[tuple[str, ...], ...] = (("||",), ("&&",), ("==", "!="), ("<", "<=", ">", ">="), ("+", "-"), ("*", "/", "%"))


def _advance_position(text: str, line: int, column: int) -> tuple[int, int]:
    for char in text:
        if char == "\n":
            line, column = line + 1, 1
        else:
            column += 1
    return line, column


def _validate_interpolation(raw: str, multiline: bool) -> None:
    if multiline:
        positions = [p for p in (raw.find("\n"), raw.find("\r")) if p >= 0]
        body = raw[min(positions) + 1 : -3]
    else:
        body = raw[1:-1]
    i = 0
    while i < len(body):
        if not multiline and body[i] == "\\":
            i += 2
            continue
        if body[i] != "$":
            i += 1
            continue
        if body.startswith("$$", i):
            i += 2
            continue
        if body.startswith("${", i):
            depth, j, quote, escaped = 1, i + 2, False, False
            while j < len(body) and depth:
                c = body[j]
                if quote:
                    if escaped:
                        escaped = False
                    elif c == "\\":
                        escaped = True
                    elif c == '"':
                        quote = False
                elif c == '"':
                    quote = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                j += 1
            if depth:
                raise BootstrapSyntaxError("unterminated ${...} string interpolation")
            parser = _Parser(body[i + 2 : j - 1])
            parser.skip_newlines()
            parser.expression()
            parser.skip_newlines()
            if parser.current.kind != "EOF":
                parser.fail("unexpected trailing interpolation expression")
            i = j
            continue
        j = i + 1
        if j >= len(body) or not (body[j].isalpha() or body[j] == "_"):
            raise BootstrapSyntaxError("'$' must be '$$', $qualified.name or ${expr}")
        j += 1
        while j < len(body) and (body[j].isalnum() or body[j] == "_"):
            j += 1
        while j < len(body) and body[j] == ".":
            j += 1
            if j >= len(body) or not (body[j].isalpha() or body[j] == "_"):
                raise BootstrapSyntaxError("malformed qualified string interpolation")
            j += 1
            while j < len(body) and (body[j].isalnum() or body[j] == "_"):
                j += 1
        i = j


def _decode_string(raw: str) -> str:
    if raw.startswith('"""'):
        starts = [p for p in (raw.find("\n"), raw.find("\r")) if p >= 0]
        p = min(starts)
        p += 2 if raw[p : p + 2] == "\r\n" else 1
        return raw[p:-3]
    body, out, i = raw[1:-1], "", 0
    escapes = {'"': '"', "\\": "\\", "n": "\n", "r": "\r", "t": "\t", "$": "$"}
    while i < len(body):
        if body[i] == "\\":
            out += escapes[body[i + 1]]
            i += 2
        else:
            out += body[i]
            i += 1
    return out


def _tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i, line, col, size = 0, 1, 1, len(source)
    while i < size:
        c = source[i]
        if c in " \t":
            i, col = i + 1, col + 1
            continue
        if source.startswith("\r\n", i):
            tokens.append(Token("NEWLINE", "\n", line, col)); i += 2; line += 1; col = 1; continue
        if c in "\r\n":
            tokens.append(Token("NEWLINE", "\n", line, col)); i += 1; line += 1; col = 1; continue
        if source.startswith("//", i):
            while i < size and source[i] not in "\r\n": i += 1; col += 1
            continue
        if source.startswith("/*", i):
            depth = 1; i += 2; col += 2
            while i < size and depth:
                if source.startswith("/*", i): depth += 1; i += 2; col += 2
                elif source.startswith("*/", i): depth -= 1; i += 2; col += 2
                elif source.startswith("\r\n", i): tokens.append(Token("NEWLINE", "\n", line, col)); i += 2; line += 1; col = 1
                elif source[i] in "\r\n": tokens.append(Token("NEWLINE", "\n", line, col)); i += 1; line += 1; col = 1
                else: i += 1; col += 1
            if depth: raise BootstrapSyntaxError("unterminated block comment")
            continue
        if source.startswith('"""', i):
            sl, sc = line, col; end = source.find('"""', i + 3)
            if end < 0: raise BootstrapSyntaxError(f"unterminated multiline string at {sl}:{sc}")
            raw = source[i:end + 3]
            poss = [p for p in (raw.find("\n"), raw.find("\r")) if p >= 0]
            if not poss: raise BootstrapSyntaxError(f"multiline string opening delimiter must be followed by newline at {sl}:{sc}")
            header = raw[3:min(poss)]
            if header and (not (header[0].isalpha() or header[0] == "_") or not all(ch.isalnum() or ch == "_" for ch in header)):
                raise BootstrapSyntaxError(f"invalid embedded-language tag at {sl}:{sc}")
            _validate_interpolation(raw, True)
            tokens.append(Token("STRING", raw, sl, sc)); line, col = _advance_position(raw, line, col); i = end + 3; continue
        if c == '"':
            sl, sc, start = line, col, i; i += 1; col += 1; escaped = False
            while i < size:
                cur = source[i]
                if cur in "\r\n": raise BootstrapSyntaxError(f"newline in string at {sl}:{sc}")
                i += 1; col += 1
                if escaped:
                    if cur not in {'"', "\\", "n", "r", "t", "$"}: raise BootstrapSyntaxError(f"unsupported escape \\{cur} at {sl}:{sc}")
                    escaped = False; continue
                if cur == "\\": escaped = True; continue
                if cur == '"': break
            else: raise BootstrapSyntaxError(f"unterminated string at {sl}:{sc}")
            raw = source[start:i]; _validate_interpolation(raw, False); tokens.append(Token("STRING", raw, sl, sc)); continue
        matched = next((x for x in _MULTI if source.startswith(x, i)), None)
        if matched:
            tokens.append(Token("SYMBOL", matched, line, col)); i += len(matched); col += len(matched); continue
        if c.isdigit():
            start, sc = i, col
            while i < size and source[i].isdigit(): i += 1; col += 1
            if i < size and source[i] == "." and not source.startswith("..", i):
                if i + 1 >= size or not source[i + 1].isdigit(): raise BootstrapSyntaxError(f"malformed decimal at {line}:{sc}")
                i += 1; col += 1
                while i < size and source[i].isdigit(): i += 1; col += 1
                tokens.append(Token("DECIMAL", source[start:i], line, sc))
            else: tokens.append(Token("INTEGER", source[start:i], line, sc))
            continue
        if c.isalpha() or c == "_":
            start, sc = i, col; i += 1; col += 1
            while i < size and (source[i].isalnum() or source[i] == "_"): i += 1; col += 1
            tokens.append(Token("IDENT", source[start:i], line, sc)); continue
        if c in _SINGLE:
            tokens.append(Token("SYMBOL", c, line, col)); i += 1; col += 1; continue
        raise BootstrapSyntaxError(f"unexpected character {c!r} at {line}:{col}")
    tokens.append(Token("EOF", "", line, col))
    return tokens


class _Parser:
    def __init__(self, source: str) -> None:
        self.tokens, self.index = _tokenize(source), 0

    @property
    def current(self) -> Token: return self.tokens[self.index]
    def peek(self, offset: int = 1) -> Token: return self.tokens[min(self.index + offset, len(self.tokens) - 1)]
    def advance(self) -> Token:
        token = self.current
        if token.kind != "EOF": self.index += 1
        return token
    def match(self, value: str) -> bool:
        if self.current.value == value: self.advance(); return True
        return False
    def require(self, value: str) -> Token:
        if not self.match(value): self.fail(f"expected {value!r}")
        return self.tokens[self.index - 1]
    def name(self) -> str:
        if self.current.kind != "IDENT": self.fail("expected identifier")
        return self.advance().value
    def fail(self, message: str) -> None:
        t = self.current; raise BootstrapSyntaxError(f"{message} at {t.line}:{t.column}; found {t.value!r}")
    def skip_newlines(self) -> None:
        while self.current.kind == "NEWLINE": self.advance()
    def newline_then(self, values: set[str]) -> bool:
        j = self.index
        if self.tokens[j].kind != "NEWLINE": return False
        while self.tokens[j].kind == "NEWLINE": j += 1
        if self.tokens[j].value in values: self.index = j; return True
        return False
    def statement_end(self, required: bool) -> bool:
        if self.match(";"): self.skip_newlines(); return True
        if self.current.kind == "NEWLINE": self.skip_newlines(); return True
        if required: self.fail("expected semicolon or terminating newline")
        return False

    def program(self) -> Program:
        self.skip_newlines()
        if not self.match("module"): self.fail("source-file must begin with module declaration")
        module = self.qualified_name(); self.statement_end(True)
        imports: list[str] = []; aliases: list[tuple[str, str | None]] = []
        while self.current.value == "import":
            self.advance(); imported = self.qualified_name(); alias = self.name() if self.match("as") else None
            imports.append(imported); aliases.append((imported, alias)); self.statement_end(True); self.skip_newlines()
        declarations: list[Declaration] = []
        while self.current.kind != "EOF": declarations.append(self.declaration()); self.skip_newlines()
        return Program(module, tuple(imports), tuple(declarations), tuple(aliases))

    def qualified_name(self) -> str:
        parts = [self.name()]
        while self.match("."): parts.append(self.name())
        return ".".join(parts)

    def type_ref(self) -> TypeRef:
        name = self.qualified_name(); args: list[TypeRef] = []
        if self.match("<"):
            self.skip_newlines()
            if self.match("> "): self.fail("generic TypeRef requires at least one argument")
            if self.current.value == ">": self.fail("generic TypeRef requires at least one argument")
            while True:
                args.append(self.type_ref()); self.skip_newlines()
                if self.match(">"): break
                self.require(","); self.skip_newlines()
        return TypeRef(name, tuple(args), self.match("?"))

    def generic_parameters(self) -> tuple[GenericParameter, ...]:
        self.require("<"); self.skip_newlines()
        if self.current.value == ">": self.fail("generic parameter list must not be empty")
        result: list[GenericParameter] = []
        while True:
            name = self.name(); constraint = None
            if self.match(":"): self.skip_newlines(); constraint = self.type_ref()
            result.append(GenericParameter(name, constraint)); self.skip_newlines()
            if self.match(">"): return tuple(result)
            self.require(","); self.skip_newlines()

    def declaration(self) -> Declaration:
        exported = self.match("export"); decl_type = self.type_ref(); name = self.name()
        generics = self.generic_parameters() if self.current.value == "<" else ()
        present = self.match("("); arguments: tuple[tuple[str, Value], ...] = (); specs: tuple[NamedArgument, ...] = (); binder = None
        if present: arguments, specs, binder = self.declaration_arguments()
        result = self.type_ref() if self.match("->") else None
        body: tuple[BodyEntry, ...] = (); has_body = False
        if self.match("{"): has_body = True; body = self.declaration_body()
        if has_body: self.statement_end(False)
        elif self.current.kind != "EOF": self.statement_end(True)
        return Declaration(decl_type.name, name, exported, arguments, present, result, body, decl_type, generics, specs, binder)

    def declaration_arguments(self) -> tuple[tuple[tuple[str, Value], ...], tuple[NamedArgument, ...], str | None]:
        self.skip_newlines()
        if self.match(")"): self.fail("empty declaration argument list '()' is invalid; omit it for a closed zero-parameter contract")
        if self.current.kind == "IDENT" and self.peek().value == "?" and self.peek(2).value == ":" and self.peek(3).value == "...":
            binder = self.advance().value; self.advance(); self.advance(); self.advance(); self.skip_newlines(); self.require(")"); return (), (), binder
        values: list[tuple[str, Value]] = []; specs: list[NamedArgument] = []
        while True:
            name = self.name(); optional = self.match("?"); self.require(":"); self.skip_newlines(); typ = self.type_ref(); default = None
            if self.match("="): self.skip_newlines(); default = self.value({",", ")"}, False)
            values.append((name, default or Value("typeRef", typ, self.format_type(typ)))); specs.append(NamedArgument(name, typ, optional, default)); self.skip_newlines()
            if self.match(")"): return tuple(values), tuple(specs), None
            self.require(","); self.skip_newlines()

    def declaration_body(self) -> tuple[BodyEntry, ...]:
        result: list[BodyEntry] = []; self.skip_newlines()
        while not self.match("}"):
            if self.current.kind == "EOF": self.fail("unclosed declaration body")
            result.append(self.body_entry()); self.skip_newlines()
        return tuple(result)

    def body_entry(self) -> BodyEntry:
        body_type = self.qualified_name(); name = self.advance().value if self.current.kind == "IDENT" else None; value = None
        if self.match(":"): self.skip_newlines(); value = self.value({";", "@", "}"}, True)
        modifiers: list[ModifierCall] = []
        while True:
            if self.current.value == "@": modifiers.append(self.modifier()); continue
            if self.newline_then({"@"}): self.skip_newlines(); modifiers.append(self.modifier()); continue
            break
        if self.match(";"): form = "inline"; self.skip_newlines()
        elif self.current.kind == "NEWLINE": self.skip_newlines(); form = "continued" if modifiers else "inline"
        elif self.current.value == "}": form = "inline"
        else: self.fail("expected body-entry terminator, modifier or declaration close")
        return BodyEntry(body_type, name, value, tuple(modifiers), form)

    def modifier(self) -> ModifierCall:
        self.require("@"); name = self.name(); args: list[tuple[str, Value]] = []
        if self.match("("):
            self.skip_newlines()
            if self.match(")"): return ModifierCall(name)
            pos = 0
            while True:
                if self.current.kind == "IDENT" and self.peek().value == ":": arg_name = self.advance().value; self.advance(); self.skip_newlines()
                else: arg_name = f"${pos}"
                args.append((arg_name, self.value({",", ")"}, False))); pos += 1; self.skip_newlines()
                if self.match(")"): break
                self.require(","); self.skip_newlines()
        return ModifierCall(name, tuple(args))

    def value(self, stop: set[str], allow_newline_stop: bool = True) -> Value:
        start = self.index
        if self.current.kind == "IDENT":
            saved = self.index
            try:
                typ = self.type_ref()
                if self.current.value in stop or (allow_newline_stop and self.current.kind == "NEWLINE") or self.current.kind == "EOF":
                    return Value("typeRef", typ, self.raw(start, self.index))
            except BootstrapSyntaxError:
                pass
            self.index = saved
        self.expression(stop, allow_newline_stop)
        if self.index == start: self.fail("expected value")
        raw = self.raw(start, self.index); first = self.tokens[start]
        if self.index == start + 1 and first.kind == "STRING": return Value("string", _decode_string(first.value), first.value)
        if self.index == start + 1 and first.kind in {"INTEGER", "DECIMAL"}: return Value("number", int(first.value) if first.kind == "INTEGER" else float(first.value), first.value)
        if self.index == start + 1 and first.value in {"true", "false", "null"}: return Value("literal", {"true": True, "false": False, "null": None}[first.value], first.value)
        if first.value == "[" and self.tokens[self.index - 1].value == "]": return Value("list", self.list_json(raw), raw)
        return Value("raw", raw, raw)

    def expression(self, stop: set[str] | None = None, allow_newline_stop: bool = True) -> None: self.binary(0, stop or set(), allow_newline_stop)
    def binary(self, level: int, stop: set[str], allow_newline_stop: bool) -> None:
        if level == len(_LEVELS): self.unary(stop, allow_newline_stop); return
        self.binary(level + 1, stop, allow_newline_stop); ops = set(_LEVELS[level])
        while True:
            if self.current.kind == "NEWLINE":
                if allow_newline_stop and not self.newline_then(ops): return
                self.skip_newlines()
            if self.current.value not in ops: return
            self.advance(); self.skip_newlines(); self.binary(level + 1, stop, allow_newline_stop)
    def unary(self, stop: set[str], allow_newline_stop: bool) -> None:
        if self.current.value in {"!", "-", "+"}: self.advance(); self.skip_newlines(); self.unary(stop, allow_newline_stop); return
        self.postfix(stop, allow_newline_stop)
    def postfix(self, stop: set[str], allow_newline_stop: bool) -> None:
        self.primary(stop, allow_newline_stop)
        while True:
            if self.current.kind == "NEWLINE":
                if allow_newline_stop and not self.newline_then({".", "(", "["}): return
                self.skip_newlines()
            if self.match("."): self.name(); continue
            if self.match("("):
                self.skip_newlines()
                if self.match(")"): continue
                while True:
                    if self.current.kind == "IDENT" and self.peek().value == ":": self.advance(); self.advance(); self.skip_newlines()
                    self.expression({",", ")"}, False); self.skip_newlines()
                    if self.match(")"): break
                    self.require(","); self.skip_newlines()
                continue
            if self.match("["):
                self.skip_newlines(); self.expression({"]"}, False); self.skip_newlines(); self.require("]"); continue
            return
    def primary(self, stop: set[str], allow_newline_stop: bool) -> None:
        token = self.current
        if token.value in stop or (allow_newline_stop and token.kind == "NEWLINE"): self.fail("expected expression")
        if token.kind == "INTEGER":
            self.advance()
            if self.match(".."): self.skip_newlines(); self.advance() if self.current.kind == "INTEGER" or self.current.value == "*" else self.fail("range upper bound must be unsigned integer or '*'")
            return
        if token.kind in {"DECIMAL", "STRING"} or token.value in {"true", "false", "null"}: self.advance(); return
        if token.kind == "IDENT": self.qualified_name(); return
        if self.match("("): self.skip_newlines(); self.expression({")"}, False); self.skip_newlines(); self.require(")"); return
        if self.match("["):
            self.skip_newlines()
            if self.match("]"): return
            while True:
                self.expression({",", "]"}, False); self.skip_newlines()
                if self.match("]"): return
                self.require(","); self.skip_newlines()
        self.fail("expected expression primary")

    def kernel_term(self) -> KernelTerm:
        name = self.name()
        if name not in KERNEL_META_COMBINATORS: self.fail(f"unknown bootstrap meta-combinator {name!r}")
        self.require("("); args: list[KernelTerm | str | int | float | bool | None] = []; self.skip_newlines()
        if self.match(")"): return KernelTerm(name)
        while True:
            args.append(self.kernel_atom()); self.skip_newlines()
            if self.match(")"): return KernelTerm(name, tuple(args))
            self.require(","); self.skip_newlines()
    def kernel_atom(self) -> KernelTerm | str | int | float | bool | None:
        token = self.current
        if token.kind == "STRING": self.advance(); return _decode_string(token.value)
        if token.kind in {"INTEGER", "DECIMAL"}: self.advance(); return int(token.value) if token.kind == "INTEGER" else float(token.value)
        if token.value in {"true", "false", "null"}: self.advance(); return {"true": True, "false": False, "null": None}[token.value]
        if token.kind == "IDENT":
            if token.value in KERNEL_META_COMBINATORS and self.peek().value == "(": return self.kernel_term()
            return self.qualified_name()
        self.fail("expected bootstrap meta-combinator argument")

    def raw(self, start: int, end: int) -> str:
        out, previous = "", None; no_before = {")", "]", "}", ",", ":", "?", ">", ".", ";", "(", "["}; no_after = {"(", "[", "{", "<", ".", "@", "$"}
        for token in self.tokens[start:end]:
            if token.kind == "NEWLINE": out += "\n"; previous = token; continue
            if out and not out.endswith(("\n", " ")) and token.value not in no_before and (previous is None or previous.value not in no_after): out += " "
            out += token.value; previous = token
        return out
    @staticmethod
    def format_type(typ: TypeRef) -> str:
        out = typ.name
        if typ.arguments: out += "<" + ", ".join(_Parser.format_type(item) for item in typ.arguments) + ">"
        return out + ("?" if typ.optional else "")
    @staticmethod
    def list_json(raw: str) -> list[Any]:
        parser = _Parser(raw); parser.require("["); parser.skip_newlines(); result: list[Any] = []
        if parser.match("]"): return result
        while True:
            result.append(parser.value({",", "]"}, False).to_json()); parser.skip_newlines()
            if parser.match("]"): return result
            parser.require(","); parser.skip_newlines()


def _validate_bindings(program: Program) -> None:
    imports = [alias or name.rsplit(".", 1)[-1] for name, alias in program.import_aliases]
    if len(imports) != len(set(imports)): raise BootstrapSyntaxError("duplicate or ambiguous bootstrap import binding")
    seen: dict[str, str] = {}
    for declaration in program.declarations:
        if declaration.name is None: continue
        previous = seen.get(declaration.name)
        if previous is not None: raise BootstrapSyntaxError(f"duplicate or ambiguous bootstrap binding {declaration.name!r}: {previous!r} and {declaration.kind!r}")
        seen[declaration.name] = declaration.kind


def parse_source(source: str) -> Program:
    """Parse the binding AIDL Core source-file grammar without domain knowledge."""
    return _Parser(source).program()


def parse_bootstrap_source(source: str) -> Program:
    program = parse_source(source); _validate_bindings(program); return program


def parse_type_ref(source: str) -> TypeRef:
    parser = _Parser(source); result = parser.type_ref(); parser.skip_newlines()
    if parser.current.kind != "EOF": parser.fail("unexpected trailing TypeRef input")
    return result


def parse_expression(source: str) -> Value:
    parser = _Parser(source); parser.skip_newlines(); result = parser.value(set(), False); parser.skip_newlines()
    if parser.current.kind != "EOF": parser.fail("unexpected trailing expression input")
    return result


def parse_meta_combinator(source: str) -> KernelTerm:
    parser = _Parser(source); result = parser.kernel_term(); parser.skip_newlines()
    if parser.current.kind != "EOF": parser.fail("unexpected trailing bootstrap meta-combinator input")
    return result


def source_digest(source: str) -> str:
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def generate_projection(source: str) -> dict[str, Any]:
    program = parse_bootstrap_source(source)
    return {"schemaVersion": 1, "kernelVersion": KERNEL_VERSION, "sourceModule": program.module, "sourceSha256": source_digest(source), "declarations": [declaration.to_json() for declaration in program.declarations]}


def projection_text(source: str) -> str:
    return json.dumps(generate_projection(source), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def check_projection(core_path: Path, projection_path: Path) -> None:
    expected = projection_text(core_path.read_text(encoding="utf-8")); actual = projection_path.read_text(encoding="utf-8")
    if actual != expected: raise BootstrapSyntaxError(f"Core projection drift: regenerate {projection_path} from {core_path}")
