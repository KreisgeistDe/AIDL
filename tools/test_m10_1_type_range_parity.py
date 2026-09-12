from __future__ import annotations

import json

try:
    from .aidl_parser import Node
    from .compiler_language_surface import LanguageSurfaceBridge, _format_type
except ImportError:  # pragma: no cover
    from aidl_parser import Node
    from compiler_language_surface import LanguageSurfaceBridge, _format_type


def _operation(kind: str, parameters: str, returns: str) -> Node:
    return Node(
        kind=kind,
        name="bounded",
        attrs={"parameters": parameters, "returns": returns},
        children=[],
    )


def _parameter_type(declaration):
    header = next(item for item in declaration.header_args if item.name == "parameters")
    return header.value[0].type_ref


def test_query_range_constraints_are_structured_and_deterministic() -> None:
    bridge = LanguageSurfaceBridge()
    declaration, diagnostics = bridge.normalize_declaration(
        _operation("query", "(limit: int(1..10))", "decimal(-2.5..7.5)?")
    )

    assert diagnostics == []
    parameter = _parameter_type(declaration)
    assert parameter.semantic() == {
        "kind": "scalar",
        "optional": False,
        "name": "int",
        "range": {"min": 1, "max": 10},
    }
    assert declaration.result_type is not None
    assert declaration.result_type.semantic() == {
        "kind": "scalar",
        "optional": True,
        "name": "decimal",
        "range": {"min": -2.5, "max": 7.5},
    }
    assert _format_type(parameter) == "int(1..10)"
    assert _format_type(declaration.result_type) == "decimal(-2.5..7.5)?"
    first = declaration.semantic_json()
    second = declaration.semantic_json()
    assert first == second
    assert json.loads(first)["result_type"]["range"] == {"min": -2.5, "max": 7.5}


def test_mutation_range_constraints_preserve_string_bounds() -> None:
    bridge = LanguageSurfaceBridge()
    declaration, diagnostics = bridge.normalize_declaration(
        _operation("mutation", '(code: string("a".."z"))', "int(0..1)")
    )

    assert diagnostics == []
    parameter = _parameter_type(declaration)
    assert parameter.range == ("a", "z")
    assert _format_type(parameter) == 'string("a".."z")'
    assert declaration.result_type is not None
    assert declaration.result_type.range == (0, 1)


def test_non_range_constraints_fail_closed() -> None:
    bridge = LanguageSurfaceBridge()
    diagnostics = []
    value = bridge.type_ref("int(1)", diagnostics)

    assert value.range is None
    assert value.name == "int(1)"
    assert [item.code for item in diagnostics] == ["AIDL-N015"]
    assert "outside frozen TypeRef.range parity" in diagnostics[0].message


def test_generic_type_arguments_fail_closed() -> None:
    bridge = LanguageSurfaceBridge()
    diagnostics = []
    value = bridge.type_ref("Result<string>", diagnostics)

    assert value.range is None
    assert value.name == "Result<string>"
    assert [item.code for item in diagnostics] == ["AIDL-N015"]
    assert "generic type arguments" in diagnostics[0].message


def test_list_element_range_is_preserved_recursively() -> None:
    bridge = LanguageSurfaceBridge()
    diagnostics = []
    value = bridge.type_ref("[int(1..3)]?", diagnostics)

    assert diagnostics == []
    assert value.kind == "list"
    assert value.optional is True
    assert value.element is not None
    assert value.element.range == (1, 3)
    assert _format_type(value) == "[int(1..3)]?"
