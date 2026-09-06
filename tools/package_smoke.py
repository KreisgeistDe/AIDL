from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURE = ROOT / "fixtures" / "valid" / "m4-minimal" / "app.aidl"


def _run(command: list[str], *, cwd: Path, env: dict[str, str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != expected:
        raise RuntimeError(
            f"command returned {completed.returncode}, expected {expected}: {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aidl-package-smoke-") as temp_dir:
        work = Path(temp_dir)
        wheelhouse = work / "wheelhouse"
        wheelhouse.mkdir()

        build_env = os.environ.copy()
        build_env.pop("PYTHONPATH", None)
        build_env["PYTHONNOUSERSITE"] = "1"
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-deps",
                "--wheel-dir",
                str(wheelhouse),
                str(ROOT),
            ],
            cwd=work,
            env=build_env,
        )
        wheels = sorted(wheelhouse.glob("aidl_toolchain-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected exactly one AIDL wheel, found: {wheels}")

        venv_dir = work / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
        python = scripts_dir / ("python.exe" if os.name == "nt" else "python")
        aidl = scripts_dir / ("aidl.exe" if os.name == "nt" else "aidl")

        runtime_env = os.environ.copy()
        runtime_env.pop("PYTHONPATH", None)
        runtime_env["PYTHONNOUSERSITE"] = "1"
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(wheels[0]),
            ],
            cwd=work,
            env=runtime_env,
        )

        project = work / "project"
        project.mkdir()
        shutil.copy2(VALID_FIXTURE, project / "app.aidl")
        invalid = project / "invalid.aidl"
        invalid.write_text("module smoke.invalid\nexport value Broken {\n", encoding="utf-8")

        help_result = _run([str(aidl), "--help"], cwd=work, env=runtime_env)
        if "AIDL compiler command line interface" not in help_result.stdout:
            raise RuntimeError("installed aidl --help did not expose the production CLI")

        _run([str(aidl), "check", str(project / "app.aidl")], cwd=work, env=runtime_env)
        _run(
            [
                str(aidl),
                "diff",
                "--old",
                str(project / "app.aidl"),
                "--new",
                str(project / "app.aidl"),
                "--format",
                "json",
            ],
            cwd=work,
            env=runtime_env,
        )
        _run([str(aidl), "check", str(invalid)], cwd=work, env=runtime_env, expected=1)

        import_result = _run(
            [str(python), "-c", "import tools.aidl_cli, spec; print(tools.aidl_cli.__file__); print(spec.__file__)"],
            cwd=work,
            env=runtime_env,
        )
        if str(ROOT) in import_result.stdout:
            raise RuntimeError("installed smoke imported AIDL modules from the repository checkout")

    print("AIDL package smoke: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
