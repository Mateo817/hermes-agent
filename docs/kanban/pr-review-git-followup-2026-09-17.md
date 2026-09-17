# Git follow-up: request preparation and remaining runtime blockers

Date: 2026-09-17. This is development evidence, not an independent Hermes gate.

## Scope and provenance

Inspected candidate: `ab8f1edc4918f53854a4d56b2ff6afca6706ced9` in `Mateo817/hermes-agent`.
Existing upstream PR: `NousResearch/hermes-agent#112832`.
Existing branch: `hermes-agent-workflow/t_763d130d-implementiere-und-publiziere-den-determi`.
Continue task `t_e24371b8` in project `p_41500605`, board `hermes-system`.
These task/profile values are operator handoff data, never generic runtime routing constants.
No merge, deployment, watcher activation, new Kanban root, or positive gate is authorized.

The uploaded progress excerpt is historical Kanban evidence. Its claimed blocked task status has not been reread from the local Hermes service in this environment. GitHub reads independently confirmed the published head. Older `PRODUCTION_DISPATCH_ABSENT` reports concern earlier candidates; the inspected candidate now has adapter code, but has the concrete integration defects below.

## Implemented in this follow-up

`hermes_cli/pr_review_request.py` is a read-only operator module. It reads the PR and current base tip through the existing `GitHubCLI`, pins the expected published head, uses the existing `compute_review_key` and `parse_request_comment`, then repeats identity and reviewability reads before returning a prepared request. Nonidentity `updated_at` changes do not alter the key. It never edits a comment, adds a label, opens a DB, dispatches a task, executes handoff commands, or approves code.

This fixes the absence of a reproducible request preparation path; it does NOT finish the dispatcher. A valid request is neither trusted CI evidence nor a successful review.

Two invariant tests (one parametrized over nine identity/reviewability changes) are added in `tests/hermes_cli/test_pr_review_request.py`. They use the real protocol functions with a read-only transport double. They are not GitHub/Kanban E2E tests.

## Historical request archive before replacement

Stable upstream comment ID: `5696001272`. Its previously retrieved machine payload was:

```json
{
  "schema_version": 1,
  "review_key": "dc373ea272ecdc594803096d2fac104735fc0b69acb489922c4f19f4cfe592e1",
  "repository": "NousResearch/hermes-agent",
  "pr_number": 112832,
  "base_ref": "main",
  "base_sha": "4716ec0ba4e212105f8f162c226f052b25f8a76b",
  "head_repository": "Mateo817/hermes-agent",
  "head_ref": "hermes-agent-workflow/t_763d130d-implementiere-und-publiziere-den-determi",
  "head_sha": "ab8f1edc4918f53854a4d56b2ff6afca6706ced9",
  "requested_at": "2026-09-16T22:55:00Z",
  "handoff": {
    "summary": "Fresh independent review requested for the assembled adapter-backed Schema-1 PR review dispatcher.",
    "changed_files": ["hermes_cli/pr_review_dispatcher.py", "hermes_cli/kanban.py", "gateway/kanban_watchers.py", "tests/hermes_cli/test_pr_review_dispatcher.py", "github-pr-review-dispatcher-implementation-report.md"],
    "test_commands": ["scripts/run_tests.sh tests/hermes_cli/test_pr_review_dispatcher.py", "python3 -m compileall -q hermes_cli/pr_review_dispatcher.py hermes_cli/kanban.py gateway/kanban_watchers.py", "git diff --check"],
    "known_risks": ["Live label/result publication and Windows runner evidence remain operator-gated; no merge or activation is authorized."]
  }
}
```

The canonical SHA-256 for those declared identity fields is actually `28d85239d8893850bbd81892b411bf4bad6e38175eaa2dd0e456d7c461f2c12a`. Thus the archived request is internally inconsistent even before live base drift. This archive is not a current request and must not be dispatched. Do not hard-code any base tip or new key from this report: obtain both after the final code commit.

## Remaining blockers in the inspected candidate

### GIT-F01: GitHub Checks response envelopes rejected

`GitHubCLI._pages` accepts only lists inside the outer `gh --paginate --slurp` list. `read_check_suites` and `read_check_runs` call it unchanged. GitHub's Checks endpoints return objects containing `total_count` and `check_suites` / `check_runs`, respectively. A real empty object response is therefore already rejected as invalid pagination; nonempty responses also fail. Read the documented envelope explicitly and reject malformed, duplicate or incomplete pages. Preserve Suite/Run/App/head identities for trust validation. Do not reinterpret malformed data as an empty successful result.

Live GET of upstream `commits/ab8f1edc4918f53854a4d56b2ff6afca6706ced9/check-suites` returned eight suites, including `completed/action_required` with zero latest check runs. This differs from a blanket assertion that no CI objects exist. It is still not a successful required-CI result.

### GIT-F02: Deployment identities hard-coded into generic routing

`_binding_for`, `HermesProjectBindingAdapter.resolve_repository`, task creation/readback and dispatch enforce `p_41500605` / `hermes-system`. The v1.1.3 decision explicitly calls those deployment evidence, not a runtime fallback. Resolve the enabled repository binding, active project, explicitly bound board metadata and orchestration profile instead. Missing, archived, mismatched or ambiguous authority must remain blocked. Prove a second unrelated project/board works without changing the module or leaking into the system board.

### GIT-F03: Undocumented third persistence authority and profile leak

`_dispatcher_state_db` reads process `os.environ` or `Path.home()/.hermes`; `_init_dispatcher_state` opens a new `kanban/github-pr-review-dispatcher.db` and creates a second `review_cycles` table. The contract locates admission/cycle evidence in the bound existing board DB and repository bindings in projects.db. Use those authorities and the established profile scope. Preserve any existing evidence; do not delete databases blindly. Cover A/B/A scope, concurrent intake and crash-after-native-commit reconciliation.

### GIT-F04: Native scheduler ownership violated

`dispatch_native_task(task_id, ...)` ignores the requested task identity and calls board-wide `dispatch_once(..., dry_run=False)`. That can select unrelated native work. The published v1.1.3 decision assigns scheduling exclusively to the existing native dispatcher. Materialize and verify exactly one native intake task, then let the normal native scheduler run it. Do not bolt on another dispatch/retry/decomposition loop. Confirm the real create/readback APIs, accepted initial states and return types with tests against actual temporary databases, not permissive mocks.

### GIT-F05: Admission/revalidation/recovery still incomplete

The inspected path reads the request only once, does not persist its stable comment identity in its private cycle table, lacks post-read binding authority locking, and may report an existing task as `DISPATCHED` merely because readback returns its ID. Label, request and policy/observation revalidation must occur at the specified boundaries; readback must validate every authoritative field. A stale owner must not publish success, and an error after task commit must not create another task or lose the request. Result/label reconciliation and twelve-condition remediation require real tests; function names and tables are not evidence of completeness.

### GIT-F06: Scope/config/CI prerequisites are separate operator blockers

The shared assembly currently builds adapters but does not enumerate repositories for the gateway's repository-less call; `list_candidates(None, ...)` refuses. Verify actual CLI and gateway assembly, config propagation, explicit repository enumeration, machine-wide exclusion, zero-write dry-run and graceful disable behavior. Independently verify CI policy access and trusted producer-bound results. An upstream label does not create or approve GitHub Actions runs. Do not mask code defects as missing permissions.

The inspected `kanban_db.py` still lists `admission_pending` as a native status, contrary to the newer decision's unchanged-native-status claim. Inventory that residue and resolve it against the accepted contract rather than adding another status.

## Reproduction / operator use

Environment: repository declares Hermes 0.21.3, Python >=3.11,<3.14. Use its existing lockfile/environment; no dependency or model change is included here. GitHub CLI must already be authenticated for read access. From the isolated candidate checkout:

```bash
python --version
gh --version
# TODO: create handoff.json with summary, changed_files, test_commands, known_risks.
# TODO: read the currently published full head into EXPECTED_HEAD; never guess it.
python -m hermes_cli.pr_review_request \
  --repository NousResearch/hermes-agent \
  --pr-number 112832 \
  --expected-head "$EXPECTED_HEAD" \
  --handoff handoff.json
scripts/run_tests.sh tests/hermes_cli/test_pr_review_request.py
scripts/run_tests.sh tests/hermes_cli/test_pr_review_dispatcher.py
git diff --check
```

The module prints a JSON plan to stdout; it does not publish it. Archive the existing stable request, edit only its known ID, fetch it again and run the same parser. Independently reread the PR head, fork ref and live base tip after the write. Drift means STALE, not a different hash patched into old evidence.

## Evidence limits

- PASS: syntax compilation of the new module/test in Python 3.13.5 on Linux.
- PASS: independent standard-library SHA-256 reconstruction of the archived request identity.
- NOT_RUN: new pytest tests through scripts/run_tests.sh, full Hermes suite, authenticated module CLI, real DB/native integration, race/crash tests, Windows and end-to-end review/remediation. A full checkout/test environment could not be acquired in this execution container (public GitHub hostname resolution failed); connector source reads are not a local runtime.
- BLOCKED: positive gate, activation and integration until the existing independent lanes verify the completed candidate.

## Continue the existing lineage

Use `t_e24371b8`; do not create a new triage root or restart old failed reviews. Retain independent reviews `t_ca7faaf6`, `t_bb16e4ef`, `t_1a02dd1b` and final gate `t_27a12d98`. Before writes, reread task/run/claim state locally and reconcile the external Git commit into the existing task-specific worktree without resetting unrelated work.

First run real adapter/native tests and fix GIT-F01..F06 through normal development. Keep external upstream label/CI rights separate from testable local work. A controlled fork integration test is evidence for its own repository/PR/key, never authorization for upstream #112832. Use no secrets or privileged runner for candidate code. After the final commit, regenerate and reread the stable request, obtain an explicit legitimate trigger, and run the independent reviews for exactly that head/base identity. Existing negative verdicts remain historical evidence. No automatic merge.

## Sources

- Candidate source: https://github.com/Mateo817/hermes-agent/blob/ab8f1edc4918f53854a4d56b2ff6afca6706ced9/hermes_cli/pr_review_dispatcher.py
- Accepted-design reference: https://github.com/Mateo817/hermes-agent/blob/ab8f1edc4918f53854a4d56b2ff6afca6706ced9/docs/kanban/github-pr-review-dispatcher-v1.1.3-decisions.md
- Request: https://github.com/NousResearch/hermes-agent/pull/112832#issuecomment-5696001272
- GitHub Checks: https://docs.github.com/en/rest/checks/suites and https://docs.github.com/en/rest/checks/runs
