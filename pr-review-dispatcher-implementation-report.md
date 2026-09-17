PR-review dispatcher implementation report

Candidate
- Worktree: /home/developer/.hermes/hermes-agent/.worktrees/t_8ea823bc
- Approved contract ancestor: fe02031480e87b22be7c7e54d56bfb492faffefa (verified ancestor)
- Forbidden ancestry aad0cbd55e9fef41cad79f7ca6f75b0e14a74ff6 (verified absent)
- GitHub push/PR mutation: not performed

Implemented changes
- hermes_cli/pr_review_dispatcher.py: explicit fixed-host GET API calls, pagination validation, current base-ref tip lookup, producer-bound required-CI discovery/validation, exact ref/parser/key validation, 12-condition remediation eligibility, admission states, non-null adapter failure reporting, and cross-platform lock helper usage.
- hermes_cli/kanban.py: PR-review poll exits non-zero when report.errors is non-empty.
- gateway/kanban_watchers.py: removed direct Unix-only fcntl use and reused shared singleton locking.
- tests/hermes_cli/test_pr_review_dispatcher.py: updated contract tests for lowercase immutable SHAs, producer-bound checks, candidate-head validation, and 12 remediation conditions.

Verification
- PASS: scripts/run_tests.sh tests/hermes_cli/test_pr_review_dispatcher.py (6 tests).
- PASS: python3 -m compileall -q hermes_cli/pr_review_dispatcher.py gateway/kanban_watchers.py hermes_cli/kanban.py.
- PASS: git diff --check.
- PASS: approved-contract ancestry and forbidden-ancestry checks.
- NOT_RUN/BLOCKED: full repository suite timed out in the execution environment after 420 seconds; no complete-suite result is claimed.
- NOT_RUN: actual Windows runner, GitHub CI, production GitHub/DB E2E, concurrent poller/crash-boundary E2E, and remote fork push/readback. These require downstream QA/review and/or external environment access.

Known scope limits
- This is a local reviewable candidate only. No PR body/comment/label, merge, deployment, activation, or force/history rewrite was performed.
- Child QA, code-review, and security-review tasks remain queued and are released by parent completion for independent fail-closed validation.
