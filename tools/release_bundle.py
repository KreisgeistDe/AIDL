from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CONFIG_ERROR_EXIT = 2
PRERELEASE_RE = re.compile(r"^\d+\.\d+\.\d+(?:a|b|rc)\d+$")
PUBLICATION = "github-prerelease-on-tag"


class ReleaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseConfig:
    schema_version: int
    distribution: str
    version: str
    tag: str
    notes_source: str
    contract_glob: str
    publication: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        raise ReleaseError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout.strip()


def load_config(root: Path = ROOT, path: Path | None = None) -> ReleaseConfig:
    config_path = path or root / "release" / "release.json"
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot read release config {config_path}: {exc}") from exc
    expected = {
        "schemaVersion", "distribution", "version", "tag",
        "notesSource", "contractGlob", "publication",
    }
    if set(raw) != expected:
        raise ReleaseError(f"release config fields must be exactly {sorted(expected)}")
    if raw["schemaVersion"] != 1:
        raise ReleaseError("release config schemaVersion must be 1")
    if raw["publication"] != PUBLICATION:
        raise ReleaseError(f"release publication must be exactly {PUBLICATION!r}")
    version = str(raw["version"])
    if not PRERELEASE_RE.fullmatch(version):
        raise ReleaseError("release version must be an explicit PEP 440 pre-release like 0.1.0rc1")
    return ReleaseConfig(
        schema_version=raw["schemaVersion"], distribution=raw["distribution"],
        version=version, tag=raw["tag"], notes_source=raw["notesSource"],
        contract_glob=raw["contractGlob"], publication=raw["publication"],
    )


def project_version(root: Path = ROOT) -> tuple[str, str]:
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        project = data["project"]
        return str(project["name"]), str(project["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseError(f"cannot read project name/version from pyproject.toml: {exc}") from exc


def tracked_contracts(root: Path, config: ReleaseConfig) -> list[Path]:
    output = _run(["git", "ls-files", "-z", "--", config.contract_glob], cwd=root)
    names = [name for name in output.split("\0") if name]
    paths = sorted((Path(name) for name in names if name.endswith(".json")), key=lambda p: p.as_posix())
    if not paths:
        raise ReleaseError(f"no tracked JSON contracts match {config.contract_glob}")
    for path in paths:
        if not (root / path).is_file():
            raise ReleaseError(f"tracked contract is missing from working tree: {path}")
    return paths


def release_notes_text(root: Path, config: ReleaseConfig) -> str:
    notes_path = root / config.notes_source
    try:
        notes = notes_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReleaseError(f"cannot read release notes source {notes_path}: {exc}") from exc
    heading = f"## {config.version} — scoped toolchain pre-release"
    start = notes.find(heading)
    if start < 0:
        raise ReleaseError(f"release notes source must contain exact version heading {heading!r}")
    end = notes.find("\n## ", start + len(heading))
    section = notes[start:] if end < 0 else notes[start:end]
    return section.rstrip() + "\n"


def validate_contract(root: Path, config: ReleaseConfig, *, tag: str | None = None) -> list[Path]:
    distribution, version = project_version(root)
    if distribution != config.distribution:
        raise ReleaseError(f"release distribution {config.distribution!r} does not match pyproject {distribution!r}")
    if version != config.version:
        raise ReleaseError(f"release version {config.version!r} does not match pyproject version {version!r}")
    expected_tag = f"{config.distribution}-v{config.version}"
    if config.tag != expected_tag:
        raise ReleaseError(f"release tag must be exactly {expected_tag!r}")
    if tag is not None and tag != config.tag:
        raise ReleaseError(f"requested tag {tag!r} does not match release tag {config.tag!r}")
    release_notes_text(root, config)
    return tracked_contracts(root, config)


def source_identity(root: Path) -> tuple[str, int]:
    commit = _run(["git", "rev-parse", "HEAD"], cwd=root)
    epoch_text = _run(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=root)
    try:
        return commit, int(epoch_text)
    except ValueError as exc:
        raise ReleaseError(f"invalid git commit timestamp: {epoch_text!r}") from exc


def expected_wheel_name(config: ReleaseConfig) -> str:
    return f"{config.distribution.replace('-', '_')}-{config.version}-py3-none-any.whl"


def _build_wheel(root: Path, destination: Path, config: ReleaseConfig, epoch: int) -> Path:
    wheelhouse = destination / "wheelhouse"
    wheelhouse.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(PYTHONNOUSERSITE="1", PYTHONHASHSEED="0", SOURCE_DATE_EPOCH=str(epoch))
    _run([
        sys.executable, "-m", "pip", "wheel", "--disable-pip-version-check",
        "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheelhouse), str(root),
    ], cwd=destination, env=env)
    wheels = sorted(wheelhouse.glob("*.whl"))
    if len(wheels) != 1:
        raise ReleaseError(f"expected exactly one wheel, found {[p.name for p in wheels]}")
    expected = expected_wheel_name(config)
    if wheels[0].name != expected:
        raise ReleaseError(f"wheel name {wheels[0].name!r} does not match expected {expected!r}")
    return wheels[0]


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _checksum_lines(paths: Iterable[Path], base: Path) -> str:
    entries = sorted(paths, key=lambda p: p.relative_to(base).as_posix())
    return "".join(f"{_sha256(p)}  {p.relative_to(base).as_posix()}\n" for p in entries)


def _archive_tree(stage: Path, archive: Path, epoch: int) -> None:
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as tar:
                for path in sorted(stage.rglob("*"), key=lambda p: p.relative_to(stage).as_posix()):
                    relative = path.relative_to(stage)
                    info = tar.gettarinfo(str(path), arcname=f"{stage.name}/{relative.as_posix()}")
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = epoch
                    if path.is_dir():
                        info.mode = 0o755
                        tar.addfile(info)
                    else:
                        info.mode = 0o644
                        with path.open("rb") as handle:
                            tar.addfile(info, handle)


def build_bundle(root: Path, output: Path, config: ReleaseConfig, *, tag: str | None = None) -> Path:
    contracts = validate_contract(root, config, tag=tag)
    commit, epoch = source_identity(root)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    temp_build = output / ".build"
    temp_build.mkdir()
    wheel = _build_wheel(root, temp_build, config, epoch)
    stage = output / f"{config.distribution}-{config.version}-release"
    contracts_dir = stage / "contracts"
    contracts_dir.mkdir(parents=True)
    wheel_target = stage / wheel.name
    shutil.copyfile(wheel, wheel_target)
    released_contracts: list[dict[str, str]] = []
    components: list[Path] = [wheel_target]
    for source in contracts:
        target = contracts_dir / source.name
        shutil.copyfile(root / source, target)
        components.append(target)
        released_contracts.append({
            "releasePath": target.relative_to(stage).as_posix(),
            "sha256": _sha256(target), "sourcePath": source.as_posix(),
        })
    notes_target = stage / f"{config.distribution}-{config.version}-release-notes.md"
    notes_target.write_text(release_notes_text(root, config), encoding="utf-8")
    components.append(notes_target)
    manifest_target = stage / f"{config.distribution}-{config.version}-release-manifest.json"
    _write_json(manifest_target, {
        "schemaVersion": 1, "distribution": config.distribution, "version": config.version,
        "tag": config.tag, "sourceCommit": commit, "sourceDateEpoch": epoch,
        "publication": config.publication,
        "wheel": {"path": wheel_target.relative_to(stage).as_posix(), "sha256": _sha256(wheel_target)},
        "releaseNotes": {"path": notes_target.relative_to(stage).as_posix(), "sha256": _sha256(notes_target), "sourcePath": config.notes_source},
        "contracts": released_contracts,
    })
    components.append(manifest_target)
    checksums = stage / "SHA256SUMS"
    checksums.write_text(_checksum_lines(components, stage), encoding="utf-8")
    archive = output / f"{stage.name}.tar.gz"
    _archive_tree(stage, archive, epoch)
    (output / f"{archive.name}.sha256").write_text(f"{_sha256(archive)}  {archive.name}\n", encoding="utf-8")
    shutil.rmtree(temp_build)
    validate_bundle(root, output, config, tag=tag)
    return stage


def _expected_stage_files(root: Path, config: ReleaseConfig) -> set[str]:
    contracts = validate_contract(root, config)
    return {
        expected_wheel_name(config), f"{config.distribution}-{config.version}-release-notes.md",
        f"{config.distribution}-{config.version}-release-manifest.json", "SHA256SUMS",
        *(f"contracts/{path.name}" for path in contracts),
    }


def _all_relative_files(path: Path) -> set[str]:
    return {item.relative_to(path).as_posix() for item in path.rglob("*") if item.is_file()}


def validate_bundle(root: Path, output: Path, config: ReleaseConfig, *, tag: str | None = None) -> None:
    contracts = validate_contract(root, config, tag=tag)
    commit, epoch = source_identity(root)
    stage_name = f"{config.distribution}-{config.version}-release"
    stage = output / stage_name
    archive = output / f"{stage_name}.tar.gz"
    archive_checksum = output / f"{archive.name}.sha256"
    expected_root = {stage_name, archive.name, archive_checksum.name}
    actual_root = {p.name for p in output.iterdir()}
    if actual_root != expected_root:
        raise ReleaseError(f"release output entries differ: expected {sorted(expected_root)}, got {sorted(actual_root)}")
    expected_stage = _expected_stage_files(root, config)
    actual_stage = _all_relative_files(stage)
    if actual_stage != expected_stage:
        raise ReleaseError(f"release stage files differ: expected {sorted(expected_stage)}, got {sorted(actual_stage)}")
    manifest_path = stage / f"{config.distribution}-{config.version}-release-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot read release manifest: {exc}") from exc
    if manifest.get("distribution") != config.distribution or manifest.get("version") != config.version:
        raise ReleaseError("release manifest distribution/version mismatch")
    if manifest.get("tag") != config.tag:
        raise ReleaseError("release manifest tag mismatch")
    if manifest.get("sourceCommit") != commit or manifest.get("sourceDateEpoch") != epoch:
        raise ReleaseError("release manifest source identity mismatch")
    if manifest.get("publication") != config.publication:
        raise ReleaseError("release manifest publication mismatch")
    entries = manifest.get("contracts")
    expected_sources = [p.as_posix() for p in contracts]
    if not isinstance(entries, list):
        raise ReleaseError("release manifest contracts must be a list")
    if [entry.get("sourcePath") for entry in entries] != expected_sources:
        raise ReleaseError("release manifest contract inventory differs")
    for entry in entries:
        target = stage / entry["releasePath"]
        if entry["sha256"] != _sha256(target):
            raise ReleaseError(f"release manifest checksum mismatch for {entry['releasePath']}")
    for name, entry in (("wheel", manifest.get("wheel", {})), ("releaseNotes", manifest.get("releaseNotes", {}))):
        path_value = entry.get("path")
        if not isinstance(path_value, str) or entry.get("sha256") != _sha256(stage / path_value):
            raise ReleaseError(f"release manifest checksum mismatch for {name}")
    notes_path = stage / manifest["releaseNotes"]["path"]
    if notes_path.read_text(encoding="utf-8") != release_notes_text(root, config):
        raise ReleaseError("release notes drift from configured scoped section")
    checksum_targets = [stage / rel for rel in sorted(expected_stage) if rel != "SHA256SUMS"]
    if (stage / "SHA256SUMS").read_text(encoding="utf-8") != _checksum_lines(checksum_targets, stage):
        raise ReleaseError("SHA256SUMS does not exactly match release components")
    if archive_checksum.read_text(encoding="utf-8") != f"{_sha256(archive)}  {archive.name}\n":
        raise ReleaseError("archive SHA-256 file does not match release archive")
    with tarfile.open(archive, "r:gz") as tar:
        members = sorted(m.name for m in tar.getmembers() if m.isfile())
        expected_members = sorted(f"{stage_name}/{path}" for path in expected_stage)
        if members != expected_members:
            raise ReleaseError(f"archive members differ: expected {expected_members}, got {members}")
        for member in members:
            extracted = tar.extractfile(member)
            if extracted is None:
                raise ReleaseError(f"archive member cannot be read: {member}")
            relative = member.removeprefix(f"{stage_name}/")
            if extracted.read() != (stage / relative).read_bytes():
                raise ReleaseError(f"archive content mismatch for {member}")


def compare_output_trees(first: Path, second: Path) -> None:
    first_files, second_files = _all_relative_files(first), _all_relative_files(second)
    if first_files != second_files:
        raise ReleaseError(f"reproducibility file set differs: {sorted(first_files)} != {sorted(second_files)}")
    for relative in sorted(first_files):
        if (first / relative).read_bytes() != (second / relative).read_bytes():
            raise ReleaseError(f"reproducibility mismatch for {relative}")


def reproduce_bundle(root: Path, output: Path, config: ReleaseConfig, *, tag: str | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="aidl-release-repro-") as temp:
        first, second = Path(temp) / "first", Path(temp) / "second"
        build_bundle(root, first, config, tag=tag)
        build_bundle(root, second, config, tag=tag)
        compare_output_trees(first, second)
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(first, output)
    validate_bundle(root, output, config, tag=tag)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and certify deterministic AIDL release bundles")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--tag")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify-contract")
    for command in ("build", "validate", "reproduce"):
        child = subparsers.add_parser(command)
        child.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    try:
        config = load_config(root, args.config.resolve() if args.config else None)
        if args.command == "verify-contract":
            contracts = validate_contract(root, config, tag=args.tag)
            print(f"release contract: {config.distribution} {config.version}, {len(contracts)} JSON contracts, {config.publication}")
        elif args.command == "build":
            build_bundle(root, args.output.resolve(), config, tag=args.tag)
            print(f"release bundle: built {args.output.resolve()}")
        elif args.command == "validate":
            validate_bundle(root, args.output.resolve(), config, tag=args.tag)
            print(f"release bundle: valid {args.output.resolve()}")
        elif args.command == "reproduce":
            reproduce_bundle(root, args.output.resolve(), config, tag=args.tag)
            print(f"release bundle: reproducible {args.output.resolve()}")
        return 0
    except ReleaseError as exc:
        print(f"release-bundle: {exc}", file=sys.stderr)
        return CONFIG_ERROR_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
