"""Negative corpus for the intent router.

Every prompt here is ordinary engineering conversation that must neither
route a workflow nor grant merge/approve authority. When a false positive
is observed in real use, add the offending prompt here first, then fix the
router until the corpus is silent again: noise becomes a reproducible test
input, never a feeling.
"""

import sys
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from intent_router import (  # noqa: E402
    request_grants_merge_or_approve,
    route_intent,
)

NOISE_PROMPTS = (
    # Informational questions
    "What does git status show?",
    "What is the difference between rebase and merge?",
    "What's the diff between these two branches?",
    "What are the failing tests?",
    "How does the retry logic work?",
    "How do I run the linter locally?",
    "How can we speed up the test suite?",
    "How should we name this module?",
    "How would you approach this refactor?",
    "Why is CI red?",
    "Why does the cache invalidate twice?",
    "Which branch should I base this on?",
    "Which of these two designs is simpler?",
    "Who owns this module?",
    "Explain what a pull request review is.",
    "Explain the delivery gate to me.",
    "Describe the review budget states.",
    "Define what a golden task is.",
    "Summarize the review threads.",
    "Summarize what changed in this commit.",
    "Tell me about the review budget.",
    "Tell me which files the diff touches.",
    # Advice questions
    "Should I approve PR 42?",
    "Should we approve pull request 42?",
    "Should we approve and merge PR 42?",
    "Should we split this file?",
    "Should I rebase before opening the PR?",
    "Would you approve PR 42?",
    "Would you structure it differently?",
    "Would you push back on this design?",
    # Negations
    "Do not push this branch.",
    "Do not review this PR.",
    "Do not plan this change.",
    "Do not push or merge this branch.",
    "Don't merge anything today.",
    "Never push directly to main.",
    # Ship-family nouns, not verbs
    "The push failed with a non-fast-forward error.",
    "The merge introduced a regression.",
    "Merge conflicts appeared in three files.",
    "Merge commits clutter the history.",
    "Our last push broke CI.",
    "The last merge reverted my change.",
    "That push was rejected by the remote.",
    "Every push triggers the full pipeline.",
    "A failed merge left conflict markers behind.",
    # build/apply/address without workflow objects
    "Build the project and tell me if it compiles.",
    "Build passes now.",
    "Can you build and run the docker image?",
    "Apply your best judgment here.",
    "Apply the same reasoning to the second module.",
    "Apply migrations before deploying.",
    "Address the root cause of the flaky test.",
    "Address the performance regression in the parser.",
    "Update the address field validation.",
    "The billing address is stored unencrypted.",
    # Ordinary engineering tasks that are not the four workflows
    "Fix the typo in the README.",
    "Fix the flaky test in ci/utils.test.ts.",
    "Rename getCwd to getCurrentWorkingDirectory across the project.",
    "Refactor the parser to remove the global state.",
    "Debug why the webhook retries twice.",
    "Investigate the memory leak in the worker.",
    "Profile the slow endpoint and report the numbers.",
    "Write a unit test for the parser.",
    "Add logging to the retry loop.",
    "Delete the dead code in utils.",
    "Format the code with prettier.",
    "Run npm install and report the result.",
    "Run the test suite and paste the failures.",
    "Execute the test suite.",
    "Install the dependencies.",
    "Bump the version.",
    "Tag the release.",
    "Update the changelog for 2.3.0.",
    "Rebase onto main.",
    "Checkout the feature branch.",
    "Cherry-pick the hotfix commit.",
    "Stash my local changes.",
    "Revert the last commit locally.",
    "Commit these changes locally.",
    "Squash the fixup commits locally.",
    "Read the review comments and summarize them.",
    "List open PRs.",
    "List the files in this directory.",
    "Show me the staged changes.",
    "Show me the diff for the last commit.",
    "Print the current branch name.",
    "Search for usages of the deprecated API.",
    "Grep for TODO comments in src.",
    "Count the lines of code in the plugins directory.",
    "Open the failing workflow run in the browser.",
    "Double-check the PR description for typos.",
    "Compare the two branches and tell me what differs.",
    "Look at the review budget hook and tell me what it denies.",
    "Trace where the session id comes from.",
    "Check whether the linter passes.",
    "Verify the JSON schema is valid.",
    "Convert the config from YAML to TOML.",
    "Translate this error message to plain English.",
    "Document the retry behavior in the module docstring.",
    "Draft release notes for the next version.",
    "Generate a changelog entry from the last five commits.",
    # Status and chatter
    "Tests pass locally but fail in CI.",
    "CI has been slow all day.",
    "The build is failing on CI.",
    "The linter is complaining about unused imports.",
    "That stack trace points at the cache layer.",
    "Thanks, that looks right.",
    "Sounds good, carry on.",
    "Interesting, I did not expect that result.",
    "Good catch on the off-by-one.",
    "Let me think about that for a moment.",
    "Hold off for now.",
    "Nothing else for today.",
)


class RouterNoiseCorpusTests(unittest.TestCase):
    def test_corpus_has_at_least_one_hundred_prompts(self):
        self.assertGreaterEqual(len(NOISE_PROMPTS), 100)
        self.assertEqual(
            len(set(NOISE_PROMPTS)),
            len(NOISE_PROMPTS),
            "corpus prompts must be unique",
        )

    def test_no_corpus_prompt_routes_a_workflow(self):
        for prompt in NOISE_PROMPTS:
            with self.subTest(prompt=prompt):
                self.assertIsNone(
                    route_intent(prompt),
                    f"noise prompt must not route: {prompt!r}",
                )

    def test_no_corpus_prompt_grants_merge_or_approve_authority(self):
        for prompt in NOISE_PROMPTS:
            with self.subTest(prompt=prompt):
                self.assertFalse(
                    request_grants_merge_or_approve(prompt),
                    f"noise prompt must not grant authority: {prompt!r}",
                )


if __name__ == "__main__":
    unittest.main()
