from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from tools.ir_diff import IrDiffChange, diff_canonical_ir


CompatibilityClass = Literal["safe", "conditional", "migration-required", "breaking"]


class IrCompatibilityClassificationError(ValueError):
    """Raised when classifications are requested for facts not owned by the supplied IR states."""


@dataclass(frozen=True)
class IrCompatibilityClassification:
    kind: str
    path: str
    classification: CompatibilityClass
    rule: str
    reason: str

    def to_json(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "path": self.path,
            "classification": self.classification,
            "rule": self.rule,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class _Candidate:
    classification: CompatibilityClass
    rule: str
    reason: str


@dataclass(frozen=True)
class _Context:
    public_operation_ids: frozenset[str]
    public_input_type_ids: frozenset[str]
    public_output_type_ids: frozenset[str]


_SAFE_STANDALONE_DECLARATION_KINDS = frozenset({"alias", "enum", "opaque", "value", "view"})
_CLASS_RANK: dict[CompatibilityClass, int] = {
    "safe": 0,
    "conditional": 1,
    "migration-required": 2,
    "breaking": 3,
}


def _direct_declaration(change: IrDiffChange) -> Mapping[str, Any] | None:
    parts = change.path.split("/")
    if len(parts) != 3 or parts[1] != "declarations":
        return None
    candidate = change.new_value if change.kind == "added" else change.old_value
    return candidate if isinstance(candidate, Mapping) else None


def _declaration_selector(path: str) -> tuple[str, str] | None:
    parts = path.split("/")
    if len(parts) < 3 or parts[1] != "declarations" or ":" not in parts[2]:
        return None
    kind, declaration_id = parts[2].split(":", 1)
    return kind, declaration_id


def _declarations_by_id(document: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    declarations = document.get("declarations")
    if not isinstance(declarations, list):
        return result
    for declaration in declarations:
        if not isinstance(declaration, Mapping):
            continue
        declaration_id = declaration.get("declarationId")
        if isinstance(declaration_id, str):
            result[declaration_id] = declaration
    return result


def _collect_type_refs(value: Any, result: set[str]) -> None:
    if isinstance(value, Mapping):
        kind = value.get("kind")
        if kind == "named":
            declaration_id = value.get("declarationId")
            if isinstance(declaration_id, str):
                result.add(declaration_id)
        elif kind == "ref":
            entity_id = value.get("entityId")
            if isinstance(entity_id, str):
                result.add(entity_id)
        for child in value.values():
            _collect_type_refs(child, result)
    elif isinstance(value, list):
        for child in value:
            _collect_type_refs(child, result)


def _expand_type_refs(document: Mapping[str, Any], roots: set[str]) -> frozenset[str]:
    declarations = _declarations_by_id(document)
    seen: set[str] = set()
    pending = list(sorted(roots))
    while pending:
        declaration_id = pending.pop(0)
        if declaration_id in seen:
            continue
        seen.add(declaration_id)
        declaration = declarations.get(declaration_id)
        if declaration is None:
            continue
        nested: set[str] = set()
        _collect_type_refs(declaration, nested)
        pending.extend(sorted(nested - seen))
    return frozenset(seen)


def _context(document: Mapping[str, Any]) -> _Context:
    declarations = _declarations_by_id(document)
    public_operations: set[str] = set()
    for declaration in declarations.values():
        if declaration.get("kind") != "api":
            continue
        operations = declaration.get("operations")
        if not isinstance(operations, list):
            continue
        for operation in operations:
            if not isinstance(operation, Mapping):
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str):
                public_operations.add(operation_id)

    input_roots: set[str] = set()
    output_roots: set[str] = set()
    for operation_id in public_operations:
        operation = declarations.get(operation_id)
        if operation is None:
            continue
        _collect_type_refs(operation.get("input"), input_roots)
        _collect_type_refs(operation.get("output"), output_roots)

    return _Context(
        public_operation_ids=frozenset(public_operations),
        public_input_type_ids=_expand_type_refs(document, input_roots),
        public_output_type_ids=_expand_type_refs(document, output_roots),
    )


def _merge_context(old_document: Mapping[str, Any], new_document: Mapping[str, Any]) -> _Context:
    old = _context(old_document)
    new = _context(new_document)
    return _Context(
        public_operation_ids=old.public_operation_ids | new.public_operation_ids,
        public_input_type_ids=old.public_input_type_ids | new.public_input_type_ids,
        public_output_type_ids=old.public_output_type_ids | new.public_output_type_ids,
    )


def _is_field_path(path: str, declaration_kind: str | None = None) -> bool:
    parts = path.split("/")
    if len(parts) < 5 or parts[1] != "declarations" or parts[3] != "fields" or not parts[4].isdigit():
        return False
    return declaration_kind is None or parts[2].startswith(f"{declaration_kind}:")


def _is_operation_record_field_path(path: str, section: str) -> bool:
    parts = path.split("/")
    return (
        len(parts) >= 6
        and parts[1] == "declarations"
        and (parts[2].startswith("query:") or parts[2].startswith("mutation:"))
        and parts[3] == section
        and parts[4] == "fields"
        and parts[5].isdigit()
    )


def _public_field_surfaces(change: IrDiffChange, context: _Context) -> frozenset[str]:
    selector = _declaration_selector(change.path)
    if selector is None:
        return frozenset()
    _kind, declaration_id = selector
    surfaces: set[str] = set()
    if _is_field_path(change.path):
        if declaration_id in context.public_input_type_ids:
            surfaces.add("input")
        if declaration_id in context.public_output_type_ids:
            surfaces.add("output")
    if declaration_id in context.public_operation_ids:
        if _is_operation_record_field_path(change.path, "input"):
            surfaces.add("input")
        if _is_operation_record_field_path(change.path, "output"):
            surfaces.add("output")
    return frozenset(surfaces)


def _field_mapping(change: IrDiffChange) -> Mapping[str, Any] | None:
    value = change.new_value if change.kind == "added" else change.old_value
    return value if isinstance(value, Mapping) else None


def _numeric_direction(change: IrDiffChange) -> int | None:
    old = change.old_value
    new = change.new_value
    if isinstance(old, bool) or isinstance(new, bool):
        return None
    if not isinstance(old, (int, float)) or not isinstance(new, (int, float)):
        return None
    return (new > old) - (new < old)


def _constraint_tightening(change: IrDiffChange) -> bool | None:
    direction = _numeric_direction(change)
    if direction is None or direction == 0:
        return None
    if change.path.endswith(("/minimum", "/minLength")):
        return direction > 0
    if change.path.endswith(("/maximum", "/maxLength")):
        return direction < 0
    return None


def _candidate(
    candidates: list[_Candidate],
    classification: CompatibilityClass,
    rule: str,
    reason: str,
) -> None:
    candidates.append(_Candidate(classification, rule, reason))


def _api_candidates(change: IrDiffChange, context: _Context, candidates: list[_Candidate]) -> None:
    selector = _declaration_selector(change.path)
    if selector is None:
        if change.path.startswith("/app/apiIds/") or change.path.startswith("/system/apiIds/"):
            if change.kind == "added":
                _candidate(candidates, "safe", "api.exposure-added", "Adding another API exposure does not remove an existing public API contract.")
            elif change.kind in {"removed", "changed"}:
                _candidate(candidates, "breaking", "api.exposure-removed-or-replaced", "Removing or replacing an exposed API removes an existing public contract target.")
        return

    kind, declaration_id = selector
    if kind == "api":
        parts = change.path.split("/")
        if len(parts) >= 4 and parts[3] == "operations":
            if change.kind == "added":
                _candidate(candidates, "safe", "api.operation-added", "Adding a public API operation is additive and does not remove or tighten an existing operation contract.")
            elif change.kind == "removed":
                _candidate(candidates, "breaking", "api.operation-removed", "Removing a public API operation removes an existing client contract.")
            elif change.kind == "changed":
                _candidate(candidates, "breaking", "api.operation-replaced", "Replacing a public API operation changes the existing operation identity exposed to clients.")
        if change.kind == "changed" and change.path.endswith("/auth/mode"):
            _candidate(candidates, "breaking", "api.auth-changed", "Changing public API authentication requirements changes the client access contract.")
        if change.kind == "changed" and change.path.endswith("/transport"):
            _candidate(candidates, "breaking", "api.transport-changed", "Changing the API transport changes the public wire contract.")
        if change.kind == "changed" and change.path.endswith("/errorEncoding"):
            _candidate(candidates, "breaking", "api.error-encoding-changed", "Changing public error encoding changes the client-visible error wire contract.")
        if change.kind == "changed" and change.path.endswith("/majorVersion"):
            _candidate(candidates, "breaking", "api.major-version-replaced", "Changing an API major in place replaces the public compatibility domain instead of adding a parallel major.")
        if "/rateLimit/" in change.path or change.path.endswith("/rateLimit"):
            _candidate(candidates, "conditional", "api.rate-limit-changed", "Changing rate limits can affect clients at runtime and requires deployment/client expectation review.")
        if change.path.endswith("/compatibility"):
            _candidate(candidates, "conditional", "api.compatibility-policy-changed", "Changing the declared API compatibility policy changes rollout expectations and requires review.")

    if kind in {"query", "mutation"} and declaration_id in context.public_operation_ids:
        if change.kind == "changed" and change.path.endswith("/auth/mode"):
            _candidate(candidates, "breaking", "client.auth-changed", "Changing authentication on a public operation changes the client access contract.")
        if change.kind == "changed" and change.path.endswith("/consistency"):
            _candidate(candidates, "breaking", "client.consistency-changed", "Changing consistency on a public operation changes observable client semantics.")
        if "/idempotency/" in change.path or change.path.endswith("/idempotency"):
            _candidate(candidates, "breaking", "client.idempotency-changed", "Changing public mutation idempotency semantics changes retry behavior observed by clients.")
        if change.path.startswith(f"/declarations/{kind}:{declaration_id}/errorIds/"):
            if change.kind == "added":
                _candidate(candidates, "conditional", "client.error-added", "A new declared public error is not provably safe because Canonical IR does not record whether all clients accept unknown errors.")
            else:
                _candidate(candidates, "breaking", "client.error-removed-or-replaced", "Removing or replacing a stable public error changes the client-visible error contract.")


def _event_candidates(change: IrDiffChange, candidates: list[_Candidate]) -> None:
    selector = _declaration_selector(change.path)
    declaration = _direct_declaration(change)
    if declaration is not None and change.kind == "added" and declaration.get("kind") == "event":
        _candidate(candidates, "safe", "event.version-added", "Adding a new immutable event schema/version is additive until a topic begins delivering it.")

    if selector is None:
        return
    kind, _declaration_id = selector
    parts = change.path.split("/")
    if kind == "event" and len(parts) > 3:
        _candidate(candidates, "breaking", "event.schema-mutated", "Existing event schemas are immutable; changing an event version in place is breaking.")
        return
    if kind != "topic":
        return

    if len(parts) >= 4 and parts[3] == "eventIds":
        if change.kind == "added":
            _candidate(candidates, "conditional", "event.topic-version-added", "Delivering an additional event schema on an existing topic requires producer/consumer overlap or accepted-version evidence.")
        elif change.kind == "removed":
            _candidate(candidates, "breaking", "event.topic-version-removed", "Removing an event schema from a topic can strand consumers that still accept or require that version.")
        else:
            _candidate(candidates, "breaking", "event.topic-version-replaced", "Replacing one delivered event schema with another changes the topic contract without an overlap window.")
    if change.kind == "changed" and change.path.endswith("/partitionField"):
        _candidate(candidates, "breaking", "event.partition-changed", "Changing the topic partition field changes ordering/routing identity for consumers.")
    if change.kind == "changed" and change.path.endswith("/retentionMs"):
        direction = _numeric_direction(change)
        if direction is not None and direction < 0:
            _candidate(candidates, "breaking", "event.retention-reduced", "Reducing topic retention can remove old messages before consumers can process or upcast them.")
        elif direction is not None and direction > 0:
            _candidate(candidates, "safe", "event.retention-increased", "Increasing topic retention preserves existing messages for at least as long as before.")
    if change.kind == "changed" and change.path.endswith(("/delivery", "/ordering", "/compatibility")):
        _candidate(candidates, "conditional", "event.delivery-policy-changed", "Changing topic delivery, ordering, or compatibility policy requires producer/consumer coordination review.")


def _persisted_schema_candidates(change: IrDiffChange, candidates: list[_Candidate]) -> None:
    selector = _declaration_selector(change.path)
    if selector is None:
        return
    kind, _declaration_id = selector
    if kind != "entity":
        return

    if change.path.endswith("/identityFields") or "/identityFields/" in change.path:
        _candidate(candidates, "breaking", "entity.identity-changed", "Changing persisted entity identity changes storage keys and reference contracts.")

    if not _is_field_path(change.path, "entity"):
        return

    parts = change.path.split("/")
    direct_field = len(parts) == 5
    if direct_field and change.kind == "added":
        field = _field_mapping(change)
        if field is not None and field.get("required") is True:
            _candidate(candidates, "migration-required", "entity.required-field-added", "Adding a required persisted field requires an expand/backfill migration for existing rows.")
        else:
            _candidate(candidates, "migration-required", "entity.field-added", "Adding a persisted field changes the stored schema and requires an additive expand migration.")
    if direct_field and change.kind == "removed":
        _candidate(candidates, "breaking", "entity.field-removed", "Removing a persisted field is a destructive contract/schema change and can lose stored data.")

    if change.kind == "changed" and change.path.endswith("/required"):
        if change.old_value is False and change.new_value is True:
            _candidate(candidates, "migration-required", "entity.field-required-tightened", "Making a persisted field required needs existing rows to be backfilled or otherwise migrated.")
        else:
            _candidate(candidates, "migration-required", "entity.field-required-relaxed", "Changing persisted nullability still requires a schema migration even when the contract is relaxed.")
    if change.kind == "changed" and change.path.endswith("/name"):
        _candidate(candidates, "breaking", "entity.field-renamed", "Renaming a persisted field changes the stored schema and canonical field contract.")
    if change.kind == "changed" and "/type/" in change.path:
        if "/constraints/" in change.path:
            _candidate(candidates, "migration-required", "entity.constraint-changed", "Changing a persisted field constraint requires schema/data compatibility validation and migration.")
        else:
            _candidate(candidates, "breaking", "entity.field-type-changed", "Changing a persisted field type changes its stored representation and contract.")
    if change.kind == "changed" and change.path.endswith(("/primary", "/concurrencyToken", "/generated", "/onDelete")):
        _candidate(candidates, "breaking", "entity.storage-semantics-changed", "Changing persisted identity, generation, concurrency, or delete semantics changes storage behavior incompatibly.")


def _client_field_candidates(change: IrDiffChange, context: _Context, candidates: list[_Candidate]) -> None:
    surfaces = _public_field_surfaces(change, context)
    if not surfaces:
        return
    parts = change.path.split("/")
    direct_field = (
        (_is_field_path(change.path) and len(parts) == 5)
        or (_is_operation_record_field_path(change.path, "input") and len(parts) == 6)
        or (_is_operation_record_field_path(change.path, "output") and len(parts) == 6)
    )

    if direct_field:
        field = _field_mapping(change)
        if change.kind == "added":
            if "input" in surfaces:
                if field is not None and field.get("required") is True:
                    _candidate(candidates, "breaking", "client.input-required-field-added", "Adding a required field to a public operation input breaks existing callers that do not send it.")
                else:
                    _candidate(candidates, "conditional", "client.input-optional-field-added", "An optional public input field is only provably compatible when a default/unknown-field contract is carried; current Canonical IR does not retain that proof.")
            if "output" in surfaces:
                _candidate(candidates, "safe", "client.output-field-added", "Adding a field to a public output is additive for clients that consume the existing output shape.")
        elif change.kind == "removed":
            if "input" in surfaces:
                _candidate(candidates, "breaking", "client.input-field-removed", "Removing a public input field breaks callers that still send that field.")
            if "output" in surfaces:
                _candidate(candidates, "breaking", "client.output-field-removed", "Removing a public output field breaks clients that read that field.")

    if change.kind != "changed":
        return

    if change.path.endswith("/name"):
        if "input" in surfaces:
            _candidate(candidates, "breaking", "client.input-field-renamed", "Renaming a public input field changes the request contract.")
        if "output" in surfaces:
            _candidate(candidates, "breaking", "client.output-field-renamed", "Renaming a public output field changes the response contract.")

    if change.path.endswith("/required"):
        if "input" in surfaces:
            if change.old_value is False and change.new_value is True:
                _candidate(candidates, "breaking", "client.input-required-tightened", "Making a public input field required narrows accepted requests.")
            elif change.old_value is True and change.new_value is False:
                _candidate(candidates, "safe", "client.input-required-relaxed", "Making a public input field optional widens accepted requests.")
        if "output" in surfaces:
            if change.old_value is True and change.new_value is False:
                _candidate(candidates, "breaking", "client.output-nullability-broadened", "Making a public output field nullable broadens output nullability and breaks clients that rely on a value.")
            elif change.old_value is False and change.new_value is True:
                _candidate(candidates, "safe", "client.output-nullability-narrowed", "Making a public output field non-null narrows possible responses without removing a value clients relied on.")

    if "/constraints/" in change.path and "input" in surfaces:
        tightening = _constraint_tightening(change)
        if tightening is True:
            _candidate(candidates, "breaking", "client.input-constraint-tightened", "Narrowing a public input constraint rejects requests that were previously valid.")
        elif tightening is False:
            _candidate(candidates, "safe", "client.input-constraint-relaxed", "Relaxing a public input constraint accepts all previously valid requests.")

    if "/type/" in change.path and "/constraints/" not in change.path:
        if "input" in surfaces:
            _candidate(candidates, "breaking", "client.input-type-changed", "Changing a public input field type changes the request contract.")
        if "output" in surfaces:
            _candidate(candidates, "breaking", "client.output-type-changed", "Changing a public output field type changes the response contract.")


def _public_operation_shape_candidates(change: IrDiffChange, context: _Context, candidates: list[_Candidate]) -> None:
    selector = _declaration_selector(change.path)
    if selector is None:
        return
    kind, declaration_id = selector
    if kind not in {"query", "mutation"} or declaration_id not in context.public_operation_ids:
        return

    if change.kind == "changed" and change.path.endswith("/output/kind"):
        if change.new_value == "nullable":
            _candidate(candidates, "breaking", "client.output-nullability-broadened", "Broadening public operation output nullability breaks clients that rely on a non-null response.")
    if change.kind == "changed" and change.path.endswith("/input/kind"):
        _candidate(candidates, "breaking", "client.input-shape-changed", "Changing the top-level public input shape changes the request contract.")


def _classify(change: IrDiffChange, context: _Context) -> IrCompatibilityClassification:
    candidates: list[_Candidate] = []
    declaration = _direct_declaration(change)
    if declaration is not None:
        kind = declaration.get("kind")
        if change.kind == "removed":
            _candidate(candidates, "breaking", "declaration.removed", "Removing an existing declaration removes a canonical contract target.")
        if change.kind == "added" and kind in _SAFE_STANDALONE_DECLARATION_KINDS:
            _candidate(candidates, "safe", "declaration.standalone-added", f"Adding a standalone {kind} declaration does not remove or tighten an existing canonical contract.")

    _api_candidates(change, context, candidates)
    _event_candidates(change, candidates)
    _persisted_schema_candidates(change, candidates)
    _client_field_candidates(change, context, candidates)
    _public_operation_shape_candidates(change, context, candidates)

    if change.kind == "changed" and change.path.endswith("/timeoutMs"):
        _candidate(candidates, "conditional", "operation.timeout-changed", "Changing an operation timeout can affect callers and runtime behavior; compatibility depends on deployment and consumer expectations.")

    if not candidates:
        _candidate(candidates, "conditional", "unmodelled.review-required", "M7 compatibility rules have no Canonical-IR evidence proving this semantic change safe, migration-required, or breaking; compatibility review is required.")

    best_index, best = max(
        enumerate(candidates),
        key=lambda item: (_CLASS_RANK[item[1].classification], -item[0]),
    )
    _ = best_index
    return IrCompatibilityClassification(
        change.kind,
        change.path,
        best.classification,
        best.rule,
        best.reason,
    )


def classify_ir_diff(
    changes: Sequence[IrDiffChange],
    old_document: Mapping[str, Any],
    new_document: Mapping[str, Any],
) -> list[IrCompatibilityClassification]:
    """Classify authoritative M7-01 facts across carried compatibility surfaces.

    The supplied Canonical IR states are revalidated through the existing M7-01
    diff boundary, and supplied facts must match that authoritative result
    exactly. Rules use only semantics carried by Canonical IR 0.3.0. Unknown or
    unsupported surfaces, including sync/client-version semantics not present in
    Core IR, remain deliberately ``conditional`` rather than being guessed safe.
    """

    authoritative = diff_canonical_ir(old_document, new_document)
    supplied = list(changes)
    if supplied != authoritative:
        raise IrCompatibilityClassificationError(
            "diff facts do not match the authoritative M7-01 diff for the supplied Canonical IR states"
        )
    context = _merge_context(old_document, new_document)
    return [_classify(change, context) for change in supplied]


def ir_compatibility_to_json(
    classifications: Sequence[IrCompatibilityClassification],
) -> list[dict[str, str]]:
    return [classification.to_json() for classification in classifications]
