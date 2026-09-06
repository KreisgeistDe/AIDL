import { Pool } from "pg";

export interface GeneratedQueryResult {
  readonly rowCount: number | null;
  readonly rows: ReadonlyArray<Record<string, unknown>>;
}

export interface GeneratedPgClient {
  query(sql: string, params?: ReadonlyArray<unknown>): Promise<GeneratedQueryResult>;
}

export function createPool(): Pool {
  return new Pool({
    connectionString: process.env.DATABASE_URL ?? "postgres://postgres:postgres@127.0.0.1:5432/petstore",
  });
}

export function generatedClient(pool: Pool): GeneratedPgClient {
  return {
    async query(sql: string, params: ReadonlyArray<unknown> = []): Promise<GeneratedQueryResult> {
      const result = await pool.query(sql, [...params]);
      return {
        rowCount: result.rowCount,
        rows: result.rows as ReadonlyArray<Record<string, unknown>>,
      };
    },
  };
}
