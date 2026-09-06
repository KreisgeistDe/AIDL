from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.generate_postgres_idempotency import GENERATED_IDEMPOTENCY_PATH, generate_postgres_idempotency_files
from tools.generate_postgres_outbox import GENERATED_OUTBOX_PATH, generate_postgres_outbox_files
from tools.test_generate_postgres_idempotency import _ir as idempotency_ir
from tools.test_generate_postgres_outbox import _ir as outbox_ir


class GeneratedRuntimeTypeScriptCompileTest(unittest.TestCase):
    def test_m4_06_and_m4_07_runtimes_compile_with_typescript_5_9_strict_nodenext(self) -> None:
        node_version = subprocess.run(
            ["node", "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        npm_version = subprocess.run(
            ["npm", "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertTrue(node_version.startswith("v22."), node_version)
        self.assertTrue(npm_version.startswith("10."), npm_version)

        idempotency_runtime = generate_postgres_idempotency_files(idempotency_ir())[GENERATED_IDEMPOTENCY_PATH]
        outbox_runtime = generate_postgres_outbox_files(outbox_ir())[GENERATED_OUTBOX_PATH]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "idempotency.ts").write_text(idempotency_runtime, encoding="utf-8")
            (root / "outbox.ts").write_text(outbox_runtime, encoding="utf-8")
            (root / "tsconfig.json").write_text(
                json.dumps(
                    {
                        "compilerOptions": {
                            "target": "ES2022",
                            "module": "NodeNext",
                            "moduleResolution": "NodeNext",
                            "strict": True,
                            "noEmit": True,
                            "skipLibCheck": True,
                        },
                        "include": ["idempotency.ts", "outbox.ts"],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "npm",
                    "exec",
                    "--yes",
                    "--package=typescript@5.9.3",
                    "--",
                    "tsc",
                    "--project",
                    str(root / "tsconfig.json"),
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
