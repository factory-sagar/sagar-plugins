import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from delivery_ledger import (  # noqa: E402
    is_push_command,
    load_state,
    parse_push_command,
    record_push,
)
from intent_router import route_intent  # noqa: E402
from pre_push_policy import push_policy_violation  # noqa: E402
from stop_delivery_gate import (  # noqa: E402
    DeliverySnapshot,
    body_is_fresh,
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
                    "version": 1,
                    "session_id": "session-1",
                    "repo_root": "/repo",
                    "branch": "feature",
                    "pushed_head": "abc123",
                    "pr_number": 42,
                },
            )


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

    def test_avoids_routing_informational_questions(self):
        self.assertIsNone(route_intent("What does git status show?"))
        self.assertIsNone(route_intent("Explain what a pull request review is."))
        self.assertIsNone(route_intent("Do not push this branch."))


class StopGateTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "pushed_head": "abc123",
            "pr_number": 42,
        }

    def test_green_current_pr_is_complete(self):
        snapshot = DeliverySnapshot(
            local_head="abc123",
            remote_head="abc123",
            pr_head="abc123",
            dirty_worktree=False,
            checks_complete=True,
            checks_green=True,
            unresolved_threads=0,
            body_fresh=True,
        )
        self.assertEqual(pending_obligations(self.state, snapshot), [])

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
            dirty_worktree=True,
            checks_complete=False,
            checks_green=False,
            unresolved_threads=2,
            body_fresh=False,
        )
        obligations = pending_obligations(self.state, snapshot)

        self.assertEqual(len(obligations), 6)
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
            dirty_worktree=None,
            checks_complete=None,
            checks_green=None,
            unresolved_threads=None,
            body_fresh=None,
        )
        obligations = pending_obligations(self.state, snapshot)

        self.assertGreaterEqual(len(obligations), 4)
        self.assertTrue(any("could not verify" in item for item in obligations))


if __name__ == "__main__":
    unittest.main()
