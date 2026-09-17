"""Request publication preparation; not dispatcher or live GitHub E2E tests."""
from dataclasses import replace
import hashlib

import pytest

from hermes_cli.pr_review_dispatcher import PullRequestSnapshot, parse_request_comment
from hermes_cli.pr_review_request import prepare_request


class ReadOnlyGitHub:
    def __init__(self, *snapshots):
        self.snapshots = iter(snapshots)
        self.reads = []

    def read_pull_request(self, repository, number):
        self.reads.append((repository, number))
        return next(self.snapshots)


def snapshot():
    return PullRequestSnapshot("Owner/Repo", 7, True, False, "main", "a" * 40,
                               "Contributor/Repo", "Fix/Case", "b" * 40, "old")


def handoff():
    return {"summary": "Candidate only; independent review required.",
            "changed_files": ["module.py"], "test_commands": [], "known_risks": []}


def test_request_roundtrips_with_independent_hash_and_ignores_nonidentity_updates():
    first = snapshot()
    github = ReadOnlyGitHub(first, replace(first, updated_at="new"))
    plan = prepare_request(github, repository="Owner/Repo", pr_number=7,
                           expected_head=first.head_sha, handoff=handoff())
    preimage = "\n".join(("1", "owner/repo", "7", "main", "a" * 40,
                          "contributor/repo", "Fix/Case", "b" * 40))
    assert plan["preimage"] == preimage
    assert plan["review_key"] == hashlib.sha256(preimage.encode("utf-8")).hexdigest()
    assert parse_request_comment(plan["request_body"])["review_key"] == plan["review_key"]
    assert plan["writes_performed"] == 0
    assert plan["status"] == "PREPARED_NOT_TRIGGERED"
    assert github.reads == [("owner/repo", 7), ("owner/repo", 7)]


@pytest.mark.parametrize("changed", [
    {"base_sha": "c" * 40}, {"head_sha": "c" * 40}, {"base_ref": "release"},
    {"head_ref": "Other"}, {"head_repository": "Other/Repo"},
    {"repository": "Other/Repo"}, {"number": 8}, {"open": False}, {"draft": True},
])
def test_request_rejects_drift_or_revoked_reviewability(changed):
    first = snapshot()
    github = ReadOnlyGitHub(first, replace(first, **changed))
    with pytest.raises(ValueError):
        prepare_request(github, repository=first.repository, pr_number=first.number,
                        expected_head=first.head_sha, handoff=handoff())
