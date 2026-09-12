#!/usr/bin/env python3
"""Deterministic, read-only metrics for docs/06-grammar.md.

This module measures the normative target-grammar projection. Top-level declaration
coverage is derived from the frozen language-surface contract rather than from
legacy special-case EBNF alternatives, so documentation metrics cannot make a
second declaration inventory.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

GRAMMAR = Path("docs/06-grammar.md")
CONTRACT = Path("spec/language-surface-v1.json")
WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PRODUCTION_START = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\s*=(.*)$")
PRODUCTION_NAME_ONLY = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\s*$")
PRODUCTION_CONTINUATION_START = re.compile(r"^\s*=(.*)$")
TERMINAL = re.compile(r'"((?:\\.|[^"\\])*)"')


def ebnf_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading = "(preamble)"
    in_ebnf = False
    block: list[str] = []
    block_heading = heading
    for line in text.splitlines():
        stripped = line.strip()
        if line.startswith("## "):
            heading = line[3:].strip()
        if not in_ebnf and stripped == "~~~ebnf":
            in_ebnf = True
            block = []
            block_heading = heading
            continue
        if in_ebnf and stripped == "~~~":
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
        pending: str | None = None
        pieces: list[str] = []
        for line in block.splitlines():
            match = PRODUCTION_START.match(line)
            if match:
                if current is not None:
                    result[current] = (section, " ".join(pieces).strip())
                current = match.group(1)
                pending = None
                pieces = [match.group(2).strip()]
            elif current is None:
                name_only = PRODUCTION_NAME_ONLY.match(line)
                continuation_start = PRODUCTION_CONTINUATION_START.match(line)
                if name_only:
                    pending = name_only.group(1)
                    continue
                if pending is not None and continuation_start:
                    current = pending
                    pending = None
                    pieces = [continuation_start.group(1).strip()]
                elif line.strip():
                    pending = None
            else:
                pieces.append(line.strip())
            if current is not None and ";" in line:
                result[current] = (section, " ".join(pieces).strip())
                current = None
                pending = None
                pieces = []
        if current is not None:
            result[current] = (section, " ".join(pieces).strip())
    return result


def split_top_level_alternatives(rhs: str) -> list[str]:
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
    if not flags:
        flags.append("plain")
    starter = next((item for item in literals if WORD.fullmatch(item)), "<nonterminal>")
    return starter + ":" + "+".join(flags)


def _contract_declaration_kinds(contract_path: Path) -> list[str]:
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    if data.get("authority") != "M10.1" or data.get("status") != "frozen" or data.get("contract_revision") != 4:
        raise ValueError("frozen language contract identity drift")
    rows = data.get("declaration_kinds")
    if not isinstance(rows, list):
        raise ValueError("frozen language contract declaration_kinds drift")
    kinds = [row.get("kind") for row in rows if isinstance(row, dict)]
    if len(kinds) != len(rows) or not all(isinstance(kind, str) and kind for kind in kinds) or len(set(kinds)) != len(kinds):
        raise ValueError("frozen language contract declaration kind drift")
    return kinds


def measure(path: Path = GRAMMAR, contract_path: Path = CONTRACT) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    sections = ebnf_sections(text)
    prods = productions(sections)
    declaration_kinds = _contract_declaration_kinds(contract_path)

    terminals: set[str] = set()
    terminal_sections: dict[str, set[str]] = defaultdict(set)
    for section, block in sections:
        for terminal in TERMINAL.findall(block):
            terminals.add(terminal)
            terminal_sections[terminal].add(section)

    alternative_count = 0
    signatures: Counter[str] = Counter()
    marker_counts: Counter[str] = Counter()
    for _, rhs in prods.values():
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

    inline_block_duals = []
    for name, (_, rhs) in prods.items():
        alts = split_top_level_alternatives(rhs)
        if any('"{"' in alt for alt in alts) and any("newline" in alt for alt in alts):
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
        "contract": str(contract_path),
        "contract_revision": 4,
        "ebnf_sections": len(sections),
        "productions": len(prods),
        "production_alternatives": alternative_count,
        "quoted_terminals_total": len(terminals),
        "top_level_declaration_productions": len(declaration_kinds),
        "concrete_top_level_forms": len(declaration_kinds),
        "declaration_productions": declaration_kinds,
        "surface_signatures": len(signatures),
        "surface_signature_counts": dict(sorted(signatures.items())),
        "structural_markers": dict(sorted(marker_counts.items())),
        "inline_block_dual_productions": sorted(inline_block_duals),
        "terminals_by_section": by_section,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=GRAMMAR)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(measure(args.path, args.contract), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
