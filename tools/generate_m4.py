from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from tools.generate_fastify_api import generate_fastify_api_files
from tools.generate_postgres_idempotency import generate_postgres_idempotency_files
from tools.generate_postgres_outbox import generate_postgres_outbox_files
from tools.generate_postgres_persistence import generate_postgres_persistence_files
from tools.generate_postgres_transactions import generate_postgres_transaction_files
from tools.generate_typescript_domain import generate_typescript_domain_files
from tools.generated_ownership import GeneratedOwnershipError, mark_generated_files, write_generated_files


Generator = Callable[[Mapping[str, Any]], dict[str, str]]
_GENERATORS: tuple[Generator, ...] = (
    generate_typescript_domain_files,
    generate_fastify_api_files,
    generate_postgres_persistence_files,
    generate_postgres_transaction_files,
    generate_postgres_idempotency_files,
    generate_postgres_outbox_files,
)


def generate_m4_files(ir: Mapping[str, Any]) -> dict[str, str]:
    """Generate the complete M4-02..M4-07 file set and attach M4-08 ownership markers."""
    bodies: dict[str, str] = {}
    for generator in _GENERATORS:
        generated = generator(ir)
        for path, body in generated.items():
            if path in bodies:
                raise GeneratedOwnershipError(f"M4 generators collide on generated path '{path}'")
            bodies[path] = body
    return mark_generated_files(bodies)


def generate_and_write_m4(ir: Mapping[str, Any], root: Path) -> dict[str, str]:
    """Run generation fully, preflight every destination, then safely replace the file set."""
    files = generate_m4_files(ir)
    write_generated_files(root, files)
    return files
