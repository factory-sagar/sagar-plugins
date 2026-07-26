# PR Mechanics

Non-obvious API facts for operating on a pull request. Read this before verifying thread state,
replying, resolving, or gating on the live head.

## Thread resolution state is GraphQL-only

The REST API does not expose whether a review thread is resolved. `gh pr view --comments` cannot
answer it, so a gate that requires zero unresolved threads must query GraphQL:

```bash
gh api graphql -f query='
query {
  repository(owner: "<owner>", name: "<repo>") {
    pullRequest(number: <number>) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 1) { nodes { databaseId body } }
        }
      }
    }
  }
}'
```

A thread's `comments.nodes[].databaseId` equals the comment id returned by the REST API. That is
how you match a GraphQL thread to a REST inline comment.

## Replying to a thread needs the replies endpoint

`gh pr comment` posts a new top-level conversation comment, which does not reply in-thread and
leaves the thread unresolved:

```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments/<comment-id>/replies -f body='<reply>'
```

## Resolving a thread takes threadId

The mutation input field is `threadId`, not `thread_id` and not the comment id:

```bash
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "<thread-id>"}) {
    thread { id isResolved }
  }
}'
```

Resolve only threads you have replied to and that are not open questions.

## Live head and base state

The PR head SHA field is `headRefOid`:

```bash
gh pr view <url> --json number,title,author,headRefName,headRefOid,baseRefName,state,body
```

Behind and ahead counts against the live base:

```bash
git fetch origin <base-branch>
git rev-list --left-right --count origin/<base-branch>...HEAD
```
