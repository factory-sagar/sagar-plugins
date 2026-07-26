# Landing decision

**Mode:** `land`  
**Tier:** deep, this is a broad, high-consequence PR.

With all merge gates satisfied and the final, immediately preceding live-head check confirming:

```text
reviewedHeadSha == headRefOid == <reviewed-head-sha>
```

the next and only operation is to **merge the PR**. Do not make any intervening tool or API call, and do not submit an approval because approval was not authorized. This is describe-only because GitHub is unavailable.

# If the live head is `<changed-head-sha>`

**Block the merge.** A different live head invalidates continuity with the reviewed commit.

Required recovery steps:

1. Synchronize the local PR branch with `<changed-head-sha>`.
2. Rerun applicable local verification.
3. Commit a new corrective commit only if needed, never create an empty commit.
4. Run one fresh delta `change-review` over `<reviewed-head-sha>...HEAD`, with the complete base-to-head diff as context. Include security review if the changed paths require it.
5. If clean, record the resulting committed SHA as the new `reviewedHeadSha`, push without rewriting history, and wait for required CI to pass for that exact head.
6. Reconfirm the PR body and zero unresolved review threads.
7. As the final API call immediately before merge, re-fetch `headRefOid` and require equality with the new `reviewedHeadSha`.
8. Only if that comparison passes, make merge the next operation.

The delta loop remains limited to three passes; exhaustion or a repeated root cause blocks landing.
