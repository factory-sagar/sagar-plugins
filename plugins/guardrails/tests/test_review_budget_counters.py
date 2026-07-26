import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

import review_budget  # noqa: E402


REVIEWER_CAPS = {
    "change-review": 6,
    "security": 4,
    "review-worker": 6,
}


class ReviewBudgetCounterTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        self.state_dir = root / "budget"
        self.log_dir = root / "log"
        patcher = mock.patch.dict(
            os.environ,
            {
                "DROID_REVIEW_BUDGET_DIR": str(self.state_dir),
                "DROID_GUARDRAILS_LOG_DIR": str(self.log_dir),
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def require_budget_violation(self):
        decision = getattr(review_budget, "budget_violation", None)
        self.assertIsNotNone(
            decision,
            "review_budget must export budget_violation(*, subagent_type, calls_so_far)",
        )
        return decision

    def budget_violation(self, *, subagent_type, calls_so_far):
        decision = self.require_budget_violation()
        return decision(
            subagent_type=subagent_type,
            calls_so_far=calls_so_far,
        )

    def run_hook(self, payload):
        stdout = io.StringIO()
        stderr = io.StringIO()
        original = (sys.stdin, sys.stdout, sys.stderr)
        try:
            sys.stdin = io.StringIO(
                payload if isinstance(payload, str) else json.dumps(payload)
            )
            sys.stdout = stdout
            sys.stderr = stderr
            code = review_budget.main()
        finally:
            sys.stdin, sys.stdout, sys.stderr = original
        return code, stdout.getvalue(), stderr.getvalue()

    def begin_request(self, session_id, prompt, transcript_path=""):
        return self.run_hook(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session_id,
                "prompt": prompt,
                "transcript_path": transcript_path,
            }
        )

    def task(self, session_id, subagent_type, description=""):
        return self.run_hook(
            {
                "hook_event_name": "PreToolUse",
                "session_id": session_id,
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": subagent_type,
                    "description": description,
                },
            }
        )

    def denial_reason(self, output):
        if not output:
            return None
        return json.loads(output)["hookSpecificOutput"]["permissionDecisionReason"]

    def logged_decisions(self):
        log_file = self.log_dir / "decisions.jsonl"
        if not log_file.exists():
            return []
        return [
            json.loads(line)
            for line in log_file.read_text(encoding="utf-8").splitlines()
        ]

    def test_allows_each_individual_cap_boundary_and_denies_the_next_call(self):
        self.require_budget_violation()
        for subagent_type, cap in REVIEWER_CAPS.items():
            with self.subTest(subagent_type=subagent_type):
                self.assertIsNone(
                    self.budget_violation(
                        subagent_type=subagent_type,
                        calls_so_far={subagent_type: cap - 1},
                    )
                )
                self.assertIsNotNone(
                    self.budget_violation(
                        subagent_type=subagent_type,
                        calls_so_far={subagent_type: cap},
                    )
                )

    def test_denial_reason_names_the_cap_and_new_instruction_reset(self):
        self.require_budget_violation()
        for subagent_type, cap in REVIEWER_CAPS.items():
            with self.subTest(subagent_type=subagent_type):
                reason = self.budget_violation(
                    subagent_type=subagent_type,
                    calls_so_far={subagent_type: cap},
                )
                self.assertIsNotNone(reason)
                self.assertIn(subagent_type, reason)
                self.assertIn(str(cap), reason)
                self.assertIn("new user instruction", reason.lower())
                self.assertIn("resets the budget", reason.lower())

    def test_combined_reviewer_cap_denies_without_an_individual_cap_hit(self):
        calls_so_far = {
            "change-review": 5,
            "security": 3,
            "review-worker": 4,
        }
        reason = self.budget_violation(
            subagent_type="security",
            calls_so_far=calls_so_far,
        )
        self.assertIsNotNone(reason)
        self.assertIn("combined", reason.lower())
        self.assertIn("12", reason)

    def test_different_user_prompt_resets_every_reviewer_counter(self):
        self.budget_violation(subagent_type="change-review", calls_so_far={})
        self.assertEqual(self.begin_request("reset", "Review the first diff."), (0, "", ""))
        for _ in range(REVIEWER_CAPS["change-review"]):
            self.assertEqual(self.task("reset", "change-review"), (0, "", ""))
        self.assertIsNotNone(self.denial_reason(self.task("reset", "change-review")[1]))

        self.assertEqual(self.begin_request("reset", "Review the next diff."), (0, "", ""))
        self.assertEqual(self.task("reset", "change-review"), (0, "", ""))

    def test_same_prompt_and_transcript_cursor_do_not_reset_counters(self):
        self.budget_violation(subagent_type="change-review", calls_so_far={})
        transcript = Path(self.scratch.name) / "session.jsonl"
        transcript.write_text(
            '{"type":"message","id":"cursor-1","message":{"role":"user"}}\n',
            encoding="utf-8",
        )
        self.assertEqual(
            self.begin_request("idempotent", "Review the diff.", str(transcript)),
            (0, "", ""),
        )
        for _ in range(REVIEWER_CAPS["change-review"]):
            self.assertEqual(self.task("idempotent", "change-review"), (0, "", ""))

        self.assertEqual(
            self.begin_request("idempotent", "Review the diff.", str(transcript)),
            (0, "", ""),
        )
        self.assertIsNotNone(
            self.denial_reason(self.task("idempotent", "change-review")[1])
        )

    def test_non_reviewers_neither_deny_nor_consume_reviewer_budget(self):
        self.require_budget_violation()
        for subagent_type in (
            "implementer",
            "worker",
            "explorer",
            "debugger",
            "security-helper",
        ):
            with self.subTest(subagent_type=subagent_type):
                self.assertIsNone(
                    self.budget_violation(
                        subagent_type=subagent_type,
                        calls_so_far={subagent_type: 20},
                    )
                )
        self.assertEqual(
            self.begin_request("non-reviewer", "Implement the requested change."),
            (0, "", ""),
        )
        for _ in range(20):
            self.assertEqual(
                self.task("non-reviewer", "implementer"),
                (0, "", ""),
            )
        for _ in range(REVIEWER_CAPS["change-review"]):
            self.assertEqual(
                self.task("non-reviewer", "change-review"),
                (0, "", ""),
            )
        self.assertIsNotNone(
            self.denial_reason(self.task("non-reviewer", "change-review")[1])
        )

    def test_descriptions_do_not_change_count_only_decisions(self):
        """Descriptions are untrusted labels, not budget inputs."""
        self.budget_violation(subagent_type="change-review", calls_so_far={})
        descriptions = (
            "",
            "Review the diff without a label.",
            "[review:standard] Review the diff.",
        )
        outcomes = []
        for index, description in enumerate(descriptions):
            session_id = f"description-{index}"
            self.assertEqual(
                self.begin_request(session_id, "Review this change."),
                (0, "", ""),
            )
            calls = [
                self.task(session_id, "change-review", description)[1]
                for _ in range(REVIEWER_CAPS["change-review"] + 1)
            ]
            outcomes.append(tuple(bool(output) for output in calls))
        self.assertEqual(outcomes, [(False,) * 6 + (True,)] * len(descriptions))

    def test_unreadable_state_fails_open_and_logs_the_decision(self):
        """A cost bound must not block a legitimate review when state is unavailable."""
        self.budget_violation(subagent_type="change-review", calls_so_far={})
        self.assertEqual(
            self.task("missing-state", "change-review"),
            (0, "", ""),
        )
        self.assertEqual(self.begin_request("invalid-state", "Review the diff."), (0, "", ""))
        state_path = review_budget.review_state_path(self.state_dir, "invalid-state")
        state_path.write_text("{not-json", encoding="utf-8")
        self.assertEqual(
            self.task("invalid-state", "change-review"),
            (0, "", ""),
        )

        decisions = self.logged_decisions()
        self.assertEqual(
            [(decision["hook"], decision["session_id"]) for decision in decisions],
            [
                ("review_budget", "missing-state"),
                ("review_budget", "invalid-state"),
            ],
        )

    def test_malformed_input_exits_without_a_denial(self):
        self.budget_violation(subagent_type="change-review", calls_so_far={})
        malformed_inputs = (
            "not-json",
            {
                "hook_event_name": "PreToolUse",
                "session_id": "missing-tool-input",
                "tool_name": "Task",
            },
            {
                "hook_event_name": "PreToolUse",
                "session_id": "missing-subagent-type",
                "tool_name": "Task",
                "tool_input": {"description": "Review the diff."},
            },
            {
                "hook_event_name": "PreToolUse",
                "session_id": "non-task",
                "tool_name": "Execute",
                "tool_input": {"subagent_type": "change-review"},
            },
        )
        for payload in malformed_inputs:
            with self.subTest(payload=payload):
                self.assertEqual(self.run_hook(payload), (0, "", ""))

    def test_concurrent_task_increments_preserve_both_calls(self):
        self.budget_violation(subagent_type="change-review", calls_so_far={})
        session_id = "concurrent"
        self.assertEqual(self.begin_request(session_id, "Review the diff."), (0, "", ""))
        for _ in range(4):
            self.assertEqual(self.task(session_id, "change-review"), (0, "", ""))

        payload = json.dumps(
            {
                "hook_event_name": "PreToolUse",
                "session_id": session_id,
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": "change-review",
                    "description": "",
                },
            }
        )
        command = [sys.executable, str(HOOKS / "review_budget.py")]
        processes = [
            subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(2)
        ]
        results = [process.communicate(payload) for process in processes]
        self.assertEqual(
            [
                (process.returncode, stdout, stderr)
                for process, (stdout, stderr) in zip(processes, results)
            ],
            [(0, "", ""), (0, "", "")],
        )
        self.assertIsNotNone(
            self.denial_reason(self.task(session_id, "change-review")[1])
        )


if __name__ == "__main__":
    unittest.main()
