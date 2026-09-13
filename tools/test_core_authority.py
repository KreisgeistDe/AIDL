from __future__ import annotations

import unittest
from pathlib import Path

from tools.compiler_language_surface_body_parity import ContractBodyParityBridge
from tools.core_authority import (
    COMPATIBILITY_BINDING_PATH,
    REVISION4_PATH,
    CoreAuthorityError,
    assert_revision4_compatibility_authorized,
    git_blob_sha1,
)


class CoreAuthorityTest(unittest.TestCase):
    def test_revision4_projection_is_exactly_core_authorized(self) -> None:
        contract = assert_revision4_compatibility_authorized()
        self.assertEqual(contract["authority"], "M10.1")
        self.assertEqual(contract["status"], "frozen")
        self.assertEqual(
            git_blob_sha1(REVISION4_PATH.read_bytes()),
            "1494f07be6ca92fc8198c18e7887b9c0851bf18e",
        )

    def test_revision4_projection_drift_fails_closed(self) -> None:
        drifted = REVISION4_PATH.read_bytes() + b"\n"
        with self.assertRaisesRegex(CoreAuthorityError, "projection drift"):
            assert_revision4_compatibility_authorized(contract_bytes=drifted)

    def test_binding_role_cannot_restore_semantic_authority(self) -> None:
        binding = COMPATIBILITY_BINDING_PATH.read_text(encoding="utf-8").replace(
            'role: "compatibility-only"',
            'role: "semantic-authority"',
        )
        with self.assertRaisesRegex(CoreAuthorityError, "compatibility role"):
            assert_revision4_compatibility_authorized(binding_source=binding)

    def test_production_bridge_uses_core_authority_gate(self) -> None:
        bridge = ContractBodyParityBridge()
        self.assertEqual(bridge.contract["contract_revision"], 4)


if __name__ == "__main__":
    unittest.main()
