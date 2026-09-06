import assert from "node:assert/strict";
import { test } from "node:test";

import { Pool } from "pg";

import { createApp } from "../src/app.js";
import { migrate } from "../src/migrate.js";

const DATABASE_URL = process.env.DATABASE_URL ?? "postgres://postgres:postgres@127.0.0.1:5432/petstore";
const PET_TABLE = '"petstore_m4_runnablepet"';

async function resetDatabase(pool: Pool): Promise<void> {
  await pool.query('DROP TABLE IF EXISTS "aidl_outbox" CASCADE');
  await pool.query('DROP TABLE IF EXISTS "aidl_idempotency" CASCADE');
  await pool.query(`DROP TABLE IF EXISTS ${PET_TABLE} CASCADE`);
}

test("AIDL-generated createPet HTTP route is idempotent across PostgreSQL state and outbox", async (t) => {
  const pool = new Pool({ connectionString: DATABASE_URL });
  const app = createApp(pool);

  t.after(async () => {
    await app.close();
    await resetDatabase(pool);
    await pool.end();
  });

  await resetDatabase(pool);
  assert.deepEqual(await migrate(pool), [
    "0001_initial.sql",
    "0002_idempotency.sql",
    "0003_outbox.sql",
  ]);

  const input = {
    operationId: "10000000-0000-4000-8000-000000000001",
    id: "20000000-0000-4000-8000-000000000002",
    name: "M4 E2E Pet",
  };

  const first = await app.inject({
    method: "POST",
    url: "/createPet",
    payload: input,
  });
  assert.equal(first.statusCode, 200);

  const firstBody = first.json() as Record<string, unknown>;
  assert.equal(firstBody.id, input.id);
  assert.equal(firstBody.name, input.name);
  assert.ok("revision" in firstBody);

  const pet = await pool.query(`SELECT "id", "revision", "name" FROM ${PET_TABLE}`);
  assert.equal(pet.rowCount, 1);
  assert.equal(pet.rows[0]?.id, input.id);
  assert.equal(pet.rows[0]?.name, input.name);
  assert.equal(String(pet.rows[0]?.revision), String(firstBody.revision));

  const idempotency = await pool.query(
    'SELECT "state", "result" FROM "aidl_idempotency" ORDER BY "operation_id", "scope", "key"',
  );
  assert.equal(idempotency.rowCount, 1);
  assert.equal(idempotency.rows[0]?.state, "completed");
  assert.deepEqual(idempotency.rows[0]?.result, firstBody);

  const outbox = await pool.query(
    'SELECT "event_id", "event_type", "event_version", "topic", "partition_key", "payload" FROM "aidl_outbox" ORDER BY "sequence"',
  );
  assert.equal(outbox.rowCount, 1);
  assert.equal(outbox.rows[0]?.event_id, input.operationId);
  assert.equal(outbox.rows[0]?.event_type, "petstore.m4.RunnablePetCreated");
  assert.equal(outbox.rows[0]?.event_version, 1);
  assert.equal(outbox.rows[0]?.topic, "petstore.m4.RunnablePetEvents");
  assert.equal(outbox.rows[0]?.partition_key, input.id);
  assert.equal((outbox.rows[0]?.payload as Record<string, unknown> | undefined)?.petId, input.id);

  const retry = await app.inject({
    method: "POST",
    url: "/createPet",
    payload: input,
  });
  assert.equal(retry.statusCode, 200);
  assert.deepEqual(retry.json(), firstBody);

  const counts = await Promise.all([
    pool.query(`SELECT count(*)::int AS "count" FROM ${PET_TABLE}`),
    pool.query('SELECT count(*)::int AS "count" FROM "aidl_idempotency"'),
    pool.query('SELECT count(*)::int AS "count" FROM "aidl_outbox"'),
  ]);
  assert.deepEqual(counts.map((result) => result.rows[0]?.count), [1, 1, 1]);
});
