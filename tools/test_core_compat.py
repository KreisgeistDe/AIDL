from __future__ import annotations

import unittest

from tools.core_bootstrap import TypeRef
from tools.core_compat import (
    NormalizedTypeRef,
    RangeConstraint,
    canonical_header,
    normalize_client_header,
    normalize_legacy_type_ref,
    normalize_migration_header,
    semantic_hash,
)


class CoreCompatibilityTest(unittest.TestCase):
    def test_legacy_list_normalizes_to_core_generic_typeref(self) -> None:
        legacy = normalize_legacy_type_ref("[uuid]?")
        canonical = NormalizedTypeRef(TypeRef("list", (TypeRef("uuid"),), True))
        self.assertEqual(legacy, canonical)
        self.assertEqual(semantic_hash(legacy), semantic_hash(canonical))

    def test_legacy_range_preserves_bounds_in_compatibility_envelope(self) -> None:
        legacy = normalize_legacy_type_ref("string(1..80)?")
        canonical = NormalizedTypeRef(
            TypeRef("string", (), True),
            (RangeConstraint("1", "80"),),
        )
        self.assertEqual(legacy, canonical)
        self.assertEqual(semantic_hash(legacy), semantic_hash(canonical))
        self.assertEqual(legacy.to_json()["constraints"][0]["kind"], "range")

    def test_nested_core_generic_is_already_canonical(self) -> None:
        normalized = normalize_legacy_type_ref("list<ref<Entity>>?")
        self.assertEqual(normalized.type_ref.name, "list")
        self.assertTrue(normalized.type_ref.optional)
        self.assertEqual(normalized.type_ref.arguments[0].name, "ref")

    def test_legacy_client_header_matches_named_core_header(self) -> None:
        legacy = normalize_client_header("client Billing for Payments")
        canonical = canonical_header(
            "client",
            "Billing",
            service={"declarationRef": "Payments"},
        )
        self.assertEqual(legacy, canonical)
        self.assertEqual(semantic_hash(legacy), semantic_hash(canonical))

    def test_legacy_migration_header_matches_named_core_header(self) -> None:
        legacy = normalize_migration_header('migration M from "1" to "2"')
        canonical = canonical_header(
            "migration",
            "M",
            fromVersion="1",
            toVersion="2",
        )
        self.assertEqual(legacy, canonical)
        self.assertEqual(semantic_hash(legacy), semantic_hash(canonical))

    def test_unsupported_legacy_shapes_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            normalize_legacy_type_ref("[]")
        with self.assertRaises(ValueError):
            normalize_client_header("client C on Service")
        with self.assertRaises(ValueError):
            normalize_migration_header("migration M 1 2")


if __name__ == "__main__":
    unittest.main()
