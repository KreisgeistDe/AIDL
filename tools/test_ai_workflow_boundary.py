from __future__ import annotations

import unittest

from tools.validate_ai_workflow_boundary import (
    AUTHORIZED_LEGACY_DELETIONS,
    parse_name_status_z,
    violations,
)


def _record(*fields: str) -> bytes:
    return b"\0".join(field.encode("utf-8") for field in fields) + b"\0"


class AiWorkflowBoundaryTests(unittest.TestCase):
    def test_all_four_legacy_deletions_are_allowed(self) -> None:
        raw = b"".join(_record("D", path) for path in sorted(AUTHORIZED_LEGACY_DELETIONS))
        self.assertEqual(violations(parse_name_status_z(raw)), ())

    def test_unrelated_non_ai_change_is_allowed(self) -> None:
        self.assertEqual(violations(parse_name_status_z(_record("M", "README.md"))), ())

    def test_unauthorized_ai_deletion_is_rejected(self) -> None:
        errors = violations(parse_name_status_z(_record("D", ".ai/other.json")))
        self.assertEqual(len(errors), 1)
        self.assertIn("unauthorized .ai deletion", errors[0])

    def test_rename_from_non_ai_into_ai_is_rejected(self) -> None:
        errors = violations(
            parse_name_status_z(_record("R100", "docs/legacy.md", ".ai/legacy.md"))
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("docs/legacy.md -> .ai/legacy.md", errors[0])

    def test_rename_from_ai_to_non_ai_is_rejected(self) -> None:
        errors = violations(
            parse_name_status_z(_record("R100", ".ai/legacy.md", "docs/legacy.md"))
        )
        self.assertEqual(len(errors), 1)
        self.assertIn(".ai/legacy.md -> docs/legacy.md", errors[0])

    def test_copy_from_non_ai_into_ai_is_rejected(self) -> None:
        errors = violations(
            parse_name_status_z(_record("C100", "docs/legacy.md", ".ai/legacy.md"))
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("docs/legacy.md -> .ai/legacy.md", errors[0])

    def test_copy_from_ai_to_non_ai_is_rejected(self) -> None:
        errors = violations(
            parse_name_status_z(_record("C100", ".ai/legacy.md", "docs/legacy.md"))
        )
        self.assertEqual(len(errors), 1)
        self.assertIn(".ai/legacy.md -> docs/legacy.md", errors[0])

    def test_tab_delimited_status_token_is_supported(self) -> None:
        raw = _record("R100\tdocs/legacy.md", ".ai/legacy.md")
        errors = violations(parse_name_status_z(raw))
        self.assertEqual(len(errors), 1)
        self.assertIn("docs/legacy.md -> .ai/legacy.md", errors[0])


if __name__ == "__main__":
    unittest.main()
