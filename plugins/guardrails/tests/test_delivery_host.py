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

import stop_delivery_gate  # noqa: E402
from delivery_ledger import (  # noqa: E402
    classify_delivery_host,
    load_state,
    record_push,
)
from stop_delivery_gate import DeliverySnapshot, pending_obligations  # noqa: E402


class DeliveryHostClassificationTests(unittest.TestCase):
    def test_classifies_delivery_hosts_from_remote_urls(self):
        cases = (
            ("https://github.com/owner/repo.git", None, "github"),
            ("git@github.com:owner/repo.git", None, "github"),
            ("https://gitlab.com/owner/repo.git", None, "unsupported"),
            ("git@bitbucket.org:owner/repo.git", None, "unsupported"),
            ("ssh://git@code.example.test:2222/owner/repo.git", None, "unsupported"),
            (None, None, "none"),
            (
                "ssh://git@ghe.example.test/owner/repo.git",
                {"ghe.example.test"},
                "github",
            ),
        )

        for remote_url, enterprise_hosts, expected in cases:
            with self.subTest(remote_url=remote_url):
                self.assertEqual(
                    classify_delivery_host(remote_url, enterprise_hosts),
                    expected,
                )

    def test_detection_falls_back_to_config_and_recognizes_configured_enterprise_host(self):
        configured = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout="", stderr=""
        )
        with (
            mock.patch.object(
                stop_delivery_gate,
                "run_text",
                side_effect=[None, "git@ghe.example.test:owner/repo.git"],
            ),
            mock.patch.object(stop_delivery_gate, "run", return_value=configured),
        ):
            self.assertEqual(
                stop_delivery_gate.detect_delivery_host("/repo"),
                ("github", "ghe.example.test"),
            )


class UnsupportedDeliveryHostTests(unittest.TestCase):
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
        self.repo = root / "repo"
        self.remote = root / "remote.git"
        self.command(["git", "init", "-q", str(self.repo)])
        self.command(["git", "init", "--bare", "-q", str(self.remote)])
        (self.repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
        self.command(["git", "add", "tracked.txt"])
        self.command(
            [
                "git",
                "-c",
                "user.name=Delivery Host Test",
                "-c",
                "user.email=delivery-host@example.test",
                "commit",
                "-qm",
                "initial",
            ]
        )
        self.repo_root = self.command(["git", "rev-parse", "--show-toplevel"])
        self.command(
            [
                "git",
                "remote",
                "add",
                "origin",
                "git@gitlab.com:owner/repo.git",
            ]
        )
        self.head = self.command(["git", "rev-parse", "HEAD"])
        self.branch = self.command(["git", "branch", "--show-current"])
        self.command(["git", "update-ref", f"refs/remotes/origin/{self.branch}", self.head])

    def command(self, command):
        result = subprocess.run(
            command,
            cwd=self.repo if self.repo.exists() else None,
            capture_output=True,
            check=True,
            text=True,
        )
        return result.stdout.strip()

    def record_clean_push(self, session_id):
        return record_push(
            state_dir=Path(os.environ["DROID_DELIVERY_LEDGER_DIR"]),
            session_id=session_id,
            repo_root=self.repo_root,
            branch=self.branch,
            pushed_head=self.head,
            pr_number=None,
        )

    def run_main(self, session_id):
        stdout = io.StringIO()
        original = sys.stdin, sys.stdout
        try:
            sys.stdin = io.StringIO(
                json.dumps({"session_id": session_id, "cwd": str(self.repo)})
            )
            sys.stdout = stdout
            code = stop_delivery_gate.main()
        finally:
            sys.stdin, sys.stdout = original
        return code, stdout.getvalue()

    def host_skip_notes(self):
        records = [
            json.loads(line)
            for line in (
                Path(os.environ["DROID_GUARDRAILS_LOG_DIR"]) / "decisions.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        ]
        return [
            str(record["detail"])
            for record in records
            if record["decision"] == "skip"
        ]

    def test_clean_gitlab_push_completes_with_one_host_note(self):
        path = self.record_clean_push("gitlab-clean")

        code, stdout = self.run_main("gitlab-clean")

        self.assertEqual((code, stdout), (0, ""))
        self.assertEqual(
            self.host_skip_notes(),
            [
                "Delivery gate: PR, CI, and review-thread verification is unsupported "
                "for gitlab.com; only git push integrity was checked."
            ],
        )
        self.assertIsNone(load_state(path)["pushed_head"])

    def test_dirty_gitlab_worktree_still_blocks_with_one_host_note(self):
        self.record_clean_push("gitlab-dirty")
        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")

        code, stdout = self.run_main("gitlab-dirty")

        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(stdout)["decision"],
            "block",
        )
        self.assertIn("uncommitted tracked changes", json.loads(stdout)["reason"])
        self.assertEqual(len(self.host_skip_notes()), 1)


class GithubDeliveryHostTests(unittest.TestCase):
    def test_github_obligations_are_unchanged_for_an_equivalent_snapshot(self):
        state = {"pushed_head": "abc123", "pr_number": 42}
        snapshot = DeliverySnapshot(
            local_head="def456",
            remote_head="abc123",
            dirty_tracked=True,
            unexpected_untracked=("new.txt",),
            pr_state="unavailable",
            pr_head=None,
            checks_complete=None,
            checks_green=None,
            unresolved_threads=None,
            body_fresh=None,
        )
        expected = [
            "The worktree contains uncommitted tracked changes.",
            "New untracked delivery files remain: new.txt.",
            "Local HEAD contains unpushed work created after the recorded push.",
            "Remote branch does not contain the current local HEAD.",
            "Delivery gate could not verify PR, CI, or review-thread state via gh.",
        ]

        self.assertEqual(
            pending_obligations(
                state,
                snapshot,
                thread_authority=True,
                delivery_host="github",
            ),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
