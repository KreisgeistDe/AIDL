import Fastify, { type FastifyInstance } from "fastify";
import type { Pool } from "pg";

import { registerApiRoutes, type ApiHandlers } from "../generated/api.js";
import type { RunnablePet } from "../generated/domain.js";
import { executeCreatePetIdempotent } from "../generated/idempotency.js";
import { executeCreatePetTransaction } from "../generated/transactions.js";
import { generatedClient } from "./db.js";

export function createApp(pool: Pool): FastifyInstance {
  const app = Fastify({ logger: false });
  const client = generatedClient(pool);
  const handlers: ApiHandlers = {
    async createPet(input) {
      return (await executeCreatePetIdempotent(
        client,
        input,
        () => executeCreatePetTransaction(client, input),
      )) as RunnablePet;
    },
  };
  registerApiRoutes(app, handlers);
  return app;
}
