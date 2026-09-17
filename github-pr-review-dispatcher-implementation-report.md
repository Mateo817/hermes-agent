# Adapter-backed PR dispatcher implementation report

Implementation commit: 6aa8da15dcc670df886fdeabbc8e5a634a224fa6
Implementation tree: see git show 6aa8da15dcc670df886fdeabbc8e5a634a224fa6^{tree}
Implementation parent: 3d1dc1939967bf3107c15e60fc21315dd59cd269
Approved contract ancestor: fe02031480e87b22be7c7e54d56bfb492faffefa
Forbidden ancestor check: aad0cbd55e9fef41cad79f7ca6f75b0e14a74ff6 absent

Publication
- Existing fork PR branch was read at d2e57bce19ba619230b719dca94cba5b608a1ec1 and fast-forward pushed to 6aa8da15dcc670df886fdeabbc8e5a634a224fa6.
- PR #112832 readback: OPEN, non-draft, unmerged; base main; head repository Mateo817/hermes-agent; head 6aa8da15dcc670df886fdeabbc8e5a634a224fa6.
- Current upstream main tip: 4716ec0ba4e212105f8f162c226f052b25f8a76b.
- Review-Key preimage fields were recomputed from those reads; key: 4af3a74a14f7f6c61e4da5786c12497a951867ef88ad8668a015bf82d78dbc6d.
- Stable request comment 5696001272 was updated and read back with the new Schema-1 body and key.
- Label write/readback: BLOCKED, GitHub returned HTTP 403 “Must have admin rights to Repository”; no label was simulated.
- No result comment, merge, activation, or default/protected branch write performed.

Implementation
- Added shared adapter assembly for CLI and Gateway.
- Added explicit project p_41500605 -> board hermes-system binding validation, no default/current/name fallback.
- Added profile-scoped native task create/readback and native dispatcher delegation.
- Added Read A-D identity and stable Schema-1 request validation, producer-bound required CI, durable cycle state, task materialization CAS, retry-after-stale-claim recovery, and task readback recovery.
- Added dry-run path with no durable or external writes.
- Added isolated tests for assembled dry-run and one-task materialization, plus existing contract tests.

Verification
- PASS: scripts/run_tests.sh tests/hermes_cli/test_pr_review_dispatcher.py (8 tests).
- PASS: python3 -m compileall -q hermes_cli/pr_review_dispatcher.py hermes_cli/kanban.py gateway/kanban_watchers.py.
- PASS: git diff --check.
- PASS: fork ref readback and PR head/base readback.
- BLOCKED/NOT_RUN: required trusted CI on final head, trigger label, result publication/reconciliation, authorized live GitHub->project->board task E2E, actual Windows runner, full repository suite, two-process race/crash E2E, and independent review gates.

Safety
- No merge or activation authorized.
- The label permission failure is an external blocker; do not infer a successful trigger or gate from the updated comment or pushed ref.
