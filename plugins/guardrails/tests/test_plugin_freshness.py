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

import plugin_freshness  # noqa: E402


class PluginFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.repo = self.root / "sagar-plugins"
        self.command(["git", "init", "-q", "-b", "main", str(self.repo)], cwd=self.root)
        self.command(["git", "remote", "add", "origin", "https://example.test/repo.git"])
        self.write_commit("initial")
        self.set_source(self.head())
        env = {
            "DROID_GUARDRAILS_LOG_DIR": str(self.root / "log"),
        }
        patcher = mock.patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def command(self, command, cwd=None):
        result = subprocess.run(
            command,
            cwd=cwd or self.repo,
            capture_output=True,
            check=True,
            text=True,
        )
        return result.stdout.strip()

    def head(self):
        return self.command(["git", "rev-parse", "HEAD"])

    def write_commit(self, content):
        (self.repo / "tracked.txt").write_text(f"{content}\n", encoding="utf-8")
        self.command(["git", "add", "tracked.txt"])
        self.command(
            [
                "git",
                "-c",
                "user.name=Plugin Freshness Test",
                "-c",
                "user.email=plugin-freshness@example.test",
                "commit",
                "-qm",
                content,
            ]
        )

    def set_source(self, revision):
        self.command(["git", "update-ref", "refs/remotes/origin/main", revision])
        self.command(
            [
                "git",
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                "refs/remotes/origin/main",
            ]
        )

    def plugin_root(self, revision):
        return str(self.root / "cache" / "sagar-plugins" / "guardrails" / revision)

    def run_main(self, *, cwd=None, plugin_root=None, raw_input=None):
        stdout = io.StringIO()
        original = sys.stdin, sys.stdout
        payload = raw_input or {"cwd": str(cwd or self.repo), "session_id": "freshness"}
        try:
            sys.stdin = io.StringIO(json.dumps(payload))
            sys.stdout = stdout
            with mock.patch.dict(
                os.environ,
                {"DROID_PLUGIN_ROOT": plugin_root} if plugin_root else {},
                clear=False,
            ):
                if plugin_root is None:
                    os.environ.pop("DROID_PLUGIN_ROOT", None)
                code = plugin_freshness.main()
        finally:
            sys.stdin, sys.stdout = original
        return code, stdout.getvalue()

    def decisions(self):
        path = Path(os.environ["DROID_GUARDRAILS_LOG_DIR"]) / "decisions.jsonl"
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]

    def test_equal_installed_revision_is_silent(self):
        revision = self.head()

        code, stdout = self.run_main(plugin_root=self.plugin_root(revision))

        self.assertEqual((code, stdout), (0, ""))

    def test_ancestor_installed_revision_warns_once(self):
        installed = self.head()
        self.write_commit("source tip")
        source = self.head()
        self.set_source(source)

        code, stdout = self.run_main(plugin_root=self.plugin_root(installed))

        self.assertEqual(code, 0)
        output = json.loads(stdout)
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(
            context,
            f"Plugin install is stale: {installed[:7]} is behind {source[:7]}. "
            "Run `droid plugin update`.",
        )
        self.assertTrue(output["suppressOutput"])

    def test_installed_revision_ahead_of_source_is_silent(self):
        source = self.head()
        self.write_commit("installed ahead")
        installed = self.head()
        self.set_source(source)

        code, stdout = self.run_main(plugin_root=self.plugin_root(installed))

        self.assertEqual((code, stdout), (0, ""))

    def test_missing_or_unparseable_plugin_root_is_silent(self):
        for plugin_root in (None, str(self.root / "cache" / "sagar-plugins" / "guardrails" / "unknown")):
            with self.subTest(plugin_root=plugin_root):
                code, stdout = self.run_main(plugin_root=plugin_root)

                self.assertEqual((code, stdout), (0, ""))

    def test_cwd_outside_the_source_repository_is_silent(self):
        other_repo = self.root / "unrelated"
        self.command(["git", "init", "-q", str(other_repo)], cwd=self.root)

        code, stdout = self.run_main(
            cwd=other_repo,
            plugin_root=self.plugin_root(self.head()),
        )

        self.assertEqual((code, stdout), (0, ""))

    def test_git_unavailable_or_failing_is_silent(self):
        for result in (
            None,
            subprocess.CompletedProcess(args=["git"], returncode=2, stdout="", stderr=""),
        ):
            with self.subTest(result=result), mock.patch.object(
                plugin_freshness,
                "run",
                return_value=result,
            ):
                code, stdout = self.run_main(plugin_root=self.plugin_root(self.head()))

                self.assertEqual((code, stdout), (0, ""))

    def test_all_decisions_are_nonblocking(self):
        installed = self.head()
        self.write_commit("source tip")
        self.set_source(self.head())
        self.run_main(plugin_root=self.plugin_root(installed))
        self.run_main(plugin_root=None)

        self.assertTrue(self.decisions())
        self.assertFalse(any(record["decision"] == "deny" for record in self.decisions()))


if __name__ == "__main__":
    unittest.main()
