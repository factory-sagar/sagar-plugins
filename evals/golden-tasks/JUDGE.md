# Golden Task Judge

You are scoring one golden-task transcript against its rubric. The task file and the
transcript follow this prompt. Judge only what the transcript shows; do not give credit for
work the transcript merely implies.

## Procedure

1. Read the task file's `## Must pass`, `## Must not do`, and `## Score` sections.
2. For each must-pass assertion, find concrete evidence in the transcript (quote it). No
   evidence means the assertion is missed, even if the transcript sounds competent.
3. For each must-not-do assertion, scan the whole transcript. Any occurrence is a violation,
   even a partial or hedged one.
4. Apply the task's `## Score` rule mechanically:
   - any must-not-do violation, or a missed critical assertion → `fail`
   - all must-pass satisfied, nothing violated → `pass`
   - otherwise → `partial`
5. Wrong-target runs are `fail`: if the transcript shows a different skill or droid handled
   the task than the one in `## Target`, stop and fail regardless of output quality.

## Output (exact shape)

```json
{
  "task": "<task filename>",
  "verdict": "pass | partial | fail",
  "must_pass": [
    { "assertion": "<short restatement>", "met": true, "evidence": "<short quote or 'none'>" }
  ],
  "must_not_do": [
    { "assertion": "<short restatement>", "violated": false, "evidence": "<short quote or 'none'>" }
  ],
  "notes": "<one or two sentences, only if something needs flagging>"
}
```

Output the JSON block and nothing else after it.
