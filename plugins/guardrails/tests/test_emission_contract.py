"""Emission contract for every guardrail hook.

A hook writes to stdout only to change agent behavior: an intent injection,
a permission deny, a Task-input normalization, or a stop-gate decision. Every
silent path is unchanged, every decision is logged to the guardrails decision
log, and accidental prints are caught by a static census of print sites.
"""

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

import delivery_ledger  # noqa: E402
import intent_router  # noqa: E402
import pre_push_policy  # noqa: E402
import review_budget  # noqa: E402
import stop_delivery_gate  # noqa: E402


class EmissionContractTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        self.log_dir = root / "log"
        env = {
            "DROID_REVIEW_BUDGET_DIR": str(root / "budget"),
            "DROID_DELIVERY_LEDGER_DIR": str(root / "ledger"),
            "DROID_INTENT_STATE_DIR": str(root / "intent"),
            "DROID_GUARDRAILS_LOG_DIR": str(self.log_dir),
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, module, payload):
        stdout = io.StringIO()
        stderr = io.StringIO()
        original = (sys.stdin, sys.stdout, sys.stderr)
        try:
            sys.stdin = io.StringIO(
                payload if isinstance(payload, str) else json.dumps(payload)
            )
            sys.stdout = stdout
            sys.stderr = stderr
            code = module.main()
        finally:
            sys.stdin, sys.stdout, sys.stderr = original
        return code, stdout.getvalue(), stderr.getvalue()

    def logged_decisions(self):
        log_file = self.log_dir / "decisions.jsonl"
        if not log_file.exists():
            return []
        return [
            json.loads(line)
            for line in log_file.read_text(encoding="utf-8").splitlines()
        ]

    def make_git_repo(self):
        repo = tempfile.mkdtemp(dir=self.scratch.name)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        return repo

    def test_every_hook_ignores_malformed_stdin_silently(self):
        for module in (
            intent_router,
            review_budget,
            delivery_ledger,
            pre_push_policy,
            stop_delivery_gate,
        ):
            with self.subTest(module=module.__name__):
                code, out, err = self.run_main(module, "not json")
                self.assertEqual((code, out, err), (0, "", ""))

    def test_intent_router_is_silent_for_informational_prompts(self):
        code, out, err = self.run_main(
            intent_router,
            {"prompt": "What does git status show?", "session_id": "emit-1"},
        )
        self.assertEqual((code, out, err), (0, "", ""))
        state = intent_router.load_request_intent(
            intent_router.intent_state_directory(), "emit-1"
        )
        self.assertEqual(state["routes"], [])
        self.assertFalse(state["merge_or_approve"])
        self.assertEqual(self.logged_decisions(), [])

    def test_intent_router_is_silent_for_ordinary_work_prompts(self):
        code, out, err = self.run_main(
            intent_router,
            {"prompt": "Fix the typo in the README.", "session_id": "emit-2"},
        )
        self.assertEqual((code, out, err), (0, "", ""))

    def test_intent_router_injects_and_logs_for_workflow_prompts(self):
        code, out, err = self.run_main(
            intent_router,
            {"prompt": "Review PR 123.", "session_id": "emit-3"},
        )
        self.assertEqual((code, err), (0, ""))
        response = json.loads(out)
        self.assertIn(
            "`review-pr`",
            response["hookSpecificOutput"]["additionalContext"],
        )
        self.assertTrue(response["suppressOutput"])
        decisions = self.logged_decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["hook"], "intent_router")
        self.assertEqual(decisions[0]["decision"], "inject")

    def test_intent_router_suppresses_injection_for_explicit_invocations(self):
        code, out, err = self.run_main(
            intent_router,
            {"prompt": "use review-pr on this branch", "session_id": "emit-4"},
        )
        self.assertEqual((code, out, err), (0, "", ""))
        state = intent_router.load_request_intent(
            intent_router.intent_state_directory(), "emit-4"
        )
        self.assertEqual(state["routes"], ["review-pr"])

    def test_intent_router_records_merge_authority_for_the_stop_gate(self):
        self.run_main(
            intent_router,
            {"prompt": "Approve and merge PR 42.", "session_id": "emit-5"},
        )
        state = intent_router.load_request_intent(
            intent_router.intent_state_directory(), "emit-5"
        )
        self.assertTrue(state["merge_or_approve"])

    def test_review_budget_is_silent_on_prompt_and_non_review_tasks(self):
        payloads = (
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "emit-6",
                "prompt": "Review and fix the change.",
            },
            {
                "hook_event_name": "PreToolUse",
                "session_id": "emit-6",
                "tool_name": "Execute",
                "tool_input": {"command": "ls"},
            },
            {
                "hook_event_name": "PreToolUse",
                "session_id": "emit-6",
                "tool_name": "Task",
                "tool_input": {"subagent_type": "worker", "description": "explore"},
            },
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                code, out, err = self.run_main(review_budget, payload)
                self.assertEqual((code, out, err), (0, "", ""))
        self.assertEqual(self.logged_decisions(), [])

    def test_review_budget_denies_are_emitted_and_logged(self):
        self.run_main(
            review_budget,
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "emit-7",
                "prompt": "Review the change.",
            },
        )
        code, out, err = self.run_main(
            review_budget,
            {
                "hook_event_name": "PreToolUse",
                "session_id": "emit-7",
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": "change-review",
                    "description": "Review without a stage tag",
                },
            },
        )
        self.assertEqual((code, err), (0, ""))
        response = json.loads(out)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"], "deny"
        )
        decisions = self.logged_decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["hook"], "review_budget")
        self.assertEqual(decisions[0]["decision"], "deny")

    def test_review_budget_normalization_is_emitted_and_logged(self):
        self.run_main(
            review_budget,
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "emit-7-normalize",
                "prompt": "Review the change.",
            },
        )
        code, out, err = self.run_main(
            review_budget,
            {
                "hook_event_name": "PreToolUse",
                "session_id": "emit-7-normalize",
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": "security",
                    "description": (
                        "[review:standard:security] Check config inputs"
                    ),
                },
            },
        )
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            json.loads(out),
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": {
                        "description": (
                            "[review:standard:security] [security:selected] "
                            "Check config inputs"
                        )
                    },
                },
                "suppressOutput": True,
            },
        )
        decisions = self.logged_decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["hook"], "review_budget")
        self.assertEqual(decisions[0]["decision"], "normalize")

    def test_delivery_ledger_is_silent_on_session_start_and_non_push_commands(self):
        repo = self.make_git_repo()
        payloads = (
            {
                "hook_event_name": "SessionStart",
                "session_id": "emit-8",
                "cwd": repo,
            },
            {
                "hook_event_name": "PostToolUse",
                "session_id": "emit-8",
                "cwd": repo,
                "tool_name": "Execute",
                "tool_input": {"command": "git status"},
            },
            {
                "hook_event_name": "PostToolUse",
                "session_id": "emit-8",
                "cwd": repo,
                "tool_name": "Read",
                "tool_input": {},
            },
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                code, out, err = self.run_main(delivery_ledger, payload)
                self.assertEqual((code, out, err), (0, "", ""))

    def test_pre_push_policy_is_silent_for_non_push_commands(self):
        payloads = (
            {"tool_name": "Read", "tool_input": {}},
            {"tool_name": "Execute", "tool_input": {"command": "git status"}},
            {"tool_name": "Execute", "tool_input": {"command": "echo 'git push'"}},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                code, out, err = self.run_main(pre_push_policy, payload)
                self.assertEqual((code, out, err), (0, "", ""))

    def test_pre_push_policy_denies_on_stderr_and_logs(self):
        repo = self.make_git_repo()
        code, out, err = self.run_main(
            pre_push_policy,
            {
                "session_id": "emit-9",
                "cwd": repo,
                "tool_name": "Execute",
                "tool_input": {"command": "git push --force origin feature"},
            },
        )
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("force-with-lease", err)
        decisions = self.logged_decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["hook"], "pre_push_policy")

    def test_stop_gate_is_silent_when_no_push_was_recorded(self):
        repo = self.make_git_repo()
        code, out, err = self.run_main(
            stop_delivery_gate,
            {"session_id": "emit-10", "cwd": repo},
        )
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertEqual(self.logged_decisions(), [])

    def test_hook_print_sites_are_exactly_the_decision_paths(self):
        expected_print_sites = {
            "intent_router.py": 1,
            "review_budget.py": 1,
            "delivery_ledger.py": 0,
            "pre_push_policy.py": 1,
            "stop_delivery_gate.py": 1,
            "guardrails_log.py": 0,
        }
        for name, expected in expected_print_sites.items():
            with self.subTest(hook=name):
                source = (HOOKS / name).read_text(encoding="utf-8")
                self.assertEqual(
                    source.count("print("),
                    expected,
                    f"{name} gained or lost a print site; stdout is only for "
                    "decisions, and every decision path must be tested.",
                )


if __name__ == "__main__":
    unittest.main()
