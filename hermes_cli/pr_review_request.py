"""Prepare, but never publish or trigger, a Schema-1 PR review request.

Uses the dispatcher's existing protocol implementation. A prepared request is
only a point-in-time snapshot, not a review, CI result, or integration approval.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from hermes_cli.pr_review_dispatcher import (
    FULL_SHA_RE,
    REVIEW_REQUEST_MARKER,
    GitHubCLI,
    PullRequestSnapshot,
    canonical_repository,
    compute_review_key,
    normalize_review_identity,
    parse_request_comment,
    review_key_preimage,
)


def _identity(snapshot: PullRequestSnapshot, repository: str, number: int) -> dict[str, Any]:
    if (not isinstance(snapshot, PullRequestSnapshot)
            or snapshot.open is not True or snapshot.draft is not False):
        raise ValueError("PR_NOT_REVIEWABLE")
    identity = normalize_review_identity(
        repository=snapshot.repository, pr_number=snapshot.number,
        base_ref=snapshot.base_ref, base_sha=snapshot.base_sha,
        head_repository=snapshot.head_repository, head_ref=snapshot.head_ref,
        head_sha=snapshot.head_sha,
    )
    if identity["repository"] != repository or identity["pr_number"] != number:
        raise ValueError("PR_IDENTITY_MISMATCH")
    return identity


def prepare_request(github: GitHubCLI, *, repository: str, pr_number: int,
                    expected_head: str, handoff: Mapping[str, Any]) -> dict[str, Any]:
    """Read twice and render through the same parser the poller will use.

    The caller still must archive the previous request, update its stable comment
    ID, read the published comment back, and revalidate immediately before any
    trigger. This function has no GitHub, filesystem, or Kanban write operation.
    """
    repository = canonical_repository(repository)
    if type(pr_number) is not int or pr_number <= 0:
        raise ValueError("INVALID_PR_NUMBER")
    if not isinstance(expected_head, str) or not FULL_SHA_RE.fullmatch(expected_head):
        raise ValueError("EXPECTED_FULL_HEAD_REQUIRED")
    first = _identity(github.read_pull_request(repository, pr_number), repository, pr_number)
    if first["head_sha"] != expected_head:
        raise ValueError("HEAD_CHANGED")
    payload = {
        **first,
        "review_key": compute_review_key(first),
        "requested_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "handoff": dict(handoff),
    }
    body = REVIEW_REQUEST_MARKER + "\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n```\n"
    parsed = parse_request_comment(body)
    if parsed != payload:
        raise ValueError("REQUEST_ROUNDTRIP_MISMATCH")
    second = _identity(github.read_pull_request(repository, pr_number), repository, pr_number)
    if second != first:
        raise ValueError("PR_IDENTITY_DRIFT")
    return {
        "status": "PREPARED_NOT_TRIGGERED",
        "identity": first,
        "review_key": parsed["review_key"],
        "preimage": review_key_preimage(first),
        "request_body": body,
        "writes_performed": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--handoff", required=True, type=Path, help="JSON object with summary, changed_files, test_commands and known_risks")
    args = parser.parse_args(argv)
    try:
        # This is trusted operator input, never an instruction to execute the
        # test_commands supplied by a PR author.
        if args.handoff.stat().st_size > 65536:
            raise ValueError("HANDOFF_TOO_LARGE")
        handoff = json.loads(args.handoff.read_text(encoding="utf-8"))
        if not isinstance(handoff, dict):
            raise ValueError("HANDOFF_OBJECT_REQUIRED")
        plan = prepare_request(GitHubCLI(), repository=args.repository, pr_number=args.pr_number,
                               expected_head=args.expected_head, handoff=handoff)
    except (OSError, RuntimeError, TypeError, ValueError):
        # Do not expose subprocess output, request bodies or local paths.
        print(json.dumps({"status": "BLOCKED", "reason": "REQUEST_PREPARATION_FAILED", "writes_performed": 0}), file=sys.stderr)
        return 2
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
