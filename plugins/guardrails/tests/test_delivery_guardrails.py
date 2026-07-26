import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

import stop_delivery_gate  # noqa: E402
from delivery_ledger import (  # noqa: E402
    clear_push_state,
    is_push_command,
    load_state,
    parse_push_command,
    record_push,
    record_session_baseline,
    state_path,
)
from intent_router import route_intent  # noqa: E402
from pre_push_policy import push_policy_violation  # noqa: E402
from stop_delivery_gate import (  # noqa: E402
    DeliverySnapshot,
    body_is_fresh,
    classify_worktree,
    delivery_gate_output,
    pending_obligations,
)


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

    def make_snapshot(self, **overrides):
        fields = {
            "local_head": "abc123",
            "remote_head": "abc123",
            "dirty_tracked": False,
            "unexpected_untracked": (),
            "pr_state": "ok",
            "pr_head": "abc123",
            "checks_complete": True,
            "checks_green": True,
            "unresolved_threads": 0,
            "body_fresh": True,
        }
        fields.update(overrides)
        return DeliverySnapshot(**fields)

    def test_green_current_pr_is_complete(self):
        self.assertEqual(
            pending_obligations(
                self.state,
                self.make_snapshot(),
                thread_authority=True,
            ),
            [],
        )

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
        snapshot = self.make_snapshot(
            local_head="def456",
            dirty_tracked=True,
            unexpected_untracked=("src/new.ts",),
            checks_complete=False,
            checks_green=False,
            unresolved_threads=2,
            body_fresh=False,
        )
        obligations = pending_obligations(
            self.state,
            snapshot,
            thread_authority=True,
        )

        self.assertEqual(len(obligations), 7)
        self.assertTrue(any("worktree" in item for item in obligations))
        self.assertTrue(any("unpushed" in item for item in obligations))
        self.assertTrue(any("CI" in item for item in obligations))
        self.assertTrue(any("threads" in item for item in obligations))
        self.assertTrue(any("body" in item for item in obligations))

    def test_threads_do_not_block_without_merge_or_approve_authority(self):
        snapshot = self.make_snapshot(unresolved_threads=3, body_fresh=None)

        self.assertEqual(
            pending_obligations(self.state, snapshot, thread_authority=False),
            [],
        )
        self.assertIsNone(
            delivery_gate_output(
                self.state,
                snapshot,
                stop_hook_active=False,
                thread_authority=False,
            )
        )

    def test_threads_block_when_the_request_granted_merge_or_approve(self):
        snapshot = self.make_snapshot(unresolved_threads=3)
        obligations = pending_obligations(
            self.state,
            snapshot,
            thread_authority=True,
        )

        self.assertEqual(obligations, ["3 unresolved review threads remain."])
        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=False,
            thread_authority=True,
        )
        self.assertEqual(output["decision"], "block")
        self.assertIn("review thread", output["reason"])

    def test_unmanaged_pr_body_is_not_blocked_but_stale_marker_is(self):
        unmanaged = pending_obligations(
            self.state,
            self.make_snapshot(body_fresh=None),
            thread_authority=True,
        )
        self.assertEqual(unmanaged, [])

        stale = pending_obligations(
            self.state,
            self.make_snapshot(body_fresh=False),
            thread_authority=True,
        )
        self.assertEqual(stale, ["PR body is not stamped for the current PR head."])

    def test_branch_without_a_pr_enforces_only_push_integrity(self):
        snapshot = self.make_snapshot(
            pr_state="none",
            pr_head=None,
            checks_complete=None,
            checks_green=None,
            unresolved_threads=None,
            body_fresh=None,
        )

        self.assertEqual(
            pending_obligations(self.state, snapshot, thread_authority=True),
            [],
        )
        dirty = self.make_snapshot(
            pr_state="none",
            pr_head=None,
            checks_complete=None,
            checks_green=None,
            unresolved_threads=None,
            body_fresh=None,
            dirty_tracked=True,
        )
        self.assertEqual(
            pending_obligations(self.state, dirty, thread_authority=True),
            ["The worktree contains uncommitted tracked changes."],
        )

    def test_gh_unavailable_consolidates_into_one_failed_closed_obligation(self):
        snapshot = self.make_snapshot(
            pr_state="unavailable",
            pr_head=None,
            checks_complete=None,
            checks_green=None,
            unresolved_threads=None,
            body_fresh=None,
        )
        obligations = pending_obligations(
            self.state,
            snapshot,
            thread_authority=True,
        )

        self.assertEqual(len(obligations), 1)
        self.assertIn("could not verify PR, CI, or review-thread state", obligations[0])
        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=False,
            thread_authority=True,
        )
        self.assertEqual(output["decision"], "block")
        self.assertIn("gh auth status", output["reason"])

    def test_unknown_local_state_blocks_instead_of_claiming_green(self):
        snapshot = self.make_snapshot(
            remote_head=None,
            dirty_tracked=None,
            unexpected_untracked=None,
            pr_state="unavailable",
            pr_head=None,
            checks_complete=None,
            checks_green=None,
            unresolved_threads=None,
            body_fresh=None,
        )
        obligations = pending_obligations(
            self.state,
            snapshot,
            thread_authority=True,
        )

        self.assertGreaterEqual(len(obligations), 4)
        self.assertTrue(any("could not verify" in item for item in obligations))

    def test_pending_ci_block_requires_one_foreground_watch(self):
        snapshot = self.make_snapshot(checks_complete=False, checks_green=False)

        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=False,
            thread_authority=True,
        )

        self.assertEqual(output["decision"], "block")
        self.assertIn("Do not retry Stop", output["reason"])
        self.assertIn("gh pr checks 42 --watch --interval 10", output["reason"])

    def test_pending_ci_reentry_stops_without_another_continuation(self):
        snapshot = self.make_snapshot(checks_complete=False, checks_green=False)

        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=True,
            thread_authority=True,
        )

        self.assertFalse(output["continue"])
        self.assertIn("not accepted as complete", output["stopReason"])

    def test_actionable_reentry_still_blocks(self):
        snapshot = self.make_snapshot(dirty_tracked=True)

        output = delivery_gate_output(
            self.state,
            snapshot,
            stop_hook_active=True,
            thread_authority=True,
        )

        self.assertEqual(output["decision"], "block")
        self.assertIn("uncommitted tracked changes", output["reason"])

    def test_unchanged_obligations_on_reentry_stop_instead_of_looping(self):
        snapshot = self.make_snapshot(dirty_tracked=True)
        state = {
            **self.state,
            "last_block_obligations": [
                "The worktree contains uncommitted tracked changes."
            ],
        }

        output = delivery_gate_output(
            state,
            snapshot,
            stop_hook_active=True,
            thread_authority=True,
        )

        self.assertFalse(output["continue"])
        self.assertIn("unchanged obligations", output["stopReason"])

    def test_changed_obligations_on_reentry_block_again(self):
        snapshot = self.make_snapshot(dirty_tracked=True, checks_green=False)
        state = {
            **self.state,
            "last_block_obligations": [
                "The worktree contains uncommitted tracked changes."
            ],
        }

        output = delivery_gate_output(
            state,
            snapshot,
            stop_hook_active=True,
            thread_authority=True,
        )

        self.assertEqual(output["decision"], "block")

    def test_block_reason_is_two_lines_with_a_next_step(self):
        cases = (
            self.make_snapshot(checks_complete=True, checks_green=False),
            self.make_snapshot(unresolved_threads=2),
            self.make_snapshot(body_fresh=False),
            self.make_snapshot(dirty_tracked=True),
        )
        for snapshot in cases:
            with self.subTest(snapshot=snapshot):
                output = delivery_gate_output(
                    self.state,
                    snapshot,
                    stop_hook_active=False,
                    thread_authority=True,
                )
                self.assertEqual(output["decision"], "block")
                lines = output["reason"].split("\n")
                self.assertEqual(len(lines), 2)
                self.assertTrue(lines[0].startswith("Delivery remains incomplete: "))
                self.assertIn("`", lines[1], "next step must name a command")


class StopGateFetchPrTests(unittest.TestCase):
    def fake_result(self, returncode, stdout="", stderr=""):
        return subprocess.CompletedProcess(
            args=["gh"],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def test_missing_pr_is_classified_as_none(self):
        for stderr in (
            'no pull requests found for branch "feature"',
            "GraphQL: Could not resolve to a PullRequest with the number of 999.",
        ):
            with self.subTest(stderr=stderr):
                with mock.patch.object(
                    stop_delivery_gate.subprocess,
                    "run",
                    return_value=self.fake_result(1, stderr=stderr),
                ):
                    pr, pr_state = stop_delivery_gate.fetch_pr("/repo", None)
                self.assertIsNone(pr)
                self.assertEqual(pr_state, "none")

    def test_auth_network_timeout_and_parse_failures_are_unavailable(self):
        failures = (
            self.fake_result(1, stderr="HTTP 401: Bad credentials"),
            self.fake_result(1, stderr="dial tcp: lookup api.github.com: no such host"),
            self.fake_result(0, stdout="not json"),
        )
        for result in failures:
            with self.subTest(result=result):
                with mock.patch.object(
                    stop_delivery_gate.subprocess,
                    "run",
                    return_value=result,
                ):
                    pr, pr_state = stop_delivery_gate.fetch_pr("/repo", 42)
                self.assertIsNone(pr)
                self.assertEqual(pr_state, "unavailable")
        with mock.patch.object(
            stop_delivery_gate.subprocess,
            "run",
            side_effect=OSError("gh not installed"),
        ):
            pr, pr_state = stop_delivery_gate.fetch_pr("/repo", 42)
        self.assertIsNone(pr)
        self.assertEqual(pr_state, "unavailable")

    def test_valid_pr_json_is_classified_as_ok(self):
        payload = json.dumps({"number": 42, "headRefOid": "abc123", "body": ""})
        with mock.patch.object(
            stop_delivery_gate.subprocess,
            "run",
            return_value=self.fake_result(0, stdout=payload),
        ):
            pr, pr_state = stop_delivery_gate.fetch_pr("/repo", 42)
        self.assertEqual(pr_state, "ok")
        self.assertEqual(pr["number"], 42)


class StopGateSnapshotTests(unittest.TestCase):
    def test_fetch_checks_classifies_pending_green_and_failed(self):
        cases = (
            ([{"state": "SUCCESS"}, {"state": "SUCCESS"}], (True, True)),
            ([{"state": "SUCCESS"}, {"state": "IN_PROGRESS"}], (False, False)),
            ([{"state": "SUCCESS"}, {"state": "FAILURE"}], (True, False)),
            ("not a list", (None, None)),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                with mock.patch.object(
                    stop_delivery_gate, "run_json", return_value=value
                ):
                    self.assertEqual(
                        stop_delivery_gate.fetch_checks("/repo", 42),
                        expected,
                    )

    def test_fetch_unresolved_threads_counts_and_fails_closed(self):
        identity = {"nameWithOwner": "owner/repo"}
        page = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {"isResolved": True},
                                {"isResolved": False},
                                {"isResolved": False},
                            ]
                        }
                    }
                }
            }
        }
        with mock.patch.object(
            stop_delivery_gate, "run_json", side_effect=[identity, [page]]
        ):
            self.assertEqual(
                stop_delivery_gate.fetch_unresolved_threads("/repo", 42), 2
            )
        with mock.patch.object(
            stop_delivery_gate, "run_json", side_effect=[identity, [{"data": {}}]]
        ):
            self.assertIsNone(
                stop_delivery_gate.fetch_unresolved_threads("/repo", 42)
            )
        with mock.patch.object(
            stop_delivery_gate, "run_json", side_effect=["not a dict"]
        ):
            self.assertIsNone(
                stop_delivery_gate.fetch_unresolved_threads("/repo", 42)
            )

    def test_snapshot_skips_thread_fetch_without_authority_and_detects_stamps(self):
        state = {
            "repo_root": "/repo",
            "branch": "feature",
            "pr_number": 42,
            "baseline_untracked": [],
        }
        pr = {
            "number": 42,
            "headRefOid": "abc123",
            "body": "Body\n<!-- pr-body-head=old -->",
        }
        with (
            mock.patch.object(stop_delivery_gate, "run_text", return_value="abc123"),
            mock.patch.object(
                stop_delivery_gate, "fetch_pr", return_value=(pr, "ok")
            ),
            mock.patch.object(
                stop_delivery_gate, "fetch_checks", return_value=(True, True)
            ),
            mock.patch.object(
                stop_delivery_gate, "fetch_unresolved_threads"
            ) as threads,
        ):
            snapshot, pr_number = stop_delivery_gate.snapshot_delivery(
                state, thread_authority=False
            )
        threads.assert_not_called()
        self.assertEqual(pr_number, 42)
        self.assertIsNone(snapshot.unresolved_threads)
        self.assertFalse(snapshot.body_fresh)

        unmanaged = {**pr, "body": "Body with no marker"}
        with (
            mock.patch.object(stop_delivery_gate, "run_text", return_value="abc123"),
            mock.patch.object(
                stop_delivery_gate, "fetch_pr", return_value=(unmanaged, "ok")
            ),
            mock.patch.object(
                stop_delivery_gate, "fetch_checks", return_value=(True, True)
            ),
            mock.patch.object(
                stop_delivery_gate, "fetch_unresolved_threads", return_value=1
            ),
        ):
            snapshot, _ = stop_delivery_gate.snapshot_delivery(
                state, thread_authority=True
            )
        self.assertIsNone(snapshot.body_fresh)
        self.assertEqual(snapshot.unresolved_threads, 1)


class StopGateMainTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        env = {
            "DROID_DELIVERY_LEDGER_DIR": str(root / "ledger"),
            "DROID_INTENT_STATE_DIR": str(root / "intent"),
            "DROID_GUARDRAILS_LOG_DIR": str(root / "log"),
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        repo = tempfile.mkdtemp(dir=self.scratch.name)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        self.repo_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def run_main(self, payload):
        stdout = io.StringIO()
        original = (sys.stdin, sys.stdout)
        try:
            sys.stdin = io.StringIO(json.dumps(payload))
            sys.stdout = stdout
            code = stop_delivery_gate.main()
        finally:
            sys.stdin, sys.stdout = original
        return code, stdout.getvalue()

    def dirty_snapshot(self):
        return DeliverySnapshot(
            local_head="abc123",
            remote_head="abc123",
            dirty_tracked=True,
            unexpected_untracked=(),
            pr_state="ok",
            pr_head="abc123",
            checks_complete=True,
            checks_green=True,
            unresolved_threads=0,
            body_fresh=True,
        )

    def test_main_blocks_persists_obligations_then_stops_on_identical_reentry(self):
        record_push(
            state_dir=Path(os.environ["DROID_DELIVERY_LEDGER_DIR"]),
            session_id="gate-main",
            repo_root=self.repo_root,
            branch="feature",
            pushed_head="abc123",
            pr_number=42,
        )

        with mock.patch.object(
            stop_delivery_gate,
            "snapshot_delivery",
            return_value=(self.dirty_snapshot(), 42),
        ):
            code, out = self.run_main(
                {"session_id": "gate-main", "cwd": self.repo_root}
            )
            self.assertEqual(code, 0)
            first = json.loads(out)
            self.assertEqual(first["decision"], "block")

            state_file = state_path(
                Path(os.environ["DROID_DELIVERY_LEDGER_DIR"]),
                "gate-main",
                self.repo_root,
            )
            persisted = load_state(state_file)
            self.assertEqual(
                persisted["last_block_obligations"],
                ["The worktree contains uncommitted tracked changes."],
            )

            code, out = self.run_main(
                {
                    "session_id": "gate-main",
                    "cwd": self.repo_root,
                    "stop_hook_active": True,
                }
            )
            self.assertEqual(code, 0)
            second = json.loads(out)
            self.assertFalse(second["continue"])
            self.assertIn("unchanged obligations", second["stopReason"])

    def test_main_clears_push_state_when_delivery_is_complete(self):
        record_push(
            state_dir=Path(os.environ["DROID_DELIVERY_LEDGER_DIR"]),
            session_id="gate-clean",
            repo_root=self.repo_root,
            branch="feature",
            pushed_head="abc123",
            pr_number=42,
        )
        clean = DeliverySnapshot(
            local_head="abc123",
            remote_head="abc123",
            dirty_tracked=False,
            unexpected_untracked=(),
            pr_state="ok",
            pr_head="abc123",
            checks_complete=True,
            checks_green=True,
            unresolved_threads=0,
            body_fresh=True,
        )
        with mock.patch.object(
            stop_delivery_gate,
            "snapshot_delivery",
            return_value=(clean, 42),
        ):
            code, out = self.run_main(
                {"session_id": "gate-clean", "cwd": self.repo_root}
            )
        self.assertEqual((code, out), (0, ""))
        state_file = state_path(
            Path(os.environ["DROID_DELIVERY_LEDGER_DIR"]),
            "gate-clean",
            self.repo_root,
        )
        self.assertIsNone(load_state(state_file)["pushed_head"])


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

    def test_tdd_workflow_requires_one_targeted_test_per_unit(self):
        self.assert_policy_matches(
            "plugins/practices/skills/tdd-workflow/SKILL.md",
            r"(?is)one targeted test.*per unit",
            "each unit receives one targeted test before implementation",
        )

    def test_tdd_workflow_defers_full_suite_to_program_completion(self):
        self.assert_policy_matches(
            "plugins/practices/skills/tdd-workflow/SKILL.md",
            r"(?is)full suite.*program completion",
            "the full suite or integration gate is reserved for program completion",
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

    def test_review_pr_makes_the_pair_review_the_broad_mutating_review(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)pair\s+review.*independent\s+broad\s+mutating\s+review.*"
            r"without.*preliminary\s+deep",
            "the pre-push pair review is the independent broad mutating review without a preliminary deep pair",
        )

    def test_supporting_review_tier_guidance_keeps_independent_high_consequence_work_deep(self):
        for relative_path in (
            "plugins/review/skills/review-pr/deep-review.md",
            "plugins/review/README.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assert_policy_matches(
                    relative_path,
                    r"(?m)^(?:-\s+)?A\s+small,\s+well-tested\s+edit\s+to\s+existing\s+"
                    r"risk-sensitive\s+logic\s+remains\s+light\s+only\s+when\s+no\s+"
                    r"independently\s+high-consequence\s+responsibility\s+applies\.$",
                    "small, well-tested edits to existing risk-sensitive logic remain "
                    "light only without an independently high-consequence responsibility",
                )
                self.assert_policy_matches(
                    relative_path,
                    r"(?m)^(?:-\s+)?Migrations,\s+concurrency,\s+externally\s+controlled\s+"
                    r"state,\s+multi-phase\s+transitions,\s+and\s+new\s+or\s+materially\s+"
                    r"rewritten\s+authorization\s+decisions\s+remain\s+deep\s+even\s+"
                    r"when\s+small\.$",
                    "migrations, concurrency, externally controlled state, "
                    "multi-phase transitions, and new or materially rewritten "
                    "authorization decisions remain deep even when small",
                )
                policy = self.policy_text(relative_path)
                self.assertNotRegex(
                    policy,
                    r"(?s)Do not escalate to deep on a small, well-tested touch to a "
                    r"risk-sensitive path alone\.\s+Escalate\s+only when the diff is also "
                    r"large or the risk-sensitive logic is new/rewritten\.",
                    msg=(
                        f"{relative_path} must not restore the former conflicting "
                        "deep-review light-tier carve-out."
                    ),
                )
                self.assertNotRegex(
                    policy,
                    r"(?s)The escalation heuristic leans light:\s+a small, well-tested "
                    r"touch to a risk-sensitive path stays light;\s+deep is reserved for "
                    r"large diffs or new/rewritten risk-sensitive logic\.",
                    msg=(
                        f"{relative_path} must not restore the former conflicting README "
                        "light-tier guidance."
                    ),
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

    def test_investigation_and_synthesis_droids_route_review_handoffs_through_review_pr(self):
        for relative_path in (
            "plugins/investigation/droids/quick-analysis.md",
            "plugins/investigation/droids/deep-understanding.md",
            "plugins/investigation/droids/deep-research.md",
            "plugins/synthesis/droids/pr-describer.md",
            "plugins/synthesis/droids/commit-message-writer.md",
        ):
            with self.subTest(relative_path=relative_path):
                policy = self.policy_text(relative_path)
                self.assertRegex(
                    policy,
                    r"(?is)hand.*review ownership.*review-pr",
                    msg=(
                        f"{relative_path} must hand review ownership to review-pr "
                        "when review follow-up is needed."
                    ),
                )
                self.assertNotRegex(
                    policy,
                    r"(?im)^(?:-\s*)?(?:"
                    r".*(?:→|->)\s*`?(?:change-review|security)"
                    r"|.*\b(?:delegate|recommend|flag|hand.{0,40}off)\b.*"
                    r"\b(?:change-review|security)\b"
                    r"|\*\*(?:change-review|security)\*\*\s+—"
                    r")",
                    msg=(
                        f"{relative_path} must not directly recommend change-review "
                        "or security for review follow-up."
                    ),
                )

    def test_debugger_and_prompt_optimizer_route_security_review_followups_through_review_pr(self):
        for relative_path in (
            "plugins/investigation/droids/debugger.md",
            "plugins/meta/droids/prompt-optimizer.md",
        ):
            with self.subTest(relative_path=relative_path):
                policy = self.policy_text(relative_path)
                self.assertRegex(
                    policy,
                    r"(?is)security-shaped.*hand.*review ownership.*review-pr",
                    msg=(
                        f"{relative_path} must hand security review follow-up "
                        "ownership to review-pr."
                    ),
                )
                self.assertNotRegex(
                    policy,
                    r"(?im)^-\s+.*security-shaped.*(?:→|->)\s*"
                    r"(?:flag|delegate|hand).*security\b",
                    msg=(
                        f"{relative_path} must not direct security-shaped review "
                        "follow-up to security."
                    ),
                )

    def test_review_pr_blocks_on_loop_exhaustion_or_non_convergence(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)loop\s+budget\s+is\s+exhausted.*same\s+root-cause\s+finding\s+"
            r"survives\s+two\s+consecutive.*block.*"
            r"report\s+the\s+remaining\s+findings.*"
            r"new\s+user\s+instruction\s+resets\s+the\s+loop\s+budget",
            "loop exhaustion or non-convergence blocks with a report and the budget-reset recovery",
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

    def test_review_pr_reuses_current_head_validation_evidence(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)reuse.*valid current-head validation evidence",
            "valid current-head validation evidence is reused",
        )

    def test_review_pr_runs_only_missing_ci_parity_validation_commands(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)run only.*missing.*CI-parity command",
            "only CI-parity commands missing from reusable evidence are run",
        )

    def test_review_pr_requires_fresh_targeted_and_integration_validation_after_head_change(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)head-changing correction.*fresh targeted validation.*fresh integration",
            "a head-changing correction receives fresh targeted and integration validation",
        )

    def test_review_pr_requires_fresh_user_request_when_approval_head_changes(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)completed normal review.*live.*head.*(?:changes|differs).*"
            r"fresh user review request",
            "a live approval head change after completed normal review requires a fresh user review request",
        )

    def test_approval_head_change_stops_comment_and_deep_review_procedures(self):
        for relative_path in (
            "plugins/review/skills/review-pr/fix-comments.md",
            "plugins/review/skills/review-pr/deep-review.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assert_policy_matches(
                    relative_path,
                    r"(?is)approval.*head.*(?:changes|differs).*stop.*"
                    r"fresh user review request.*(?:never|do not).*rerun.*"
                    r"(?:review|existing request)",
                    "an approval-head change stops the request and requires fresh review authority",
                )

    def test_tdd_workflow_uses_selected_targeted_command_at_each_checkpoint(self):
        self.assert_policy_matches(
            "plugins/practices/skills/tdd-workflow/SKILL.md",
            r"(?is)RED/GREEN/refactor checkpoints.*selected targeted command.*"
            r"(?:not|rather than).*broad suite",
            "RED, GREEN, and refactor checkpoints use the selected targeted command rather than a broad suite",
        )

    def test_tdd_checkpoint_templates_claim_only_targeted_verification(self):
        policy = self.policy_text("plugins/practices/skills/tdd-workflow/SKILL.md")
        self.assertNotRegex(
            policy,
            r"(?is)GREEN:.*(?:no regressions|all tests still passing)",
            "TDD checkpoints must not claim program-level regression coverage.",
        )
        self.assert_policy_matches(
            "plugins/practices/skills/tdd-workflow/SKILL.md",
            r"(?is)GREEN:.*targeted (?:test|validator|verification)",
            "GREEN checkpoint templates record only targeted verification",
        )
        self.assert_policy_matches(
            "plugins/practices/skills/tdd-workflow/SKILL.md",
            r"(?is)Self-Check.*targeted (?:test|validator|verification).*"
            r"program completion",
            "the TDD self-check reserves full-suite claims for program completion",
        )

    def test_public_plugin_readmes_hand_review_ownership_to_review_pr(self):
        for relative_path in (
            "plugins/build/README.md",
            "plugins/investigation/README.md",
            "plugins/practices/README.md",
            "plugins/review/README.md",
            "plugins/synthesis/README.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assert_policy_matches(
                    relative_path,
                    r"(?is)hand.*review ownership.*review-pr",
                    "review ownership is handed to review-pr",
                )
                self.assertNotRegex(
                    self.policy_text(relative_path),
                    r"(?im)(?:hand|delegate|run|invoke|recommend)[^\n]{0,100}"
                    r"(?:change-review|security)",
                    msg=(
                        f"{relative_path} must not hand review work directly to "
                        "change-review or security."
                    ),
                )


if __name__ == "__main__":
    unittest.main()
