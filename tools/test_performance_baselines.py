from __future__ import annotations

import copy
import unittest

from tools.performance_baselines import (
    ROOT,
    load_contract,
    render_workload,
    validate_data,
)


class PerformanceBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract(ROOT)

    def test_repository_contract_is_valid(self) -> None:
        self.assertEqual([], validate_data(self.contract, root=ROOT))

    def test_workload_rendering_is_byte_deterministic(self) -> None:
        for workload in self.contract["workloads"]:
            self.assertEqual(render_workload(workload), render_workload(workload))

    def test_baseline_drift_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["workloads"][0]["baseline"]["declarations"] += 1
        errors = validate_data(candidate, root=ROOT)
        self.assertTrue(
            any("small/declarations: baseline" in error for error in errors), errors
        )

    def test_resource_limit_below_large_workload_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["resourceLimits"]["sourceBytes"] = (
            candidate["workloads"][-1]["baseline"]["sourceBytes"] - 1
        )
        errors = validate_data(candidate, root=ROOT)
        self.assertTrue(
            any("large/sourceBytes" in error and "exceeds resource limit" in error for error in errors),
            errors,
        )

    def test_resource_limit_cannot_become_unbounded(self) -> None:
        candidate = copy.deepcopy(self.contract)
        large_declarations = candidate["workloads"][-1]["baseline"]["declarations"]
        candidate["resourceLimits"]["declarations"] = large_declarations * 2 + 1
        errors = validate_data(candidate, root=ROOT)
        self.assertTrue(
            any("declarations: resource limit" in error and "exceeds 2x" in error for error in errors),
            errors,
        )

    def test_workload_order_is_part_of_contract(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["workloads"][0], candidate["workloads"][1] = (
            candidate["workloads"][1],
            candidate["workloads"][0],
        )
        errors = validate_data(candidate, root=ROOT)
        self.assertIn(
            "workloads must be exactly small, medium, large in that order",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
