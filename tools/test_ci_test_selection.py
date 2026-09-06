from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.ci_test_selection import (
    CONFIG_ERROR_EXIT,
    Exclusion,
    SelectionError,
    SelectionPolicy,
    TestSelection,
    load_policy,
    main,
    select_tests,
)


def _policy(*exclusions: Exclusion) -> SelectionPolicy:
    return SelectionPolicy(
        version=1,
        roots=("tools",),
        pattern="test_*.py",
        exclusions=tuple(exclusions),
    )


def _exclusion(path: str = "tools/test_special.py") -> Exclusion:
    return Exclusion(
        path=path,
        ci_job="Specialized Gate",
        command=f"python3 -m unittest {path}",
        reason="Executed by a dedicated independently visible CI gate.",
    )


class CiTestSelectionTest(unittest.TestCase):
    def test_missing_registration_defaults_new_committed_test_to_execution(self) -> None:
        selection = select_tests(
            ["tools/helper.py", "tools/test_new_regression.py"],
            _policy(),
        )
        self.assertEqual(("tools/test_new_regression.py",), selection.discovered)
        self.assertEqual(selection.discovered, selection.selected)
        self.assertEqual((), selection.excluded)

    def test_selection_is_deduplicated_and_deterministically_sorted(self) -> None:
        selection = select_tests(
            [
                "tools/test_z.py",
                "tools/test_a.py",
                "tools/test_z.py",
                "other/test_ignored.py",
            ],
            _policy(),
        )
        self.assertEqual(("tools/test_a.py", "tools/test_z.py"), selection.discovered)
        self.assertEqual(selection.discovered, selection.selected)

    def test_explicit_exclusion_remains_discovered_but_not_generically_selected(self) -> None:
        exclusion = _exclusion()
        selection = select_tests(
            ["tools/test_default.py", exclusion.path],
            _policy(exclusion),
        )
        self.assertEqual(
            ("tools/test_default.py", "tools/test_special.py"),
            selection.discovered,
        )
        self.assertEqual(("tools/test_default.py",), selection.selected)
        self.assertEqual((exclusion,), selection.excluded)

    def test_stale_exclusion_fails_validation(self) -> None:
        with self.assertRaisesRegex(SelectionError, "not committed discovered test modules"):
            select_tests(["tools/test_default.py"], _policy(_exclusion()))

    def test_policy_requires_versioned_explicit_exclusion_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "roots": ["tools"],
                        "pattern": "test_*.py",
                        "exclusions": [
                            {
                                "path": "tools/test_special.py",
                                "ciJob": "Specialized Gate",
                                "command": "python3 -m unittest tools/test_special.py"
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SelectionError, "must contain exactly"):
                load_policy(path)

            path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "roots": ["tools"],
                        "pattern": "test_*.py",
                        "exclusions": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SelectionError, "unsupported test-selection policy version"):
                load_policy(path)

    def test_configuration_error_has_stable_exit_two(self) -> None:
        stderr = io.StringIO()
        with patch(
            "tools.ci_test_selection.repository_selection",
            side_effect=SelectionError("broken policy"),
        ), redirect_stderr(stderr):
            code = main(["validate"])
        self.assertEqual(CONFIG_ERROR_EXIT, code)
        self.assertIn("test-selection: broken policy", stderr.getvalue())

    def test_run_propagates_unittest_exit_status(self) -> None:
        selection = TestSelection(
            discovered=("tools/test_one.py",),
            selected=("tools/test_one.py",),
            excluded=(),
        )
        with patch(
            "tools.ci_test_selection.repository_selection",
            return_value=selection,
        ), patch(
            "tools.ci_test_selection.subprocess.run",
            return_value=SimpleNamespace(returncode=1),
        ) as run:
            code = main(["run"])
        self.assertEqual(1, code)
        command = run.call_args.args[0]
        self.assertEqual(["-m", "unittest", "tools/test_one.py"], command[1:])


if __name__ == "__main__":
    unittest.main()
