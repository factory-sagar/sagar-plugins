# Golden Task 11: Review-PR Comment Triage

Version: 2

## Target

`review-pr`.

## Prompt

```text
You are running the comment-triage step of review-pr. GitHub is unreachable in this
environment, so do not attempt gh calls: produce (1) the triage table, (2) the exact fix
you would apply for each comment you accept, and (3) a reply draft for every comment.

PR context: the diff registers a new GET /attempts route before /:id, adds
attempts-route-shadowing.test.ts asserting the route resolves, and changes the handler to
return 404 (previously 200 with an empty body) when the subscription does not exist —
update-subscription-404.test.ts added in this PR asserts the 404.

Comment 1 (factory-droid[bot], P1, has a ```suggestion block):
"Clamp /attempts limit to a safe integer range. User-controlled `limit` is passed straight
into Firestore .limit(), so limit=-1 or limit=1.5 can throw (500) and large values drive
expensive reads."
suggestion block:
  const normalizedLimit = Math.min(Math.max(Math.trunc(limit), 1), 200);
  const attempts = await subscriptions.listNotificationAttempts(
    subscriptionId,
    subscriptionId ? undefined : user.id,
    normalizedLimit,
  );

Comment 2 (code-review bot, P2):
"Regression: this endpoint previously returned 200 with an empty body for a missing
subscription; it now returns 404. Restore the 200 behavior to avoid breaking clients."

Comment 3 (human reviewer):
"Should /attempts also be visible to org admins who don't own the subscription, or is
owner-only intentional here?"
```

## Intent

The run exists to give the PR operator a per-comment, evidence-backed triage that applies the
safe integer clamp, preserves the intentionally test-enforced 404, and leaves the owner-only
authorization question for an owner decision. Success means all three comments receive their
correct classification, an exact accepted fix where applicable, and a reply draft explaining the
outcome; correct handling of Comments 1 and 2 with a weak Comment 3 reply or classification is
partial achievement, while reverting the 404, widening authorization, or omitting a reply misses
the point entirely.

## Fulfillment

- Classifies Comment 1 as a real bug and adopts the clamp (the suggestion block or an equivalent 1..200 integer clamp).
- Classifies Comment 2 as a false positive because the new 404 is asserted by a test added in this PR; the reply draft cites that test as evidence.
- Classifies Comment 3 as a question/product decision, answers or defers it to the owner, and does NOT change authorization behavior.
- Produces a reply draft for every comment, each stating what was done and why.
- Triage reasoning is per-comment (real bug / valid improvement / false positive / question), not a blanket "applied all suggestions".

## Boundaries

- Blindly apply Comment 2's requested revert (it would break the new test).
- Widen authorization in response to Comment 3 without an owner decision.
- Attempt gh/network calls after being told GitHub is unreachable.

## Score

- Derived, not judged: a wrong-target run or any violated boundary → `fail`; intent `missed` → `fail`.
- Intent `partially achieved` with no violation → `partial`.
- Intent `achieved` with no violation → `pass`.
