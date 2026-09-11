"""Contract-driven M10.1 operation-body parity for the production bridge.

This adapter extends the existing ``LanguageSurfaceBridge`` only for body-slot
shapes already declared by ``spec/language-surface-v1.json``. It intentionally
owns no clause inventory of its own: the frozen contract remains the only table
that decides which query/mutation body facts may enter canonical semantics.
"""

from __future__ import annotations

from typing import Any, Mapping

try:
    from .aidl_parser import Node
    from .compiler_language_surface import (
        BodySlot,
        BridgeDiagnostic,
        Declaration,
        LanguageSurfaceBridge,
        UnsupportedMigration,
        _after_keyword,
        _annotation_prefix,
        _format_parameter_list,
        _format_type,
        _literal,
        _surface,
    )
except ImportError:  # pragma: no cover
    from aidl_parser import Node
    from compiler_language_surface import (
        BodySlot,
        BridgeDiagnostic,
        Declaration,
        LanguageSurfaceBridge,
        UnsupportedMigration,
        _after_keyword,
        _annotation_prefix,
        _format_parameter_list,
        _format_type,
        _literal,
        _surface,
    )


class ContractBodyParityBridge(LanguageSurfaceBridge):
    """Normalize only contract-declared scalar operation body slots losslessly."""

    def _body(
        self,
        node: Node,
        kind: str,
        schema: Mapping[str, Any],
        diagnostics: list[BridgeDiagnostic],
    ) -> list[BodySlot]:
        start = len(diagnostics)
        result = super()._body(node, kind, schema, diagnostics)
        if kind not in {"query", "mutation"}:
            return result

        specs = {item["id"]: item for item in schema.get("body_slots", [])}
        normalized_texts: set[str] = set()
        for child in node.children:
            text = _surface(child.name or "")
            if not text:
                continue
            for slot_id, spec in specs.items():
                if slot_id == "read" or spec.get("name_policy") != "none":
                    continue
                mode = spec.get("value_mode")
                if mode not in {"expression", "literal"}:
                    continue
                if not (text.startswith(f"{slot_id}:") or text.startswith(f"{slot_id} ")):
                    continue
                value: Any = _after_keyword(text, slot_id)
                if mode == "literal":
                    value = _literal(value)
                result.append(BodySlot(slot_id, None, str(mode), value))
                normalized_texts.add(text)
                break

        if normalized_texts:
            diagnostics[start:] = [
                item
                for item in diagnostics[start:]
                if not (
                    item.code == "AIDL-N010"
                    and any(
                        item.message == f"legacy body clause not normalized yet: {text}"
                        for text in normalized_texts
                    )
                )
            ]

        canonical_order = {
            item["id"]: index
            for index, item in enumerate(schema.get("body_slots", []))
            if item.get("order") == "canonical"
        }
        result.sort(key=lambda slot: (canonical_order.get(slot.slot_id, len(canonical_order)), slot.slot_id))
        return result

    def format_legacy(self, declaration: Declaration) -> str:
        if declaration.kind not in {"query", "mutation"}:
            return super().format_legacy(declaration)
        prefix = _annotation_prefix(declaration.modifiers) + (
            "export " if declaration.exported else ""
        )
        headers = {item.name: item.value for item in declaration.header_args}
        result_type = (
            f" -> {_format_type(declaration.result_type)}"
            if declaration.result_type
            else ""
        )
        parameters = _format_parameter_list(headers.get("parameters", ()))
        lines = [
            f"{prefix}{declaration.kind} {declaration.name}({parameters}){result_type} {{"
        ]
        lines.extend(f"  {slot.slot_id}: {slot.value}" for slot in declaration.body_slots)
        return "\n".join(lines + ["}"]) + "\n"

    def migrate_to_canonical_preview(self, declaration: Declaration) -> str:
        if declaration.kind in {"query", "mutation"} and any(
            slot.slot_id != "read" for slot in declaration.body_slots
        ):
            raise UnsupportedMigration(
                "operation body target syntax is not yet a separately versioned production parser surface"
            )
        return super().migrate_to_canonical_preview(declaration)
