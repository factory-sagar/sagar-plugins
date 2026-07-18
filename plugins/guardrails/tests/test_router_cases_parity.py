"""Deterministic parity between the routing eval cases and the intent router.

`evals/routing/cases.json` is the single source for routing expectations. Every
case tagged `layer: hook` must be decided exactly by `route_intent`, so the
deterministic majority of the routing eval runs here in CI for free and cannot
drift from the live-eval definitions. Cases tagged `layer: model` (none today)
are exercised only by the live eval scored by scripts/eval-routing.mjs.
"""

import json
import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from intent_router import route_intent  # noqa: E402

CASES_FILE = Path(__file__).resolve().parents[3] / "evals" / "routing" / "cases.json"


def expected_sequence(case):
    if "expectedSequence" in case:
        return list(case["expectedSequence"])
    if case["expectedPrimary"] is None:
        return []
    return [case["expectedPrimary"]]


class RouterCasesParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]

    def test_every_case_declares_a_known_layer(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertIn(case.get("layer"), {"hook", "model"})

    def test_hook_layer_cases_match_route_intent_exactly(self):
        hook_cases = [case for case in self.cases if case.get("layer") == "hook"]
        self.assertGreater(len(hook_cases), 0, "no hook-layer cases found")
        for case in hook_cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    route_intent(case["prompt"]) or [],
                    expected_sequence(case),
                    f"prompt: {case['prompt']!r}",
                )


if __name__ == "__main__":
    unittest.main()
