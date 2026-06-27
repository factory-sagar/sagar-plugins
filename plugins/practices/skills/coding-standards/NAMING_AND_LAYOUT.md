# Naming and Layout

Use naming and layout to make intent obvious before a reader inspects implementation details. Local project conventions win when they are clear, consistent, and compatible with the standards.

## Naming

| Kind | Strong default | Prefer | Avoid |
| --- | --- | --- | --- |
| Variables | Descriptive nouns | `totalRevenue`, `pendingItems`, `apiKeyHash` | `x`, `data`, `result`, `obj` |
| Booleans | `is`, `has`, `should`, `can`, `did`, `will` prefix | `isAuthenticated`, `hasItems`, `shouldRetry` | `flag`, `auth`, `check`, `active` |
| Functions | Verb plus noun | `fetchUserProfile`, `validateEmail`, `parseSemver` | `process`, `handle`, `do`, `manage` |
| Classes and types | Domain noun | `User`, `OrderRepository`, `RateLimitDecision` | `Manager`, `Helper`, `Util`, `Processor` |
| Constants | Project convention, often screaming snake | `MAX_RETRIES`, `DEFAULT_TIMEOUT_MS` | `max`, `value`, `cfg` |
| Files | Match the dominant export or responsibility | `user-profile.tsx`, `order_repository.py`, `rate-limit.ts` | `index.ts`, `utils.py`, `helpers.js` |
| Tests | Mirror source plus test suffix | `rate-limit.test.ts`, `test_rate_limit.py` | `tests.ts`, `misc_spec.rb` |

Prefer names that describe what a thing does or owns, not where it sits in a vague architecture. `findUserByEmail` is usually clearer than `UserService`.

## File organization

- Organize by feature or domain when the codebase has that convention.
- Keep files cohesive. A file mixing unrelated features is several files waiting to happen.
- Prefer many focused modules to a few mega-files.
- Keep public entrypoints shallow and policy-bearing modules deep.
- Use barrel files only when they preserve a clear public surface.
- Generated and vendored code is exempt from naming and layout judgment, except for discovery and build integration.

## Comments

- Comments explain why, not what.
- Delete stale comments that merely restate code or contradict it.
- Add comments for non-obvious invariants, compatibility seams, and justified type or lint escape hatches.

## Review checklist

- Would a new reader understand each public name without opening three callers?
- Do booleans read clearly at call sites?
- Does each file have one dominant responsibility?
- Are generic helpers split into named modules when they own real policy?
- Are comments explaining constraints rather than paraphrasing code?
