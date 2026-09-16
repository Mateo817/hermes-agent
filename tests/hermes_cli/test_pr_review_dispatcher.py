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


@pytest.fixture
def identity():
    return normalize_review_identity(
        repository="NousResearch/hermes-agent", pr_number=7, base_ref="main",
        base_sha="A" * 40, head_repository="Mateo817/hermes-agent",
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


def test_ci_requires_every_required_check_success():
    assert validate_required_ci({"readable": True, "required": ["unit"], "checks": [{"name": "unit", "conclusion": "success"}]}) == "PASS"
    assert validate_required_ci({"readable": True, "required": ["unit"], "checks": [{"name": "unit", "conclusion": "queued"}]}) == "PENDING"
    assert validate_required_ci({"readable": False, "required": ["unit"], "checks": []}) == "BLOCKED"


def test_remediation_has_exactly_ten_cumulative_conditions():
    values = {name: True for name in ("small_findings", "unique_source", "limited_change", "complete_todo", "trusted_head", "safe_branch", "current_cas", "exclusive_serialization", "separate_identities", "verifiable_completion")}
    assert remediation_eligibility(values)["eligible"]
    values["safe_branch"] = False
    assert not remediation_eligibility(values)["eligible"]
