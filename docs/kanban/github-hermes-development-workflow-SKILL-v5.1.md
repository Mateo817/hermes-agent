---
name: github-hermes-development-workflow
description: Gate GitHub changes through revision-bound Hermes review.
version: 5.1.1
author: Mateo (Mateo817), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, development, pull-requests, review, kanban]
    related_skills: [github, requesting-code-review]
---

# GitHub/Hermes Development Workflow

Use this workflow for repository changes that must pass an independent, revision-bound Hermes review before integration. GitHub is source of truth for code identity; Hermes is source of truth for review orchestration and gate evidence. This skill never authorizes merge, deployment, self-approval, privileged execution of untrusted code, or production activation.

## When to Use

- Features, fixes, refactors, architecture, tests, CI, documentation, or maintenance delivered through a pull request.
- Follow-up development after `CHANGES_REQUIRED`, `BLOCKED`, or `STALE` evidence.
- Bounded technical remediation delegated by Hermes after every eligibility condition passes.

Do not use this workflow to bypass project rules, repair an ambiguous request heuristically, merge automatically, or reinterpret a negative historical gate as approval.

## Prerequisites

- Read repository rules (`AGENTS.md`, `CONTRIBUTING.md`, README, ADR and PR conventions) before writes.
- Use the authenticated GitHub CLI through `terminal`; verify repository identity, permissions, fork ownership and write authority without printing credentials.
- Work in a clean, task-owned development worktree and non-default branch.
- Resolve exactly one configured repository → Hermes project → Kanban board → orchestration binding. No current/default/last-board, `hermes-system`, profile, reviewer, worker, provider, or model fallback.
- Treat the architecture contract `github-pr-review-dispatcher/v1.1.2` as normative for Schema 1 transport and adapters.
- Run Python tests through `scripts/run_tests.sh`, never direct `pytest`.

## How to Run

Load this skill for the development session, then follow the procedure in order. Use `terminal` for authenticated `gh`, Git and repository-native test commands; use `read_file` and `search_files` for source discovery and `patch` or `write_file` for scoped edits. Do not hand work to the dispatcher until the request and fresh GitHub identity satisfy Schema 1.

## Quick Reference

- Request wire: one stable marker plus one `json` fence.
- Review key: eight ordered fields, seven LF bytes, UTF-8, SHA-256.
- Public gate: `APPROVED|CHANGES_REQUIRED|BLOCKED|FAILED`.
- Admission: review cycle → label reconciliation → Read C → one native task → exact readback.
- Required CI: authoritative Base-Ref policy → exact context + GitHub App ID → exact Head suite/run → canonical digests.
- Remediation: all twelve conditions, branch CAS, new key and independent re-review.
- Integration: separate authority; this workflow never auto-merges.

## Status Domains

Keep these domains separate:

- Check state: `PASS|FAIL|NOT_RUN|BLOCKED`.
- Public gate: `APPROVED|CHANGES_REQUIRED|BLOCKED|FAILED`.
- Lifecycle includes `REQUESTED`, `IN_PROGRESS`, `REMEDIATION_REQUIRED`, `REMEDIATION_IN_PROGRESS`, `STALE`, and `COMPLETED`.

`NOT_RUN` is never a positive public gate. Internal engine `PASS` becomes public `APPROVED` only in the result adapter after all independent reviews, required CI and final revalidation pass. `STALE` is lifecycle, not gate. Native Kanban `done` is not approval.

## Procedure

### 1. Establish the exact repository state

Use `terminal` to read the canonical repository, default branch, relevant implementation, tests, CI, open PRs, fork relation, permissions and current remote refs. Before each write, re-check branch ownership and cleanliness.

Classify the change as `feature|fix|refactor|architecture|test|ci|docs|maintenance`. Record scope and out-of-scope work. Never invent an API, parameter, path or permission.

Completion criterion: the base repository/ref, head repository/ref, current base tip, current head SHA, branch authority, change type and project rules are explicit and freshly evidenced.

### 2. Implement only on a development branch

Never write to the default, base, protected integration, or release branch. Preserve unrelated changes. Do not force-push, rewrite shared history, merge, or weaken CI/review gates without separate authorization.

Run the repository-prescribed tests. Record every relevant check as `PASS`, `FAIL`, `NOT_RUN`, or `BLOCKED` with the exact commit and reason. Empty, missing, queued, pending, skipped, unreadable or stale-head checks are not `PASS`.

Completion criterion: implementation and tests are bound to one full head SHA on a durable non-default ref.

### 3. Create or update the pull request

The PR body is the human handoff and contains:

- Objective
- Scope and Out of Scope
- Change Type
- Implementation and Components
- Architecture decision where relevant
- Acceptance Criteria
- Tests with check states
- Compatibility/migration
- Known Risks and Open Points
- `Independent Hermes review required before integration.`

The PR remains an implementation proposal until the exact current review key has a public `APPROVED` result. No direct merge follows from creating or updating the PR.

Completion criterion: the open, unmerged PR body fully describes the exact head candidate.

### 4. Read canonical GitHub identity

Read from GitHub, not from historical handoff text:

1. Base repository `nameWithOwner`.
2. PR number.
3. Base ref exactly as returned by GitHub.
4. Current base tip from a fresh, explicit read of that base ref. Do not use historical PR `.base.sha`, merge-base, a local tracking ref, or default-branch tip when the PR targets another ref.
5. Head repository `nameWithOwner`.
6. Head ref exactly as returned by GitHub.
7. Current full PR head SHA.

Ref identity is exact UTF-8 codepoint/byte identity from GitHub. Validate syntax without case folding, Unicode normalization, trimming, or rewriting. Reject control characters, invalid Git ref syntax, transformation-dependent validity, or ambiguity.

Completion criterion: all seven GitHub values are fresh and exact; the base tip came from its own base-ref read.

### 5. Compute Review-Key Schema 1

Canonical fields, in order:

1. ASCII `1`
2. base repository lowercase
3. positive decimal PR number
4. exact base ref
5. full lowercase base-tip SHA
6. head repository lowercase
7. exact head ref
8. full lowercase head SHA

Join with exactly seven ASCII LF bytes, no trailing LF, encode UTF-8, and compute lowercase SHA-256 hex. The comment's key is a comparison value, never a trust anchor.

Completion criterion: escaped preimage and independently recomputable 64-character key are recorded without transforming either ref.

### 6. Maintain one canonical Schema 1 request

Each PR has one stable request comment ID. Machine wire format is exactly:

    <!-- hermes-review-request -->
    ```json
    {
      "schema_version": 1,
      "review_key": "<sha256>",
      "repository": "owner/repository",
      "pr_number": 123,
      "base_ref": "<exact-ref>",
      "base_sha": "<fresh-base-tip>",
      "head_repository": "owner/repository",
      "head_ref": "<exact-ref>",
      "head_sha": "<head-sha>",
      "requested_at": "<RFC3339 UTC>",
      "handoff": {
        "summary": "<non-empty summary>",
        "changed_files": ["<repo-relative path>"],
        "test_commands": ["<command>"],
        "known_risks": ["<risk>"]
      }
    }
    ```

Except whitespace, no prose or second block may appear. The flat named-field example from skill v5 is human/legacy documentation only; never auto-accept it as Schema 1. An incompatible format requires a new schema version, staged migration and independent review.

Persist `review_request_comment_id`. Update that exact comment for a new cycle. Zero markers, multiple markers, a stored ID pointing to the wrong marker, or ID/marker ambiguity is `BLOCKED`; never choose the newest comment or silently delete conflicts.

Completion criterion: one stable comment ID contains the exact JSON-fence request and every asserted identity matches fresh GitHub reads and the recomputed key.

### 7. Revalidate before triggering

Use Read → Compute → Write → Revalidate. Immediately before adding `hermes-review-requested`, re-read open/unmerged/draft state, exact base/head identities, current base tip, comment ID/body hash, key, binding and trigger state. Any drift makes the old cycle `STALE` and requires a new request/key.

Completion criterion: PR, request, key, binding and label preconditions match one snapshot immediately before the trigger write.

### 8. Admit without changing native Kanban lifecycle

The deterministic poller may resolve only repository → project → board → configured orchestration. It must not choose a global orchestrator, reviewer, worker, provider or model.

Before final admission, persist only review-cycle state. Do not create a native task and do not add a native `admission_pending` status. After label reconciliation, perform Read C against PR/head/base-tip/request/label/binding. Only after Read C and binding revalidation may one regular native task be created with the exact configured orchestration route and a unique review-key idempotency key.

Read the created task back and verify ID, status, assignee, project, body key, binding fingerprint and idempotency key. Do not mark the request processed before this readback. Crash/retry reconciles the same cycle and exact task; it never suffixes a key, deletes/recreates the cycle, or creates a second task.

After materialization, native Hermes decomposition, dependencies, readiness, dispatch, retry, review, failure handling and escalation remain unchanged. Do not add global native-dispatch guards or a competing controller.

Completion criterion: Read C passed, exactly one native task was created/read back, and no task existed before Read C.

### 9. Review and gate the exact candidate

Before review work, perform Read D. Before result/gate publication, perform Read E. Both re-read exact head, explicit base-ref tip, request/comment identity, label/binding and key. Drift preserves history, marks the old lifecycle `STALE`, and forbids approval of the current PR from old evidence.

Resolve required checks only from authoritative GitHub policy for the current base ref. Fully paginate explicit `GET /repos/{owner}/{repo}/rules/branches/{base_ref}` and applicable Branch Protection reads with an explicit supported API version. Every required check must yield exactly `(context_name, producer_kind=github_app, producer_app_id)` with a positive numeric App ID from Ruleset `integration_id` or Branch Protection `checks.app_id`. Legacy context-only policy, null/`-1` App ID, conflicting overlapping policies, no required checks, inaccessible/partial pagination or required-workflow identity are `BLOCKED`, never positive. Do not infer policy from names, statuses, comments, workflow output, handoff text, project similarity or defaults.

For the exact candidate head, fully paginate Check Suites, re-read every returned Suite by ID without prefiltering by App/name, and list every Suite's Check Runs with `filter=all`; this is required to detect a same-name spoof from another producer. Exactly one Run per policy tuple must have exact `name`, exact numeric `app.id`, matching Suite ID, Run and Suite `head_sha` equal to the candidate, `status=completed`, `conclusion=success` and valid `completed_at`. Commit Statuses never satisfy v1.1.2. Same-name wrong producer, producer change, duplicate match, missing App/Suite/Head fields, wrong head, skipped/neutral/cancelled/timed-out/action-required/stale/failure are `FAIL`/terminal `FAILED`; queued/in-progress/waiting/requested/pending are `PENDING`; absent Run is `MISSING`; unreadable or unsupported policy/observation is `BLOCKED`.

Persist policy source kind/id/API identity, base ref/tip, retrieval time/ETag, sorted producer tuples and canonical policy digest. Persist context, expected App ID, Run ID, Suite ID, observed App ID/name/Run head/Suite head/status/conclusion/completed-at/details URL, separate Run/Suite retrieval time/ETag and canonical observation digest. Retrieval/transport metadata is audited but excluded from canonical digest preimages, so a fresh content-identical read remains equal. Before review (Read D) and before result/gate (Read E), re-read policy and observations completely. Any source, digest, producer, Run, Suite or identity drift marks the cycle `STALE`; cached digests are not revalidation. If access is insufficient, report the exact operator action: grant the dedicated GitHub App/fine-grained token read access to repository Administration/Rulesets and Checks/Contents/Metadata, including applicable organization/enterprise rules, then rerun; never configure a guessed App ID.

Public result wire values are only `APPROVED|CHANGES_REQUIRED|BLOCKED|FAILED`. Result comments are append-only or otherwise revision-safe and include exact key/base/head, check states, findings, remediations, unresolved risks and generated timestamp. A result comment is a projection of durable review evidence, not independent authority.

Completion criterion: result is bound to the exact current key, uses the public vocabulary, and only publishes `APPROVED` after Read E and every gate succeeds.

### 10. Evaluate all twelve remediation conditions

Hermes may delegate a bounded technical remediation only when every condition is individually true and evidenced:

1. It fixes one concretely documented finding with unique finding ID, current source key and source head.
2. Existing PR scope is not expanded.
3. No new product requirement arises.
4. No new architecture decision is needed.
5. No public API or CLI materially changes.
6. No persisted schema or engineering IR materially changes.
7. No security, trust or permission boundary changes.
8. No new external integration is introduced.
9. Existing tests or complete acceptance criteria can verify the result.
10. The change occurs only on the existing PR head branch; no base/default/protected write, merge or history rewrite.
11. The branch is freshly proven writable and trusted, expected-head CAS and exclusive branch claim hold, and untrusted code gets no privileged secrets/runner.
12. The change is local and technically bounded; configured orchestration supplies a worker distinct from authorizing reviewers, and commit is followed by tests, audit handoff, fresh base/head reads, new key/request and independent re-review.

Old ten-flag aggregates are deprecated compatibility diagnostics only. They never authorize remediation. If any of the twelve is false or unknown, use normal development with `CHANGES_REQUIRED` or `BLOCKED`.

Completion criterion: twelve separate booleans plus evidence are persisted; all true is necessary but does not itself approve the result.

### 11. Serialize and audit any allowed remediation

Create one idempotent remediation TODO per `(source_review_key, finding_id)`. Include TODO/finding IDs, source key/head, goal, scope, components/files, acceptance, tests, existing PR branch, configured worker, workspace and expected head.

Serialize branch writes. Re-read expected remote head before commit and immediately before a fast-forward push. Never force-replace history. After push, read remote head, mark the old cycle stale, record changed files/commit/tests/worker, refresh base tip and head, compute a new key, update the stable request, revalidate, re-trigger and require an independent reviewer. Implementers and remediation workers cannot self-approve.

Completion criterion: audit links finding → TODO → worker → commit → new key → independent review, with no reused approval.

### 12. Integrate separately

`APPROVED` means only that one exact review key passed Hermes review. Immediately before any separately authorized merge, re-read the GitHub state, recompute the key, verify matching public approval, required CI, open findings and project governance. Key drift means no merge.

Completion criterion: integration, if separately authorized, uses the same still-current approved key and is not performed by this workflow automatically.

## Failure and Retry Rules

- Temporary GitHub, rate-limit, database-busy or uncertain-write errors do not consume the request. Keep durable attempt/backoff state and read before retry.
- Never mark processing successful until native task creation and exact readback commit.
- Stable comment ambiguity, malformed/unknown schema, binding ambiguity, stale snapshot, legacy/conflicting/empty/unreadable/unsupported CI policy, incomplete check pagination or invariant mismatch fail closed.
- Dry-run performs the same reads and validations but makes zero GitHub, database, task, lockfile, branch, workspace, configuration, worker or model writes.
- Logs exclude tokens, headers, cookies, secrets, raw private URLs and unredacted subprocess error bodies.

## Verification

Record exact commands, commit/ref and one of `PASS|FAIL|NOT_RUN|BLOCKED` for:

- Review-key golden cases, including case- and Unicode-distinct refs without transformation.
- Strict marker-plus-one-JSON-fence parser and rejection of the legacy flat block.
- Stable comment-ID conflicts and limits.
- Canonical binding with no default/global fallbacks.
- Pre-task admission, Read-C drift, concurrent pollers, crash boundaries and exactly-one materialization/readback.
- Unchanged native Kanban decomposition/dependency/dispatch/retry/escalation behavior.
- Public result mapping; `NOT_RUN` and internal `PASS` never leak as public gates.
- All twelve remediation conditions independently false and collectively true.
- Required-CI provenance: same-name spoof, missing/changed App ID, duplicate match, legacy context-only, conflicting/changed rules, no requirements, inaccessible/partial policy, unsupported workflow requirement, missing Suite/Head, wrong Head, absent/pending/skipped/neutral/failure and drift at both Read D/E boundaries; plus fork/untrusted safety and branch CAS.
- Profile A → B → A isolation and profile-scoped config/credentials.
- Real Windows-marked behavior on Windows and full E2E chains.
- `git diff --check`, repository checks and required CI.

Do not conclude `DONE`, `IMPLEMENTED`, or `APPROVED` from helper functions, a draft, smoke-only tests, native task `done`, or absent checks.

## Pitfalls

- PR `.base.sha` is historical request metadata, not the current base-ref tip.
- Unicode-normalizing a ref changes identity even when display text looks equivalent.
- A mutable result/comment cannot authorize itself; durable reviewed evidence and current key do.
- A commit containing this skill does not install or activate it. Runtime profiles have isolated skill homes and sessions cache loaded skills.
- `hermes skills inspect <immutable-url>` is only immutable-URL preview/trust evidence and may report `Trust: community`; it is not a PASS or security scan. Actual profile-scoped `hermes -p <profile> skills install <immutable-url> --yes` without `--force` performs quarantine/security scanning. A scan/quarantine verdict blocks installation, and success still requires reading back installed bytes/version/hash for that exact profile. Never use `--force` in the standard plan.
- The dispatcher remains disabled until implementation, independent reviews, required CI, dry-run and explicit operator activation all pass.
