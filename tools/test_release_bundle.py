from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.release_bundle import (
    PUBLICATION,
    ReleaseError,
    compare_output_trees,
    load_config,
    release_notes_text,
    validate_bundle,
    validate_contract,
)

ROOT = Path(__file__).resolve().parents[1]


class ReleaseBundleTests(unittest.TestCase):
    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory(prefix="aidl-release-test-")
        root = Path(temp.name)
        (root / "release").mkdir()
        (root / "spec").mkdir()
        (root / "pyproject.toml").write_text(
            "[project]\n"
            'name = "aidl-toolchain"\n'
            'version = "0.1.0rc1"\n',
            encoding="utf-8",
        )
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n\n"
            "## 0.1.0rc1 — scoped toolchain pre-release\n\n"
            "- bounded current claim\n\n"
            "## 0.0.0 — unreleased toolchain baseline\n\n"
            "- historical broad claim\n",
            encoding="utf-8",
        )
        (root / "release" / "release.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "distribution": "aidl-toolchain",
                    "version": "0.1.0rc1",
                    "tag": "aidl-toolchain-v0.1.0rc1",
                    "notesSource": "CHANGELOG.md",
                    "contractGlob": "spec/*.json",
                    "publication": PUBLICATION,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "spec" / "alpha.schema.json").write_text(
            '{"$schema":"https://json-schema.org/draft/2020-12/schema"}\n',
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"],
            cwd=root,
            check=True,
        )
        return temp, root

    def test_contract_requires_pyproject_version_match(self) -> None:
        temp, root = self._fixture()
        self.addCleanup(temp.cleanup)
        config = load_config(root)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "aidl-toolchain"\nversion = "0.1.0rc2"\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(ReleaseError, "does not match pyproject version"):
            validate_contract(root, config)

    def test_contract_requires_exact_tag(self) -> None:
        temp, root = self._fixture()
        self.addCleanup(temp.cleanup)
        config = load_config(root)
        with self.assertRaisesRegex(ReleaseError, "requested tag"):
            validate_contract(root, config, tag="aidl-toolchain-v0.1.0rc2")

    def test_config_requires_explicit_prerelease_version(self) -> None:
        temp, root = self._fixture()
        self.addCleanup(temp.cleanup)
        path = root / "release" / "release.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["version"] = "0.1.0"
        raw["tag"] = "aidl-toolchain-v0.1.0"
        path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "explicit PEP 440 pre-release"):
            load_config(root)

    def test_config_requires_tag_only_github_prerelease_publication(self) -> None:
        temp, root = self._fixture()
        self.addCleanup(temp.cleanup)
        path = root / "release" / "release.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["publication"] = "disabled"
        path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "publication must be exactly"):
            load_config(root)

    def test_release_notes_are_only_current_scoped_section(self) -> None:
        temp, root = self._fixture()
        self.addCleanup(temp.cleanup)
        notes = release_notes_text(root, load_config(root))
        self.assertIn("bounded current claim", notes)
        self.assertNotIn("historical broad claim", notes)
        self.assertFalse(notes.startswith("# Changelog"))

    def test_current_notes_name_every_nonimplemented_profile_as_nonclaim(self) -> None:
        config = load_config(ROOT)
        notes = release_notes_text(ROOT, config)
        manifest = json.loads((ROOT / "spec" / "conformance-manifest.json").read_text(encoding="utf-8"))
        nonimplemented_profiles = [
            surface["id"]
            for surface in manifest["surfaces"]
            if surface["kind"] == "profile" and surface["status"] != "implemented"
        ]
        self.assertTrue(nonimplemented_profiles)
        for profile_id in nonimplemented_profiles:
            with self.subTest(profile_id=profile_id):
                self.assertIn(f"`{profile_id}`", notes)
        self.assertIn("No stability or production-completeness promise", notes)

    def test_release_workflow_publication_is_exact_tag_prerelease_only(self) -> None:
        config = load_config(ROOT)
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("contents: write", workflow)
        self.assertIn(f"github.ref_name == '{config.tag}'", workflow)
        self.assertIn("github.ref_type == 'tag'", workflow)
        self.assertIn("--verify-tag", workflow)
        self.assertIn("--prerelease", workflow)
        self.assertNotIn("latest", workflow.lower())

    def test_contract_inventory_tracks_new_json_contracts_deterministically(self) -> None:
        temp, root = self._fixture()
        self.addCleanup(temp.cleanup)
        (root / "spec" / "zeta.json").write_text("{}\n", encoding="utf-8")
        subprocess.run(["git", "add", "spec/zeta.json"], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "add contract"],
            cwd=root,
            check=True,
        )
        contracts = validate_contract(root, load_config(root))
        self.assertEqual([path.as_posix() for path in contracts], ["spec/alpha.schema.json", "spec/zeta.json"])

    def test_compare_output_trees_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root / "first", root / "second"
            first.mkdir()
            second.mkdir()
            (first / "artifact").write_bytes(b"same")
            with self.assertRaisesRegex(ReleaseError, "file set differs"):
                compare_output_trees(first, second)

    def test_compare_output_trees_rejects_non_reproducible_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root / "first", root / "second"
            first.mkdir()
            second.mkdir()
            (first / "artifact").write_bytes(b"first")
            (second / "artifact").write_bytes(b"second")
            with self.assertRaisesRegex(ReleaseError, "reproducibility mismatch"):
                compare_output_trees(first, second)

    def test_validate_bundle_rejects_additional_root_artifact(self) -> None:
        temp, root = self._fixture()
        self.addCleanup(temp.cleanup)
        config = load_config(root)
        output = root / "dist-release"
        stage = output / "aidl-toolchain-0.1.0rc1-release"
        stage.mkdir(parents=True)
        (output / "unexpected.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "release output entries differ"):
            validate_bundle(root, output, config)


if __name__ == "__main__":
    unittest.main()
