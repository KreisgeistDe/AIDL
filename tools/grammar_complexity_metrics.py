#!/usr/bin/env python3
"""Deterministic, read-only metrics for docs/06-grammar.md.

This module measures the normative grammar text. It is review tooling only: it
neither parses AIDL source nor changes compiler/language behavior.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

GRAMMAR = Path("docs/06-grammar.md")
WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PRODUCTION_START = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\s*=(.*)$")
TERMINAL = re.compile(r'"((?:\\.|[^"\\])*)"')


def ebnf_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading = "(preamble)"
    in_ebnf = False
    block: list[str] = []
    block_heading = heading
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
        if line.strip() == "~~~ebnf":
            if not in_ebnf:
                in_ebnf = True
                block = []
                block_heading = heading
            else:
                sections.append((block_heading, "\n".join(block)))
                in_ebnf = False
            continue
        if in_ebnf:
            block.append(line)
    return sections


def productions(sections: list[tuple[str, str]]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for section, block in sections:
        current: str | None = None
        pieces: list[str] = []
        for line in block.splitlines():
            match = PRODUCTION_START.match(line)
            if match:
                if current is not None:
                    result[current] = (section, " ".join(pieces).strip())
                current = match.group(1)
                pieces = [match.group(2).strip()]
            elif current is not None:
                pieces.append(line.strip())
            if current is not None and ";" in line:
                result[current] = (section, " ".join(pieces).strip())
                current = None
                pieces = []
        if current is not None:
            result[current] = (section, " ".join(pieces).strip())
    return result


def split_top_level_alternatives(rhs: str) -> list[str]:
    """Split EBNF alternatives at un-nested | tokens."""
    result: list[str] = []
    start = 0
    stack: list[str] = []
    quote = False
    escaped = False
    pairs = {')': '(', ']': '[', '}': '{'}
    for index, char in enumerate(rhs):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = False
            continue
        if char == '"':
            quote = True
            continue
        if char in "([{":
            stack.append(char)
        elif char in ")]}" and stack and stack[-1] == pairs[char]:
            stack.pop()
        elif char == "|" and not stack:
            result.append(rhs[start:index].strip())
            start = index + 1
    result.append(rhs[start:].strip().rstrip(" ;"))
    return [item for item in result if item]


def pattern_signature(alt: str) -> str:
    """Return a coarse surface-shape signature, deliberately syntax-only."""
    literals = TERMINAL.findall(alt)
    flags: list[str] = []
    if '"{"' in alt:
        flags.append("block")
    if "newline" in alt:
        flags.append("leaf")
    if '":"' in alt:
        flags.append("colon")
    if '"="' in alt:
        flags.append("equals")
    if '"->"' in alt:
        flags.append("arrow")
    if '"["' in alt:
        flags.append("list")
    if '"("' in alt:
        flags.append("paren")
    if "profileProperty" in alt or "uiStatement" in alt or "testStatement" in alt:
        flags.append("generic-sublanguage")
    if not flags:
        flags.append("plain")
    starter = next((item for item in literals if WORD.fullmatch(item)), "<nonterminal>")
    return starter + ":" + "+".join(flags)


def measure(path: Path = GRAMMAR) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    sections = ebnf_sections(text)
    prods = productions(sections)

    terminals: set[str] = set()
    terminal_sections: dict[str, set[str]] = defaultdict(set)
    for section, block in sections:
        for terminal in TERMINAL.findall(block):
            terminals.add(terminal)
            terminal_sections[terminal].add(section)

    lexical_names = {
        "letter", "digit", "identifier", "typeName", "upperLetter", "qualifiedName",
        "integer", "decimalLiteral", "percentage", "durationLiteral", "byteLiteral",
        "cpuLiteral", "number", "string", "regex", "comment", "annotation", "newline",
    }
    lexical_terminals: set[str] = set()
    for name in lexical_names:
        item = prods.get(name)
        if item:
            lexical_terminals.update(TERMINAL.findall(item[1]))

    syntax_terminals = terminals - lexical_terminals
    syntax_words = sorted(item for item in syntax_terminals if WORD.fullmatch(item))
    syntax_symbols = sorted(item for item in syntax_terminals if not WORD.fullmatch(item))
    lexical_words = sorted(item for item in lexical_terminals if WORD.fullmatch(item))
    lexical_symbols = sorted(item for item in lexical_terminals if not WORD.fullmatch(item))

    declaration_rhs = prods["declaration"][1]
    declaration_alts = split_top_level_alternatives(declaration_rhs)
    declaration_refs = [re.sub(r"[ ;]", "", item) for item in declaration_alts]
    concrete_top_level_forms = len(declaration_refs) + 1  # aliasDecl => alias | opaque

    alternative_count = 0
    signatures: Counter[str] = Counter()
    marker_counts: Counter[str] = Counter()
    for name, (_, rhs) in prods.items():
        alts = split_top_level_alternatives(rhs)
        alternative_count += len(alts)
        for alt in alts:
            signatures[pattern_signature(alt)] += 1
            if '"{"' in alt:
                marker_counts["block_alternatives"] += 1
            if "newline" in alt:
                marker_counts["leaf_alternatives"] += 1
            if '":"' in alt:
                marker_counts["colon_alternatives"] += 1
            if '"="' in alt:
                marker_counts["equals_alternatives"] += 1
            if '"->"' in alt:
                marker_counts["arrow_alternatives"] += 1
            if '"["' in alt:
                marker_counts["list_alternatives"] += 1
            if "profileProperty" in alt:
                marker_counts["profile_property_alternatives"] += 1
            if "uiStatement" in alt:
                marker_counts["ui_statement_alternatives"] += 1
            if "testStatement" in alt:
                marker_counts["test_statement_alternatives"] += 1

    inline_block_duals = []
    for name, (_, rhs) in prods.items():
        alts = split_top_level_alternatives(rhs)
        has_block = any('"{"' in alt for alt in alts)
        has_leaf = any("newline" in alt for alt in alts)
        if has_block and has_leaf:
            inline_block_duals.append(name)

    by_section: dict[str, dict[str, int]] = {}
    for section, _ in sections:
        unique = {term for term, places in terminal_sections.items() if section in places}
        by_section[section] = {
            "unique_terminals": len(unique),
            "word_terminals": sum(bool(WORD.fullmatch(item)) for item in unique),
            "symbol_terminals": sum(not bool(WORD.fullmatch(item)) for item in unique),
        }

    return {
        "grammar": str(path),
        "ebnf_sections": len(sections),
        "productions": len(prods),
        "production_alternatives": alternative_count,
        "quoted_terminals_total": len(terminals),
        "lexical_terminals": len(lexical_terminals),
        "lexical_word_terminals": len(lexical_words),
        "lexical_symbol_terminals": len(lexical_symbols),
        "syntax_terminals": len(syntax_terminals),
        "syntax_word_terminals": len(syntax_words),
        "syntax_symbol_terminals": len(syntax_symbols),
        "top_level_declaration_productions": len(declaration_refs),
        "concrete_top_level_forms": concrete_top_level_forms,
        "declaration_productions": declaration_refs,
        "surface_signatures": len(signatures),
        "surface_signature_counts": dict(sorted(signatures.items())),
        "structural_markers": dict(sorted(marker_counts.items())),
        "inline_block_dual_productions": sorted(inline_block_duals),
        "syntax_word_terminal_values": syntax_words,
        "lexical_word_terminal_values": lexical_words,
        "terminals_by_section": by_section,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=GRAMMAR)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(measure(args.path), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
