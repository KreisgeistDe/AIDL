from __future__ import annotations

import json
from typing import Any, Mapping

PLAN_VERSION = "0.1.0"


class PlanBuildError(ValueError):
    pass


def _identity(item: Mapping[str, Any], kind: str) -> tuple[str, str, str]:
    declaration_id = item.get("declarationId")
    name = item.get("name")
    fqn = item.get("fqn")
    if not all(isinstance(value, str) and value for value in (declaration_id, name, fqn)):
        raise PlanBuildError(f"{kind} is missing stable identity fields")
    return declaration_id, name, fqn


def _select_deployment(document: Mapping[str, Any], requested: str | None) -> Mapping[str, Any]:
    deployments = document.get("deployments")
    app = document.get("app")
    if not isinstance(deployments, list) or not isinstance(app, Mapping):
        raise PlanBuildError("canonical IR is missing app/deployments")

    selector = requested or app.get("defaultDeploymentId")
    if not isinstance(selector, str) or not selector:
        raise PlanBuildError("no deployment selector is available")

    matches: list[Mapping[str, Any]] = []
    for deployment in deployments:
        if not isinstance(deployment, Mapping):
            raise PlanBuildError("deployment entry must be an object")
        declaration_id, name, fqn = _identity(deployment, "deployment")
        if selector in {declaration_id, name, fqn}:
            matches.append(deployment)

    if len(matches) != 1:
        raise PlanBuildError(
            f"deployment selector '{selector}' matched {len(matches)} deployments; expected exactly one"
        )
    return matches[0]


def _binding_actions(deployment: Mapping[str, Any], key: str, action_kind: str, id_key: str) -> list[dict[str, Any]]:
    raw = deployment.get(key, [])
    if not isinstance(raw, list):
        raise PlanBuildError(f"deployment {key} must be an array")
    actions: list[dict[str, Any]] = []
    for binding in raw:
        if not isinstance(binding, Mapping):
            raise PlanBuildError(f"deployment {key} entry must be an object")
        target = binding.get(id_key)
        adapter = binding.get("adapter")
        if not isinstance(target, str) or not target or not isinstance(adapter, str) or not adapter:
            raise PlanBuildError(f"deployment {key} entry lacks {id_key}/adapter")
        actions.append({"kind": action_kind, "targetId": target, "adapter": adapter})
    return actions


def build_plan(document: Mapping[str, Any], deployment: str | None = None) -> dict[str, Any]:
    """Build a deterministic read-only plan solely from canonical IR."""
    ir_version = document.get("irVersion")
    semantic_hash = document.get("semanticHash")
    app = document.get("app")
    system = document.get("system")
    if not isinstance(ir_version, str) or not isinstance(semantic_hash, str):
        raise PlanBuildError("canonical IR lacks version/hash")
    if not isinstance(app, Mapping) or not isinstance(system, Mapping):
        raise PlanBuildError("canonical IR lacks app/system")

    app_id, _, _ = _identity(app, "app")
    system_id, _, _ = _identity(system, "system")
    selected = _select_deployment(document, deployment)
    deployment_id, deployment_name, deployment_fqn = _identity(selected, "deployment")

    actions = _binding_actions(selected, "resourceBindings", "bindResource", "resourceId")
    actions += _binding_actions(selected, "serviceBindings", "deployService", "serviceId")

    for api_id in system.get("apiIds", []):
        if not isinstance(api_id, str):
            raise PlanBuildError("system apiIds must contain strings")
        actions.append({"kind": "exposeApi", "targetId": api_id})
    for topic_id in system.get("topicIds", []):
        if not isinstance(topic_id, str):
            raise PlanBuildError("system topicIds must contain strings")
        actions.append({"kind": "activateTopic", "targetId": topic_id})

    actions.sort(key=lambda item: (item["kind"], item["targetId"], item.get("adapter", "")))
    return {
        "planVersion": PLAN_VERSION,
        "irVersion": ir_version,
        "sourceSemanticHash": semantic_hash,
        "appId": app_id,
        "systemId": system_id,
        "deployment": {
            "declarationId": deployment_id,
            "name": deployment_name,
            "fqn": deployment_fqn,
            "environment": selected.get("environment"),
            "regions": list(selected.get("regions", [])),
        },
        "actions": actions,
    }


def canonical_plan_json_text(plan: Mapping[str, Any]) -> str:
    return json.dumps(
        plan,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
