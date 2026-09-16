"""Fail-closed orchestration for the ``hermes-triage`` edge CLI.

The controller deliberately delegates decomposition and dispatch to Hermes' public
CLI.  This module contains validation, identity, locking, and readback logic; it
never implements an alternative decomposition algorithm.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
import tomllib
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote

TASK_ID_RE = re.compile(r"^t_[0-9a-f]{8}$")
BOARD_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
EXIT_CODES = {
    "READY_FOR_REVIEW": 0, "READY_FOR_DISPATCH": 0, "DISPATCHED": 0,
    "FAILED_PRECHECK": 10, "FAILED_CREATE_VALIDATION": 20,
    "FAILED_DECOMPOSITION": 30, "FAILED_GRAPH_VALIDATION": 40,
    "FAILED_DISPATCH_PREFLIGHT": 50, "FAILED_DISPATCH": 60,
    "FAILED_AUDIT": 70, "FAILED_INTERNAL": 99,
}
STATUSES = {"triage", "todo", "scheduled", "ready", "running", "blocked", "review", "done", "archived"}
SECRET_KEY = re.compile(r"token|secret|password|passwd|api_key|authorization|cookie|credential", re.I)
SECRET_TEXT = re.compile(r"(?i)(bearer\s+|basic\s+)[^\s,;]+|(?i:[a-z_]*key)=[^\s]+")


@dataclass(frozen=True)
class NormalizedBody:
    source_name: str
    text: str
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class Metadata:
    board: str
    title: str
    assignee: str
    priority: int
    triage: bool
    decompose: bool
    dispatch: bool
    idempotency_key: str | None
    schema_version: int = 1


@dataclass(frozen=True)
class NormalizedRequest:
    schema_version: int
    board: str
    title: str
    body: str
    body_sha256: str
    assignee: str
    priority: int
    triage: bool
    decompose: bool
    metadata_dispatch: bool
    cli_dispatch_override: bool
    effective_dispatch: bool
    effective_project: str | None
    idempotency_key: str


@dataclass
class CommandResult:
    argv_redacted: list[str]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


@dataclass
class RetryBudget:
    """One process-wide retry credit, shared by every upstream operation."""
    remaining: int = 1
    used: int = 0
    exhausted: bool = False

    def consume(self) -> bool:
        if self.remaining <= 0:
            self.exhausted = True
            return False
        self.remaining -= 1
        self.used += 1
        return True


def board_fingerprint(board: Mapping[str, Any]) -> str:
    """Return a stable identity fingerprint (never based on mtime)."""
    payload = {"slug": board.get("slug", board.get("name")),
               "project_id": board.get("project_id"),
               "db_path": str(board.get("db_path", ""))}
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _task_obj(show: Mapping[str, Any]) -> Mapping[str, Any]:
    value = show.get("task", show)
    return value if isinstance(value, Mapping) else {}


def _relationship_ids(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result = []
    for item in value:
        if isinstance(item, Mapping):
            item = item.get("id", item.get("task_id"))
        if item is not None:
            result.append(str(item))
    return result


class BoardReadError(RuntimeError):
    """The controller cannot prove that a board was inspected read-only."""


_BOARD_TASK_COLUMNS = (
    "id", "title", "body", "assignee", "project_id", "status",
    "priority", "created_at", "idempotency_key", "claim_lock",
)


def _safe_sqlite_tasks(db_path: str) -> list[dict[str, Any]]:
    """Read a board DB strictly read-only, failing closed on any uncertainty."""
    path = Path(db_path)
    if not path.is_absolute() or not path.is_file():
        raise BoardReadError("board database is not a readable regular file")
    try:
        uri = path.as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
            required = {"id", "title", "body", "assignee", "project_id", "status", "idempotency_key"}
            if not required <= columns:
                raise BoardReadError("board database schema cannot be verified read-only")
            # Missing ordering columns are not guessed.  The dispatch gate
            # treats NULL ordering metadata as unverifiable and fails closed.
            expressions = [
                column if column in columns else f"NULL AS {column}"
                for column in _BOARD_TASK_COLUMNS
            ]
            rows = conn.execute("SELECT " + ",".join(expressions) + " FROM tasks").fetchall()
            return [dict(zip(_BOARD_TASK_COLUMNS, row)) for row in rows]
    except BoardReadError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise BoardReadError("board database could not be inspected read-only") from exc


def dispatcher_candidate_snapshot(db_path: str) -> tuple[tuple[Any, ...], ...]:
    """Return the complete board-wide inventory relevant to dispatch.

    This intentionally bypasses ``hermes kanban list``: Hermes 0.21.0's list
    command calls ``recompute_ready`` and is therefore not a read operation.

    Include every task state that the dispatcher can inspect or promote, not
    merely currently-ready tasks.  In particular, ``todo`` rows can be
    promoted by the dispatch dry-run and ``review`` rows are dispatched by
    the review lane; omitting either permits an unrelated race to slip past
    the dry-run revalidation.
    """
    tasks = _safe_sqlite_tasks(db_path)
    return tuple(sorted(
        (str(task.get("id")), task.get("status"), task.get("assignee"),
         task.get("claim_lock"), task.get("priority"), task.get("created_at"))
        for task in tasks
        if task.get("status") in {"todo", "ready", "review", "running", "scheduled"}
    ))


def dispatcher_selection_snapshot(db_path: str, max_count: int) -> tuple[str, ...]:
    """Compute the exact eligible board-wide prefix used by dispatch_once."""
    tasks = _safe_sqlite_tasks(db_path)
    eligible = [
        task for task in tasks
        if task.get("status") in {"ready", "review"} and not task.get("claim_lock")
    ]
    if any(task.get("priority") is None or task.get("created_at") is None for task in eligible):
        raise BoardReadError("dispatcher ordering metadata is unreadable")
    # The ready lane is consumed before the review lane; a review candidate is
    # therefore never silently ignored by this preflight.
    ready = sorted(
        (task for task in eligible if task.get("status") == "ready"),
        key=lambda task: (-int(task["priority"]), int(task["created_at"]), str(task["id"])),
    )
    review = sorted(
        (task for task in eligible if task.get("status") == "review"),
        key=lambda task: (-int(task["priority"]), int(task["created_at"]), str(task["id"])),
    )
    return tuple(str(task["id"]) for task in (ready + review)[:max_count])


def scan_cross_board_collisions(boards: Sequence[Mapping[str, Any]], request: Mapping[str, Any], target_board: str) -> list[dict[str, Any]]:
    """Find identical business intent on another board, without changing state."""
    collisions = []
    for board in boards:
        slug = board.get("slug", board.get("name"))
        if not isinstance(slug, str) or slug == target_board:
            continue
        for task in _safe_sqlite_tasks(str(board.get("db_path", ""))):
            if (task.get("title") == request.get("title")
                    and task.get("body") == request.get("body")
                    and task.get("assignee") == request.get("assignee")):
                collisions.append({"board": slug, "task_id": task.get("id"),
                                   "kind": "content"})
            if request.get("idempotency_key") and task.get("idempotency_key") == request["idempotency_key"]:
                collisions.append({"board": slug, "task_id": task.get("id"),
                                   "kind": "idempotency"})
    return collisions


class ValidationResult(list):
    """List-like validation report with a stable aggregate contract."""

    def __init__(self, checks: Sequence[Mapping[str, Any]], **fields: Any):
        super().__init__(dict(check) for check in checks)
        self.checks = list(self)
        self.ok = all(bool(check.get("ok")) for check in self)
        for name, value in fields.items():
            setattr(self, name, value)

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "checks": self.checks, **self.__dict__}


class HermesRunner:
    def __init__(self, executable: str | None = None):
        self.executable = executable

    def resolve(self) -> str:
        path = self.executable or shutil.which("hermes")
        if not path:
            raise RuntimeError("Hermes CLI not found")
        return str(Path(path).resolve())

    def run(self, argv: Sequence[str], timeout_s: int) -> CommandResult:
        try:
            cp = subprocess.run(list(argv), shell=False, text=True, encoding="utf-8",
                                errors="strict", capture_output=True, timeout=timeout_s)
            return CommandResult(_redact_argv(list(argv)), cp.returncode, cp.stdout, cp.stderr)
        except subprocess.TimeoutExpired as exc:
            return CommandResult(_redact_argv(list(argv)), 124,
                                 _as_text(exc.stdout), _as_text(exc.stderr), True)
        except OSError as exc:
            raise RuntimeError(f"Hermes process failed: {type(exc).__name__}") from exc


def _as_text(value: Any) -> str:
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else (value or "")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: "[REDACTED]" if SECRET_KEY.search(str(k)) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = SECRET_TEXT.sub("[REDACTED]", value)
        return re.sub(r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*[^\s,;]+", r"\1=[REDACTED]", value)
    return value


def _redact_argv(argv: Sequence[str]) -> list[str]:
    return ["[REDACTED]" if i and argv[i - 1] in {"--body", "--idempotency-key"} else str(v) for i, v in enumerate(argv)]


def _json(text: str, *, expect: type) -> Any:
    if not text.strip():
        raise ValueError("empty JSON response")
    value = json.loads(text)
    if not isinstance(value, expect):
        raise ValueError("unexpected JSON response shape")
    return value


def parse_request(path: str | os.PathLike[str]) -> NormalizedBody:
    p = Path(path)
    st = p.stat()
    if not p.is_file() or st.st_size > 1024 * 1024:
        raise ValueError("request must be a regular file no larger than 1 MiB")
    raw = p.read_bytes()
    text = raw.decode("utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    while lines and not lines[0].strip(): lines.pop(0)
    while lines and not lines[-1].strip(): lines.pop()
    text = "\n".join(lines) + "\n"
    if not text.strip():
        raise ValueError("request must not be empty")
    encoded = text.encode("utf-8")
    return NormalizedBody(p.name, text, len(encoded), hashlib.sha256(encoded).hexdigest())


def _string(value: Any, name: str, maximum: int, *, visible_ascii: bool = False) -> str:
    if not isinstance(value, str): raise ValueError(f"{name} must be a string")
    value = unicodedata.normalize("NFKC", value).strip()
    if not value or len(value) > maximum or any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError(f"invalid {name}")
    if visible_ascii and (not value.isascii() or any(c.isspace() for c in value)):
        raise ValueError(f"invalid {name}")
    return value


def parse_metadata(path: str | os.PathLike[str], cli_dispatch_override: bool = False) -> Metadata:
    with Path(path).open("rb") as fh: raw = tomllib.load(fh)
    if set(raw) != {"triage"} or not isinstance(raw["triage"], dict):
        raise ValueError("metadata must contain exactly one [triage] table")
    data = raw["triage"]
    allowed = {"schema_version", "board", "title", "assignee", "priority", "triage", "decompose", "dispatch", "idempotency_key"}
    if set(data) - allowed: raise ValueError("unknown metadata field")
    version = data.get("schema_version", 1)
    if isinstance(version, bool) or version != 1: raise ValueError("schema_version must be 1")
    board = _string(data.get("board"), "board", 64)
    if not BOARD_RE.fullmatch(board): raise ValueError("invalid board slug")
    title = _string(data.get("title"), "title", 200)
    priority = data.get("priority", 0)
    if isinstance(priority, bool) or not isinstance(priority, int) or not -1000 <= priority <= 1000: raise ValueError("invalid priority")
    assignee = _string(data.get("assignee"), "assignee", 200)
    triage = data.get("triage", True)
    decompose = data.get("decompose", True)
    dispatch = data.get("dispatch", False)
    if triage is not True or not isinstance(decompose, bool) or not isinstance(dispatch, bool) or (dispatch and not decompose):
        raise ValueError("triage must be true; dispatch requires decompose=true")
    key = data.get("idempotency_key")
    if key is not None: key = _string(key, "idempotency_key", 200, visible_ascii=True)
    return Metadata(board, title, assignee, priority, triage, decompose, dispatch,
                    key, version)


def make_idempotency_key(request: NormalizedRequest) -> str:
    payload = {"schema_version": request.schema_version, "board": request.board,
               "title": request.title, "body_sha256": request.body_sha256,
               "assignee": request.assignee, "priority": request.priority,
               "project": request.effective_project}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "triage:v1:" + hashlib.sha256(canonical).hexdigest()


def make_intent_lock_key(request: NormalizedRequest) -> str:
    """Return a board-independent identity for cross-board serialization."""
    payload = {
        "schema_version": request.schema_version,
        "title": request.title,
        "body_sha256": request.body_sha256,
        "assignee": request.assignee,
        "priority": request.priority,
        "project": request.effective_project,
    }
    return "intent:v1:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def build_normalized_request(body: NormalizedBody, metadata: Metadata, board_info: Mapping[str, Any], cli_dispatch_override: bool = False) -> NormalizedRequest:
    project = board_info.get("project_id") or None
    provisional = NormalizedRequest(metadata.schema_version, metadata.board, metadata.title, body.text,
        body.sha256, metadata.assignee, metadata.priority, True, metadata.decompose,
        metadata.dispatch, cli_dispatch_override, metadata.dispatch or cli_dispatch_override, project, "")
    key = metadata.idempotency_key or make_idempotency_key(provisional)
    return NormalizedRequest(**{**provisional.__dict__, "idempotency_key": key})


def validate_create_readback(expected: NormalizedRequest, show: Mapping[str, Any], idempotency_rows: Sequence[tuple[str, str | None]]) -> list[dict[str, Any]]:
    task = show.get("task", show)
    checks = []
    def check(cid: str, ok: bool, detail: Any = None): checks.append({"id": cid, "ok": bool(ok), "detail": detail})
    tid = task.get("id")
    check("root.id", bool(TASK_ID_RE.fullmatch(str(tid or ""))))
    check("root.idempotency_unique", len(idempotency_rows) == 1 and idempotency_rows[0][0] == tid)
    actual_board = task.get("board") or show.get("board")
    expected_board = getattr(expected, "board", None)
    check("root.board", actual_board in (None, expected_board), actual_board)
    check("root.title", task.get("title") == expected.title)
    check("root.body", task.get("body") == expected.body)
    check("root.assignee", task.get("assignee") == expected.assignee)
    check("root.priority", task.get("priority") == expected.priority)
    expected_project = getattr(expected, "effective_project", getattr(expected, "project_id", None))
    check("root.project", task.get("project_id") == expected_project)
    check("root.triage", task.get("status") == "triage")
    check("root.parents", not show.get("parents", []))
    check("root.children", not show.get("children", []))
    return ValidationResult(checks)


def build_graph_snapshot(root_show: Mapping[str, Any], child_shows: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]], board_tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if isinstance(child_shows, Mapping):
        children = dict(child_shows)
    else:
        children = {}
        for item in child_shows:
            task = item.get("task", item)
            if task.get("id"):
                children[str(task["id"])] = item
    return {"root": root_show, "children": children, "board_tasks": list(board_tasks)}


def _graph_edges(snapshot: Mapping[str, Any]) -> set[tuple[str, str]]:
    edges = set()
    for show in [snapshot["root"], *snapshot.get("children", {}).values(),
                 *snapshot.get("nodes", {}).values()]:
        obj = _task_obj(show)
        tid = obj.get("id")
        for child in _relationship_ids(show.get("children", obj.get("children", []))):
            edges.add((str(tid), child))
    return edges


def validate_graph(expected: NormalizedRequest, decompose_result: Mapping[str, Any], snapshot: Mapping[str, Any], profiles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    def check(cid, ok, detail=None): checks.append({"id": cid, "ok": bool(ok), "detail": detail})
    root_show = snapshot["root"]
    root = _task_obj(root_show)
    child_ids = [str(x) for x in snapshot.get("children", {})]
    nodes = {str(k): v for k, v in snapshot.get("children", {}).items()}
    nodes.update({str(k): v for k, v in snapshot.get("nodes", {}).items()})
    all_shows = [root_show, *nodes.values()]
    reported = decompose_result.get("child_ids") or []
    fanout = bool(decompose_result.get("fanout"))
    check("graph.child_ids", set(reported) == set(child_ids) if fanout else not child_ids)
    check("graph.status", root.get("status") in ({"todo"} if fanout else {"ready", "todo"}))
    names = {p.get("name") for p in profiles if p.get("on_disk")}
    check("profile.on_disk", root.get("assignee") in names)
    all_ids = {root.get("id"), *child_ids}
    check("graph.task_ids", all(TASK_ID_RE.fullmatch(str(x)) for x in all_ids))
    child_tasks = [v.get("task", v) for v in snapshot.get("children", {}).values()]
    check("graph.statuses", all(t.get("status") in STATUSES for t in [root, *child_tasks]))
    check("graph.child_profiles", all(t.get("assignee") in names for t in child_tasks))
    edges = _graph_edges(snapshot)
    references = []
    for show in all_shows:
        obj = _task_obj(show)
        tid = str(obj.get("id"))
        parents = _relationship_ids(show.get("parents", obj.get("parents", [])))
        children_for_show = _relationship_ids(show.get("children", obj.get("children", [])))
        references.extend((tid, x, "parent") for x in parents)
        references.extend((tid, x, "child") for x in children_for_show)
        check(f"graph.{tid}.no_duplicate_relationships",
              len(parents) == len(set(parents)) and len(children_for_show) == len(set(children_for_show)))
    check("graph.edges_reachable", all(e[0] in all_ids and e[1] in all_ids for e in edges))
    check("graph.dependencies_exist", all(x in all_ids for _, x, _ in references))
    root_board = root.get("board") or root_show.get("board")
    scope_ok = True
    raw_edge_count = 0
    for show in all_shows:
        obj = _task_obj(show)
        scope_ok = scope_ok and (not (show.get("board") or obj.get("board")) or
                                 (show.get("board") or obj.get("board")) == root_board)
        raw_children = show.get("children", obj.get("children", [])) or []
        raw_edge_count += len(raw_children)
    check("graph.board_scope", scope_ok)
    check("graph.edge_duplicates", len(edges) == raw_edge_count)
    child_events = [event for show in snapshot.get("children", {}).values()
                    for event in show.get("events", [])
                    if isinstance(event, Mapping) and event.get("kind") == "created"]
    check("graph.child_created_events", all(
        event.get("payload", {}).get("from_decompose_of") == root.get("id")
        for event in child_events
    ) and len(child_events) == len(child_ids))
    reverse_ok = True
    # Every reachable relationship must be represented in both directions.
    # Do not special-case the root: recursive decompositions and dependency
    # edges are valid only when the referenced node can be read and agrees.
    for source_id, show in ((str(_task_obj(root_show).get("id")), root_show), *nodes.items()):
        obj = _task_obj(show)
        parents = _relationship_ids(show.get("parents", obj.get("parents", [])))
        children_for_show = _relationship_ids(show.get("children", obj.get("children", [])))
        for parent_id in parents:
            parent_show = nodes.get(parent_id) if parent_id != str(root.get("id")) else root_show
            if parent_show is None:
                reverse_ok = False
                continue
            parent_obj = _task_obj(parent_show)
            parent_children = _relationship_ids(parent_show.get("children", parent_obj.get("children", [])))
            reverse_ok = reverse_ok and source_id in parent_children
        for child_id in children_for_show:
            child_show = root_show if child_id == str(root.get("id")) else nodes.get(child_id)
            if child_show is None:
                reverse_ok = False
                continue
            child_obj = _task_obj(child_show)
            child_parents = _relationship_ids(child_show.get("parents", child_obj.get("parents", [])))
            reverse_ok = reverse_ok and source_id in child_parents
    check("graph.edges_bidirectional", reverse_ok)
    indegree = {x: 0 for x in all_ids}
    for a, b in edges:
        if a == b: indegree[a] = 1
        elif b in indegree: indegree[b] += 1
    queue = [x for x, d in indegree.items() if d == 0]; seen = 0
    while queue:
        n = queue.pop(); seen += 1
        for a, b in edges:
            if a == n and b in indegree:
                indegree[b] -= 1
                if indegree[b] == 0: queue.append(b)
    check("graph.acyclic", seen == len(indegree))
    return ValidationResult(checks)


def validate_dispatch_dry_run(snapshot: Mapping[str, Any], dry_run_json: Mapping[str, Any]) -> list[str]:
    bad = []
    for field in ("reclaimed", "crashed", "timed_out", "stale", "auto_blocked", "auto_assigned_default", "skipped_unassigned", "skipped_nonspawnable", "skipped_per_profile_capped", "promoted"):
        value = dry_run_json.get(field, 0)
        if value not in (0, [], {}, None): bad.append(field)
    initiative = {str(snapshot["root"].get("task", snapshot["root"]).get("id")), *map(str, snapshot.get("children", {}))}
    spawned = [str(x.get("task_id")) for x in dry_run_json.get("spawned", []) if isinstance(x, Mapping)]
    if not spawned or not set(spawned) <= initiative: bad.append("only_initiative")
    if bad:
        raise ValueError("dispatch dry-run is unsafe: " + ",".join(sorted(set(bad))))
    return ValidationResult([], task_ids=sorted(spawned), plan=dict(dry_run_json))


@contextlib.contextmanager
def board_lock(board: str, key: str, home: Path | None = None):
    root = home or Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    directory = root / "kanban" / "triage-controller-locks"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{board}.{hashlib.sha256(key.encode()).hexdigest()}.lock"
    with path.open("a+") as fh:
        from hermes_cli.kanban_db_connect import _try_lock_nb, _unlock
        if not _try_lock_nb(fh):
            raise RuntimeError("controller lock is busy")
        try: yield
        finally: _unlock(fh)


@contextlib.contextmanager
def intent_lock(intent: str, home: Path | None = None):
    """Serialize one business intent across every board.

    The board lock is intentionally insufficient: two boards can otherwise
    pass collision reads concurrently and both create the same initiative.
    This lock is keyed only by the cross-board intent identity.
    """
    root = home or Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    directory = root / "kanban" / "triage-controller-intent-locks"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{hashlib.sha256(intent.encode()).hexdigest()}.lock"
    with path.open("a+") as fh:
        from hermes_cli.kanban_db_connect import _try_lock_nb, _unlock
        if not _try_lock_nb(fh):
            raise RuntimeError("exclusive intent lock unavailable")
        try: yield
        finally: _unlock(fh)


@contextlib.contextmanager
def submission_locks(board: str, board_key: str, intent_key: str, home: Path | None = None):
    """Acquire the cross-board intent lock before the board lock."""
    with intent_lock(intent_key, home):
        with board_lock(board, board_key, home):
            yield


@dataclass
class AuditReport:
    state: str = "FAILED_PRECHECK"
    exit_code: int = 10
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validations: list[dict[str, Any]] = field(default_factory=list)
    root_id: str | None = None
    root_details: dict[str, Any] = field(default_factory=dict)
    board: dict[str, Any] = field(default_factory=dict)
    request: dict[str, Any] = field(default_factory=dict)
    idempotency: dict[str, Any] = field(default_factory=dict)
    children: list[dict[str, Any]] = field(default_factory=list)
    decomposition: dict[str, Any] = field(default_factory=lambda: {"requested": False, "attempted": False, "fanout": None, "reported_child_ids": [], "readback_child_ids": []})
    dispatch: dict[str, Any] = field(default_factory=lambda: {"requested": False, "attempted": False, "spawned_task_ids": [], "verified_running_task_ids": []})
    hermes_version: str | None = None
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    dry_run: dict[str, Any] = field(default_factory=lambda: {"attempted": False, "valid": None, "planned_task_ids": [], "raw_summary": None})
    retries: list[dict[str, Any]] = field(default_factory=list)
    retry_budget: dict[str, Any] = field(default_factory=lambda: {"initial": 1, "used": 0, "remaining": 1, "exhausted": False})
    def as_dict(self) -> dict[str, Any]:
        return {"audit_schema_version": 1, "run_id": self.run_id, "started_at": self.started_at,
                "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "controller_version": "1.0.0", "hermes_version": self.hermes_version, "state": self.state,
                "exit_code": self.exit_code, "board": self.board, "request": self.request,
                "idempotency": self.idempotency, "root": {"id": self.root_id, **self.root_details}, "children": self.children, "dependencies": self.dependencies,
                "decomposition": self.decomposition,
                "validations": self.validations, "dry_run": self.dry_run,
                "dispatch": self.dispatch,
                "retries": self.retries, "retry_budget": self.retry_budget,
                "warnings": self.warnings, "errors": self.errors}


def write_audit(report: AuditReport, path: str | os.PathLike[str]) -> None:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".triage-", dir=target.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(redact(report.as_dict()), fh, ensure_ascii=False, indent=2); fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
        os.replace(temp, target)
    except Exception:
        with contextlib.suppress(OSError): os.unlink(temp)
        raise


def read_dispatcher_presence() -> dict[str, Any]:
    """Conservative, read-only probe for Hermes' embedded gateway dispatcher."""
    try:
        from gateway.status import resolve_gateway_liveness
        from hermes_cli.config import load_config
        live = resolve_gateway_liveness(use_cache=False)
        cfg = load_config()
        enabled = bool(cfg.get("kanban", {}).get("dispatch_in_gateway", True))
        return {"gateway_running": bool(live.pid and enabled), "dispatch_enabled": enabled,
                "probe_error": live.probe_error}
    except Exception as exc:
        return {"gateway_running": True, "dispatch_enabled": True,
                "probe_error": type(exc).__name__}


def main(argv: Sequence[str] | None = None) -> int:
    """Compatibility entry point; the installed script uses ``triage_cli``."""
    if argv and len(argv) >= 3 and argv[0] == "submit":
        request = Path(argv[1])
        try:
            config = Path(argv[argv.index("--config") + 1])
        except (ValueError, IndexError):
            config = None
        if not request.exists() or config is None or not config.exists():
            # Match argparse's conventional status for an uninitializable CLI
            # invocation; no audit is written because its destination is not
            # trustworthy until the request is parseable.
            return 2
    from hermes_cli.triage_cli import main as cli_main
    return cli_main(argv)


# Schema-1 PR review dispatcher policy.  The implementation is deliberately
# transport-agnostic: GitHub and Kanban adapters are injected by callers.
REVIEW_REQUEST_MARKER = "<!-- hermes-review-request -->"
REVIEW_RESULT_MARKER = "<!-- hermes-review-result -->"
REPOSITORY_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_.-]{0,38})/[a-z0-9](?:[a-z0-9_.-]{0,99})$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REVIEW_KEY_RE = re.compile(r"^[0-9a-f]{64}$")
LIFECYCLE_STATES = frozenset({
    "DISCOVERED", "CLAIMED", "TASK_CREATED", "IN_REVIEW",
    "REMEDIATION_PENDING", "REMEDIATING", "REREVIEW_REQUESTED",
    "COMPLETED", "BLOCKED", "STALE",
})
GATE_STATES = frozenset({"NOT_RUN", "PASS", "CHANGES_REQUIRED", "BLOCKED"})
ADMISSION_STATES = frozenset({"PENDING_READ_C", "MATERIALIZING_TASK", "MATERIALIZED", "STALE"})


@dataclass(frozen=True)
class PullRequestRef:
    repository: str
    number: int


@dataclass(frozen=True)
class PullRequestSnapshot:
    repository: str
    number: int
    open: bool
    draft: bool
    base_ref: str
    base_sha: str
    head_repository: str
    head_ref: str
    head_sha: str
    updated_at: str = ""


@dataclass(frozen=True)
class IssueComment:
    id: int
    body: str
    actor: str = ""
    updated_at: str = ""


class GitHubCLI:
    """Small authenticated GitHub port backed by fixed-host GETs."""

    def __init__(self, executable: str = "gh", timeout: int = 30):
        self.executable, self.timeout = executable, timeout

    def _api(self, *parts: str) -> Any:
        argv = [self.executable, "api", "--hostname", "github.com", "--method", "GET", *parts]
        try:
            result = subprocess.run(argv, shell=False, check=True, text=True,
                                    encoding="utf-8", capture_output=True, timeout=self.timeout)
            return json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise RuntimeError("GitHub API operation failed") from exc

    def _pages(self, endpoint: str, *fields: str) -> list[dict[str, Any]]:
        pages = self._api(endpoint, *fields, "--paginate", "--slurp")
        if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
            raise RuntimeError("GitHub returned invalid pagination")
        rows = [row for page in pages for row in page]
        if any(not isinstance(row, dict) for row in rows):
            raise RuntimeError("GitHub returned invalid pagination row")
        return rows

    def list_candidates(self, repository: str | None, label: str) -> list[PullRequestRef]:
        if repository is not None:
            repository = canonical_repository(repository)
            rows = self._pages(f"repos/{repository}/issues", "-f", f"labels={label}", "-f", "state=open")
            numbers = {int(row["number"]) for row in rows if row.get("pull_request")}
            if any(number <= 0 for number in numbers):
                raise RuntimeError("GitHub returned an invalid pull request number")
            return [PullRequestRef(repository, number) for number in sorted(numbers)]
        raise ValueError("repository binding is required; global search is not authoritative")

    def read_pull_request(self, repository: str, number: int) -> PullRequestSnapshot:
        repository = canonical_repository(repository)
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise ValueError("pr_number must be positive")
        row = self._api(f"repos/{repository}/pulls/{number}")
        base = row.get("base", {})
        head = row.get("head", {})
        head_repo = (head.get("repo") or {}).get("full_name") or head.get("repo", {}).get("nameWithOwner")
        base_ref = _canonical_ref(base.get("ref", ""), "base_ref")
        base_tip = self._api(f"repos/{repository}/git/ref/heads/{quote(base_ref, safe='')}")
        if base_tip.get("ref") != f"refs/heads/{base_ref}" or base_tip.get("object", {}).get("type") != "commit":
            raise RuntimeError("GitHub returned an invalid base-ref tip")
        return PullRequestSnapshot(repository, number, row.get("state") == "open", bool(row.get("draft")),
            base_ref, base_tip.get("object", {}).get("sha", ""), head_repo or "", head.get("ref", ""), head.get("sha", ""), row.get("updated_at", ""))

    def list_issue_comments(self, repository: str, number: int) -> list[IssueComment]:
        rows = self._pages(f"repos/{canonical_repository(repository)}/issues/{int(number)}/comments")
        return [IssueComment(int(row["id"]), row.get("body", ""), (row.get("user") or {}).get("login", ""), row.get("updated_at", "")) for row in rows]

    def read_required_check_policy(self, repository: str, base_ref: str, base_tip: str) -> dict[str, Any]:
        """Read only producer-bound required checks for one current base tip.

        The caller must persist the returned source/evidence and re-read it at
        Read D/E.  Legacy ``contexts`` entries and workflow rules are rejected
        instead of being guessed into an App identity.
        """
        repository = canonical_repository(repository)
        base_ref = _canonical_ref(base_ref, "base_ref")
        if not FULL_SHA_RE.fullmatch(base_tip):
            raise ValueError("invalid base tip")
        rules = self._pages(f"repos/{repository}/rules/branches/{quote(base_ref, safe='')}" , "-f", "per_page=100")
        protection = self._api(f"repos/{repository}/branches/{quote(base_ref, safe='')}/protection")
        required: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        for rule in rules:
            if not isinstance(rule, dict):
                raise RuntimeError("invalid ruleset response")
            rule_type = rule.get("type")
            if rule_type == "workflows":
                raise RuntimeError("unsupported required workflow policy")
            if rule_type != "required_status_checks":
                continue
            checks = (rule.get("parameters") or {}).get("required_status_checks", rule.get("required_status_checks", []))
            for check in checks:
                app_id = check.get("integration_id")
                if not isinstance(check.get("context"), str) or type(app_id) is not int or app_id <= 0:
                    raise RuntimeError("unreadable producer-bound ruleset")
                required.append({"name": check["context"], "app_id": app_id})
            sources.append({"kind": "ruleset", "id": rule.get("id"), "source": rule.get("source")})
        status = (protection or {}).get("required_status_checks") if isinstance(protection, dict) else None
        if status is not None:
            checks = status.get("checks")
            if not isinstance(checks, list):
                raise RuntimeError("unreadable branch protection policy")
            if status.get("contexts"):
                raise RuntimeError("legacy context-only policy is unsupported")
            for check in checks:
                app_id = check.get("app_id")
                if not isinstance(check.get("context"), str) or type(app_id) is not int or app_id <= 0:
                    raise RuntimeError("unreadable producer-bound protection")
                required.append({"name": check["context"], "app_id": app_id})
            sources.append({"kind": "branch_protection", "id": repository, "source": "protection"})
        tuples = {(item["name"], item["app_id"]) for item in required}
        if not tuples or len(tuples) != len({item["name"] for item in required}):
            raise RuntimeError("required-check policy is empty or ambiguous")
        return {"base_ref": base_ref, "base_tip": base_tip,
                "required": sorted(required, key=lambda item: (item["name"], item["app_id"])),
                "sources": sources}

    def read_check_suites(self, repository: str, head_sha: str) -> list[dict[str, Any]]:
        repository = canonical_repository(repository)
        if not FULL_SHA_RE.fullmatch(head_sha):
            raise ValueError("invalid head sha")
        return self._pages(f"repos/{repository}/commits/{head_sha}/check-suites", "-f", "per_page=100")

    def read_check_suite(self, repository: str, suite_id: int) -> dict[str, Any]:
        return self._api(f"repos/{canonical_repository(repository)}/check-suites/{int(suite_id)}")

    def read_check_runs(self, repository: str, suite_id: int, *, filter: str = "all") -> list[dict[str, Any]]:
        if filter != "all":
            raise ValueError("v1.1.3 requires filter=all")
        rows = self._pages(f"repos/{canonical_repository(repository)}/check-suites/{int(suite_id)}/check-runs", "-f", "per_page=100", "-f", "filter=all")
        return rows


def canonical_repository(value: str) -> str:
    value = str(value).strip().lower()
    if not REPOSITORY_RE.fullmatch(value) or ".git" in value:
        raise ValueError("invalid canonical repository")
    return value


def _canonical_ref(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid {name}")
    if not value or value != value.strip() or "\n" in value or "\x00" in value:
        raise ValueError(f"invalid {name}")
    if (".." in value or value.startswith(("/", "-")) or value.endswith(("/", "."))
            or "//" in value or value == "@" or "@{" in value
            or any(c in value for c in " ~^:?*[\\")
            or any(part.startswith(".") or part.endswith(".lock") for part in value.split("/"))):
        raise ValueError(f"invalid {name}")
    if any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError(f"invalid {name}")
    return value


def normalize_review_identity(*, repository: str, pr_number: int, base_ref: str,
                              base_sha: str, head_repository: str, head_ref: str,
                              head_sha: str) -> dict[str, Any]:
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number <= 0:
        raise ValueError("pr_number must be a positive integer")
    if not FULL_SHA_RE.fullmatch(base_sha) or not FULL_SHA_RE.fullmatch(head_sha):
        raise ValueError("full lowercase SHAs are required")
    return {"schema_version": 1, "repository": canonical_repository(repository),
            "pr_number": pr_number, "base_ref": _canonical_ref(base_ref, "base_ref"),
            "base_sha": base_sha, "head_repository": canonical_repository(head_repository),
            "head_ref": _canonical_ref(head_ref, "head_ref"), "head_sha": head_sha}


def review_key_preimage(identity: Mapping[str, Any]) -> str:
    normalized = normalize_review_identity(**{k: identity[k] for k in (
        "repository", "pr_number", "base_ref", "base_sha",
        "head_repository", "head_ref", "head_sha")})
    return "\n".join(("1", normalized["repository"], str(normalized["pr_number"]),
                      normalized["base_ref"], normalized["base_sha"],
                      normalized["head_repository"], normalized["head_ref"],
                      normalized["head_sha"]))


def compute_review_key(identity: Mapping[str, Any]) -> str:
    return hashlib.sha256(review_key_preimage(identity).encode("utf-8")).hexdigest()


def parse_request_comment(body: str) -> dict[str, Any]:
    """Parse exactly one marker followed by one JSON fenced block."""
    if not isinstance(body, str) or not body.startswith(REVIEW_REQUEST_MARKER + "\n"):
        raise ValueError("REQUEST_COMMENT_MISSING")
    tail = body[len(REVIEW_REQUEST_MARKER):].strip()
    match = re.fullmatch(r"```json[ \t]*\n(.*?)\n```", tail, re.DOTALL)
    if not match or tail.count("```") != 2:
        raise ValueError("MALFORMED_REQUEST")
    duplicate = False
    def hook(pairs):
        nonlocal duplicate
        result = {}
        for key, value in pairs:
            if key in result:
                duplicate = True
            result[key] = value
        return result
    try:
        value = json.loads(match.group(1), object_pairs_hook=hook)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("MALFORMED_REQUEST") from exc
    if duplicate or not isinstance(value, dict) or type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise ValueError("MALFORMED_REQUEST")
    required = {"review_key", "repository", "pr_number", "base_ref", "base_sha",
                "head_repository", "head_ref", "head_sha", "requested_at", "handoff"}
    if not required <= value.keys() or not REVIEW_KEY_RE.fullmatch(str(value["review_key"])):
        raise ValueError("MALFORMED_REQUEST")
    if (isinstance(value.get("pr_number"), bool) or not isinstance(value.get("pr_number"), int)
            or value["pr_number"] <= 0):
        raise ValueError("MALFORMED_REQUEST")
    try:
        normalized = normalize_review_identity(**{key: value[key] for key in (
            "repository", "pr_number", "base_ref", "base_sha",
            "head_repository", "head_ref", "head_sha")})
    except (TypeError, ValueError) as exc:
        raise ValueError("MALFORMED_REQUEST") from exc
    handoff = value.get("handoff")
    if not isinstance(value.get("requested_at"), str):
        raise ValueError("MALFORMED_REQUEST")
    try:
        datetime.fromisoformat(value["requested_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("MALFORMED_REQUEST") from exc
    if not isinstance(handoff, Mapping) or not isinstance(handoff.get("summary"), str) or not handoff["summary"].strip():
        raise ValueError("MALFORMED_REQUEST")
    for field_name in ("changed_files", "test_commands", "known_risks"):
        items = handoff.get(field_name)
        if not isinstance(items, list) or len(items) > 200 or not all(isinstance(item, str) and item.strip() for item in items):
            raise ValueError("MALFORMED_REQUEST")
        if field_name == "changed_files" and any(item.startswith(("/", "\\")) or ".." in item.split("/") for item in items):
            raise ValueError("MALFORMED_REQUEST")
    if value["review_key"] != compute_review_key(normalized):
        raise ValueError("REQUEST_MISMATCH")
    return {**value, **normalized}


def binding_fingerprint(*, repository: str, project_id: str, board_slug: str,
                        orchestration_profile: str, binding_revision: int) -> str:
    """Hash the exact six-field Schema-1 authority preimage."""
    if isinstance(binding_revision, bool) or int(binding_revision) <= 0:
        raise ValueError("binding_revision must be positive")
    fields = ("binding/v1", canonical_repository(repository), str(project_id),
              str(board_slug), str(orchestration_profile), str(int(binding_revision)))
    if any(not field or any(unicodedata.category(c).startswith("C") for c in field) for field in fields):
        raise ValueError("invalid binding authority field")
    return hashlib.sha256("\n".join(fields).encode("utf-8")).hexdigest()


def validate_runtime_config(config: Mapping[str, Any]) -> dict[str, Any]:
    section = config.get("kanban", {}).get("github_pr_review", {}) if isinstance(config, Mapping) else {}
    expected = {"interval_seconds": 300, "label": "hermes-review-requested",
                "request_marker": REVIEW_REQUEST_MARKER, "result_marker": REVIEW_RESULT_MARKER}
    errors = [key for key, value in expected.items() if section.get(key, value) != value]
    return {"valid": not errors, "errors": errors, "enabled": section.get("enabled", False)}


def validate_required_ci(snapshot: Mapping[str, Any]) -> str:
    """Return PASS only for a complete successful required-check snapshot."""
    if not snapshot.get("readable", False):
        return "BLOCKED"
    checks = snapshot.get("checks")
    required = snapshot.get("required")
    if not isinstance(checks, list) or not isinstance(required, list) or not required:
        return "MISSING"
    required_tuples = []
    for item in required:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str) or type(item.get("app_id")) is not int or item["app_id"] <= 0:
            return "BLOCKED"
        required_tuples.append((item["name"], item["app_id"]))
    if len(required_tuples) != len(set(required_tuples)):
        return "MISSING"
    matches = []
    candidate_head = snapshot.get("head_sha")
    if not isinstance(candidate_head, str) or not FULL_SHA_RE.fullmatch(candidate_head):
        return "BLOCKED"
    for name, app_id in required_tuples:
        named = [item for item in checks if isinstance(item, Mapping) and item.get("name") == name]
        if len(named) != 1:
            return "FAIL" if named else "MISSING"
        if named[0].get("app_id") != app_id:
            return "FAIL"
        matches.append(named[0])
    if any(item.get("status") in {"queued", "in_progress", "waiting", "requested", "pending"} for item in matches):
        return "PENDING"
    if any(item.get("status") != "completed" or item.get("conclusion") != "success" or item.get("head_sha") != candidate_head for item in matches):
        return "FAIL"
    return "PASS"


def remediation_eligibility(conditions: Mapping[str, bool]) -> dict[str, Any]:
    names = ("documented_finding", "scope_unchanged", "no_new_product_requirement",
             "no_new_architecture", "no_public_api_change", "no_schema_change",
             "no_security_boundary_change", "no_external_integration", "verifiable_completion",
             "existing_pr_branch_only", "trusted_head_cas", "bounded_separate_worker")
    values = {name: conditions.get(name) is True for name in names}
    return {"eligible": all(values.values()), "conditions": values,
            "failure": None if all(values.values()) else "REMEDIATION_INELIGIBLE"}


def validate_state(lifecycle: str, gate: str, admission: str) -> None:
    if lifecycle not in LIFECYCLE_STATES or gate not in GATE_STATES or admission not in ADMISSION_STATES:
        raise ValueError("invalid PR review state")
    if gate == "PASS" and lifecycle in {"STALE", "BLOCKED"}:
        raise ValueError("STALE/BLOCKED lifecycle cannot authorize PASS")
    if admission == "PENDING_READ_C" and lifecycle not in {"DISCOVERED", "CLAIMED"}:
        raise ValueError("pending admission has invalid lifecycle")
    if admission == "MATERIALIZING_TASK" and lifecycle not in {"CLAIMED", "IN_REVIEW"}:
        raise ValueError("materializing admission has invalid lifecycle")
    if admission == "MATERIALIZED" and lifecycle not in {"IN_REVIEW", "COMPLETED", "REMEDIATION_PENDING", "REMEDIATING", "REREVIEW_REQUESTED"}:
        raise ValueError("materialized admission has invalid lifecycle")


@dataclass(frozen=True)
class PollReport:
    candidates: tuple[dict[str, Any], ...] = ()
    processed: tuple[dict[str, Any], ...] = ()
    writes_performed: int = 0
    dry_run: bool = False
    errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"candidates": list(self.candidates), "processed": list(self.processed),
                "writes_performed": self.writes_performed, "dry_run": self.dry_run,
                "errors": list(self.errors)}


class DispatcherBindingError(RuntimeError):
    """A repository binding is absent, ambiguous, or no longer authoritative."""


def _invoke(obj: Any, names: Sequence[str], *args: Any, **kwargs: Any) -> Any:
    """Call one of an adapter's explicitly named port methods.

    Ports are deliberately duck-typed so the CLI, gateway, and isolated tests can
    assemble the same controller without importing a particular board client.
    No fallback value is returned: an absent port is a configuration failure.
    """
    for name in names:
        method = getattr(obj, name, None)
        if callable(method):
            return method(*args, **kwargs)
    raise DispatcherBindingError(f"adapter port unavailable: {'/'.join(names)}")


def _dispatcher_state_db() -> Path:
    root = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    return root / "kanban" / "github-pr-review-dispatcher.db"


def _init_dispatcher_state(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS review_cycles (
        review_key TEXT PRIMARY KEY, repository TEXT NOT NULL, pr_number INTEGER NOT NULL,
        head_sha TEXT NOT NULL, lifecycle TEXT NOT NULL, admission TEXT NOT NULL,
        task_id TEXT, binding_fingerprint TEXT NOT NULL, updated_at INTEGER NOT NULL,
        UNIQUE(repository, pr_number, review_key))""")
    return conn


def _binding_for(bindings: Any, repository: str) -> Mapping[str, Any]:
    value = _invoke(bindings, ("resolve_repository", "resolve_binding", "binding_for"), repository)
    if not isinstance(value, Mapping):
        raise DispatcherBindingError("repository binding response is not an object")
    required = ("project_id", "board", "orchestration_profile", "binding_revision")
    if any(not value.get(k) for k in required):
        raise DispatcherBindingError("repository binding is incomplete")
    # This workflow is intentionally exact: no current-board/name/default lookup.
    if value["project_id"] != "p_41500605" or value["board"] != "hermes-system":
        raise DispatcherBindingError("repository binding is not the configured project/board")
    return value


class HermesProjectBindingAdapter:
    """Explicit profile-scoped project/board port for the native Kanban store."""

    def resolve_repository(self, repository: str) -> Mapping[str, Any]:
        from hermes_cli import projects_db
        with projects_db.connect_closing() as conn:
            binding = projects_db.get_repository_binding(conn, canonical_repository(repository), enabled_only=True)
            if not binding or binding["project_id"] != "p_41500605":
                raise DispatcherBindingError("enabled repository binding is absent")
            project = conn.execute("SELECT board_slug FROM projects WHERE id=?", (binding["project_id"],)).fetchone()
            if not project or project["board_slug"] != "hermes-system":
                raise DispatcherBindingError("project board authority is not hermes-system")
            return {**binding, "board": "hermes-system"}

    def create_native_task(self, identity: Mapping[str, Any], review_key: str, binding: Mapping[str, Any]) -> Mapping[str, Any]:
        from hermes_cli import kanban_db as kb
        from hermes_cli import kanban_db_connect as kbc
        body = json.dumps({"schema_version": 1, "review_key": review_key, "identity": dict(identity)}, sort_keys=True)
        with kbc.connect_closing(board="hermes-system") as conn:
            task_id = kb.create_task(conn, title=f"Review PR #{identity['pr_number']}", body=body,
                assignee=str(binding["orchestration_profile"]), created_by="github-pr-review",
                idempotency_key=review_key, triage=True, initial_status="triage",
                board="hermes-system", project_id="p_41500605")
            return {"id": task_id, "review_key": review_key}

    def read_native_task(self, task_id: str, binding: Mapping[str, Any]) -> Mapping[str, Any]:
        from hermes_cli import kanban_db as kb
        from hermes_cli import kanban_db_connect as kbc
        with kbc.connect_closing(board="hermes-system") as conn:
            task = kb.get_task(conn, task_id)
            if task is None:
                raise RuntimeError("native task readback missing")
            return {"id": task.id, "review_key": task.idempotency_key, "status": task.status,
                    "assignee": task.assignee, "project_id": task.project_id}

    def dispatch_native_task(self, task_id: str, binding: Mapping[str, Any]) -> Mapping[str, Any]:
        from hermes_cli import kanban_db_dispatch as kbd
        from hermes_cli import kanban_db_connect as kbc
        with kbc.connect_closing(board="hermes-system") as conn:
            result = kbd.dispatch_once(conn, dry_run=False)
            return {"spawned": getattr(result, "spawned", [])}


def assemble_dispatcher_adapters() -> tuple[GitHubCLI, HermesProjectBindingAdapter]:
    """Build the one shared adapter assembly used by CLI and Gateway."""
    return GitHubCLI(), HermesProjectBindingAdapter()


def _read_cycle(conn: sqlite3.Connection, key: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM review_cycles WHERE review_key=?", (key,)).fetchone()


def _persist_cycle(conn: sqlite3.Connection, identity: Mapping[str, Any], key: str,
                   binding: Mapping[str, Any], *, lifecycle: str, admission: str,
                   task_id: str | None = None) -> None:
    conn.execute("""INSERT INTO review_cycles
        (review_key,repository,pr_number,head_sha,lifecycle,admission,task_id,
         binding_fingerprint,updated_at) VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(review_key) DO UPDATE SET lifecycle=excluded.lifecycle,
         admission=excluded.admission, task_id=COALESCE(excluded.task_id,task_id),
         updated_at=excluded.updated_at""", (
        key, identity["repository"], identity["pr_number"], identity["head_sha"],
        lifecycle, admission, task_id,
        binding_fingerprint(repository=identity["repository"], project_id=str(binding["project_id"]),
                            board_slug=str(binding["board"]), orchestration_profile=str(binding["orchestration_profile"]),
                            binding_revision=int(binding["binding_revision"])), int(time.time())))


def _claim_materialization(conn: sqlite3.Connection, key: str) -> bool:
    """CAS the durable cycle into its single native-task write owner."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        changed = conn.execute(
            "UPDATE review_cycles SET lifecycle='MATERIALIZING_TASK', admission='MATERIALIZING_TASK', updated_at=? "
            "WHERE review_key=? AND task_id IS NULL AND (lifecycle='CLAIMED' OR (lifecycle='MATERIALIZING_TASK' AND updated_at < ?))", (int(time.time()), key, int(time.time()) - 300)
        ).rowcount
        conn.commit()
        return changed == 1
    except Exception:
        conn.rollback()
        raise


def _process_review(ref: PullRequestRef, github: Any, bindings: Any, conn: sqlite3.Connection | None,
                    *, dry_run: bool) -> dict[str, Any]:
    """Run Read A–E and native admission for one candidate.

    Every mutating port is reached only after identity, binding, policy, and
    producer-bound CI checks have been re-read.  Existing cycles are reconciled
    before another task creation attempt, which covers unknown-write recovery.
    """
    first = _invoke(github, ("read_pull_request",), ref.repository, ref.number)
    if not isinstance(first, PullRequestSnapshot) or not first.open or first.draft:
        return {"repository": ref.repository, "pr_number": ref.number, "status": "STALE"}
    identity = normalize_review_identity(repository=first.repository, pr_number=first.number,
        base_ref=first.base_ref, base_sha=first.base_sha, head_repository=first.head_repository,
        head_ref=first.head_ref, head_sha=first.head_sha)
    key = compute_review_key(identity)
    comments = _invoke(github, ("list_issue_comments",), identity["repository"], identity["pr_number"])
    request_comments = [comment for comment in comments if REVIEW_REQUEST_MARKER in getattr(comment, "body", "")]
    if len(request_comments) != 1:
        raise RuntimeError("request comment identity is ambiguous")
    request = parse_request_comment(request_comments[0].body)
    if request["review_key"] != key:
        raise RuntimeError("request comment is stale")
    binding = _binding_for(bindings, identity["repository"])
    fp = binding_fingerprint(repository=identity["repository"], project_id=str(binding["project_id"]),
                              board_slug=str(binding["board"]), orchestration_profile=str(binding["orchestration_profile"]),
                              binding_revision=int(binding["binding_revision"]))
    existing = _read_cycle(conn, key) if conn is not None else None
    if existing and existing["binding_fingerprint"] != fp:
        raise DispatcherBindingError("cycle binding fingerprint changed")
    policy = _invoke(github, ("read_required_check_policy",), identity["repository"], identity["base_ref"], identity["base_sha"])
    suites = _invoke(github, ("read_check_suites",), identity["repository"], identity["head_sha"])
    checks: list[dict[str, Any]] = []
    for suite in suites:
        sid = suite.get("id") if isinstance(suite, Mapping) else None
        if not isinstance(sid, int):
            raise RuntimeError("invalid check suite identity")
        observed = _invoke(github, ("read_check_suite",), identity["repository"], sid)
        runs = _invoke(github, ("read_check_runs",), identity["repository"], sid, filter="all")
        for run in runs:
            if isinstance(run, Mapping):
                checks.append({"name": run.get("name"), "app_id": (run.get("app") or {}).get("id", run.get("app_id")),
                               "status": run.get("status"), "conclusion": run.get("conclusion"),
                               "head_sha": run.get("head_sha"), "suite_id": observed.get("id", sid)})
    ci = validate_required_ci({"readable": True, "head_sha": identity["head_sha"],
                               "required": policy.get("required", []), "checks": checks})
    if ci != "PASS":
        raise RuntimeError(f"required CI is {ci}")
    # Read D immediately before admission.  A second PR read catches ref/base drift.
    second = _invoke(github, ("read_pull_request",), ref.repository, ref.number)
    if second != first:
        raise RuntimeError("PR identity drift at Read D")
    if not existing and not dry_run:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _persist_cycle(conn, identity, key, binding, lifecycle="CLAIMED", admission="PENDING_READ_C")
            conn.commit()
        except Exception:
            conn.rollback(); raise
    if dry_run:
        return {"repository": identity["repository"], "pr_number": identity["pr_number"], "review_key": key,
                "status": "READY", "ci": ci, "dry_run": True}
    if existing is not None and existing["task_id"]:
        recovered = _invoke(bindings, ("read_native_task", "read_task"), existing["task_id"], binding)
        if isinstance(recovered, Mapping) and recovered.get("id") == existing["task_id"]:
            return {"repository": identity["repository"], "pr_number": identity["pr_number"],
                    "review_key": key, "status": "DISPATCHED", "task_id": existing["task_id"],
                    "recovered": True, "ci": ci}
    # Read C and native task creation/readback are delegated to configured Hermes ports.
    current = _invoke(github, ("read_pull_request",), ref.repository, ref.number)
    if current != first:
        raise RuntimeError("PR identity drift at Read C")
    assert conn is not None
    if not _claim_materialization(conn, key):
        raise RuntimeError("cycle is already claimed by another poller")
    task = _invoke(bindings, ("create_native_task", "create_task"), identity, key, binding)
    task_id = task.get("id") if isinstance(task, Mapping) else task
    if not isinstance(task_id, str):
        raise RuntimeError("native task creation returned no task id")
    readback = _invoke(bindings, ("read_native_task", "read_task"), task_id, binding)
    if not isinstance(readback, Mapping) or readback.get("id") != task_id or readback.get("review_key", key) != key:
        raise RuntimeError("native task readback mismatch")
    conn.execute("BEGIN IMMEDIATE")
    try:
        _persist_cycle(conn, identity, key, binding, lifecycle="TASK_CREATED", admission="MATERIALIZED", task_id=task_id)
        conn.commit()
    except Exception:
        conn.rollback(); raise
    _invoke(bindings, ("dispatch_native_task", "dispatch_task"), task_id, binding)
    return {"repository": identity["repository"], "pr_number": identity["pr_number"], "review_key": key,
            "status": "DISPATCHED", "task_id": task_id, "ci": ci}


def poll_once(*, github: Any = None, bindings: Any = None, dry_run: bool = False,
              repository: str | None = None, max_candidates: int = 50) -> PollReport:
    """Deterministic poll entry point; adapters own all external side effects.

    The default is intentionally read-only and returns no candidates when ports
    are not supplied.  Production wiring must inject both ports explicitly.
    """
    if github is None or bindings is None:
        # A null adapter set is an integration failure, not an empty queue.  In
        # particular, the gateway must not report a successful no-op while the
        # production repository/project/board adapter is absent.
        return PollReport(dry_run=dry_run, errors=("ADAPTERS_NOT_CONFIGURED",))
    refs = _invoke(github, ("list_candidates",), repository, "hermes-review-requested")
    refs = sorted(refs, key=lambda ref: (str(ref.repository).lower(), int(ref.number)))[:max_candidates]
    processed = []
    errors = []
    state = None if dry_run else _init_dispatcher_state(_dispatcher_state_db())
    try:
        for ref in refs:
            item = {"repository": canonical_repository(ref.repository), "pr_number": int(ref.number)}
            try:
                result = _process_review(ref, github, bindings, state, dry_run=dry_run)
                processed.append({**item, **result})
            except Exception as exc:
                errors.append(f"{item['repository']}#{item['pr_number']}: {type(exc).__name__}")
                processed.append({**item, "status": "BLOCKED"})
    finally:
        if state is not None:
            state.close()
    writes = sum(1 for item in processed if item.get("status") in {"DISPATCHED"})
    return PollReport(tuple(processed), tuple(processed), writes, dry_run, tuple(errors))
