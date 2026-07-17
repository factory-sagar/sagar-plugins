import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from delivery_ledger import (  # noqa: E402
    clear_push_state,
    is_push_command,
    load_state,
    parse_push_command,
    record_push,
    record_session_baseline,
)
from intent_router import route_intent  # noqa: E402
from pre_push_policy import push_policy_violation  # noqa: E402
from review_budget import (  # noqa: E402
    begin_request,
    load_review_state,
    main,
    review_task_violation,
    reserve_review_call,
    review_state_path,
)
from stop_delivery_gate import (  # noqa: E402
    DeliverySnapshot,
    body_is_fresh,
    classify_worktree,
    delivery_gate_output,
    pending_obligations,
)


class ReviewBudgetTests(unittest.TestCase):
    def reserve_review_calls(self, state_dir, descriptions):
        transcript = state_dir / "session.jsonl"
        transcript.write_text(
            '{"type":"message","id":"message-1","message":{"role":"user"}}\n',
            encoding="utf-8",
        )
        begin_request(
            state_dir=state_dir,
            session_id="session-1",
            prompt="Review and fix the change.",
            transcript_path=str(transcript),
        )
        return [
            reserve_review_call(
                state_dir=state_dir,
                session_id="session-1",
                description=description,
            )
            for description in descriptions
        ]

    def run_hook(self, payload, state_dir):
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        original_state_dir = os.environ.get("DROID_REVIEW_BUDGET_DIR")
        output = io.StringIO()
        try:
            os.environ["DROID_REVIEW_BUDGET_DIR"] = str(state_dir)
            sys.stdin = io.StringIO(json.dumps(payload))
            sys.stdout = output
            self.assertEqual(main(), 0)
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout
            if original_state_dir is None:
                os.environ.pop("DROID_REVIEW_BUDGET_DIR", None)
            else:
                os.environ["DROID_REVIEW_BUDGET_DIR"] = original_state_dir
        return output.getvalue()

    def test_requires_a_valid_review_stage_tag(self):
        self.assertIn(
            "stage tag",
            review_task_violation("Review final branch", state={"final_slots": []}),
        )
        self.assertIsNone(
            review_task_violation(
                "[review:standard] Review change scope",
                state={"final_slots": []},
            )
        )
        self.assertIsNone(
            review_task_violation(
                "[review:deep:primary] Review broad change",
                state={"final_slots": []},
            )
        )

    def test_allows_exactly_two_complete_final_head_rounds(self):
        state = {"final_slots": []}
        for description in (
            "[review:final:1:primary] Review frozen head",
            "[review:final:1:challenge] Challenge frozen head",
            "[review:final:2:primary] Re-review corrected head",
            "[review:final:2:challenge] Challenge corrected head",
        ):
            self.assertIsNone(review_task_violation(description, state=state))
            state["final_slots"].append(description.split("]", 1)[0] + "]")

        self.assertIn(
            "at most two",
            review_task_violation(
                "[review:final:3:primary] Review another corrected head",
                state=state,
            ),
        )

    def test_rejects_duplicate_and_out_of_order_final_head_calls(self):
        state = {"final_slots": ["[review:final:1:primary]"]}
        self.assertIn(
            "already used",
            review_task_violation(
                "[review:final:1:primary] Retry frozen head",
                state=state,
            ),
        )
        self.assertIn(
            "Complete round 1",
            review_task_violation(
                "[review:final:2:primary] Review corrected head",
                state=state,
            ),
        )

    def test_rejects_final_head_work_disguised_as_another_stage(self):
        for description in (
            "[review:standard] Review the frozen final head",
            "[review:standard] Review final Reviews diff",
            "[review:deep:primary] Recheck hardened final branch",
        ):
            with self.subTest(description=description):
                self.assertIn(
                    "final-head tag",
                    review_task_violation(
                        description,
                        state={"final_slots": []},
                    ),
                )
        self.assertIn(
            "final-head tag",
            review_task_violation(
                "[review:standard] Review change scope",
                state={"final_slots": []},
                prompt="Review the frozen committed head before this push.",
            ),
        )

    def test_standard_retry_is_allowed_once_after_standard(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:standard] Review changed files",
                    "[review:standard:retry] Complete missing evidence",
                    "[review:standard:retry] Retry the retry",
                ),
            )

        self.assertIsNone(results[0])
        self.assertIsNone(results[1])
        self.assertIn("already used", results[2])

    def test_standard_family_allows_security_once_and_rejects_other_families(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:standard] Review changed files",
                    "[review:standard:security] Inspect changed security paths",
                    "[review:standard:retry] Complete missing evidence",
                    "[review:standard:security] Repeat security review",
                    "[review:deep:primary] Start a deep review",
                    "[review:final:1:primary] Start a final review",
                ),
            )

        for result in results[:3]:
            self.assertIsNone(result)
        self.assertIn("already used", results[3])
        for result in results[4:]:
            self.assertIn("already reserved for the standard family", result)

    def test_hook_reserves_tagged_standard_security_but_allows_untagged_security(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            user_prompt = {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session-1",
                "prompt": "Review and fix the change.",
            }
            tagged_security = {
                "hook_event_name": "PreToolUse",
                "session_id": "session-1",
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": "security",
                    "description": (
                        "[review:standard:security] Inspect changed security paths"
                    ),
                },
            }
            untagged_security = {
                "hook_event_name": "PreToolUse",
                "session_id": "session-1",
                "tool_name": "Task",
                "tool_input": {
                    "subagent_type": "security",
                    "description": "Inspect changed security paths",
                },
            }

            self.run_hook(user_prompt, state_dir)
            self.assertEqual(self.run_hook(tagged_security, state_dir), "")
            state = load_review_state(review_state_path(state_dir, "session-1"))
            self.assertEqual(
                state["review_slots"],
                ["[review:standard:security]"],
                "A tagged security Task must consume the standard security budget.",
            )
            duplicate_output = self.run_hook(tagged_security, state_dir)
            self.assertNotEqual(
                duplicate_output,
                "",
                "A duplicate tagged standard security Task must receive a deny response.",
            )
            duplicate = json.loads(duplicate_output)
            self.assertEqual(
                duplicate["hookSpecificOutput"]["permissionDecision"],
                "deny",
            )
            self.assertIn(
                "already used",
                duplicate["hookSpecificOutput"]["permissionDecisionReason"],
            )
            self.assertEqual(self.run_hook(untagged_security, state_dir), "")

    def test_standard_family_rejects_duplicates_and_other_review_families(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:standard] Review changed files",
                    "[review:standard] Repeat the standard review",
                    "[review:deep:primary] Start a deep review",
                    "[review:final:1:primary] Start a final review",
                ),
            )

        self.assertIsNone(results[0])
        for result in results[1:]:
            self.assertIsNotNone(result)

    def test_deep_family_allows_each_primary_challenge_and_security_stage_once(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:deep:primary] Review broad changes",
                    "[review:deep:challenge] Challenge broad changes",
                    "[review:deep:security] Inspect security-sensitive paths",
                    "[review:deep:primary] Repeat primary review",
                    "[review:standard] Switch to a standard review",
                    "[review:final:1:primary] Switch to a final review",
                ),
            )

        for result in results[:3]:
            self.assertIsNone(result)
        for result in results[3:]:
            self.assertIsNotNone(result)

    def test_final_round_accepts_security_once_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:final:1:primary] Review frozen head",
                    "[review:final:1:challenge] Challenge frozen head",
                    "[review:final:1:security] Inspect final security changes",
                    "[review:final:1:security] Repeat final security review",
                ),
            )

        for result in results[:3]:
            self.assertIsNone(result)
        self.assertIn("already used", results[3])

    def test_final_round_two_requires_complete_primary_and_challenge_round_one(self):
        with tempfile.TemporaryDirectory() as directory:
            out_of_order = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:final:1:primary] Review frozen head",
                    "[review:final:1:security] Inspect frozen security changes",
                    "[review:final:2:security] Review correction security",
                ),
            )

        self.assertIsNone(out_of_order[0])
        self.assertIsNone(out_of_order[1])
        self.assertIn("Complete round 1", out_of_order[2])

    def test_final_round_two_allows_security_after_completed_round_one(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:final:1:primary] Review frozen head",
                    "[review:final:1:challenge] Challenge frozen head",
                    "[review:final:2:security] Review correction security",
                ),
            )

        for result in results:
            self.assertIsNone(result)

    def test_completed_final_round_two_rejects_every_new_review_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:final:1:primary] Review frozen head",
                    "[review:final:1:challenge] Challenge frozen head",
                    "[review:final:2:primary] Review corrected head",
                    "[review:final:2:challenge] Challenge corrected head",
                    "[review:standard] Start another review",
                    "[review:deep:primary] Start another deep review",
                    "[review:deep:challenge] Challenge another deep review",
                    "[review:deep:security] Start another security review",
                    "[review:final:2:security] Inspect final security changes",
                ),
            )

        for result in results[:4]:
            self.assertIsNone(result)
        for result in results[4:]:
            self.assertIsNotNone(result)
            if result is not None:
                self.assertIn("at most two", result)

    def test_duplicate_prompt_delivery_preserves_budget_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            transcript = state_dir / "session.jsonl"
            transcript.write_text(
                '{"type":"message","id":"message-1","message":{"role":"user"}}\n',
                encoding="utf-8",
            )
            begin_request(
                state_dir=state_dir,
                session_id="session-1",
                prompt="Review and fix the change.",
                transcript_path=str(transcript),
            )
            self.assertIsNone(
                reserve_review_call(
                    state_dir=state_dir,
                    session_id="session-1",
                    description="[review:final:1:primary] Review frozen head",
                )
            )

            begin_request(
                state_dir=state_dir,
                session_id="session-1",
                prompt="Review and fix the change.",
                transcript_path=str(transcript),
            )
            state = load_review_state(
                review_state_path(state_dir, "session-1")
            )
            self.assertEqual(
                state["final_slots"],
                ["[review:final:1:primary]"],
            )

            with transcript.open("a", encoding="utf-8") as stream:
                stream.write(
                    '{"type":"message","id":"hook-1","message":'
                    '{"role":"user","hookEventName":"UserPromptSubmit"}}\n'
                )
            begin_request(
                state_dir=state_dir,
                session_id="session-1",
                prompt="Review and fix the change.",
                transcript_path=str(transcript),
            )
            state = load_review_state(
                review_state_path(state_dir, "session-1")
            )
            self.assertEqual(
                state["final_slots"],
                ["[review:final:1:primary]"],
            )

            with transcript.open("a", encoding="utf-8") as stream:
                stream.write(
                    '{"type":"message","id":"message-2","message":{"role":"user"}}\n'
                )
            begin_request(
                state_dir=state_dir,
                session_id="session-1",
                prompt="Review and fix the change.",
                transcript_path=str(transcript),
            )
            state = load_review_state(
                review_state_path(state_dir, "session-1")
            )
            self.assertEqual(state["final_slots"], [])


class DeliveryLedgerTests(unittest.TestCase):
    def test_detects_real_push_commands_without_matching_prose(self):
        self.assertTrue(is_push_command("git push -u origin HEAD"))
        self.assertTrue(is_push_command("git status && git push origin feature"))
        self.assertTrue(is_push_command("cd /repo && git -C /repo push origin branch"))
        self.assertFalse(is_push_command("git checkout push"))
        self.assertFalse(is_push_command('echo "run git push later"'))
        self.assertFalse(is_push_command("printf 'git push'"))

    def test_resolves_command_local_repository(self):
        self.assertEqual(
            parse_push_command("git -C /repo push origin feature", "/fallback"),
            "/repo",
        )

    def test_records_push_state_by_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = record_push(
                state_dir=Path(directory),
                session_id="session-1",
                repo_root="/repo",
                branch="feature",
                pushed_head="abc123",
                pr_number=42,
            )

            self.assertEqual(
                load_state(path),
                {
                    "version": 2,
                    "session_id": "session-1",
                    "repo_root": "/repo",
                    "branch": "feature",
                    "pushed_head": "abc123",
                    "pr_number": 42,
                    "baseline_untracked": [],
                },
            )

    def test_push_preserves_session_start_untracked_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            record_session_baseline(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                baseline_untracked=["plans/README.md"],
            )
            path = record_push(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                branch="feature",
                pushed_head="abc123",
                pr_number=42,
                baseline_untracked=["plans/README.md", "src/forgotten.ts"],
            )

            self.assertEqual(
                load_state(path)["baseline_untracked"],
                ["plans/README.md"],
            )

    def test_repeated_session_start_preserves_first_baseline_and_push(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            record_session_baseline(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                baseline_untracked=["owned-before-start.txt"],
            )
            path = record_push(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                branch="feature",
                pushed_head="abc123",
                pr_number=42,
            )

            repeated = record_session_baseline(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                baseline_untracked=[
                    "owned-before-start.txt",
                    "created-during-session.txt",
                ],
            )

            self.assertEqual(repeated, path)
            self.assertEqual(
                load_state(path),
                {
                    "version": 2,
                    "session_id": "session-1",
                    "repo_root": "/repo",
                    "branch": "feature",
                    "pushed_head": "abc123",
                    "pr_number": 42,
                    "baseline_untracked": ["owned-before-start.txt"],
                },
            )

    def test_baselines_are_scoped_by_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            first = record_session_baseline(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo-a",
                baseline_untracked=["owned.txt"],
            )
            second = record_push(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo-b",
                branch="feature",
                pushed_head="abc123",
                pr_number=42,
                baseline_untracked=["new.txt"],
            )

            self.assertNotEqual(first, second)
            self.assertEqual(load_state(second)["baseline_untracked"], ["new.txt"])

    def test_clearing_push_preserves_session_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            path = record_push(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                branch="feature",
                pushed_head="abc123",
                pr_number=42,
                baseline_untracked=["owned.txt"],
            )
            state = load_state(path)
            clear_push_state(path, state)

            cleared = load_state(path)
            self.assertIsNone(cleared["pushed_head"])
            self.assertEqual(cleared["baseline_untracked"], ["owned.txt"])

    def test_clear_does_not_erase_a_newer_recorded_push(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            path = record_push(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                branch="feature",
                pushed_head="old-head",
                pr_number=42,
            )
            stale = load_state(path)
            record_push(
                state_dir=state_dir,
                session_id="session-1",
                repo_root="/repo",
                branch="feature",
                pushed_head="new-head",
                pr_number=42,
            )

            clear_push_state(path, stale)

            self.assertEqual(load_state(path)["pushed_head"], "new-head")


class PrePushPolicyTests(unittest.TestCase):
    def test_blocks_default_branch_force_and_bypass_pushes(self):
        self.assertIn(
            "default branch",
            push_policy_violation("git push origin main", branch="main", default_branch="main"),
        )
        self.assertIn(
            "force-with-lease",
            push_policy_violation(
                "git push --force origin feature",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIn(
            "force-with-lease",
            push_policy_violation(
                "git push -f origin feature",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIn(
            "default branch",
            push_policy_violation(
                "git push origin HEAD:main",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIn(
            "verification",
            push_policy_violation(
                "git push --no-verify origin feature",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIn(
            "pipefail",
            push_policy_violation(
                "git push origin feature | tail -5",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIn(
            "pipefail",
            push_policy_violation(
                "git push origin feature 2>&1 | tail -20",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIn(
            "pipefail",
            push_policy_violation(
                "git push origin feature | tee /tmp/push.log",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIn(
            "pipefail",
            push_policy_violation(
                "git push origin feature | tail -5; echo pipefail",
                branch="feature",
                default_branch="main",
            ),
        )

    def test_allows_feature_push_and_force_with_lease(self):
        self.assertIsNone(
            push_policy_violation(
                "git push origin feature",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIsNone(
            push_policy_violation(
                "git push --force-with-lease origin feature",
                branch="feature",
                default_branch="main",
            ),
        )
        self.assertIsNone(
            push_policy_violation(
                "set -o pipefail; git push origin feature | tail -5",
                branch="feature",
                default_branch="main",
            ),
        )


class IntentRouterTests(unittest.TestCase):
    def test_routes_short_workflow_prompts(self):
        self.assertEqual(route_intent("Review PR 123."), ["review-pr"])
        self.assertEqual(route_intent("Address PR 42."), ["review-pr"])
        self.assertEqual(route_intent("Approve PR 42."), ["review-pr"])
        self.assertEqual(route_intent("Approve this PR."), ["review-pr"])
        self.assertEqual(route_intent("Approve this pull request."), ["review-pr"])
        self.assertEqual(route_intent("Can you approve PR 42?"), ["review-pr"])
        self.assertEqual(
            route_intent("Please approve the pull request 42."),
            ["review-pr"],
        )
        self.assertEqual(
            route_intent(
                "Review the staged change and report anything that should block merge."
            ),
            ["review-pr"],
        )
        self.assertEqual(route_intent("Plan adding audit-log exports."), ["spec"])
        self.assertEqual(route_intent("Can you scope out a better architecture?"), ["spec"])
        self.assertEqual(route_intent("Implement unit U3 and verify it."), ["implement"])
        self.assertEqual(route_intent("Can you build the approved unit now?"), ["implement"])
        self.assertEqual(route_intent("Ship it."), ["ship"])
        self.assertEqual(route_intent("Can we push everything and monitor CI?"), ["ship"])
        self.assertEqual(
            route_intent("Implement the approved unit and push it."),
            ["implement", "ship"],
        )
        self.assertEqual(
            route_intent("Review and merge PR 123."),
            ["review-pr", "ship"],
        )
        self.assertEqual(
            route_intent("Push it, then approve PR 42."),
            ["review-pr", "ship"],
        )
        self.assertEqual(
            route_intent("Approve and merge PR 42."),
            ["review-pr", "ship"],
        )
        self.assertEqual(
            route_intent("Approve and land this PR."),
            ["review-pr", "ship"],
        )
        self.assertEqual(
            route_intent(
                "Implement the approved program in plans/README.md. "
                "Execute every plan in dependency order and run review-pr at the end. "
                "Do not push or merge."
            ),
            ["implement", "review-pr"],
        )
        self.assertEqual(
            route_intent("Review this change, then apply every valid fix."),
            ["review-pr"],
        )
        self.assertEqual(
            route_intent("Fix every review comment on PR 42."),
            ["review-pr"],
        )
        self.assertEqual(route_intent("Fix review comments on PR 42."), ["review-pr"])
        self.assertEqual(
            route_intent("Push this branch but do not merge it."),
            ["ship"],
        )

    def test_avoids_routing_informational_questions(self):
        self.assertIsNone(route_intent("What does git status show?"))
        self.assertIsNone(route_intent("Explain what a pull request review is."))
        self.assertIsNone(route_intent("Do not push this branch."))
        self.assertIsNone(route_intent("Do not review this PR."))
        self.assertIsNone(route_intent("Do not plan this change."))
        self.assertIsNone(route_intent("Execute the test suite."))
        self.assertIsNone(route_intent("Do not push or merge this branch."))
        self.assertIsNone(route_intent("Should I approve PR 42?"))
        self.assertIsNone(route_intent("Should we approve pull request 42?"))
        self.assertIsNone(route_intent("Would you approve PR 42?"))
        self.assertIsNone(route_intent("Should we approve and merge PR 42?"))
        self.assertEqual(route_intent("Approve the plan for PR 42."), ["spec"])
        self.assertEqual(route_intent("Approve and merge the plan for PR 42."), ["spec"])
        self.assertIsNone(route_intent("Approve this change on PR 42."))
        self.assertIsNone(route_intent("Fix every review note in the proposal."))


class StopGateTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "pushed_head": "abc123",
            "pr_number": 42,
            "baseline_untracked": ["plans/README.md"],
        }

    def test_green_current_pr_is_complete(self):
        snapshot = DeliverySnapshot(
            local_head="abc123",
            remote_head="abc123",
            pr_head="abc123",
            dirty_tracked=False,
            unexpected_untracked=(),
            checks_complete=True,
            checks_green=True,
            unresolved_threads=0,
            body_fresh=True,
        )
        self.assertEqual(pending_obligations(self.state, snapshot), [])

    def test_preexisting_untracked_files_do_not_block_delivery(self):
        dirty_tracked, unexpected = classify_worktree(
            "?? plans/README.md\n",
            ["plans/README.md"],
        )
        self.assertFalse(dirty_tracked)
        self.assertEqual(unexpected, ())

    def test_new_untracked_files_block_delivery(self):
        dirty_tracked, unexpected = classify_worktree(
            "?? plans/README.md\n?? src/new.ts\n",
            ["plans/README.md"],
        )
        self.assertFalse(dirty_tracked)
        self.assertEqual(unexpected, ("src/new.ts",))

    def test_body_freshness_marker_is_generic_and_head_specific(self):
        self.assertTrue(
            body_is_fresh("Body\n<!-- pr-body-head=abc123 -->", "abc123")
        )
        self.assertFalse(
            body_is_fresh("Body\n<!-- pr-body-head=old -->", "abc123")
        )

    def test_reports_every_unfinished_delivery_obligation(self):
        snapshot = DeliverySnapshot(
            local_head="def456",
            remote_head="abc123",
            pr_head="abc123",
            dirty_tracked=True,
            unexpected_untracked=("src/new.ts",),
            checks_complete=False,
            checks_green=False,
            unresolved_threads=2,
            body_fresh=False,
        )
        obligations = pending_obligations(self.state, snapshot)

        self.assertEqual(len(obligations), 7)
        self.assertTrue(any("worktree" in item for item in obligations))
        self.assertTrue(any("unpushed" in item for item in obligations))
        self.assertTrue(any("CI" in item for item in obligations))
        self.assertTrue(any("threads" in item for item in obligations))
        self.assertTrue(any("body" in item for item in obligations))

    def test_unknown_live_state_blocks_instead_of_claiming_green(self):
        snapshot = DeliverySnapshot(
            local_head="abc123",
            remote_head=None,
            pr_head=None,
            dirty_tracked=None,
            unexpected_untracked=None,
            checks_complete=None,
            checks_green=None,
            unresolved_threads=None,
            body_fresh=None,
        )
        obligations = pending_obligations(self.state, snapshot)

        self.assertGreaterEqual(len(obligations), 4)
        self.assertTrue(any("could not verify" in item for item in obligations))

    def test_pending_ci_block_requires_one_foreground_watch(self):
        snapshot = DeliverySnapshot(
            local_head="abc123",
            remote_head="abc123",
            pr_head="abc123",
            dirty_tracked=False,
            unexpected_untracked=(),
            checks_complete=False,
            checks_green=False,
            unresolved_threads=0,
            body_fresh=True,
        )

        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=False,
        )

        self.assertEqual(output["decision"], "block")
        self.assertIn("Do not retry Stop", output["reason"])
        self.assertIn("gh pr checks 42 --watch --interval 10", output["reason"])

    def test_pending_ci_reentry_stops_without_another_continuation(self):
        snapshot = DeliverySnapshot(
            local_head="abc123",
            remote_head="abc123",
            pr_head="abc123",
            dirty_tracked=False,
            unexpected_untracked=(),
            checks_complete=False,
            checks_green=False,
            unresolved_threads=0,
            body_fresh=True,
        )

        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=True,
        )

        self.assertFalse(output["continue"])
        self.assertIn("not accepted as complete", output["stopReason"])

    def test_actionable_reentry_still_blocks(self):
        snapshot = DeliverySnapshot(
            local_head="abc123",
            remote_head="abc123",
            pr_head="abc123",
            dirty_tracked=True,
            unexpected_untracked=(),
            checks_complete=True,
            checks_green=True,
            unresolved_threads=0,
            body_fresh=True,
        )

        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=True,
        )

        self.assertEqual(output["decision"], "block")
        self.assertIn("uncommitted tracked changes", output["reason"])


class WorkflowPolicyContractTests(unittest.TestCase):
    REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

    def policy_text(self, relative_path):
        return (self.REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")

    def assert_policy_matches(self, relative_path, pattern, behavior):
        self.assertRegex(
            self.policy_text(relative_path),
            pattern,
            msg=f"{relative_path} must state that {behavior}.",
        )

    def test_implement_requires_targeted_validation_per_independently_changed_unit(self):
        self.assert_policy_matches(
            "plugins/build/skills/implement/SKILL.md",
            r"(?is)each independently changed unit.*targeted validator",
            "each independently changed unit requires a targeted validator",
        )

    def test_implement_records_reusable_validation_evidence(self):
        self.assert_policy_matches(
            "plugins/build/skills/implement/SKILL.md",
            r"(?is)record.*reusable validation evidence",
            "unit validation evidence is recorded for later reuse",
        )

    def test_implement_defers_the_canonical_gate_until_the_program_head(self):
        self.assert_policy_matches(
            "plugins/build/skills/implement/SKILL.md",
            r"(?is)canonical (?:gate|validation).*program head.*not.*per.*unit",
            "the canonical gate runs once at the program head rather than per unit",
        )

    def test_verification_loop_reuses_valid_validation_evidence(self):
        self.assert_policy_matches(
            "plugins/practices/skills/verification-loop/SKILL.md",
            r"(?is)reuse.*valid(?:ated)? evidence",
            "valid prior validation evidence is reused",
        )

    def test_verification_loop_runs_one_integration_gate_for_the_program_head(self):
        self.assert_policy_matches(
            "plugins/practices/skills/verification-loop/SKILL.md",
            r"(?is)one integration gate.*program head",
            "one integration gate runs for the program head",
        )

    def test_verification_loop_hands_review_ownership_to_review_pr(self):
        self.assert_policy_matches(
            "plugins/practices/skills/verification-loop/SKILL.md",
            r"(?is)hand.*review ownership.*review-pr",
            "review ownership is handed to review-pr",
        )

    def test_verification_loop_does_not_launch_reviewers_directly(self):
        policy = self.policy_text(
            "plugins/practices/skills/verification-loop/SKILL.md"
        )
        self.assertNotRegex(
            policy,
            r"(?is)delegate to [`*]?(?:change-review|security)[`*]?",
            msg=(
                "verification-loop must not launch change-review or security directly; "
                "it must hand review ownership to review-pr."
            ),
        )

    def test_review_pr_makes_final_round_one_the_broad_mutating_review(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)final round 1.*independent broad mutating review.*without.*preliminary deep",
            "final round 1 is the independent broad mutating review without a preliminary deep pair",
        )

    def test_review_pr_documents_every_allowed_review_budget_stage_tag(self):
        policy = self.policy_text("plugins/review/skills/review-pr/SKILL.md")
        for stage_tag in (
            "[review:standard]",
            "[review:standard:security]",
            "[review:standard:retry]",
            "[review:deep:primary]",
            "[review:deep:challenge]",
            "[review:deep:security]",
            "[review:final:<round>:primary]",
            "[review:final:<round>:challenge]",
            "[review:final:<round>:security]",
        ):
            with self.subTest(stage_tag=stage_tag):
                self.assertIn(
                    stage_tag,
                    policy,
                    msg=(
                        "review-pr must document every review-budget stage tag so "
                        "review orchestration cannot drift from guardrail policy."
                    ),
                )

    def test_deep_review_tags_light_tier_security_with_standard_security_stage(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/deep-review.md",
            r'(?is)Task\(\s*subagent_type:\s*"security",\s*'
            r'description:\s*"\[review:standard:security\]',
            "light-tier security launches with the standard security stage tag",
        )

    def test_implementer_hands_review_ownership_to_review_pr(self):
        self.assert_policy_matches(
            "plugins/build/droids/implementer.md",
            r"(?is)hand.*review ownership.*review-pr",
            "review ownership is handed to review-pr",
        )

    def test_implementer_does_not_handoff_review_directly_to_reviewers(self):
        policy = self.policy_text("plugins/build/droids/implementer.md")
        self.assertNotRegex(
            policy,
            r"(?is)(?:delegate|hand.*?off|recommend).*?"
            r"(?:change-review|security).*?(?:re-review|review)",
            msg=(
                "implementer must not hand off review directly to change-review or "
                "security; it must hand review ownership to review-pr."
            ),
        )

    def test_test_engineer_hands_review_ownership_to_review_pr_including_test_review(self):
        policy = self.policy_text("plugins/build/droids/test-engineer.md")
        self.assert_policy_matches(
            "plugins/build/droids/test-engineer.md",
            r"(?is)hand.*review ownership.*review-pr",
            "review ownership is handed to review-pr",
        )
        self.assertNotRegex(
            policy,
            r"(?is)diff-level review.*change-review",
            msg=(
                "test-engineer must not send diff-level test review directly to "
                "change-review; it must hand review ownership to review-pr."
            ),
        )

    def test_review_pr_blocks_round_two_findings_before_edits_or_more_review(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)final round 2.*actionable finding.*block.*before.*edit.*(?:and|before).*"
            r"(?:further|more) review",
            "an actionable final-round-2 finding blocks before edits or further review",
        )

    def test_review_pr_requires_a_decision_for_scope_expanding_remedies(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)valid defect.*scope-expanding remed(?:y|ies).*user decision",
            "a valid defect is distinguished from a scope-expanding remedy requiring a user decision",
        )

    def test_fix_comments_requires_a_decision_for_scope_expanding_remedies(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/fix-comments.md",
            r"(?is)valid defect.*scope-expanding remed(?:y|ies).*user decision",
            "a valid defect is distinguished from a scope-expanding remedy requiring a user decision",
        )

    def test_change_review_cannot_authorize_respec_or_architecture_expansion(self):
        self.assert_policy_matches(
            "plugins/review/droids/change-review.md",
            r"(?is)findings?.*cannot authorize.*(?:re-?spec|architecture expansion)",
            "findings cannot authorize a respec or architecture expansion",
        )


if __name__ == "__main__":
    unittest.main()
