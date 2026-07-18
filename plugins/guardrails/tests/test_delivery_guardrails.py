import io
import json
import os
import re
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

    def test_hook_reserves_tagged_standard_security_and_rejects_untagged_security(self):
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
                        "[review:standard:security] [security:selected] "
                        "Inspect changed security paths"
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
            untagged_output = self.run_hook(untagged_security, state_dir)
            self.assertNotEqual(
                untagged_output,
                "",
                "An untagged security Task must receive a deny response.",
            )
            untagged = json.loads(untagged_output)
            self.assertEqual(
                untagged["hookSpecificOutput"]["permissionDecision"],
                "deny",
            )
            self.assertIn(
                "security",
                untagged["hookSpecificOutput"]["permissionDecisionReason"],
            )

    def test_hook_binds_review_stage_tags_to_reviewer_types(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            for index, (
                subagent_type,
                description,
                expected_decision,
            ) in enumerate(
                (
                    (
                        "security",
                        "[review:standard] Review changed files",
                        "deny",
                    ),
                    (
                        "change-review",
                        "[review:standard:security] Review security paths",
                        "deny",
                    ),
                    (
                        "security",
                        "[review:deep:security] [security:selected] "
                        "Review security paths",
                        "allow",
                    ),
                    (
                        "change-review",
                        "[review:deep:challenge] Challenge broad changes",
                        "deny",
                    ),
                )
            ):
                with self.subTest(
                    subagent_type=subagent_type,
                    description=description,
                ):
                    session_id = f"session-{index}"
                    self.run_hook(
                        {
                            "hook_event_name": "UserPromptSubmit",
                            "session_id": session_id,
                            "prompt": "Review and fix the change.",
                        },
                        state_dir,
                    )
                    output = self.run_hook(
                        {
                            "hook_event_name": "PreToolUse",
                            "session_id": session_id,
                            "tool_name": "Task",
                            "tool_input": {
                                "subagent_type": subagent_type,
                                "description": description,
                            },
                        },
                        state_dir,
                    )

                    if expected_decision == "allow":
                        self.assertEqual(output, "")
                    else:
                        self.assertNotEqual(output, "")
                        response = json.loads(output)
                        self.assertEqual(
                            response["hookSpecificOutput"]["permissionDecision"],
                            "deny",
                        )
                        self.assertIn(
                            subagent_type,
                            response["hookSpecificOutput"][
                                "permissionDecisionReason"
                            ],
                        )

    def test_hook_reserves_deep_worker_primary_challenge_and_prerequisite_retries(self):
        descriptions = (
            "[review:deep:primary] Run the deep primary pass",
            "[review:deep:retry:primary] Complete primary evidence",
            "[review:deep:challenge] Run the independent challenge pass",
            "[review:deep:retry:challenge] Complete challenge evidence",
        )
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "deep-worker",
                    "prompt": "Review the broad change deeply.",
                },
                state_dir,
            )

            for description in descriptions:
                with self.subTest(description=description):
                    self.assertEqual(
                        self.run_hook(
                            {
                                "hook_event_name": "PreToolUse",
                                "session_id": "deep-worker",
                                "tool_name": "Task",
                                "tool_input": {
                                    "subagent_type": "review-worker",
                                    "description": description,
                                },
                            },
                            state_dir,
                        ),
                        "",
                        "A declared deep review-worker stage must consume its "
                        "review budget slot.",
                    )

            state = load_review_state(review_state_path(state_dir, "deep-worker"))
            self.assertEqual(
                state["review_slots"],
                [
                    "[review:deep:primary]",
                    "[review:deep:retry:primary]",
                    "[review:deep:challenge]",
                    "[review:deep:retry:challenge]",
                ],
            )

    def test_hook_restricts_deep_worker_and_preserves_other_reviewer_roles(self):
        cases = (
            (
                "review-worker",
                "[review:standard] Attempt a standard review",
                "deny",
            ),
            (
                "review-worker",
                "[review:deep:security] [security:selected] Attempt security review",
                "deny",
            ),
            (
                "change-review",
                "[review:deep:primary] Attempt a deep primary review",
                "deny",
            ),
            (
                "change-review",
                "[review:standard] Run a standard review",
                "allow",
            ),
            (
                "change-review",
                "[review:final:1:primary] Run a final primary review",
                "allow",
            ),
            (
                "security",
                "[review:deep:security] [security:selected] Run a deep security review",
                "allow",
            ),
            (
                "security",
                "[review:deep:challenge] Attempt a deep challenge review",
                "deny",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            for index, (subagent_type, description, expected) in enumerate(cases):
                with self.subTest(
                    subagent_type=subagent_type,
                    description=description,
                ):
                    session_id = f"role-scope-{index}"
                    self.run_hook(
                        {
                            "hook_event_name": "UserPromptSubmit",
                            "session_id": session_id,
                            "prompt": "Review and fix the change.",
                        },
                        state_dir,
                    )
                    output = self.run_hook(
                        {
                            "hook_event_name": "PreToolUse",
                            "session_id": session_id,
                            "tool_name": "Task",
                            "tool_input": {
                                "subagent_type": subagent_type,
                                "description": description,
                            },
                        },
                        state_dir,
                    )

                    if expected == "allow":
                        self.assertEqual(output, "")
                    else:
                        self.assertNotEqual(output, "")
                        self.assertEqual(
                            json.loads(output)["hookSpecificOutput"][
                                "permissionDecision"
                            ],
                            "deny",
                        )

    def test_hook_requires_a_deep_worker_stage_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "untagged-deep-worker",
                    "prompt": "Review the broad change deeply.",
                },
                state_dir,
            )
            output = self.run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "session_id": "untagged-deep-worker",
                    "tool_name": "Task",
                    "tool_input": {
                        "subagent_type": "review-worker",
                        "description": "Continue the deep review.",
                    },
                },
                state_dir,
            )

        self.assertNotEqual(
            output,
            "",
            "An untagged review-worker Task must receive a deny response.",
        )
        response = json.loads(output)
        self.assertEqual(
            response["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "stage tag",
            response["hookSpecificOutput"]["permissionDecisionReason"],
        )

    def test_hook_reserves_discovery_once_for_deep_workers(self):
        description = "[review:deep:discovery] Discover applicable conventions"
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "deep-discovery",
                    "prompt": "Review the broad change deeply.",
                },
                state_dir,
            )
            first_output = self.run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "session_id": "deep-discovery",
                    "tool_name": "Task",
                    "tool_input": {
                        "subagent_type": "review-worker",
                        "description": description,
                    },
                },
                state_dir,
            )
            duplicate_output = self.run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "session_id": "deep-discovery",
                    "tool_name": "Task",
                    "tool_input": {
                        "subagent_type": "review-worker",
                        "description": description,
                    },
                },
                state_dir,
            )

        self.assertEqual(
            first_output,
            "",
            "Discovery must reserve its one deep-worker lifecycle slot.",
        )
        self.assertNotEqual(
            duplicate_output,
            "",
            "A duplicate discovery Task must receive a deny response.",
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

    def test_hook_allows_resumes_only_after_primary_with_a_resume_target(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "deep-resume",
                    "prompt": "Review the broad change deeply.",
                },
                state_dir,
            )
            missing_primary_output = self.run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "session_id": "deep-resume",
                    "tool_name": "Task",
                    "tool_input": {
                        "subagent_type": "review-worker",
                        "description": "[review:deep:resume] Continue the review",
                        "resume": "primary-task-id",
                    },
                },
                state_dir,
            )
            self.assertNotEqual(
                missing_primary_output,
                "",
                "A resume before the deep primary stage must receive a deny response.",
            )
            self.assertIn(
                "primary",
                json.loads(missing_primary_output)["hookSpecificOutput"][
                    "permissionDecisionReason"
                ],
            )

            self.assertEqual(
                self.run_hook(
                    {
                        "hook_event_name": "PreToolUse",
                        "session_id": "deep-resume",
                        "tool_name": "Task",
                        "tool_input": {
                            "subagent_type": "review-worker",
                            "description": "[review:deep:primary] Initialize review",
                        },
                    },
                    state_dir,
                ),
                "",
            )
            missing_resume_output = self.run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "session_id": "deep-resume",
                    "tool_name": "Task",
                    "tool_input": {
                        "subagent_type": "review-worker",
                        "description": "[review:deep:resume] Continue the review",
                    },
                },
                state_dir,
            )
            resumed_output = self.run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "session_id": "deep-resume",
                    "tool_name": "Task",
                    "tool_input": {
                        "subagent_type": "review-worker",
                        "description": "[review:deep:resume] Continue the review",
                        "resume": "primary-task-id",
                    },
                },
                state_dir,
            )

        missing_resume = json.loads(missing_resume_output)
        self.assertEqual(
            missing_resume["hookSpecificOutput"]["permissionDecision"],
            "deny",
        )
        self.assertIn(
            "resume",
            missing_resume["hookSpecificOutput"]["permissionDecisionReason"],
        )
        self.assertEqual(
            resumed_output,
            "",
            "A resumed primary pass with a resume target must not consume a new slot.",
        )

    def test_hook_accepts_the_final_filter_as_a_resumed_primary_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            self.run_hook(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "deep-final-filter",
                    "prompt": "Review the broad change deeply.",
                },
                state_dir,
            )
            self.assertEqual(
                self.run_hook(
                    {
                        "hook_event_name": "PreToolUse",
                        "session_id": "deep-final-filter",
                        "tool_name": "Task",
                        "tool_input": {
                            "subagent_type": "review-worker",
                            "description": "[review:deep:primary] Initialize review",
                        },
                    },
                    state_dir,
                ),
                "",
            )
            output = self.run_hook(
                {
                    "hook_event_name": "PreToolUse",
                    "session_id": "deep-final-filter",
                    "tool_name": "Task",
                    "tool_input": {
                        "subagent_type": "review-worker",
                        "description": "[review:deep:resume] Run the final filter",
                        "resume": "primary-task-id",
                    },
                },
                state_dir,
            )
            state = load_review_state(
                review_state_path(state_dir, "deep-final-filter")
            )

        self.assertEqual(output, "")
        self.assertEqual(state["review_slots"], ["[review:deep:primary]"])

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

    def test_final_round_two_reserves_selected_security_after_primary_and_challenge(self):
        with tempfile.TemporaryDirectory() as directory:
            results = self.reserve_review_calls(
                Path(directory),
                (
                    "[review:final:1:primary] Review frozen head",
                    "[review:final:1:challenge] Challenge frozen head",
                    "[review:final:2:primary] Review corrected head",
                    "[review:final:2:challenge] Challenge corrected head",
                    (
                        "[review:final:2:security] [security:selected] "
                        "Review corrected security paths"
                    ),
                    "[review:standard] Start an unrelated review",
                ),
            )

        for result in results[:5]:
            self.assertIsNone(result)
        self.assertIsNotNone(results[5])

    def test_final_round_two_blocks_all_round_one_stages_but_preserves_round_two_completion(self):
        round_two_started = {
            "final_slots": [
                "[review:final:1:primary]",
                "[review:final:1:challenge]",
                "[review:final:1:security]",
                "[review:final:2:primary]",
            ]
        }
        for tag in (
            "[review:final:1:primary]",
            "[review:final:1:challenge]",
            "[review:final:1:security]",
            "[review:final:1:retry:primary]",
            "[review:final:1:retry:challenge]",
            "[review:final:1:retry:security]",
        ):
            with self.subTest(tag=tag):
                violation = review_task_violation(
                    f"{tag} Attempt a late round-one review",
                    state=round_two_started,
                )
                self.assertIsNotNone(violation)

        self.assertIsNone(
            review_task_violation(
                "[review:final:2:challenge] Complete the round-two challenge",
                state=round_two_started,
            )
        )
        self.assertIsNone(
            review_task_violation(
                "[review:final:2:security] [security:selected] "
                "Complete the selected round-two security review",
                state=round_two_started,
            )
        )
        self.assertIsNone(
            review_task_violation(
                "[review:final:2:security] [security:selected] "
                "Close the terminal final round",
                state={
                    "final_slots": [
                        "[review:final:1:primary]",
                        "[review:final:1:challenge]",
                        "[review:final:1:security]",
                        "[review:final:2:primary]",
                        "[review:final:2:challenge]",
                    ]
                },
            )
        )

    def test_hook_requires_selected_marker_for_every_budgeted_security_stage(self):
        descriptions = (
            "[review:standard:security] Review security paths",
            "[review:deep:security] Review security paths",
            "[review:final:1:security] Review security paths",
            "[review:final:2:security] Review security paths",
            "[review:standard:retry:security] Complete security evidence",
            "[review:deep:retry:security] Complete security evidence",
            "[review:final:1:retry:security] Complete security evidence",
        )
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            for index, description in enumerate(descriptions):
                with self.subTest(description=description):
                    session_id = f"security-marker-{index}"
                    self.run_hook(
                        {
                            "hook_event_name": "UserPromptSubmit",
                            "session_id": session_id,
                            "prompt": "Review and fix the change.",
                        },
                        state_dir,
                    )
                    output = self.run_hook(
                        {
                            "hook_event_name": "PreToolUse",
                            "session_id": session_id,
                            "tool_name": "Task",
                            "tool_input": {
                                "subagent_type": "security",
                                "description": description,
                            },
                        },
                        state_dir,
                    )

                    self.assertNotEqual(
                        output,
                        "",
                        "A budgeted security Task without [security:selected] "
                        "must receive a deny response.",
                    )
                    response = json.loads(output)
                    self.assertEqual(
                        response["hookSpecificOutput"]["permissionDecision"],
                        "deny",
                    )
                    self.assertIn(
                        "[security:selected]",
                        response["hookSpecificOutput"]["permissionDecisionReason"],
                    )

    def test_selected_security_passes_allow_one_evidence_completion_retry(self):
        selected_security_passes = (
            (
                "[review:standard:security] Review security paths",
                "[review:standard:retry:security] Complete missing evidence",
            ),
            (
                "[review:deep:security] Review security-sensitive paths",
                "[review:deep:retry:security] Complete missing evidence",
            ),
            (
                "[review:final:1:primary] Review frozen head",
                "[review:final:1:challenge] Challenge frozen head",
                "[review:final:1:security] Review security paths",
                (
                    "[review:final:1:retry:security] "
                    "Complete missing security evidence"
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            for index, descriptions in enumerate(selected_security_passes):
                with self.subTest(descriptions=descriptions):
                    test_state_dir = state_dir / str(index)
                    test_state_dir.mkdir()
                    results = self.reserve_review_calls(test_state_dir, descriptions)

                    for result in results:
                        self.assertIsNone(result)
                    self.assertIn(
                        "already used",
                        reserve_review_call(
                            state_dir=test_state_dir,
                            session_id="session-1",
                            description=descriptions[-1],
                        ),
                    )

    def test_primary_and_challenge_passes_allow_one_prerequisite_gated_retry(self):
        retry_cases = (
            (
                "[review:deep:primary] Review broad changes",
                "[review:deep:retry:primary] Complete primary evidence",
            ),
            (
                "[review:deep:challenge] Challenge broad changes",
                "[review:deep:retry:challenge] Complete challenge evidence",
            ),
            (
                "[review:final:1:primary] Review frozen head",
                "[review:final:1:retry:primary] Complete primary evidence",
            ),
            (
                "[review:final:1:challenge] Challenge frozen head",
                "[review:final:1:retry:challenge] Complete challenge evidence",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            for index, descriptions in enumerate(retry_cases):
                with self.subTest(descriptions=descriptions):
                    test_state_dir = state_dir / str(index)
                    test_state_dir.mkdir()
                    retry_without_initial = review_task_violation(
                        descriptions[1],
                        state={"final_slots": []},
                    )
                    self.assertIsNotNone(retry_without_initial)
                    if retry_without_initial is not None:
                        self.assertIn("Complete", retry_without_initial)

                    results = self.reserve_review_calls(
                        test_state_dir,
                        descriptions,
                    )
                    for result in results:
                        self.assertIsNone(result)
                    self.assertIn(
                        "already used",
                        reserve_review_call(
                            state_dir=test_state_dir,
                            session_id="session-1",
                            description=descriptions[-1],
                        ),
                    )

    def test_final_round_two_rejects_all_evidence_retries_as_decision_only(self):
        for tag in (
            "[review:final:2:retry:primary]",
            "[review:final:2:retry:challenge]",
            "[review:final:2:retry:security]",
        ):
            with self.subTest(tag=tag):
                violation = review_task_violation(
                    f"{tag} Complete missing final evidence",
                    state={
                        "final_slots": [
                            "[review:final:1:primary]",
                            "[review:final:1:challenge]",
                        ]
                    },
                )

                self.assertIsNotNone(violation)
                if violation is not None:
                    self.assertIn("decision-only", violation)

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

    def test_review_pr_makes_final_round_one_the_broad_mutating_review(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)final round 1.*independent broad mutating review.*without.*preliminary deep",
            "final round 1 is the independent broad mutating review without a preliminary deep pair",
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

    def test_review_pr_documents_every_allowed_review_budget_stage_tag(self):
        policy = self.policy_text("plugins/review/skills/review-pr/SKILL.md")
        for stage_tag in (
            "[review:standard]",
            "[review:standard:security]",
            "[review:standard:retry]",
            "[review:deep:primary]",
            "[review:deep:challenge]",
            "[review:deep:security]",
            "[review:deep:retry:primary]",
            "[review:deep:retry:challenge]",
            "[review:final:<round>:primary]",
            "[review:final:<round>:challenge]",
            "[review:final:<round>:security]",
            "[review:final:1:retry:primary]",
            "[review:final:1:retry:challenge]",
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

    def test_review_pr_documents_bounded_security_evidence_retries(self):
        policy = self.policy_text("plugins/review/skills/review-pr/SKILL.md")
        self.assertIn(
            "[security:selected]",
            policy,
            "review-pr must mark selected final-round security before reserving it.",
        )
        for stage_tag in (
            "[review:standard:retry:security]",
            "[review:deep:retry:security]",
            "[review:final:1:retry:security]",
        ):
            with self.subTest(stage_tag=stage_tag):
                self.assertIn(
                    stage_tag,
                    policy,
                    msg=(
                        "review-pr must document the one evidence-completion retry "
                        "for each selected security pass."
                    ),
                )
        self.assertNotIn(
            "[review:final:2:retry:security]",
            policy,
            "Final round two is decision-only and must not permit a retry.",
        )

    def test_review_pr_requires_selected_marker_for_every_budgeted_security_task(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/SKILL.md",
            r"(?is)every budgeted security Task.*\[security:selected\].*"
            r":security",
            "every budgeted security Task pairs [security:selected] with its :security stage tag",
        )

    def test_documented_security_task_templates_include_selected_marker(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/deep-review.md",
            r'(?is)Task\(\s*subagent_type:\s*"security",\s*'
            r'description:\s*"\[review:standard:security\]\s+\[security:selected\]',
            "documented security Task templates include [security:selected] after the stage tag",
        )

    def test_deep_review_tags_light_tier_security_with_standard_security_stage(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/deep-review.md",
            r'(?is)Task\(\s*subagent_type:\s*"security",\s*'
            r'description:\s*"\[review:standard:security\]',
            "light-tier security launches with the standard security stage tag",
        )

    def test_deep_review_security_task_uses_selected_deep_security_stage(self):
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/deep-review.md",
            r'(?is)Task\(\s*subagent_type:\s*"security",\s*'
            r'description:\s*"\[review:deep:security\]\s+\[security:selected\]',
            "the deep security Task uses the selected deep security stage tag",
        )

    def test_deep_review_documents_tagged_worker_primary_and_challenge_tasks(self):
        for stage_tag, pattern in (
            (
                "[review:deep:primary]",
                r'(?is)Task\(\s*subagent_type:\s*"review-worker",\s*'
                r'description:\s*"\[review:deep:primary\]',
            ),
            (
                "[review:deep:retry:primary]",
                r'(?is)Task\(\s*subagent_type:\s*"review-worker",\s*'
                r'description:\s*"\[review:deep:retry:primary\]',
            ),
            (
                "[review:deep:challenge]",
                r'(?is)Task\(\s*subagent_type:\s*"review-worker",\s*'
                r'description:\s*"\[review:deep:challenge\]',
            ),
            (
                "[review:deep:retry:challenge]",
                r'(?is)Task\(\s*subagent_type:\s*"review-worker",\s*'
                r'description:\s*"\[review:deep:retry:challenge\]',
            ),
        ):
            with self.subTest(stage_tag=stage_tag):
                self.assert_policy_matches(
                    "plugins/review/skills/review-pr/deep-review.md",
                    pattern,
                    f"deep review documents a tagged review-worker {stage_tag} Task",
                )

    def test_deep_review_documents_the_strict_worker_lifecycle(self):
        policy = self.policy_text("plugins/review/skills/review-pr/deep-review.md")
        stages = re.findall(
            r'(?is)Task\(\s*subagent_type:\s*"review-worker",\s*'
            r'description:\s*"\[review:deep:([^\]]+)\]',
            policy,
        )
        self.assertEqual(
            stages.count("discovery"),
            1,
            "Deep review must reserve exactly one discovery Task lifecycle stage.",
        )
        self.assertIn(
            "resume",
            stages,
            "Resumed primary passes and the final filter must use the resume stage.",
        )
        for stage in stages:
            with self.subTest(stage=stage):
                self.assertIn(
                    stage,
                    {
                        "discovery",
                        "primary",
                        "retry:primary",
                        "challenge",
                        "retry:challenge",
                        "resume",
                    },
                    "Every review-worker Task must use a strict deep lifecycle stage.",
                )
        self.assert_policy_matches(
            "plugins/review/skills/review-pr/deep-review.md",
            r'(?is)Final filter.*?Task\(\s*subagent_type:\s*"review-worker",\s*'
            r'description:\s*"\[review:deep:resume\].*?resume:\s*<REVIEW_TASK_ID>',
            "the final filter resumes the primary Task with the deep resume stage",
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
