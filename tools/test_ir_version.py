from __future__ import annotations

import ast
import unittest
from pathlib import Path

from tools.ir_version import (
    CURRENT_IR_VERSION,
    IrCompatibilityError,
    IrConsumerCapabilities,
    IrVersion,
    require_compatible_ir,
)


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "tools" / "ir_version.py"


def _document(version: object = CURRENT_IR_VERSION, profiles=None):
    return {"irVersion": version, "profiles": profiles or [{"id": "core", "major": 1}]}


class IrVersionTest(unittest.TestCase):
    def test_current_version_is_explicit_and_accepted(self) -> None:
        consumer = IrConsumerCapabilities.create("0.3.0", profile_majors=[("core", 1)])
        self.assertEqual(IrVersion(0, 3, 0), IrVersion.parse(CURRENT_IR_VERSION))
        self.assertIsNone(require_compatible_ir(_document(), consumer))

    def test_older_minor_and_patch_variants_within_major_are_accepted(self) -> None:
        consumer = IrConsumerCapabilities.create("0.3.0", profile_majors=[("core", 1)])
        for version in ("0.1.9", "0.2.0", "0.3.7"):
            with self.subTest(version=version):
                require_compatible_ir(_document(version), consumer)

    def test_different_major_is_rejected(self) -> None:
        consumer = IrConsumerCapabilities.create("1.2.0", profile_majors=[("core", 1)])
        with self.assertRaisesRegex(IrCompatibilityError, "incompatible IR major"):
            require_compatible_ir(_document("0.3.0"), consumer)

    def test_newer_minor_requires_explicit_additive_field_capabilities(self) -> None:
        document = _document("0.4.0")
        strict = IrConsumerCapabilities.create("0.3.0", profile_majors=[("core", 1)])
        with self.assertRaisesRegex(IrCompatibilityError, "/newField"):
            require_compatible_ir(document, strict, additive_fields=["/newField"])

        tolerant = IrConsumerCapabilities.create(
            "0.3.0",
            profile_majors=[("core", 1)],
            tolerated_additive_fields=["/newField"],
        )
        require_compatible_ir(document, tolerant, additive_fields=["/newField"])

    def test_unknown_profile_major_is_rejected_deterministically(self) -> None:
        consumer = IrConsumerCapabilities.create(
            "0.3.0", profile_majors=[("core", 1), ("cloud", 1)]
        )
        document = _document(
            profiles=[{"id": "web", "major": 2}, {"id": "cloud", "major": 2}]
        )
        with self.assertRaisesRegex(
            IrCompatibilityError, "cloud@2, web@2"
        ):
            require_compatible_ir(document, consumer)

    def test_known_profile_majors_are_independent_of_ir_version(self) -> None:
        consumer = IrConsumerCapabilities.create(
            "0.3.0", profile_majors=[("core", 1), ("cloud", 2)]
        )
        require_compatible_ir(
            _document(profiles=[{"id": "cloud", "major": 2}, {"id": "core", "major": 1}]),
            consumer,
        )

    def test_missing_or_malformed_versions_are_rejected(self) -> None:
        consumer = IrConsumerCapabilities.create("0.3.0", profile_majors=[("core", 1)])
        for value in (None, 3, "", "0.3", "v0.3.0", "00.3.0", "0.03.0", "0.3.0-beta"):
            with self.subTest(value=value), self.assertRaises(IrCompatibilityError):
                require_compatible_ir(_document(value), consumer)

    def test_invalid_capability_manifests_and_document_profiles_are_rejected(self) -> None:
        for profile in (("", 1), ("Core", 1), ("core", 0), ("core", True)):
            with self.subTest(profile=profile), self.assertRaises(IrCompatibilityError):
                IrConsumerCapabilities.create("0.3.0", profile_majors=[profile])
        with self.assertRaises(IrCompatibilityError):
            IrConsumerCapabilities.create("0.3.0", tolerated_additive_fields=["not-a-pointer"])
        consumer = IrConsumerCapabilities.create("0.3.0", profile_majors=[("core", 1)])
        with self.assertRaises(IrCompatibilityError):
            require_compatible_ir({"irVersion": "0.3.0", "profiles": {}}, consumer)

    def test_boundary_does_not_mutate_or_depend_on_compiler_or_psi(self) -> None:
        document = _document()
        original = {"irVersion": "0.3.0", "profiles": [{"id": "core", "major": 1}]}
        consumer = IrConsumerCapabilities.create("0.3.0", profile_majors=[("core", 1)])
        require_compatible_ir(document, consumer)
        self.assertEqual(original, document)

        tree = ast.parse(VERSION_PATH.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        self.assertFalse(any("compiler" in name or "intellij" in name or "psi" in name for name in imports))


if __name__ == "__main__":
    unittest.main()
