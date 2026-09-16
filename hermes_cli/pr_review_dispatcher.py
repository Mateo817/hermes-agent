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
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows
    fcntl = None

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
        if fcntl is None:  # conservative: no unverified Windows fallback here
            raise RuntimeError("exclusive lock unavailable")
        try: fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise RuntimeError("controller lock is busy") from exc
        try: yield
        finally: fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


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
        if fcntl is None:
            raise RuntimeError("exclusive intent lock unavailable")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


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
ADMISSION_STATES = frozenset({"PENDING_READ_C", "PROMOTED", "STALE"})


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
    """Small authenticated GitHub port backed by ``gh api`` argument lists."""

    def __init__(self, executable: str = "gh", timeout: int = 30):
        self.executable, self.timeout = executable, timeout

    def _api(self, *parts: str) -> Any:
        argv = [self.executable, "api", *parts]
        try:
            result = subprocess.run(argv, shell=False, check=True, text=True,
                                    encoding="utf-8", capture_output=True, timeout=self.timeout)
            return json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise RuntimeError("GitHub API operation failed") from exc

    def list_candidates(self, repository: str | None, label: str) -> list[PullRequestRef]:
        if repository is not None:
            repository = canonical_repository(repository)
            rows = self._api(f"repos/{repository}/issues", "-f", f"labels={label}", "-f", "state=open", "--paginate")
            rows = rows if isinstance(rows, list) else []
            return [PullRequestRef(repository, int(row["number"])) for row in rows if row.get("pull_request")]
        raise ValueError("repository binding is required; global search is not authoritative")

    def read_pull_request(self, repository: str, number: int) -> PullRequestSnapshot:
        repository = canonical_repository(repository)
        row = self._api(f"repos/{repository}/pulls/{int(number)}")
        base = row.get("base", {})
        head = row.get("head", {})
        head_repo = (head.get("repo") or {}).get("full_name") or head.get("repo", {}).get("nameWithOwner")
        return PullRequestSnapshot(repository, int(number), row.get("state") == "open", bool(row.get("draft")),
            base.get("ref", ""), base.get("sha", ""), head_repo or "", head.get("ref", ""), head.get("sha", ""), row.get("updated_at", ""))

    def list_issue_comments(self, repository: str, number: int) -> list[IssueComment]:
        rows = self._api(f"repos/{canonical_repository(repository)}/issues/{int(number)}/comments", "--paginate")
        return [IssueComment(int(row["id"]), row.get("body", ""), (row.get("user") or {}).get("login", ""), row.get("updated_at", "")) for row in (rows if isinstance(rows, list) else [])]


def canonical_repository(value: str) -> str:
    value = str(value).strip().lower()
    if not REPOSITORY_RE.fullmatch(value) or ".git" in value:
        raise ValueError("invalid canonical repository")
    return value


def _canonical_ref(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid {name}")
    value = unicodedata.normalize("NFC", value)
    if not value or value != value.strip() or "\n" in value or "\x00" in value:
        raise ValueError(f"invalid {name}")
    if ".." in value or value.startswith("/") or value.endswith("/") or "//" in value:
        raise ValueError(f"invalid {name}")
    if any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError(f"invalid {name}")
    return value


def normalize_review_identity(*, repository: str, pr_number: int, base_ref: str,
                              base_sha: str, head_repository: str, head_ref: str,
                              head_sha: str) -> dict[str, Any]:
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number <= 0:
        raise ValueError("pr_number must be a positive integer")
    base_sha = str(base_sha).lower()
    head_sha = str(head_sha).lower()
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
    if not isinstance(body, str) or not body.startswith(REVIEW_REQUEST_MARKER):
        raise ValueError("REQUEST_COMMENT_MISSING")
    tail = body[len(REVIEW_REQUEST_MARKER):].strip()
    match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", tail, re.DOTALL)
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
    if duplicate or not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("MALFORMED_REQUEST")
    required = {"review_key", "repository", "pr_number", "base_ref", "base_sha",
                "head_repository", "head_ref", "head_sha", "requested_at", "handoff"}
    if not required <= value.keys() or not REVIEW_KEY_RE.fullmatch(str(value["review_key"])):
        raise ValueError("MALFORMED_REQUEST")
    if (isinstance(value.get("pr_number"), bool) or not isinstance(value.get("pr_number"), int)
            or value["pr_number"] <= 0):
        raise ValueError("MALFORMED_REQUEST")
    try:
        normalize_review_identity(**{key: value[key] for key in (
            "repository", "pr_number", "base_ref", "base_sha",
            "head_repository", "head_ref", "head_sha")})
    except (TypeError, ValueError) as exc:
        raise ValueError("MALFORMED_REQUEST") from exc
    handoff = value.get("handoff")
    if not isinstance(handoff, Mapping) or not isinstance(handoff.get("summary"), str):
        raise ValueError("MALFORMED_REQUEST")
    return value


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
    names = [str(item.get("name")) for item in checks if isinstance(item, Mapping)]
    if len(names) != len(set(names)) or any(name not in names for name in required):
        return "MISSING"
    if any(item.get("conclusion") not in {"success"} for item in checks if item.get("name") in required):
        return "FAIL" if any(item.get("conclusion") in {"failure", "cancelled", "timed_out", "action_required"} for item in checks) else "PENDING"
    return "PASS"


def remediation_eligibility(conditions: Mapping[str, bool]) -> dict[str, Any]:
    names = ("small_findings", "unique_source", "limited_change", "complete_todo",
             "trusted_head", "safe_branch", "current_cas", "exclusive_serialization",
             "separate_identities", "verifiable_completion")
    values = {name: conditions.get(name) is True for name in names}
    return {"eligible": all(values.values()), "conditions": values,
            "failure": None if all(values.values()) else "REMEDIATION_INELIGIBLE"}


def validate_state(lifecycle: str, gate: str, admission: str) -> None:
    if lifecycle not in LIFECYCLE_STATES or gate not in GATE_STATES or admission not in ADMISSION_STATES:
        raise ValueError("invalid PR review state")
    if gate == "PASS" and lifecycle in {"STALE", "BLOCKED"}:
        raise ValueError("STALE/BLOCKED lifecycle cannot authorize PASS")
    if admission == "PROMOTED" and lifecycle not in {"IN_REVIEW", "REMEDIATION_PENDING", "REMEDIATING", "REREVIEW_REQUESTED", "COMPLETED"}:
        raise ValueError("promoted admission has invalid lifecycle")


@dataclass(frozen=True)
class PollReport:
    candidates: tuple[dict[str, Any], ...] = ()
    processed: tuple[dict[str, Any], ...] = ()
    writes_performed: int = 0
    dry_run: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"candidates": list(self.candidates), "processed": list(self.processed),
                "writes_performed": self.writes_performed, "dry_run": self.dry_run}


def poll_once(*, github: Any = None, bindings: Any = None, dry_run: bool = False,
              repository: str | None = None, max_candidates: int = 50) -> PollReport:
    """Deterministic poll entry point; adapters own all external side effects.

    The default is intentionally read-only and returns no candidates when ports
    are not supplied.  Production wiring must inject both ports explicitly.
    """
    if github is None or bindings is None:
        return PollReport(dry_run=dry_run)
    refs = github.list_candidates(repository, "hermes-review-requested")
    refs = sorted(refs, key=lambda ref: (str(ref.repository).lower(), int(ref.number)))[:max_candidates]
    processed = []
    for ref in refs:
        processed.append({"repository": canonical_repository(ref.repository), "pr_number": int(ref.number),
                          "dry_run": dry_run, "status": "CANDIDATE"})
    return PollReport(tuple(processed), tuple(processed), 0 if dry_run else 0, dry_run)
