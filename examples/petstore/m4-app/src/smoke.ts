import { createApp } from "./app.js";
import { createPool } from "./db.js";
import { migrate } from "./migrate.js";

const pool = createPool();
try {
  const migrations = await migrate(pool);
  const probe = await pool.query<{ value: number }>("SELECT 1::int AS value");
  if (probe.rows[0]?.value !== 1) throw new Error("PostgreSQL readiness probe failed");
  const app = createApp(pool);
  await app.ready();
  await app.close();
  process.stdout.write(`petstore startup smoke ok (${migrations.length} migrations)\n`);
} finally {
  await pool.end();
}
