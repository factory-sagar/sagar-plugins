# Existing Comment Procedure

Use this procedure only in comments mode or a stronger authorized mode.

1. Fetch every existing review thread, including resolution state. Resolution state, threaded
   replies, and thread resolution all need the API calls in
   [`pr-mechanics.md`](./pr-mechanics.md); REST alone cannot answer them.
2. Triage each thread as valid or not against the current code and intended scope.
3. Fix valid in-scope comments. A valid defect with only scope-expanding remedies stops for a
   user decision rather than authorizing the remedy.
4. Reply to every thread, including the reason for each declined comment, and resolve every
   thread that is resolvable.
5. Run applicable validation, push the resulting commits, and watch required CI to green.

Follow `SKILL.md` for authority, approval, and landing gates.
