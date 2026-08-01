import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

import prompt_submit  # noqa: E402


class PromptSubmitTests(unittest.TestCase):
    def run_main(self, payload):
        stdout = io.StringIO()
        original_stdin, original_stdout = sys.stdin, sys.stdout
        try:
            sys.stdin = io.StringIO(json.dumps(payload))
            sys.stdout = stdout
            code = prompt_submit.main()
        finally:
            sys.stdin, sys.stdout = original_stdin, original_stdout
        return code, stdout.getvalue()

    def test_runs_both_stages_with_identical_input_in_router_then_budget_order(self):
        calls = []

        def router():
            calls.append(("router", sys.stdin.read()))
            print("router output")
            return 0

        def budget():
            calls.append(("budget", sys.stdin.read()))
            print("budget output")
            return 0

        payload = {"prompt": "Review PR 42.", "session_id": "prompt-submit"}
        with (
            mock.patch.object(prompt_submit.intent_router, "main", side_effect=router),
            mock.patch.object(prompt_submit.review_budget, "main", side_effect=budget),
        ):
            code, output = self.run_main(payload)

        encoded = json.dumps(payload)
        self.assertEqual(code, 0)
        self.assertEqual(output, "router output\nbudget output\n")
        self.assertEqual(calls, [("router", encoded), ("budget", encoded)])

    def test_stage_failure_does_not_suppress_the_later_stage(self):
        calls = []

        def router():
            calls.append("router")
            print("router output")
            return 2

        def budget():
            calls.append("budget")
            print("budget output")
            return 0

        with (
            mock.patch.object(prompt_submit.intent_router, "main", side_effect=router),
            mock.patch.object(prompt_submit.review_budget, "main", side_effect=budget),
        ):
            code, output = self.run_main({"prompt": "Review PR 42."})

        self.assertEqual(code, 2)
        self.assertEqual(output, "router output\nbudget output\n")
        self.assertEqual(calls, ["router", "budget"])


if __name__ == "__main__":
    unittest.main()
