import { createApp } from "./app.js";
import { createPool } from "./db.js";

const pool = createPool();
const app = createApp(pool);
const port = Number(process.env.PORT ?? "3000");
const host = process.env.HOST ?? "127.0.0.1";

const shutdown = async (): Promise<void> => {
  await app.close();
  await pool.end();
};

process.on("SIGINT", () => void shutdown().finally(() => process.exit(0)));
process.on("SIGTERM", () => void shutdown().finally(() => process.exit(0)));

await app.listen({ host, port });
