# GitHub PR Review Dispatcher v1.1.2 — CI producer provenance, adapter and rollout decision

Status: design complete; implementation and activation remain disabled pending independent review.

## Decision

Adopt `github-pr-review-dispatcher/v1.1.2` as the sole dispatcher contract and publish `github-hermes-development-workflow` v5.1.1 as its operator/agent workflow. The contract owns the machine protocol; the skill explains how a development agent uses it. In conflicts, the contract wins. This is a linear fail-closed correction of immutable v1.1.1 commit `2e6999f945836b4fe43e5127d3068222e297c6eb`; its ref is historical and remains unmoved.

The dispatcher extends existing Hermes project and Kanban persistence. It does not introduce a core model tool, plugin, webhook controller, alternate task lifecycle, or agentic cron job. A config-gated gateway watcher and manual `hermes kanban pr-review poll` adapter call the same deterministic domain API.

## Resolved v5-to-v1.1.2 discrepancies

| Topic | Workflow-v5/v1.1.1 statement or ambiguity | v1.1.2 resolution |
|---|---|---|
| Public gate vocabulary | v5 exposed `PASS|FAIL|NOT_RUN|BLOCKED` | Those remain check/engine values. Public results are only `APPROVED|CHANGES_REQUIRED|BLOCKED|FAILED`. `NOT_RUN` is never positive; engine `PASS` maps to `APPROVED` only after final revalidation. |
| Request body | v5 showed a flat named-field block | Schema 1 is exactly one stable marker plus one `json` fence containing the specified object. The flat block is legacy/human documentation and is never auto-accepted. |
| Base identity | v5 could be read as PR `base.sha` | `base_sha` is the current tip from a fresh explicit read of the GitHub-reported base ref. Historical PR `.base.sha`, merge-base and local tracking refs are forbidden sources. |
| Ref comparison | v5 did not settle Unicode/case behavior | Repository names and SHAs use specified lowercase canonicalization; `base_ref` and `head_ref` are exact GitHub UTF-8 codepoint/byte identity. Syntax may be rejected, never normalized, folded, trimmed or repaired. |
| Remediation eligibility | v5 described ten aggregates | Twelve independent booleans are authoritative. The ten aggregates are deprecated diagnostics and cannot authorize work. |
| Admission lifecycle | an earlier design used native `admission_pending` and created a task before final revalidation | Pre-task admission exists only in `pr_review_cycles`. Label reconciliation is followed by Read C. A regular native task is created once only after Read C and binding revalidation, then read back before success is recorded. Native Kanban statuses are unchanged. |
| Poller identity choice | v5 named reviewer/worker roles but did not define adapter ownership | The poller resolves repository → project → board → configured orchestration only. It forwards the bound orchestration profile as intake assignee and never selects a global orchestrator, reviewer, worker, provider or model. |
| Native scheduler impact | a global guard could have serialized native dispatch | Only review-specific binding/CAS guards are added. Existing native decomposition, dependency, readiness, dispatch, retry, review, failure and escalation semantics stay unchanged. |
| Processed point | label removal or cycle persistence could appear sufficient | A request is processed only after one native task is committed and its exact fields are read back. Crash/retry reconciles the same review key and task. |
| Required-CI producer | v1.1.1 required a “trusted producer” but defined no authority, comparison or durable evidence | Only an authoritative applicable GitHub policy that yields exact `(context_name, github_app, producer_app_id)` tuples is supported. Exact producer-bound Check Run plus fresh Check Suite identity is required; name/status alone and Commit Statuses never satisfy the gate. |
| Policy/observation drift | v1.1.1 re-read “required checks” without canonical identities | Canonical policy and observation preimages/digests plus source, producer, Run and Suite identities are persisted and re-read at Read D and Read E. Any change is lifecycle `STALE`. |
| Unsupported policy | legacy contexts, required workflows, overlapping rules or absent requirements could be interpreted heuristically | Context-only/null/`-1` producer, required-workflow identity, conflicts, empty requirements, incomplete pagination and unreadable permissions are `BLOCKED`; no name/default inference exists. |

## Dependency and ownership boundaries

- `hermes_cli/pr_review_dispatcher.py`: protocol, parser, exact key, ports, revalidation and review-specific state machines.
- `hermes_cli/projects_db.py`: repository binding and monotonic binding revision API.
- `hermes_cli/kanban_db.py`: additive review-cycle/TODO persistence and connection-scoped exactly-once task materialization.
- `gateway/kanban_watchers.py`: config-gated five-minute scheduling only.
- `hermes_cli/kanban.py`: manual adapter to the same domain call.
- GitHub transport: reads/writes GitHub only and has no project/board/model policy. It exposes explicit paginated Policy, Check Suite and Check Run GET operations and returns status/ETag/request identity without interpreting trust.
- Existing Kanban dispatcher: remains the only owner of native task scheduling after materialization.

Dependency direction is adapter → dispatcher domain → narrow GitHub/project/board ports. The domain module imports no gateway classes and chooses no agent/model identity.

## CI policy and observation decision

Positive evaluation supports only producer-bound status-check policy from two authoritative current-Base-Ref surfaces: active rules from `GET /repos/{owner}/{repo}/rules/branches/{base_ref}` with `required_status_checks[].integration_id`, and readable classic Branch Protection with `required_status_checks.checks[].app_id`. Both are explicit versioned GETs; list responses are fully paginated. Identical tuples may be unioned while retaining every source. Conflicting App IDs for a context, legacy `contexts`, null/`-1` producer, required-workflow rule, no requirements, unknown CI-affecting rule, partial/inaccessible policy or ambiguous Branch-Protection 404 are `BLOCKED`. A Branch-Protection 404 is absence only with separately proven repository Administration read/admin capability; otherwise the operator must grant the dedicated credential read access to Administration/Rulesets and Checks/Contents/Metadata, including applicable organization/enterprise policy, then retry.

For every tuple, enumerate Check Suites for the exact candidate SHA, GET every returned Suite by ID without App/name prefilter, and enumerate every Suite's Check Runs with `filter=all`. PASS requires exactly one Run with exact name and numeric App ID, matching Suite ID, Run and Suite heads equal to the candidate, `completed/success`, and valid `completed_at`. Commit Statuses, latest-wins, same-name wrong App, duplicate, producer rotation, absent/malformed App/Suite/Head, wrong head, pending or any non-success conclusion cannot pass. Trusted readable negative/spoofed evidence maps to `FAIL`/terminal `FAILED`; unreadable or unsupported authority maps to `BLOCKED`; absent is `MISSING`; nonterminal is `PENDING`.

Policy evidence stores source kind/id/API identity, base ref/tip, retrieval time/ETag, tuples, canonical JSON and SHA-256 digest. Observation evidence stores context, expected App ID, Run/Suite IDs, observed App/name/Run head/Suite head/status/conclusion/completed-at/details URL, separate Run/Suite retrieval time/ETag, canonical JSON and digest. Volatile retrieval/transport metadata remains audit evidence but is excluded from digest preimages. Read D and Read E append snapshots and repeat all reads. Any content digest or authority identity drift is lifecycle `STALE`, without rewriting historical gate evidence.

Negative acceptance is explicit: same-name spoofed producer, missing/changed App ID, duplicate trusted match, legacy context-only rule, conflicting/changed overlapping rules, no required checks, inaccessible or partially paginated policy, unsupported required workflow, missing Suite/Head, wrong Head, missing Run, pending/queued/in-progress/waiting/requested, skipped/neutral/cancelled/timed-out/action-required/stale/failure, Commit-Status-only and policy/observation drift separately at Read D and Read E must all remain non-PASS with the exact `FAILED|BLOCKED|PENDING|MISSING|STALE` mapping above.

Official GitHub REST documentation confirms these exact response fields and the direct commit Check Runs endpoint's 1000-suite limit/default latest filtering. Live `gh api` reads on 2026-09-16 confirmed Ruleset source/id plus `context/integration_id`, and Check Suite/Run `id`, `app.id`, `head_sha`, status, conclusion, completed-at and details URL. Repository adapter `hermes_cli/kanban_pr_acceptance.py` already provides `_api()`/`collect_acceptance()`, including pagination, percent-encoded Rules-Branch and GraphQL Branch Protection; its gate semantics are intentionally insufficient here because it permits null/`-1` App IDs plus Commit Statuses, uses `filter=latest`, does not GET Suite `head_sha`, and does not reject every duplicate/spoof. Implementation may share/refactor its transport but must not consume its current `ok` as v1.1.2 evidence, and must add the narrow operations above rather than use `gh pr checks`, `statusCheckRollup` or inferred fields.

## Migration and activation sequence

1. Land additive project and board schema migrations with the dispatcher disabled by default.
2. Add repository binding management and reject ambiguous/missing bindings. Do not create inferred bindings.
3. Add strict Schema 1 parser/key tests, A/B/C/D/E drift tests, producer-policy/Check-Suite provenance negative tests, profile A→B→A tests, concurrency/crash tests and unchanged-native-lifecycle integration tests.
4. Add manual dry-run. Dry-run performs all reads/validation and zero durable or external writes.
5. Run independent architecture, implementation, security/red-team and QA review against one immutable candidate.
6. Publish a release manifest binding the full commit SHA, durable non-default ref `refs/heads/contracts/github-pr-review-dispatcher-v1.1.2-from-2e6999f`, contract path/blob SHA-256, skill path/blob SHA-256 and this v1.1.2 decision-note path/blob SHA-256.
7. Install the reviewed skill into every intended runtime profile from the immutable commit URL, verify it is enabled there, and start a new session. Installing a repository file alone does not activate it.
8. Enable manual polling first, inspect audit events, then explicitly enable the gateway watcher for selected bindings. Rollback disables the watcher/manual trigger; additive historical evidence remains.

No existing native task status or row is rewritten. Unknown/malformed legacy request formats remain blocked until explicitly migrated to Schema 1.

## Exact runtime installation plan

The release reviewer supplies these immutable manifest values after publication:

- `RELEASE_COMMIT`: full 40-hex commit on the reviewed fork.
- `SKILL_SHA256`: SHA-256 of `docs/kanban/github-hermes-development-workflow-SKILL-v5.1.md` version `5.1.1` at that commit.
- `TARGET_PROFILE`: one member of this reviewed installation set: `agency-software-architect`, `agency-automation-engineer`, `agency-code-reviewer`, `agency-security-reviewer`, `agency-qa-automation-engineer`, `agency-technical-lead`. There is no implicit global profile inheritance. `agency-orchestrator` is explicitly excluded while its session is running.

Before each write, prove the target profile exists, has no active Kanban run, and inventory any existing `github-hermes-development-workflow` installation. If a target is active or the supported profile selector fails, stop `BLOCKED`. For each eligible target profile, run from a trusted shell:

```bash
RELEASE_COMMIT='<manifest full 40-hex commit>'
TARGET_PROFILE='<explicit profile name>'
SKILL_URL="https://raw.githubusercontent.com/Mateo817/hermes-agent/${RELEASE_COMMIT}/docs/kanban/github-hermes-development-workflow-SKILL-v5.1.md"

curl --fail --silent --show-error --location "$SKILL_URL" --output /tmp/github-hermes-development-workflow-SKILL-v5.1.md
printf '%s  %s\n' '<manifest SKILL_SHA256>' /tmp/github-hermes-development-workflow-SKILL-v5.1.md | sha256sum --check --strict
hermes -p "$TARGET_PROFILE" skills inspect "$SKILL_URL"  # immutable URL preview; expect Trust: community, not PASS
hermes -p "$TARGET_PROFILE" skills install "$SKILL_URL" --yes
hermes -p "$TARGET_PROFILE" skills list --enabled-only
```

`skills inspect` is immutable-URL preview and trust display only; `Trust: community` is expected and is neither PASS nor a security scan. The actual no-force `skills install` performs quarantine/security scanning. Any scan or quarantine rejection stops `BLOCKED`; it must not be bypassed with `--force`. After success, read the installed file bytes from the exact profile's resolved skill home, recompute SHA-256, and verify `github-hermes-development-workflow` version `5.1.1` enabled for that profile; command success or list output alone is insufficient. Verify no unrelated profile/skill file changed. Delete the temporary download after verification. Because session prompt state is cached, installation takes effect in a new/reset session; the CLI install subcommand has no `--now` option. Rollback for a newly installed copy is `hermes -p "$TARGET_PROFILE" skills uninstall github-hermes-development-workflow --yes`, followed by the same listing/readback; a pre-existing version is restored from the pre-write backup using supported tooling rather than overwritten heuristically.

Repeat for all six listed profiles and report per-profile `PASS|FAIL|BLOCKED`. For the current project, the verified mapping is project `p_41500605` (`hermes-agent-workflow`) → board `hermes-system`; the project state is owned by profile `agency-orchestrator`. This mapping is deployment evidence, not a hard-coded dispatcher fallback, and does not authorize mutation of the running orchestrator profile.

## Rollback

Disable the watcher/trigger and stop new admissions. Preserve request comments, cycle rows, attempts, tasks, results and audit evidence. Do not delete or rewrite old reviews. An already-created native task remains governed by native Kanban lifecycle. Re-enablement requires revalidation of bindings, current GitHub identities and required checks.
