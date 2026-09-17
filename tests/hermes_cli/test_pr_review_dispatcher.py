from __future__ import annotations

import hashlib
import json

import pytest

from hermes_cli.pr_review_dispatcher import (
    REVIEW_REQUEST_MARKER,
    binding_fingerprint,
    compute_review_key,
    normalize_review_identity,
    parse_request_comment,
    remediation_eligibility,
    review_key_preimage,
    validate_required_ci,
    validate_runtime_config,
)
from hermes_cli.pr_review_dispatcher import (IssueComment, PullRequestRef, PullRequestSnapshot,
                                              REVIEW_REQUEST_MARKER, poll_once)
from hermes_cli.pr_review_dispatcher import GitHubCLI


@pytest.fixture
def identity():
    return normalize_review_identity(
        repository="NousResearch/hermes-agent", pr_number=7, base_ref="main",
        base_sha="a" * 40, head_repository="Mateo817/hermes-agent",
        head_ref="Feature/Mixed", head_sha="b" * 40,
    )


def test_review_key_uses_base_tip_and_exact_seven_lf(identity):
    preimage = review_key_preimage(identity)
    assert preimage.count("\n") == 7
    assert not preimage.endswith("\n")
    assert compute_review_key(identity) == hashlib.sha256(preimage.encode()).hexdigest()
    changed = dict(identity, base_sha="c" * 40)
    assert compute_review_key(changed) != compute_review_key(identity)


def test_request_parser_rejects_duplicate_json_keys():
    body = REVIEW_REQUEST_MARKER + "\n```json\n{" + '"schema_version":1,"schema_version":1' + "}\n```"
    with pytest.raises(ValueError, match="MALFORMED_REQUEST"):
        parse_request_comment(body)


def test_request_parser_accepts_schema_one_comment(identity):
    payload = dict(identity, review_key=compute_review_key(identity), requested_at="2026-09-16T10:00:00Z",
                   handoff={"summary": "Review", "changed_files": [], "test_commands": [], "known_risks": []})
    value = parse_request_comment(REVIEW_REQUEST_MARKER + "\n```json\n" + json.dumps(payload) + "\n```")
    assert value["review_key"] == compute_review_key(identity)


def test_binding_fingerprint_is_exact_and_config_fails_closed():
    value = binding_fingerprint(repository="o/r", project_id="p", board_slug="b",
                                orchestration_profile="orchestrator", binding_revision=3)
    expected = hashlib.sha256("binding/v1\no/r\np\nb\norchestrator\n3".encode()).hexdigest()
    assert value == expected
    assert not validate_runtime_config({"kanban": {"github_pr_review": {"interval_seconds": 60}}})["valid"]


def test_ci_requires_producer_bound_completed_check_success():
    required = [{"name": "unit", "app_id": 42}]
    passing = {"name": "unit", "app_id": 42, "status": "completed", "conclusion": "success", "head_sha": "a" * 40}
    snapshot = {"readable": True, "head_sha": "a" * 40, "required": required, "checks": [passing]}
    assert validate_required_ci(snapshot) == "PASS"
    assert validate_required_ci({**snapshot, "checks": [{**passing, "status": "queued"}]}) == "PENDING"
    assert validate_required_ci({"readable": False, "required": required, "checks": []}) == "BLOCKED"


def test_checks_endpoints_parse_envelopes_and_reject_inconsistent_pages(monkeypatch):
    github = GitHubCLI()
    monkeypatch.setattr(github, "_api", lambda *args: [{"total_count": 1, "check_suites": [{"id": 9}]}])
    assert github.read_check_suites("o/r", "a" * 40) == [{"id": 9}]
    monkeypatch.setattr(github, "_api", lambda *args: [{"total_count": 0, "check_runs": []}])
    assert github.read_check_runs("o/r", 9) == []
    monkeypatch.setattr(github, "_api", lambda *args: [{"total_count": 1, "check_runs": []}])
    with pytest.raises(RuntimeError, match="inconsistent"):
        github.read_check_runs("o/r", 9)


def test_native_dispatch_adapter_defers_to_scheduler():
    from hermes_cli.pr_review_dispatcher import HermesProjectBindingAdapter
    result = HermesProjectBindingAdapter().dispatch_native_task("t_12345678", {})
    assert result == {"deferred_to_native_scheduler": True, "task_id": "t_12345678"}


def test_remediation_has_exactly_twelve_cumulative_conditions():
    values = {name: True for name in ("documented_finding", "scope_unchanged", "no_new_product_requirement", "no_new_architecture", "no_public_api_change", "no_schema_change", "no_security_boundary_change", "no_external_integration", "verifiable_completion", "existing_pr_branch_only", "trusted_head_cas", "bounded_separate_worker")}
    assert remediation_eligibility(values)["eligible"]
    values["trusted_head_cas"] = False
    assert not remediation_eligibility(values)["eligible"]


class _Github:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.writes = 0

    def list_candidates(self, repository, label):
        return [PullRequestRef("o/r", 1)]

    def read_pull_request(self, repository, number):
        return self.snapshot

    def list_issue_comments(self, repository, number):
        identity = normalize_review_identity(repository=self.snapshot.repository, pr_number=self.snapshot.number,
            base_ref=self.snapshot.base_ref, base_sha=self.snapshot.base_sha,
            head_repository=self.snapshot.head_repository, head_ref=self.snapshot.head_ref,
            head_sha=self.snapshot.head_sha)
        payload = dict(identity, review_key=compute_review_key(identity), requested_at="2026-09-16T10:00:00Z",
                       handoff={"summary": "Review", "changed_files": [], "test_commands": [], "known_risks": []})
        return [IssueComment(1, REVIEW_REQUEST_MARKER + "\n```json\n" + json.dumps(payload) + "\n```")]

    def read_required_check_policy(self, repository, base_ref, base_sha):
        return {"required": [{"name": "All required checks pass", "app_id": 15368}]}

    def read_check_suites(self, repository, head_sha):
        return [{"id": 1}]

    def read_check_suite(self, repository, suite_id):
        return {"id": suite_id, "head_sha": "b" * 40}

    def read_check_runs(self, repository, suite_id, *, filter):
        return [{"name": "All required checks pass", "app": {"id": 15368},
                 "status": "completed", "conclusion": "success", "head_sha": "b" * 40}]


class _Bindings:
    def __init__(self):
        self.created = 0
        self.key = None

    def resolve_repository(self, repository):
        return {"project_id": "p_41500605", "board": "hermes-system",
                "orchestration_profile": "orchestrator", "binding_revision": 1}

    def create_native_task(self, identity, key, binding):
        self.created += 1
        self.key = key
        return {"id": "t_12345678", "review_key": key}

    def read_native_task(self, task_id, binding):
        return {"id": task_id, "review_key": self.key}

    def dispatch_native_task(self, task_id, binding):
        return {"spawned": []}


def test_poll_once_dry_run_uses_assembled_ports_without_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    snapshot = PullRequestSnapshot("o/r", 1, True, False, "main", "a" * 40,
                                   "fork/r", "feature", "b" * 40)
    github, bindings = _Github(snapshot), _Bindings()
    report = poll_once(github=github, bindings=bindings, dry_run=True)
    assert report.writes_performed == 0
    assert report.errors == ()
    assert bindings.created == 0


def test_poll_once_materializes_one_native_task(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    snapshot = PullRequestSnapshot("o/r", 1, True, False, "main", "a" * 40,
                                   "fork/r", "feature", "b" * 40)
    bindings = _Bindings()
    report = poll_once(github=_Github(snapshot), bindings=bindings)
    assert report.errors == ()
    assert report.writes_performed == 1
    assert bindings.created == 1
