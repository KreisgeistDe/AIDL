import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { Pool } from "pg";

import { createPool } from "./db.js";

export async function migrate(pool: Pool): Promise<ReadonlyArray<string>> {
  const directory = resolve(process.cwd(), "generated", "migrations");
  const names = (await readdir(directory)).filter((name) => name.endsWith(".sql")).sort();
  for (const name of names) {
    const sql = await readFile(resolve(directory, name), "utf8");
    await pool.query(sql);
  }
  return names;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const pool = createPool();
  try {
    const names = await migrate(pool);
    process.stdout.write(`applied ${names.length} migrations\n`);
  } finally {
    await pool.end();
  }
}
