from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


IR_VERSION = "0.3.0"
GENERATED_OUTBOX_PATH = "generated/outbox.ts"
GENERATED_MIGRATION_PATH = "generated/migrations/0003_outbox.sql"


class PostgresOutboxGeneratorError(ValueError):
    pass


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PostgresOutboxGeneratorError(f"{label} must be a non-empty string")
    return value


def _ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _declarations(ir: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    raw = ir.get("declarations")
    if not isinstance(raw, list):
        raise PostgresOutboxGeneratorError("canonical IR declarations must be an array")
    declarations: list[Mapping[str, Any]] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for declaration in raw:
        if not isinstance(declaration, Mapping):
            raise PostgresOutboxGeneratorError("canonical IR declaration must be an object")
        declaration_id = declaration.get("declarationId")
        if isinstance(declaration_id, str) and declaration_id:
            by_id[declaration_id] = declaration
        declarations.append(declaration)
    return declarations, by_id


def _expr(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PostgresOutboxGeneratorError(f"{label} must be a canonical value expression")
    kind = value.get("kind")
    if kind == "literal":
        literal = value.get("value")
        if isinstance(literal, (dict, list)):
            raise PostgresOutboxGeneratorError(f"{label} literal must be scalar")
        return value
    if kind == "symbol":
        path = value.get("path")
        if not isinstance(path, list) or not path or not all(isinstance(part, str) and part for part in path):
            raise PostgresOutboxGeneratorError(f"{label} symbol path is invalid")
        if len(path) == 1 and "(" in path[0] and path[0] not in {"operationId()", "now()"}:
            raise PostgresOutboxGeneratorError(
                f"{label} producer symbol '{path[0]}' is outside the M4-07 executable subset"
            )
        return value
    if kind == "call":
        function = value.get("function")
        arguments = value.get("arguments")
        if function not in {"operationId", "now"} or not isinstance(arguments, list) or arguments:
            raise PostgresOutboxGeneratorError(f"{label} call '{function}' is outside the M4-07 executable subset")
        return value
    if kind == "record":
        fields = value.get("fields")
        if not isinstance(fields, list):
            raise PostgresOutboxGeneratorError(f"{label} record fields must be an array")
        names: set[str] = set()
        for field in fields:
            if not isinstance(field, Mapping):
                raise PostgresOutboxGeneratorError(f"{label} record field must be an object")
            name = _string(field.get("name"), f"{label} record field name")
            if name in names:
                raise PostgresOutboxGeneratorError(f"{label} has duplicate record field '{name}'")
            names.add(name)
            _expr(field.get("value"), f"{label} field '{name}'")
        return value
    raise PostgresOutboxGeneratorError(f"{label} kind '{kind}' is outside M4-07")


def _required_event_fields(event: Mapping[str, Any]) -> list[str]:
    fields = event.get("fields")
    if not isinstance(fields, list):
        raise PostgresOutboxGeneratorError("canonical event fields must be an array")
    required: list[str] = []
    for field in fields:
        if not isinstance(field, Mapping):
            raise PostgresOutboxGeneratorError("canonical event field must be an object")
        name = _string(field.get("name"), "event field name")
        if field.get("required") is True:
            required.append(name)
    for infrastructure_field in ("eventId", "occurredAt"):
        if infrastructure_field not in required:
            raise PostgresOutboxGeneratorError(
                f"event '{event.get('declarationId')}' must require '{infrastructure_field}' for M4-07"
            )
    return required


def _payload_field_names(payload: Mapping[str, Any], label: str) -> set[str]:
    if payload.get("kind") != "record":
        raise PostgresOutboxGeneratorError(f"{label} must be a canonical record expression for M4-07")
    fields = payload.get("fields")
    if not isinstance(fields, list):
        raise PostgresOutboxGeneratorError(f"{label} fields must be an array")
    return {
        _string(field.get("name"), f"{label} field name")
        for field in fields
        if isinstance(field, Mapping)
    }


def build_publish_step(step: Mapping[str, Any], declarations: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Project one canonical transaction publish step into the M4-07 outbox contract."""
    if step.get("kind") != "publish" or step.get("via") != "outbox":
        raise PostgresOutboxGeneratorError("transaction publish must use canonical via=outbox")
    event_id = _string(step.get("eventId"), "transaction publish eventId")
    topic_id = _string(step.get("topicId"), "transaction publish topicId")
    event = declarations.get(event_id)
    topic = declarations.get(topic_id)
    if event is None or event.get("kind") != "event":
        raise PostgresOutboxGeneratorError(f"transaction publish event '{event_id}' is unresolved")
    if topic is None or topic.get("kind") != "topic":
        raise PostgresOutboxGeneratorError(f"transaction publish topic '{topic_id}' is unresolved")

    event_ids = topic.get("eventIds")
    if not isinstance(event_ids, list) or event_id not in event_ids:
        raise PostgresOutboxGeneratorError(f"topic '{topic_id}' does not declare event '{event_id}'")
    if topic.get("delivery") != "atLeastOnce":
        raise PostgresOutboxGeneratorError(
            f"topic '{topic_id}' delivery '{topic.get('delivery')}' is outside the M4-07 at-least-once outbox subset"
        )
    retention_ms = topic.get("retentionMs")
    if not isinstance(retention_ms, int) or isinstance(retention_ms, bool) or retention_ms < 1:
        raise PostgresOutboxGeneratorError(f"topic '{topic_id}' has invalid retentionMs")
    partition_field = _string(topic.get("partitionField"), f"topic '{topic_id}' partitionField")

    payload = _expr(step.get("payload"), "transaction publish payload")
    payload_fields = _payload_field_names(payload, "transaction publish payload")
    required_fields = _required_event_fields(event)
    missing = sorted(set(required_fields) - payload_fields)
    if missing:
        raise PostgresOutboxGeneratorError(
            f"transaction publish event '{event_id}' misses required payload fields: {', '.join(missing)}"
        )
    if partition_field not in payload_fields:
        raise PostgresOutboxGeneratorError(
            f"transaction publish event '{event_id}' misses topic partition field '{partition_field}'"
        )

    major_version = event.get("majorVersion")
    if not isinstance(major_version, int) or isinstance(major_version, bool) or major_version < 1:
        raise PostgresOutboxGeneratorError(f"event '{event_id}' has invalid majorVersion")

    return {
        "kind": "publish",
        "eventId": event_id,
        "eventFqn": _string(event.get("fqn"), "event fqn"),
        "eventVersion": major_version,
        "topicId": topic_id,
        "topicFqn": _string(topic.get("fqn"), "topic fqn"),
        "partitionField": partition_field,
        "retentionMs": retention_ms,
        "payload": payload,
        "sql": (
            'INSERT INTO "aidl_outbox" '
            '("event_id", "event_type", "event_version", "topic", "partition_key", "payload", "occurred_at", "expires_at") '
            "VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::timestamptz, CURRENT_TIMESTAMP + ($8 * INTERVAL '1 millisecond'))"
        ),
    }


def _publish_plans(ir: Mapping[str, Any]) -> list[dict[str, Any]]:
    declarations, by_id = _declarations(ir)
    mutations = [item for item in declarations if item.get("kind") == "mutation"]
    mutations.sort(
        key=lambda item: (
            _string(item.get("fqn"), "mutation fqn"),
            _string(item.get("declarationId"), "mutation declarationId"),
        )
    )
    plans: list[dict[str, Any]] = []
    for mutation in mutations:
        root = mutation.get("rootEffect")
        if not isinstance(root, Mapping) or root.get("kind") != "transaction":
            continue
        steps = root.get("steps")
        if not isinstance(steps, list):
            raise PostgresOutboxGeneratorError("transaction steps must be an array")
        for index, step in enumerate(steps):
            if not isinstance(step, Mapping):
                raise PostgresOutboxGeneratorError("transaction step must be an object")
            if step.get("kind") != "publish":
                continue
            publish = build_publish_step(step, by_id)
            plans.append(
                {
                    "operationId": _string(mutation.get("declarationId"), "mutation declarationId"),
                    "operationFqn": _string(mutation.get("fqn"), "mutation fqn"),
                    "stepIndex": index,
                    **publish,
                }
            )
    return plans


def _migration_source() -> str:
    return '''-- Generated from canonical AIDL IR by the M4 PostgreSQL outbox generator.\nCREATE TABLE IF NOT EXISTS "aidl_outbox" (\n  "sequence" bigserial PRIMARY KEY,\n  "event_id" text NOT NULL UNIQUE,\n  "event_type" text NOT NULL,\n  "event_version" integer NOT NULL CHECK ("event_version" > 0),\n  "topic" text NOT NULL,\n  "partition_key" text NOT NULL,\n  "payload" jsonb NOT NULL,\n  "occurred_at" timestamptz NOT NULL,\n  "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,\n  "available_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,\n  "expires_at" timestamptz NOT NULL,\n  "published_at" timestamptz,\n  "attempts" integer NOT NULL DEFAULT 0 CHECK ("attempts" >= 0)\n);\n\nCREATE INDEX IF NOT EXISTS "ix_aidl_outbox_pending" ON "aidl_outbox" ("available_at", "sequence") WHERE "published_at" IS NULL;\n'''


def _runtime_source(plans: list[dict[str, Any]]) -> str:
    plan_json = json.dumps(plans, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    claim_sql = _ts_string(
        'SELECT "sequence", "event_id", "event_type", "event_version", "topic", "partition_key", "payload", "occurred_at", "attempts" FROM "aidl_outbox" WHERE "published_at" IS NULL AND "available_at" <= CURRENT_TIMESTAMP AND "expires_at" > CURRENT_TIMESTAMP ORDER BY "sequence" FOR UPDATE SKIP LOCKED LIMIT $1'
    )
    increment_attempts_sql = _ts_string(
        'UPDATE "aidl_outbox" SET "attempts" = "attempts" + 1 WHERE "sequence" = $1'
    )
    mark_published_sql = _ts_string(
        'UPDATE "aidl_outbox" SET "published_at" = CURRENT_TIMESTAMP WHERE "sequence" = $1 AND "published_at" IS NULL'
    )
    release_sql = _ts_string(
        'UPDATE "aidl_outbox" SET "available_at" = CURRENT_TIMESTAMP + ($2 * INTERVAL \'1 millisecond\') WHERE "sequence" = $1 AND "published_at" IS NULL'
    )
    return f'''// Generated from canonical AIDL IR. Do not edit by hand.\n\nexport interface PgOutboxResult {{ readonly rowCount: number | null; readonly rows: ReadonlyArray<Record<string, unknown>>; }}\nexport interface PgOutboxClient {{ query(sql: string, params?: ReadonlyArray<unknown>): Promise<PgOutboxResult>; }}\n\nexport interface OutboxPublishPlan {{ readonly kind: "publish"; readonly operationId: string; readonly operationFqn: string; readonly stepIndex: number; readonly eventId: string; readonly eventFqn: string; readonly eventVersion: number; readonly topicId: string; readonly topicFqn: string; readonly partitionField: string; readonly retentionMs: number; readonly payload: Readonly<Record<string, unknown>>; readonly sql: string; }}\n\nexport const outboxPublishPlans: ReadonlyArray<OutboxPublishPlan> = {plan_json} as ReadonlyArray<OutboxPublishPlan>;\n\nexport interface OutboxMessage {{ readonly sequence: number; readonly eventId: string; readonly eventType: string; readonly eventVersion: number; readonly topic: string; readonly partitionKey: string; readonly payload: unknown; readonly occurredAt: string; readonly attempts: number; }}\n\nexport async function claimOutboxBatch(client: PgOutboxClient, limit: number): Promise<ReadonlyArray<OutboxMessage>> {{\n  if (!Number.isInteger(limit) || limit < 1) throw new Error("outbox claim limit must be a positive integer");\n  await client.query("BEGIN");\n  try {{\n    const result = await client.query(\n      {claim_sql},\n      [limit],\n    );\n    const messages: OutboxMessage[] = [];\n    for (const row of result.rows) {{\n      await client.query({increment_attempts_sql}, [row.sequence]);\n      messages.push({{\n        sequence: Number(row.sequence), eventId: String(row.event_id), eventType: String(row.event_type),\n        eventVersion: Number(row.event_version), topic: String(row.topic), partitionKey: String(row.partition_key),\n        payload: row.payload, occurredAt: String(row.occurred_at), attempts: Number(row.attempts) + 1,\n      }});\n    }}\n    await client.query("COMMIT");\n    return messages;\n  }} catch (error) {{\n    await client.query("ROLLBACK");\n    throw error;\n  }}\n}}\n\nexport async function markOutboxPublished(client: PgOutboxClient, sequence: number): Promise<void> {{\n  const result = await client.query({mark_published_sql}, [sequence]);\n  if (result.rowCount !== 1) throw new Error("outbox message is missing or already published");\n}}\n\nexport async function releaseOutboxMessage(client: PgOutboxClient, sequence: number, delayMs: number): Promise<void> {{\n  if (!Number.isFinite(delayMs) || delayMs < 0) throw new Error("outbox retry delay must be non-negative");\n  const result = await client.query({release_sql}, [sequence, delayMs]);\n  if (result.rowCount !== 1) throw new Error("outbox message is missing or already published");\n}}\n'''


def generate_postgres_outbox_files(ir: Mapping[str, Any]) -> dict[str, str]:
    """Generate deterministic M4-07 transactional outbox/event support from canonical IR only."""
    if ir.get("irVersion") != IR_VERSION:
        raise PostgresOutboxGeneratorError(f"unsupported canonical IR version '{ir.get('irVersion')}'")
    plans = _publish_plans(ir)
    if not plans:
        raise PostgresOutboxGeneratorError("canonical IR contains no supported transactional outbox publishes")
    return {
        GENERATED_OUTBOX_PATH: _runtime_source(plans),
        GENERATED_MIGRATION_PATH: _migration_source(),
    }
