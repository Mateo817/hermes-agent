# Deterministischer GitHub-PR-Review-Dispatcher: Architekturvertrag

Status: revidierter Vorimplementierungsvertrag, Schema 1; Implementierung bis gebundenem Independent-PASS verboten
Vertragsversion: `github-pr-review-dispatcher/v1.1.0`
Architektur-Task: `t_8a99f79d` (Remediation von `t_48b63e1b`)
Inventar-Task: `t_58d44561`
Inventarisierte Upstream-Revision: `682a95258ce9e877cfb607a5ada6436183efdebb`
Inventar: `github-kanban-scheduler-inventory-2026-09-16.md`, 19149 Bytes, SHA-256 `bc29b43dc5c556698b3f3ecb0c0442a45c794cc847695039b6d04f0a90676d2f`
Kanonisches Upstream-/Basis-Repository: GitHub `NousResearch/hermes-agent`; saubere Remediation-Basis nach erneutem Remote-Fetch am 2026-09-16: `741fa6acc1545f0d1cd307ea96f0cba7023ad450`
Dauerhaftes Publikations-Repository: GitHub `Mateo817/hermes-agent`, von GitHub als Fork von `NousResearch/hermes-agent` ausgewiesen; autoritativer Nicht-Default-Ref: `refs/heads/contracts/github-pr-review-dispatcher-v1.1.0-base-741fa6a`
Verworfene Evidenzbindung (keine Autoritaet): Commit `bf2c55cdd8777d0c3e45095ea3a76e939d33fc5e`, Ref `refs/heads/contracts/github-pr-review-dispatcher-v1.0.0`, Blob-SHA-256 `4108af3c8a8abd75c98acf165a2843301e4a5287a32865aff89b9c81a7dccb39`, verbotener Parent `aad0cbd55e9fef41cad79f7ca6f75b0e14a74ff6`
Byte-identischer Transfer auf sauberer Basis: Commit `ca1ebca7097461383301f5b66b90795c3ad3bde4`, SHA-256 erneut `4108af3c8a8abd75c98acf165a2843301e4a5287a32865aff89b9c81a7dccb39`

## 1. Zweck, Geltung und harte Grenzen

Dieser Vertrag definiert genau eine minimale Integrationsfläche für einen deterministischen, modellfreien Poller, der explizit angeforderte GitHub-Pull-Request-Reviews als bestehende Hermes-Kanban-Aufgaben materialisiert. Er ist revisionsgebunden an das oben bezeichnete Inventar; die Implementierung muss Abweichungen zur tatsächlichen Implementierungsbasis erneut prüfen.

Dieser Text allein autorisiert keine Implementierung. Die einzige Implementierungsfreigabe ist ein explizites `PASS` des fuer diesen Vertrag vorgeschriebenen unabhaengigen Reviewers `agency-security-reviewer` zu einem externen Release-Manifest. Das Manifest nennt die beiden kanonischen GitHub-Repository-Identitaeten (Upstream/Basis und Publikation) sowie exakt diese fuenf Bindungswerte: finaler voller Contract-Commit-SHA, dauerhaft publizierter Nicht-Default-Ref, dieser Pfad, finaler Blob-SHA-256 und unmittelbar vorher frisch gelesener Upstream-`main`-Basis-SHA. Lokale Remote-Namen wie `origin`, `upstream` oder `fork` sind Aliase und tragen keine Autoritaet. Fehlt ein Wert, weicht er ab, ist der Ref im genannten Publikations-Repository nicht remote lesbar, ist dessen Fork-Beziehung zum genannten Upstream nicht belegbar oder nennt das PASS nur die verworfene Evidenzbindung, bleibt die Implementierung verboten.

Normative Begriffe `MUSS`, `DARF NICHT`, `SOLL` und `KANN` sind verbindlich. Bei fehlenden, widersprüchlichen oder mehrdeutigen Daten gilt fail-closed: keine Task-Erzeugung, keine Review-Freigabe und keine Branch-Mutation.

Feststehende Grenzen:

- Trigger sind gleichzeitig das GitHub-Label `hermes-review-requested` und genau ein stabiler Issue-Kommentar mit `<!-- hermes-review-request -->` und Schema 1.
- Der Poller liest Repository, PR, Base und Head selbst von GitHub. Kommentarwerte sind Behauptungen, keine Autorität.
- Pro Review-Key existiert höchstens ein Review-Zyklus.
- Routing erfolgt ausschließlich über eine eindeutige Repository→Hermes-Projekt→Kanban-Board→konfigurierte-Orchestrierung-Bindung.
- Es gibt keinen Namensheuristik-, aktuellen-Board-, `default`-, `hermes-system`-, letzten-Board- oder globalen Orchestrator-Fallback.
- Der Poller wählt und setzt keine Reviewer-, Review-/Remediation-Worker-, Provider- oder Modellidentität. Die einzige Task-Identität, die er überträgt, ist das unverändert aus der kanonischen Binding-Zeile gelesene `orchestration_profile` als Intake-Routingziel; dafür existiert kein Default. Er merged nicht und schreibt nie auf eine Default-/Base-Branch.
- Gate-Zustand und Lifecycle-Zustand sind getrennt. `STALE` ist ausschließlich Lifecycle und niemals ein Gate-Ergebnis. Kanban `done` ist niemals gleichbedeutend mit `PASS`.
- Pflicht-CI in `PENDING`, `QUEUED`, `IN_PROGRESS`, fehlend, übersprungen, abgebrochen oder unbekannt ist nicht `PASS`.
- Der Poller ruft kein LLM auf. Das gilt auch für Parsing, Routing, Retry, Dry-Run und Remediation-Eignung.
- Dieser Vertrag aktiviert keinen Dienst, erstellt kein Label, verändert keine GitHub-Ressource und implementiert keine Produktfunktion.

## 2. Verifizierte Ausgangslage und Entscheidung

Das Inventar weist geeignete vorhandene Bausteine nach:

- Projektquelle: `hermes_cli/projects_db.py`, insbesondere `projects`, `Project`, `connect()` und `get_project()`; `projects.board_slug` und `projects.primary_path` sind vorhanden.
- Board-/Task-Persistenz: `hermes_cli/kanban_db.py`, insbesondere `SCHEMA_SQL`, `connect()`, `write_txn`, `create_task()`, `task_events`, `task_runs` und `tasks.idempotency_key`.
- Dispatch-Lifecycle: `recompute_ready()`, `claim_task()`, `claim_review_task()`, `request_review()`, `request_changes()`, `release_stale_claims()` und `_record_task_failure()`.
- Scheduling/Single-Process-Guard: `GatewayKanbanWatchersMixin._kanban_dispatcher_watcher` in `gateway/kanban_watchers.py`; vorhandene Gateway-Lebensdauer-Sperre und boardbezogene `_dispatch_tick_lock()`.
- Generisches Cron-System: `cron/jobs.py`, `cron/scheduler.py`, `cron/executions.py`, `cron/incidents.py` und `cron/scheduler_provider.py`. `CronScheduler` entscheidet nur wann normale Cron-Jobs feuern; die Provider-Schnittstelle ist experimentell und erlaubt bei Nichtverfügbarkeit einen Built-in-Fallback.
- CLI: `hermes_cli/kanban.py`.

Entscheidung: Der Dispatcher wird als fokussiertes Domänenmodul `hermes_cli/pr_review_dispatcher.py` implementiert, nicht als Core-Model-Tool, Plugin, Webhook oder Cron-Agent-Job. Ein dedizierter, config-gesteuerter Gateway-Watcher in `gateway/kanban_watchers.py` ruft alle 300 Sekunden `poll_once()` auf. Dies verwendet den bereits vorhandenen Gateway-Supervisor und sein Start/Stop-Modell, ohne die experimentelle `CronScheduler`-Provider-ABC zu verbreitern, ohne einen agentischen Cron-Job und ohne Provider-Fallback. Die eigentliche Exklusivität liegt zusätzlich in einer eigenen fail-closed Prozesssperre und in SQLite-Constraints; der Timer allein ist keine Korrektheitsgrenze.

Ein manueller Operatorpfad erweitert `hermes kanban` um `pr-review poll`. Er ruft dieselbe `poll_once()`-API auf. Es entsteht kein Model-Tool und keine separate Netzwerk-API.

## 3. Komponenten, Eigentum und Abhängigkeiten

### 3.1 Modulplan

| Datei | Änderung | Eigentum |
|---|---|---|
| `hermes_cli/pr_review_dispatcher.py` | Neu: Datentypen, Parser, Normalisierung, Review-Key, GitHub-Port, Poll-/Revalidate-Logik, State-Machine, CI-Gate, Remediation-Prädikat, Dry-Run-Report | Domänenpolicy; kennt keine Gateway- oder Modellobjekte |
| `hermes_cli/projects_db.py` | Additive Migration und CRUD/Validierung für `project_repository_bindings` | kanonische Routing-Konfiguration |
| `hermes_cli/kanban_db.py` | Additive Tabellen/Operationen für Zyklen, Attempts, Events und TODOs; nicht dispatchbarer Admission-Status; atomare Cycle+Task-Erzeugung und CAS-Promotion | review-spezifische Durable State im Ziel-Board |
| `gateway/kanban_watchers.py` | Config-gesteuerter 300-Sekunden-Watcher; Start/Stop; machine-globaler fail-closed Poller-Lock | Scheduling/Prozessintegration |
| `hermes_cli/config_defaults.py` | Additive nicht-geheime `kanban.github_pr_review`-Konfiguration | Aktivierungs- und Betriebsparameter |
| `hermes_cli/kanban.py` | `pr-review poll --dry-run --json` und explizite Binding-Verwaltung/Validierung | Operatoroberfläche |
| `tests/hermes_cli/test_pr_review_dispatcher.py` | Parser, Key, State, Gate, Remediation, Dry-Run | Unit-/Vertragstests |
| `tests/hermes_cli/test_pr_review_dispatcher_db.py` | Migration, Constraints, Transaktionen, Race/Restart | Persistenztests |
| `tests/gateway/test_pr_review_watcher.py` | Intervall, Lock, Stop, Overlap, Config-Gate | Schedulerintegration |
| `tests/hermes_cli/test_pr_review_dispatcher_e2e.py` | Fake-GitHub-HTTP/CLI-Port + reale temp-DBs/temp-`HERMES_HOME` | realistischer Integrationspfad |

Dokumentation für Aktivierung/Deaktivierung kann in diesem Dokument ergänzt oder in einer fokussierten Betriebsdokumentation unter `docs/kanban/` angelegt werden. Die Implementierung DARF keine Änderungen an `toolsets.py` oder `model_tools.py` benötigen.

### 3.2 Abhängigkeitsrichtung

`gateway/kanban_watchers.py` und `hermes_cli/kanban.py` → `hermes_cli/pr_review_dispatcher.py` → schmale Ports für GitHub sowie Funktionen aus `projects_db.py`/`kanban_db.py`.

`pr_review_dispatcher.py` DARF weder Gateway-Klassen importieren noch direkt Prozessprofile, Modelle oder Reviewer auflösen. `projects_db.py` kennt GitHub-Payloads nicht. `kanban_db.py` kennt keine GitHub-Transportbibliothek; es persistiert validierte Domänenwerte.

### 3.3 GitHub-Port

Der Port stellt mindestens folgende typed Operationen bereit:

- `list_candidates(repository, label) -> list[PullRequestRef]`
- `read_pull_request(repository, number) -> PullRequestSnapshot`
- `list_issue_comments(repository, number) -> list[IssueComment]`
- `read_required_checks(repository, head_sha) -> RequiredCheckSnapshot`
- `remove_label(repository, number, label)` und `add_label(...)`
- `update_comment(repository, comment_id, body, expected_body_hash=None)`
- `create_result_comment(...) -> CommentIdentity` nur wenn noch kein persistierter Result-Kommentar existiert
- `read_branch_protection(...)` und `compare_branch_head(...)` für Remediation

Die Implementierung SOLL vorhandenes authentifiziertes `gh api` als Subprozessgrenze verwenden, weil `gh` inventarisiert ist und keine neue Python-Abhängigkeit nötig ist. Alle Aufrufe verwenden Argumentlisten ohne Shell, feste Endpunkte und JSON-Parsing; Token, Header, vollständige Prozessumgebung und rohe Fehlkörper werden nicht geloggt. HTTP-ETag/`updated_at` kann zur Optimierung dienen, ersetzt aber nie die normative Revalidation.

## 4. Kanonische Bindung und Konfiguration

### 4.1 Eine authoritative Binding-Quelle

`projects.db` des Profils, in dem der Poller aktiviert ist, erhält additiv:

```sql
CREATE TABLE IF NOT EXISTS project_repository_bindings (
    repository              TEXT PRIMARY KEY,
    project_id              TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    orchestration_profile   TEXT NOT NULL,
    enabled                 INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0,1)),
    binding_revision        INTEGER NOT NULL DEFAULT 1 CHECK (binding_revision > 0),
    created_at              INTEGER NOT NULL,
    updated_at              INTEGER NOT NULL,
    CHECK (repository = lower(repository))
);

CREATE TABLE IF NOT EXISTS project_repository_binding_versions (
    repository              TEXT PRIMARY KEY,
    last_revision           INTEGER NOT NULL CHECK (last_revision > 0),
    updated_at              INTEGER NOT NULL,
    CHECK (repository = lower(repository))
);
```

`repository` ist der kanonische GitHub-Name `owner/name` in lowercase. `project_id` zeigt auf genau einen nicht archivierten `projects`-Datensatz. Das Zielboard ist ausschließlich dessen nichtleeres `projects.board_slug`; es wird nicht in der Binding-Tabelle dupliziert. `orchestration_profile` ist das projektspezifisch konfigurierte Routingziel und nichtleer. `project_repository_binding_versions` ist ein nie geloeschtes High-Water-Ledger. Jede autoritative Aenderung der Binding-Zeile oder eines ihrer aufgeloesten Authority-Werte reserviert innerhalb derselben `BEGIN IMMEDIATE`-Transaktion `last_revision + 1` und schreibt genau diesen Wert als `binding_revision`; erstmalige Anlage beginnt bei 1. Delete deaktiviert/entfernt nur die Binding-Zeile, nie das Ledger, sodass Recreate keine Revision wiederverwenden kann. Aenderungen an `projects.board_slug`, Projektarchivstatus oder gebundener Board-Metadaten-`project_id` muessen denselben Guard nehmen und alle betroffenen Binding-Revisionen atomar erhoehen oder werden abgelehnt. Es gibt bewusst keine globale Orchestrator-Konstante und `kanban.orchestrator_profile` ist für diesen Dispatcher kein Fallback. Der Poller übernimmt `orchestration_profile` unverändert als Orchestrierungs-Assignee des Intake-Tasks; er wählt damit weder den eigentlichen Review- noch einen Remediation-Worker.

Das Board selbst MUSS anhand des expliziten Slugs geöffnet werden. Seine Metadaten MÜSSEN `project_id` gleich dem gebundenen Projekt ausweisen. Auflösungen über `get_current_board()`, persistierten current-board pointer, Umgebungsvariable ohne Binding, `default` oder Namensgleichheit sind verboten.

### 4.2 Binding-Validierung

Beim Aktivieren, beim manuellen Poll und vor jeder Task-Transaktion werden alle folgenden Bedingungen geprüft:

1. Repository erfüllt exakt `^[a-z0-9](?:[a-z0-9_.-]{0,38})/[a-z0-9](?:[a-z0-9_.-]{0,99})$` nach lowercase-Normalisierung; `.git`, URL, SSH-Syntax und Unicode werden abgelehnt.
2. Genau eine Binding-Zeile existiert und `enabled=1`.
3. Das Projekt existiert, ist nicht archiviert und hat absoluten, existierenden `primary_path` sowie nichtleeren `board_slug`.
4. Das Board existiert unter dem kanonischen Kanban-Home, ist nicht archiviert und seine Metadaten enthalten dieselbe `project_id`.
5. `orchestration_profile` ist ein kanonischer installierter Profilname und ist nicht leer. Die Validierung setzt diesen Wert nicht als Task-Assignee; sie bestätigt nur, welche konfigurierte Orchestrierung den unassigned Review-Intake übernimmt.
6. Keine zweite aktivierte Binding-Zeile oder zweite Projektidentität beansprucht dasselbe Repository. Wegen `PRIMARY KEY(repository)` ist dies lokal ausgeschlossen; inkonsistente importierte Stores blockieren dennoch.

Jeder Fehler ergibt `BINDING_MISSING`, `BINDING_AMBIGUOUS` oder `BINDING_INVALID`, schreibt keinen Task und löst keine Board-/Profil-Defaults aus.

### 4.3 Kanonischer Binding-Fingerprint und Binding-Guard

Nach erfolgreicher Aufloesung wird eine immutable Authority-Snapshot-Version erzeugt. Das Preimage besteht aus genau sechs UTF-8-Feldern in dieser Reihenfolge, mit genau fuenf ASCII-LF und ohne trailing LF:

```text
binding/v1\nrepository\nproject_id\nboard_slug\norchestration_profile\nbinding_revision
```

Repository ist lowercase; `project_id`, `board_slug` und Profil sind die unveraenderten kanonischen Persistenzwerte; `binding_revision` ist positive kanonische Dezimaldarstellung. `binding_fingerprint = sha256(preimage).hexdigest()` in lowercase. Version, Fingerprint und alle aufgeloesten Felder werden gemeinsam im Cycle und im Task-Body gespeichert. Ein Timestamp ist kein Versionsersatz.

Alle Binding-Schreiber, alle Schreiber der oben genannten aufgeloesten Projekt-/Board-Authority-Werte sowie Intake und Promotion verwenden dieselbe Sperrordnung: (1) `BEGIN IMMEDIATE` auf dem profilbezogenen `projects.db`, (2) Binding/Projekt/Board/Fingerprint frisch lesen, (3) erst dann `BEGIN IMMEDIATE` auf genau dem gebundenen Board, (4) Board-CAS ausfuehren und committen, (5) danach die `projects.db`-Transaktion committen/freigeben. Kein anderer Pfad darf diese Authority-Werte fuer ein gebundenes Repository schreiben. Damit kann eine Binding-Aenderung weder zwischen Authority-Read und Intake-Commit noch zwischen Authority-Read und Promotion-Commit eintreten. Lock-/Read-/CAS-Fehler rollen die Board-Transaktion zurueck oder lassen den Task nicht dispatchbar. Die Sperrordnung darf nirgends invertiert werden.

Der Guard wird zweimal vollstaendig ausgefuehrt: unmittelbar vor der dauerhaften Intake-Schreibtransaktion und unmittelbar vor der Admission-Promotion nach Read C. Beim zweiten Lauf muessen Revision, Fingerprint und alle vier aufgeloesten Identitaeten bytegleich mit dem gespeicherten Snapshot sein. Mutation oder Mismatch erzeugt `BINDING_CHANGED`, setzt den Cycle `STALE`, behaelt den Task in `admission_pending` und routet niemals unter alter Autoritaet. Eine spaetere Binding-Aenderung kann einen bereits gestarteten Review nicht umleiten; Read D muss ihn vor fachlicher Arbeit erneut gegen den gespeicherten Fingerprint revalidieren und andernfalls ohne Gate-Aenderung `STALE` setzen.

### 4.4 Laufzeitkonfiguration

Additiv in `DEFAULT_CONFIG["kanban"]["github_pr_review"]`:

```yaml
kanban:
  github_pr_review:
    enabled: false
    interval_seconds: 300
    label: hermes-review-requested
    request_marker: "<!-- hermes-review-request -->"
    result_marker: "<!-- hermes-review-result -->"
    lock_timeout_seconds: 0
    github_timeout_seconds: 30
    retry_base_seconds: 30
    retry_max_seconds: 1800
    max_candidates_per_tick: 50
```

`enabled` ist standardmäßig `false`. `interval_seconds` MUSS für Schema 1 exakt 300 sein; andere Werte sind Konfigurationsfehler statt stiller Korrektur. Marker und Label sind Schema-1-Konstanten und müssen bei Aktivierung exakt den angegebenen Werten entsprechen. Secrets gehören nicht in diese Konfiguration; Authentifizierung bleibt beim vorhandenen `gh` Credential-Pfad.

## 5. Request-, Result- und Kommentarvertrag

### 5.1 Request-Kommentar Schema 1

Der Kommentar besteht aus der Markerzeile, unmittelbar gefolgt von genau einem JSON-Codeblock. Außer Whitespace ist kein weiterer maschinenlesbarer Block zulässig. Unbekannte Top-Level-Felder werden für Vorwärtskompatibilität ignoriert, aber nicht in den Review-Key aufgenommen.

Pflichtfelder:

```json
{
  "schema_version": 1,
  "review_key": "<64 lowercase hex>",
  "repository": "owner/name",
  "pr_number": 123,
  "base_ref": "main",
  "base_sha": "<40 lowercase hex>",
  "head_repository": "owner/name",
  "head_ref": "feature/ref",
  "head_sha": "<40 lowercase hex>",
  "requested_at": "<RFC3339 UTC>",
  "handoff": {
    "summary": "<non-empty string>",
    "changed_files": ["<repo-relative path>"],
    "test_commands": ["<command>"],
    "known_risks": ["<string>"]
  }
}
```

Parserregeln:

- JSON muss UTF-8, ein Objekt und ohne duplicate keys sein; Zahlen dürfen nicht als Strings maskiert werden.
- `schema_version` ist integer `1`; `pr_number` ist positiver integer ohne bool.
- Repositorywerte werden lowercase normalisiert; Full-SHAs müssen vor und nach lowercase exakt 40 Hexzeichen sein; Refs werden NFC-validiert, aber case-preserving übernommen und dürfen keine Steuerzeichen, LF, NUL, `..`, führenden/trailing Slash oder Git-verbotene Refsequenzen enthalten.
- Alle im Kommentar behaupteten Identitätsfelder und `review_key` müssen den selbst gelesenen und berechneten Werten exakt entsprechen. Ein Unterschied ist kein reparierbarer Parserfehler, sondern `REQUEST_MISMATCH`/`STALE`.
- Handoff-Listen sind begrenzt (je 200 Einträge, Strings je 4096 Bytes; gesamter Kommentar höchstens GitHub-Limit). Pfade müssen relativ und traversal-frei sein. Inhalte sind untrusted Text und werden niemals als Instruktion oder Shell ausgeführt.

### 5.2 Stabile Request-Comment-ID

Für `(repository, pr_number)` wird die erste erfolgreich akzeptierte Comment-ID als `review_request_comment_id` in `pr_review_subjects` persistiert. Es gelten gleichzeitig:

- Bei der ersten Aufnahme muss exakt ein nicht minimierter, nicht gelöschter Kommentar den Marker enthalten. Null oder mehr als eins blockiert mit `REQUEST_COMMENT_MISSING` beziehungsweise `REQUEST_COMMENT_CONFLICT`.
- Nach Persistierung wird ausschließlich diese ID akzeptiert. Ein Marker an einer anderen ID ist Konflikt, auch wenn der gespeicherte Kommentar fehlt.
- Eine Änderung desselben Kommentars ist für einen neuen Head/Key erlaubt; GitHub-`updated_at`, Body-SHA-256 und Actor werden pro Zyklus auditiert.
- Der Poller darf keine andere ID erraten, keinen neuesten Kommentar wählen und keine Duplikate automatisch löschen.

### 5.3 Result-Kommentar Schema 1

Der maschinenlesbare Result-Kommentar beginnt mit `<!-- hermes-review-result -->` und enthält:

```json
{
  "schema_version": 1,
  "review_key": "<64 lowercase hex>",
  "repository": "owner/name",
  "pr_number": 123,
  "base_sha": "<40 lowercase hex>",
  "head_sha": "<40 lowercase hex>",
  "gate": "PASS|CHANGES_REQUIRED|BLOCKED|NOT_RUN",
  "lifecycle": "COMPLETED|STALE|BLOCKED",
  "required_ci": "PASS|FAIL|PENDING|MISSING",
  "task_id": "t_<id>",
  "review_run_ids": [1],
  "finding_ids": ["F-001"],
  "generated_at": "<RFC3339 UTC>"
}
```

`STALE` ist im Feld `gate` nicht zulässig. Resultate sind eine Projektion aus persistiertem Kanban-/Reviewzustand und GitHub-Revalidation, keine Eingabe, die einen Gate-Zustand autorisiert. Der Writer speichert die von GitHub zurückgegebene `result_comment_id`, Actor-ID und Body-Hash. Ein später gelesener Result-Kommentar ist nur konsistent, wenn ID, Key und Hash mit der Persistenz übereinstimmen. Ein fremder/duplizierter Marker blockiert die Veröffentlichung; er kann niemals `PASS` erzeugen. Bei ungewissem Write-Ausgang wird zuerst per ID beziehungsweise exakt persistiertem Key/Actor/Hash reconciled und nicht blind erneut erstellt.

## 6. Review-Key Schema 1

### 6.1 Normalisierung

Die acht Felder werden exakt wie folgt erzeugt:

1. `schema_version`: ASCII `1`.
2. `repository`: GitHub `nameWithOwner`, getrimmt, lowercase.
3. `pr_number`: kanonische positive Dezimaldarstellung ohne Vorzeichen oder führende Nullen.
4. `base_ref`: von GitHub gelesener Refname, case-preserving, kein Trim außer Ablehnung von umgebendem Whitespace.
5. `base_sha`: aktueller Tip des von GitHub gelesenen Base-Refs zum Zeitpunkt des Snapshots, vollständige 40-Hex-SHA, lowercase. Es ist ausdrücklich weder PR-Merge-Base noch Merge-Commit noch bei PR-Erstellung gespeicherter SHA.
6. `head_repository`: GitHub `headRepository.nameWithOwner`, getrimmt, lowercase.
7. `head_ref`: von GitHub gelesener Head-Ref, case-preserving, kein Trim außer Ablehnung von umgebendem Whitespace.
8. `head_sha`: aktueller vollständiger 40-Hex-PR-Head-SHA, lowercase.

GitHub-Abkürzungen, lokale Git-Refs, Kommentarwerte und Merge-Queue-SHAs sind keine Quelle.

### 6.2 Preimage und Hash

```text
schema_version\nrepository\npr_number\nbase_ref\nbase_sha\nhead_repository\nhead_ref\nhead_sha
```

Die Feldwerte werden in genau dieser Reihenfolge mit genau sieben ASCII-LF (`0x0a`) verbunden. Es gibt kein trailing LF. Das Preimage wird UTF-8 codiert. Der Review-Key ist lowercase `sha256(preimage).hexdigest()`.

Referenzalgorithmus:

```python
preimage = "\n".join((
    "1", repository, str(pr_number), base_ref, base_sha,
    head_repository, head_ref, head_sha,
))
review_key = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
```

Ein anderer Base-Tip oder Head-Commit erzeugt zwingend einen neuen Key und macht vorherige Zyklen `STALE`, ohne deren Gate-Ergebnis umzuschreiben.

## 7. Persistenz, Migration und Audit

### 7.1 DB-Entscheidung

Bindings gehören in das vorhandene profilbezogene `projects.db`; Review-Zyklen gehören in das vorhandene Zielboard-`kanban.db`. Es wird keine dritte Datenbank und keine JSON-State-Datei eingeführt. Beide Änderungen sind additive, idempotente Migrationen über die existierenden `connect()`-Initialisierungspfade.

Boardtabellen:

```sql
CREATE TABLE IF NOT EXISTS pr_review_subjects (
    repository                    TEXT NOT NULL,
    pr_number                     INTEGER NOT NULL,
    review_request_comment_id     INTEGER NOT NULL,
    request_comment_actor         TEXT NOT NULL,
    created_at                    INTEGER NOT NULL,
    updated_at                    INTEGER NOT NULL,
    PRIMARY KEY (repository, pr_number),
    UNIQUE (repository, review_request_comment_id)
);

CREATE TABLE IF NOT EXISTS pr_review_cycles (
    review_key              TEXT PRIMARY KEY,
    schema_version          INTEGER NOT NULL CHECK (schema_version = 1),
    repository              TEXT NOT NULL,
    pr_number               INTEGER NOT NULL,
    base_ref                TEXT NOT NULL,
    base_sha                TEXT NOT NULL,
    head_repository         TEXT NOT NULL,
    head_ref                TEXT NOT NULL,
    head_sha                TEXT NOT NULL,
    project_id              TEXT NOT NULL,
    board_slug              TEXT NOT NULL,
    orchestration_profile   TEXT NOT NULL,
    binding_revision        INTEGER NOT NULL,
    binding_fingerprint     TEXT NOT NULL,
    request_comment_id      INTEGER NOT NULL,
    request_body_sha256     TEXT NOT NULL,
    task_type               TEXT NOT NULL CHECK (task_type = 'pull_request_review'),
    task_id                 TEXT UNIQUE,
    admission_status        TEXT NOT NULL,
    lifecycle               TEXT NOT NULL,
    gate                    TEXT NOT NULL,
    required_ci             TEXT NOT NULL,
    result_comment_id       INTEGER UNIQUE,
    result_body_sha256      TEXT,
    attempt_count           INTEGER NOT NULL DEFAULT 0,
    next_attempt_at         INTEGER,
    last_error_class        TEXT,
    created_at              INTEGER NOT NULL,
    updated_at              INTEGER NOT NULL,
    UNIQUE (repository, pr_number, base_sha, head_sha)
);

CREATE TABLE IF NOT EXISTS pr_review_attempts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    review_key         TEXT NOT NULL REFERENCES pr_review_cycles(review_key),
    operation          TEXT NOT NULL,
    status             TEXT NOT NULL,
    started_at         INTEGER NOT NULL,
    ended_at           INTEGER,
    error_class        TEXT,
    retryable          INTEGER NOT NULL,
    github_request_id  TEXT,
    detail_json        TEXT
);

CREATE TABLE IF NOT EXISTS pr_review_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    review_key     TEXT,
    repository     TEXT NOT NULL,
    pr_number      INTEGER NOT NULL,
    kind           TEXT NOT NULL,
    payload_json   TEXT NOT NULL,
    created_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pr_review_todos (
    todo_id              TEXT PRIMARY KEY,
    finding_id           TEXT NOT NULL,
    source_review_key    TEXT NOT NULL REFERENCES pr_review_cycles(review_key),
    source_head_sha      TEXT NOT NULL,
    goal                 TEXT NOT NULL,
    scope_json           TEXT NOT NULL,
    components_json      TEXT NOT NULL,
    acceptance_json      TEXT NOT NULL,
    tests_json           TEXT NOT NULL,
    branch               TEXT NOT NULL,
    worker_profile       TEXT NOT NULL,
    workspace_path       TEXT NOT NULL,
    expected_head_sha    TEXT NOT NULL,
    materialization_hash TEXT NOT NULL,
    claim_owner          TEXT,
    claim_expires        INTEGER,
    status               TEXT NOT NULL,
    resulting_head_sha   TEXT,
    created_task_id      TEXT UNIQUE,
    created_at           INTEGER NOT NULL,
    updated_at           INTEGER NOT NULL,
    UNIQUE (source_review_key, finding_id)
);
```

`lifecycle`, `gate`, `required_ci`, attempt status und TODO status werden zusätzlich in Python gegen die geschlossenen Mengen dieses Vertrags validiert; SQLite-`CHECK`s SOLLEN diese Mengen spiegeln. Migrationen dürfen bestehende Tasktabellen nicht umdeuten.

`admission_status` ist die geschlossene Menge `PENDING_READ_C`, `PROMOTED`, `STALE`. Fuer Remediation-TODOs ist `status` mindestens `MATERIALIZING`, `TASK_CREATED`, `CLAIMED`, `COMPLETED`, `BLOCKED`; `materialization_hash` ist SHA-256 der kanonischen immutable Task-Spezifikation. Zusaetzlich MUESSEN zwei migrationsgepruefte partielle Unique-Indizes auf `tasks(idempotency_key)` ueber alle Task-Lifecycle-Zustaende einschliesslich `archived` hoechstens einen Task fuer jeden nichtleeren Key mit Prefix `pull_request_review:` beziehungsweise `pull_request_remediation:` zulassen; die Praedikate sind feste Schema-1-Konstanten, nicht vom Aufrufer waehlbar. Findet die Migration bereits Duplikate, bricht sie fail-closed ab und publiziert keinen davon als gueltigen Review-/Remediation-Task. Archivierung autorisiert keinen Ersatz-Task fuer denselben Review- oder Source-Key.

### 7.2 Task-Typ und immutable Metadaten

Das bestehende `tasks`-Schema besitzt keinen Task-Typ. Daher wird ein regulärer Kanban-Task erzeugt und `pull_request_review` revisionssicher in `pr_review_cycles.task_type` sowie in einem kanonischen JSON-Block im Task-Body abgebildet. Der Block enthält mindestens:

- `task_type: pull_request_review`, `schema_version: 1`, `review_key`
- Repository/PR URL und Nummer
- Base-/Head-Repository, Refs und volle SHAs
- `request_comment_id` und Request-Body-Hash
- `project_id`, expliziter `board_slug`, `binding_revision`, `binding_fingerprint` und die vier kanonischen Authority-Felder
- Handoff: Summary, Changed Files, Testbefehle, bekannte Risiken
- Pflichtaktionen: GitHub frisch lesen; vor Review und vor Gate revalidieren; CI prüfen; kein Merge
- Audit-IDs und erlaubte Gate-/Lifecycle-Werte

Der Task erhält `project_id`, den vorhandenen projektgebundenen `workspace_kind=worktree`-Pfad, `idempotency_key="pull_request_review:" + review_key` und exakt den gebundenen `orchestration_profile` als Orchestrierungs-Assignee. Dieses Feld ist ein konfiguriertes Routingziel, keine Pollerentscheidung über Reviewer oder ausführenden Remediation-Worker. `skills`, `model_override`, `provider_override`, `reasoning_effort` und Reviewer bleiben NULL/leer. Die gebundene Orchestrierung muss den Intake über ihren bestehenden, separat verantworteten Ablauf weiter routen. Falls dieses Profil nicht installiert oder nicht als Orchestrierungsweg verwendbar ist, ist die Binding-/Orchestrierungsfähigkeit `BINDING_INVALID` und kein Task wird erzeugt.

## 8. Transaktionen, Idempotenz und Admission

`tasks.idempotency_key` ist derzeit nur normal indexiert; `create_task()` dokumentiert eine akzeptierte Race, bei der konkurrierende Inserts Duplikate erzeugen können. Diese Semantik reicht für Review-Key-Exactly-Once nicht aus. Die Review-Tabelle mit `review_key PRIMARY KEY` und `task_id UNIQUE` ist daher die normative Idempotenzgrenze.

Atomare, noch nicht dispatchbare Materialisierung im explizit gebundenen Board:

1. GitHub-Read A und erste Binding-Validierung erfolgen außerhalb der Write-Transaktion.
2. Unmittelbar vor dem Write wird GitHub als Read B erneut gelesen und der Snapshot bytegenau verglichen.
3. Der Binding-Guard aus 4.3 startet, liest die Autoritaet erneut und haelt die `projects.db`-Write-Sperre.
4. `BEGIN IMMEDIATE` ueber den vorhandenen Board-`write_txn` startet.
5. `pr_review_subjects` wird auf stabile Comment-ID geprueft/eingefuegt.
6. `pr_review_cycles` wird mit `lifecycle='CLAIMED'`, `admission_status='PENDING_READ_C'`, `gate='NOT_RUN'`, Binding-Version und Fingerprint eingefuegt. Ein Unique-Konflikt bedeutet deterministisches `ALREADY_EXISTS`, nicht Retry/Create.
7. Innerhalb derselben Connection und Transaktion erzeugt eine review-spezifische Primitive den Task mit `status='admission_pending'`. Dieser Status wird additiv in der Kanban-Statusmenge eingefuehrt, ist aber weder `ready`, `review`, `todo`, `blocked` noch `scheduled` und darf von `recompute_ready`, `promote_task`, `unblock_task`, `reopen_review_task`, `claim_task`, `claim_review_task`, Stale-Reclaim oder Dispatcher-Recovery nicht veraendert oder beansprucht werden. Ausschliesslich die CAS-Promotion dieses Vertrags darf ihn verlassen.
8. Der erzeugte Task wird anhand ID, Status, Assignee, `project_id`, Body-Key, Binding-Fingerprint und Idempotency-Key zurueckgelesen. Erst danach werden `task_id` gesetzt und Lifecycle `TASK_CREATED` geschrieben.
9. Task- und Review-Events werden in derselben Board-Transaktion geschrieben; Board-Commit und danach Freigabe des Binding-Guards.
10. Nur nach bestaetigtem Commit darf der Poller den Trigger-Label-Write durchfuehren. Bis zur spaeteren Promotion ist der sichtbare Task unveraenderlich dispatch-ineligible; es existieren kein Claim, kein `task_run`, kein Worker-PID und kein Workspace-Start.

Jeder Fehler vor Commit rollt Cycle und Task gemeinsam zurück. Crash nach Commit vor Label-Entfernung oder Read C ist sicher: der nächste Lauf findet denselben Review-Key und reconciled ausschliesslich die ausstehende Label-Projektion, waehrend der Task `admission_pending` bleibt. Crash nach GitHub-Write vor Attempt-Abschluss wird read-before-retry reconciled. Es gibt keinen Delete-and-recreate-Pfad für Zyklen und keine generische/operatorische Abkuerzung aus `admission_pending`.

## 9. Scheduler, Locks und Parallelität

- Der Gateway-Watcher startet nur bei `enabled=true` und vollständig valider Konfiguration.
- Er wartet den vorhandenen Gateway-Startup-Puffer ab, führt dann sofort höchstens einen Poll aus und danach alle 300 Sekunden. Shutdown wird in kurzen Stop-Event-Waits beachtet.
- Eine machine-global/profile-store-spezifische Sperre `<HERMES_HOME>/kanban/.github-pr-review-dispatcher.lock` wird für jeden vollständigen Tick non-blocking exklusiv gehalten. Im Gegensatz zur vorhandenen `_dispatch_tick_lock()` MUSS Open-/Lock-Fehler fail-closed den Tick abbrechen; ein No-op-Fallback ist verboten.
- Zusätzlich wird pro Zielboard während der atomaren SQLite-Materialisierung dessen vorhandene `_dispatch_tick_lock()` verwendet. Da diese bei Open-Fehler derzeit fail-open ist, MUSS der Reviewpfad einen neuen öffentlichen fail-closed Lock-Wrapper verwenden oder die Reviewtransaktion allein über `BEGIN IMMEDIATE` plus Unique Constraints absichern; er darf sich nicht auf den fail-open Zweig verlassen.
- Der manuelle CLI-Poll nimmt dieselbe globale Sperre. Verliert er, meldet er `OVERLAP_SKIPPED` und schreibt nichts.
- Mehrere Hosts mit gemeinsamem DB-Dateisystem bleiben durch SQLite-Unique Constraints idempotent. File locking ist Lastreduktion, nicht alleinige Exactly-Once-Garantie.
- Kandidaten werden stabil nach `(repository, pr_number)` sortiert und pro Tick auf `max_candidates_per_tick` begrenzt. Kein Kandidat wird wegen eines Fehlers eines anderen verworfen.

## 10. GitHub Read/Compute/Write/Revalidate-Ablauf

Für jeden Kandidaten:

1. Label-Suche liefert nur Referenzen.
2. Read A: PR inklusive offen/geschlossen, Draft, Base-Repo/Ref, Head-Repo/Ref/SHA; aktueller Base-Ref-Tip; alle Marker-Kommentare; required checks; Berechtigungs-/Forkdaten.
3. Request-Parser und Comment-ID-Konsistenz.
4. Review-Key-Berechnung ausschließlich aus Read A.
5. Eindeutige Binding-Auflösung und Board-Readback.
6. Persistenz-Lookup: existierender Key wird reconciled, nicht neu erzeugt.
7. Read B unmittelbar vor der Transaktion. PR-Node-ID, open state, draft state, Base-/Head-Werte, Base-Tip, Label, Comment-ID, Body-Hash und `updated_at` müssen A entsprechen.
8. Atomare Cycle-/Task-Erzeugung als `admission_status=PENDING_READ_C` / Taskstatus `admission_pending`; noch kein Dispatch.
9. GitHub-Write: Triggerlabel für genau diesen Key entfernen. Der Request-Kommentar bleibt als stabile Historie bestehen.
10. Read C liest nach dem Write PR-Node-ID, open/draft, Base-/Head-Repository/Ref/SHA, aktuellen Base-Tip, Labelzustand, stabile Comment-ID, Body-Hash/`updated_at` und Result-Marker erneut. Alle Identitaets- und Requestwerte muessen Read B entsprechen und nur das erwartete Triggerlabel darf entfernt sein.
11. Nach erfolgreichem Read C wird der Binding-Guard erneut genommen. Innerhalb seiner Board-Transaktion bestaetigt ein einziges CAS `review_key`, gespeicherten Binding-Fingerprint, `lifecycle='TASK_CREATED'`, `admission_status='PENDING_READ_C'`, Task-ID, Taskstatus `admission_pending` und Abwesenheit von Claim/Run/Worker. Derselbe CAS setzt Cycle `admission_status='PROMOTED'`, Lifecycle `IN_REVIEW` und Taskstatus `ready`; Event und Statuswechsel committen atomar. Erst dieser Commit macht den Task claimbar.
12. Scheitert Read C oder der zweite Binding-/CAS-Check permanent, setzt eine Board-Transaktion Cycle und Admission `STALE`, waehrend der Task dauerhaft `admission_pending` bleibt. Bei transient/ungewissem Read-C-Ausgang bleibt `PENDING_READ_C` unveraendert und wird read-before-retry reconciled. Weder Fehlerpfad darf `ready`, Claim oder Worker erzeugen.

Vor Beginn eines menschlichen/agentischen Reviews MUSS der Review-Worker über eine schmale `revalidate_for_review(review_key)`-Operation Read D durchführen. Vor jedem Gate-/Result-Write MUSS `revalidate_for_gate(review_key)` Read E durchführen. Beide vergleichen aktuelle Base-/Head-/Request-/Bindingwerte und Key. Jede Abweichung setzt Lifecycle `STALE`, lässt das Gate unverändert (`NOT_RUN`, `CHANGES_REQUIRED`, `BLOCKED` oder historisches `PASS`) und verbietet die Verwendung des alten Resultats für den aktuellen PR.

## 11. Lifecycle-, Label- und Gate-State-Machines

### 11.1 Lifecycle

Geschlossene Menge:

`DISCOVERED`, `CLAIMED`, `TASK_CREATED`, `IN_REVIEW`, `REMEDIATION_PENDING`, `REMEDIATING`, `REREVIEW_REQUESTED`, `COMPLETED`, `BLOCKED`, `STALE`.

Erlaubte Übergänge:

- `DISCOVERED -> CLAIMED -> TASK_CREATED`; erst erfolgreiche Read-C-/Binding-CAS-Promotion erlaubt `TASK_CREATED -> IN_REVIEW`
- `IN_REVIEW -> COMPLETED` bei terminalem, revalidiertem Gate
- `IN_REVIEW -> REMEDIATION_PENDING -> REMEDIATING`
- `REMEDIATING -> STALE` für den alten Key, nachdem ein Worker-Commit einen neuen Head erzeugt hat
- Neuer Key: `DISCOVERED -> ... -> REREVIEW_REQUESTED -> IN_REVIEW`
- Jeder nichtterminale Zustand -> `BLOCKED` bei permanentem externen/Vertragsfehler
- Jeder nichtterminale oder terminale alte Zyklus -> `STALE` bei Base-/Head-/Request-Drift; historische Felder bleiben erhalten

`STALE` ist terminal für genau diesen Key; es kann nicht zurück nach `IN_REVIEW`. Ein neuer Commit ist ein neuer Zyklus.

### 11.2 Admission

`PENDING_READ_C -> PROMOTED` ist nur durch den in Abschnitt 10 beschriebenen atomaren CAS erlaubt. `PENDING_READ_C -> STALE` ist terminal. `PROMOTED` und `STALE` sind immutable. Fuer jeden Cycle gilt: `admission_status != PROMOTED` impliziert Taskstatus `admission_pending`, keine Claim-Felder, keinen offenen `task_run`, keinen Workerprozess und keine Dispatch-Queue-Aufnahme. Die Dispatcher-Query filtert positiv nur ihre bisherigen dispatchbaren Statuswerte und muss zusaetzlich durch einen Test beweisen, dass `admission_pending` nie selektiert wird.

### 11.3 Gate

Geschlossene Menge: `NOT_RUN`, `PASS`, `CHANGES_REQUIRED`, `BLOCKED`.

- `PASS` erfordert aktuelle Revalidation, unabhängige geforderte Reviews, keine offenen P0/P1, Pflicht-CI vollständig `PASS`, konsistenten Request/Result und offenen, nicht gemergten PR.
- `CHANGES_REQUIRED` beschreibt fachliche Findings; es ist nicht dasselbe wie Lifecycle `STALE`.
- `BLOCKED` beschreibt fehlende externe Fähigkeit, mehrdeutige Identität oder Vertragsverletzung.
- Ein historisches Gate wird nie in `STALE` umbenannt. Die aktuelle Gültigkeit ergibt sich aus dem Lifecycle und exakt passendem Key.

### 11.4 Triggerlabel

- Label + valider Request sind gemeinsam Admission.
- Vor erfolgreichem Cycle+Task-Commit bleibt das Label bei transienten und permanenten Fehlern unverändert, damit kein Request verloren geht.
- Nach Commit wird das Label idempotent entfernt. Fehler beim Entfernen werden retrybar auditiert; der persistierte Key verhindert Doppelverarbeitung.
- Ein Worker-Commit aktualisiert zuerst den stabilen Request-Kommentar auf den neuen, frisch gelesenen Key und setzt danach das Label erneut. Schlägt einer dieser Schritte ungewiss fehl, erfolgt Read/Reconcile statt blindem Wiederholen.
- Der Poller setzt kein Label aufgrund einer Heuristik und entfernt nie Labels von einem abweichenden aktuellen Key.

## 12. CI-Gate

Die Liste der Required Checks wird von GitHubs Branch-Protection/Ruleset-Auskunft für den aktuellen Base-Ref gelesen, nicht aus dem Kommentar. Wenn diese Auskunft wegen Berechtigungen nicht vollständig möglich ist, ist das Gate `BLOCKED`.

`required_ci=PASS` gilt nur, wenn jede aktuell erforderliche Check-Run-/Status-Context-Instanz für den exakten `head_sha` terminal erfolgreich ist. Neutrale/skipped Checks zählen nur dann als erfolgreich, wenn GitHub sie für die konkrete Protection ausdrücklich nicht als erforderlich behandelt. Duplicate Namen, fehlende Suite, pending/queued/in-progress, stale head, failure, cancelled, timed_out, action_required oder unbekannte Conclusion ergeben `PENDING`, `FAIL`, `MISSING` oder `BLOCKED`, nie `PASS`.

Read E vor Gate liest Required Checks erneut. Ein Check- oder Ruleset-Wechsel zwischen Bewertung und Result-Write blockiert den Write und startet die Bewertung neu.

## 13. Remediation: exakt zehn kumulative Bedingungen

Eine automatische Remediation ist nur geeignet, wenn alle folgenden zehn Bedingungen `true` sind. Das Prädikat ist pure/deterministisch, persistiert jeden Bool und die Evidenz und darf keine elfte implizite Erlaubnis besitzen.

1. **Kleine Findings:** Alle zu delegierenden Findings sind als `P2` oder `P3` klassifiziert; kein offenes `P0` oder `P1` existiert.
2. **Eindeutige Quelle:** Jedes Finding hat eine eindeutige Finding-ID, genau einen aktuellen Source-Review-Key und denselben Source-Head; widersprüchliche Reviews fehlen.
3. **Begrenzter Änderungscharakter:** Die Korrektur erweitert weder Produktumfang noch Architektur, öffentliche API/CLI, Persistenzschema, Sicherheits-/Trust-Policy, Berechtigungen, Dependency-Surface oder Deploymenttopologie.
4. **Vollständige TODO-Spezifikation:** Ziel, Scope, erlaubte Komponenten/Dateien, Acceptance Criteria und konkrete Tests sind vollständig, endlich und ohne offene Produkt-/Operatorentscheidung.
5. **Vertrauenswürdiger Head:** Head-Repository und Branch sind nach der Binding-Policy als trusted und beschreibbar bestätigt; untrusted Forks, gelöschte Repositories und unbekannte Ownership sind ausgeschlossen.
6. **Sichere Branch:** Ziel ist ausschließlich die bestehende PR-Head-Branch; sie ist weder Base-/Default- noch protected Branch, und Force-Push, Merge sowie History Rewrite sind verboten.
7. **Aktuelle CAS-Basis:** Frische GitHub-Lesung bestätigt PR offen/unmerged, Request-ID/Label/Binding aktuell und `current_head_sha == expected_head_sha == source_head_sha` unmittelbar vor dem Write.
8. **Exklusive Serialisierung:** Für `(repository, pr_number, head_ref)` existiert genau ein nicht abgelaufener Remediation-Claim; kein anderer Worker/TODO darf dieselbe Branch schreiben.
9. **Getrennte Identitäten und geringste Autorität:** Die konfigurierte Orchestrierung liefert explizit einen geeigneten Worker; er ist von allen autorisierenden Reviewern verschieden. Poller und Remediation-Prädikat wählen keine Person, kein Profil und kein Modell. Workspace/Credentials erlauben keine Default-Branch-, Admin-, Secret- oder privilegierte Fork-Runner-Nutzung.
10. **Verifizierbarer Abschluss:** Die spezifizierten Tests und Revalidation können im bestehenden projektgebundenen Worktree ausgeführt werden; nach Commit sind neuer Head, Audit-Handoff, aktualisierter Request, neuer Review-Key und unabhängiges Re-Review verpflichtend. Alte Freigaben werden nicht übertragen.

Scheitert eine Bedingung, wird keine Remediation-Task erzeugt. Das Gate bleibt/werden `CHANGES_REQUIRED` oder bei externer Unfähigkeit `BLOCKED`; der normale Entwicklungsprozess übernimmt.

## 14. TODO-/Audit-Vertrag, Branch-CAS und Re-Review

Jeder Remediation-TODO-Datensatz enthält die in `pr_review_todos` dargestellten Felder. Sein Kanban-Body spiegelt mindestens TODO-ID, Finding-ID, Source-Key/Head, Ziel, Scope, Komponenten, Acceptance, Tests, Branch, von der Orchestrierung gelieferten Worker, Workspace und expected Head. `idempotency_key` ist `pull_request_remediation:<source_review_key>:<finding_id>`.

### 14.1 Exactly-once-Materialisierung je Remediation-Quelle

Nach Nachweis aller zehn Bedingungen materialisiert genau eine neue DB-Operation TODO und Task. Sie darf den bestehenden vor-transaktionalen `create_task()`-Fast-Path weder aufrufen noch als Idempotenzbeweis verwenden:

1. Kanonischer Source-Key ist das Tupel `(source_review_key, finding_id)`; daraus werden deterministisch `todo_id`, Idempotency-Key und `materialization_hash` der vollstaendigen immutable Spezifikation berechnet.
2. Eine einzige `BEGIN IMMEDIATE`-Board-Transaktion umfasst Claim/Insert, Task-Insert, Readback, `created_task_id` und Events. `INSERT ... ON CONFLICT DO NOTHING` fuer den durch `UNIQUE(source_review_key, finding_id)` geschuetzten TODO wird mit einem neuen unvorhersagbaren Attempt-Token als `claim_owner`, einer begrenzten `claim_expires` und Status `MATERIALIZING` ausgefuehrt, danach wird genau diese Zeile gelesen. Eine bestehende unvollstaendige Zeile darf nur nach abgelaufener Lease per CAS auf einen neuen Attempt-Token uebernommen werden; waehrend einer lebenden Lease liefert sie `OVERLAP_SKIPPED` ohne Write.
3. Bei bestehender Zeile muessen Source Head, Branch, Worker, Workspace, gesamter Spezifikationshash und Idempotency-Key exakt passen. Abweichung ist `REMEDIATION_CONFLICT`, nicht Update, Delete oder zweite Task.
4. Ist `created_task_id` gesetzt, muss genau dieser eine Task unabhaengig von seinem Lifecycle mit passendem Idempotency-Key, Body-Source-Key, Assignee, Projekt, Workspace und Hash existieren. Exakt dieser Task wird idempotent zurueckgegeben; null, mehr als einer oder ein Feldmismatch ist `INTERNAL_INVARIANT` und exponiert keine weitere Task.
5. Ist `created_task_id` NULL und gehoert die Zeile dem aktuellen Attempt-Token, fuehrt die Operation genau einen direkten Task-Insert ueber eine neue connection-scoped Primitive ohne eigene Lookup-/Commit-Grenze aus und liest den Task in derselben Transaktion anhand seiner neuen ID und des unique Remediation-Idempotency-Key zurueck. Erst nach vollstaendig erfolgreichem Readback werden `created_task_id` und TODO-Status `TASK_CREATED` per CAS auf denselben Attempt-Token gesetzt, die Claim-Felder geloescht und beide Events geschrieben.
6. Ein Insert-Konflikt auf Source-Key oder Remediation-Idempotency-Key wird innerhalb derselben Transaktion durch erneutes Lesen reconciled. Nur eine exakt passende, bereits gebundene Zeile darf Erfolg liefern; sonst Rollback/fail-closed. Es gibt keinen zweiten Insert, kein Suffix und kein Delete-and-recreate.
7. Crash vor Commit hinterlaesst weder TODO noch Task. Crash beziehungsweise verlorene Antwort nach Commit wird beim Restart ueber Source-Key gelesen und liefert dieselbe `created_task_id`. Die partielle Unique-Grenze und `BEGIN IMMEDIATE` beweisen auch bei zwei Connections/Prozessen, dass fuer diesen Source-Key insgesamt nie mehr als eine Task erzeugt oder sichtbar wird.

Erst eine spaetere, getrennte CAS darf `TASK_CREATED -> CLAIMED` ausfuehren, nachdem Branch-Head und alle zehn Bedingungen frisch bestaetigt wurden. Materialisierung selbst startet keinen Worker.

Branchschreibablauf:

1. Die Orchestrierung liefert Worker und bestehenden projektgebundenen Worktree. Der Poller setzt sie nicht.
2. Unter einer fail-closed Cross-Process-Sperre pro `(repository, pr_number, head_ref)` wird der TODO-Claim per SQLite-CAS übernommen.
3. Vor Commit/Push wird GitHub frisch gelesen. `head_sha` muss expected Head sein.
4. Der Worker darf nur die bestehende Head-Branch fast-forward aktualisieren. `git push --force*`, Merge-Commit, Base-/Default-Branch-Write und neue privilegierte Credentials sind verboten.
5. Unmittelbar vor Push wird remote Head nochmals verglichen; Push verwendet Git-Protokoll-CAS (`--force-with-lease=<ref>:<expected>` ist nur als Lease/CAS zulässig, darf aber niemals nicht-fast-forward History ersetzen; bevorzugt normaler Fast-Forward-Push). Ein Lease-Verlust bricht ab.
6. Nach Push wird der Remote-Head zurückgelesen. Alter Zyklus wird `STALE`; Audit erhält Commit, vorherigen/neuen Head, Worker, Task, Tests und Zeitpunkte.
7. Der stabile Request-Kommentar wird mit frisch gelesenen Base-/Headdaten, neuem Key und aktualisiertem Handoff ersetzt; danach wird `hermes-review-requested` gesetzt.
8. Der neue Zyklus braucht unabhängige Reviews. Implementer/Remediation-Worker kann nicht selbst approven; Revieweridentitäten stammen aus dem nachgelagerten Orchestrierungs-/Reviewprozess, nicht aus dem Poller. Frühere PASS-Ergebnisse zählen nicht.

Fork-/Untrusted-Policy: Schema 1 erlaubt Review-Intake für Fork-PRs nur read-only. Remediation ist standardmäßig unzulässig, solange die konkrete Binding-Policy den Head nicht als trusted und beschreibbar ausweist. Es werden nie Fork-Code, PR-Skripte oder Tests mit Repository-/Org-Secrets oder privilegierten GitHub-Tokens ausgeführt. Bei unbekannter Herkunft, `pull_request_target`-ähnlicher Privilegierung oder fehlender Ruleset-Sicht ist Remediation `false` und Gate `BLOCKED`/`CHANGES_REQUIRED`.

## 15. Retry, Fehlerklassen und Recovery

Geschlossene Fehlerfamilien:

- `TRANSIENT_GITHUB`: Timeout, 429, 5xx, vorübergehende DNS/TLS-/Transportfehler. Retry mit exponential backoff + jitter, gedeckelt; Trigger bleibt.
- `GITHUB_AUTH`: fehlende/ungenügende Scope oder 401/403. Kein schneller Retry; `BLOCKED`, konkrete Capability ohne Tokeninhalt loggen.
- `MALFORMED_REQUEST`: Syntax/Schema/duplicate keys/ungültige Werte. Permanent bis Kommentaränderung; kein Task.
- `REQUEST_COMMENT_CONFLICT`: Null/mehrere/falsche stabile Marker-ID. Permanent bis Operatorauflösung.
- `STALE_SNAPSHOT`: A/B, Review- oder Gate-Revalidation weicht ab. Alter Key `STALE`; kein Gate-Upgrade.
- `BINDING_MISSING|AMBIGUOUS|INVALID`: kein Fallback, kein Task.
- `BINDING_CHANGED|ADMISSION_FAILED`: keine Promotion; Cycle `STALE` oder weiterhin `PENDING_READ_C`, Task bleibt `admission_pending`.
- `DB_BUSY`: bounded Retry; unbekannter Commit-Ausgang wird per Review-Key/Task-ID gelesen, nicht wiederholt.
- `LOCK_UNAVAILABLE`: Tick schreibt nichts; Alarm/Audit.
- `TASK_CREATE_FAILED`: Transaktion rollt Claim und Task zurück; retrybar nur nach Fehlerklassifikation.
- `CI_PENDING|CI_FAILED|CI_UNREADABLE`: nie PASS; pending wird später erneut gelesen, unreadable blockiert.
- `GITHUB_WRITE_UNCERTAIN`: read/reconcile vor Retry.
- `REMEDIATION_INELIGIBLE|CAS_LOST|UNTRUSTED_HEAD`: keine Branchmutation.
- `REMEDIATION_CONFLICT`: Source-Key oder Spezifikation kollidiert; kein Update und keine zweite Task.
- `INTERNAL_INVARIANT`: fail-closed, keine automatische Reparatur, strukturierter Fehler mit Korrelations-ID.

Retries erhöhen `attempt_count`, schreiben einen Attempt und `next_attempt_at`. Backoff wird pro Key persistent berechnet, sodass Restarts keinen Retry-Sturm verursachen. Dauerhafte Historie wird nie überschrieben; sensible Rohdaten und Tokens werden nicht persistiert.

## 16. Dry-Run und Logs

### 16.1 API/CLI

Interne API:

```text
poll_once(*, dry_run: bool, repository: str | None = None) -> PollReport
```

CLI:

```text
hermes kanban pr-review poll --dry-run --json
```

Optionales `repository` darf nur auf eine bereits aktivierte exakte Binding-Zeile filtern; es erzeugt keine Ad-hoc-Bindung. Ohne `--dry-run` erfordert der manuelle Poll explizit aktivierte Konfiguration. Ein zusätzlicher `validate-bindings --json`-Unterbefehl darf nur lesen.

Dry-Run MUSS dieselben Reads, Parser, Key-Berechnung, Binding-Validierung, Revalidation-Simulation, CI-/Remediation-Prädikate und stabile Sortierung ausführen. Es DARF NICHT:

- SQLite-Migrationen oder Rows/Events/Attempts schreiben,
- Lockfiles dauerhaft erzeugen,
- GitHub-Kommentare/Labels ändern,
- Tasks/Worktrees/Branches erzeugen,
- Cron-/Gateway-Konfiguration ändern,
- Worker oder Modelle starten.

Daher werden DBs read-only geöffnet und Migrationsbedarf als `MIGRATION_REQUIRED` berichtet. Reportfelder: Repository/PR, Comment-ID-Konflikte, normalisierte acht Key-Felder, escaped Preimage plus Preimage-SHA, berechneter Key, Binding/Projekt/Board/Orchestrierung, vorhandener Cycle/Task, geplante Transition/Writes, CI-Zustand, alle zehn Remediation-Bools, Skip-/Fehlerklasse und `writes_performed: 0`.

### 16.2 Strukturierte Logs

Events mindestens: `tick_start`, `tick_end`, `candidate`, `skip`, `binding`, `key_computed`, `comment_consistency`, `cycle_claim`, `task_created`, `label_reconcile`, `retry_scheduled`, `stale`, `pre_review_revalidate`, `pre_gate_revalidate`, `ci_gate`, `remediation_eligibility`, `remediation_cas`, `result_reconcile`, `error`.

Pflichtfelder: `event`, `correlation_id`, `repository`, `pr_number`, `review_key` (wenn berechenbar), `task_id` (wenn vorhanden), `error_class`, `retryable`, `dry_run`, `duration_ms`. Keine Tokens, Authorization-Header, Cookie, vollständige Prozessumgebung, Kommentar-/Task-Body-Rohtexte, Secrets, private Clone-URLs oder unredigierte subprocess stderr. GitHub Request-ID darf gespeichert werden.

## 17. Test- und Nachweismatrix

Alle Python-Tests laufen über `scripts/run_tests.sh`, nie direkt über `pytest`.

1. **Key-Golden Tests:** UTF-8, genau sieben LF, kein trailing LF, Repository/SHA lowercase, Refs case-preserving, Dezimal-PR; Base-Tip statt Merge-Base.
2. **Parser:** duplicate JSON keys, extra Marker, falsche Schema-Version, Unicode/control chars, SHA/ref/path limits, null/mehrere Kommentare, persistierte ID mismatch.
3. **Binding:** exakte Auflösung, archiviertes/fehlendes Projekt, fehlendes/mismatched Board, unbekanntes Profil, mehrere Claims; Beweis, dass current/default/last board und globale Orchestratorwerte nicht konsultiert werden.
4. **DB-Migration:** bestehende Boards/Projekte migrieren additiv und idempotent; alte Daten unverändert.
5. **Intake-Race und Admission:** zwei Prozesse/Connections für denselben Key; genau ein Cycle und Task. Ein kontrollierter Pause-Hook nach Intake-Commit und vor/waehrend Read C laesst parallel `recompute_ready`, manuelle Promote/Unblock-Versuche, Claim-, Review-Claim-, Stale-Reclaim- und Dispatcher-Ticks laufen; kein Pfad veraendert `admission_pending`, erzeugt Claim/Run/PID oder startet einen Worker. Read-C-Mutation bleibt `STALE`/nicht dispatchbar; nur erfolgreicher Binding-/Task-CAS setzt atomar `ready`.
6. **Scheduler:** exakt 300 Sekunden, non-overlap, Lockfehler fail-closed, Stop/Restart, mehrere Gateways, kein LLM-/Worker-Aufruf.
7. **State-Machines:** jede erlaubte und verbotene Transition; `STALE` nie Gate; `done` nie PASS; alte PASS nach Drift ungültig.
8. **Revalidation/TOCTOU:** Base-Tip-, Head-, Label-, Comment-, Binding- und Ruleset-Drift zwischen A/B/C, Review und Gate. Zwei Connections aktualisieren die Binding-Revision vor und waehrend Intake/Promotion; Sperrordnung plus Fingerprint-CAS liefern Rollback oder `STALE/admission_pending`, niemals Routing unter alter Projekt-/Board-/Orchestrierungsautoritaet.
9. **CI:** pending/missing/failure/duplicate/unknown nie PASS; alle required successful am exakten Head kann PASS ermöglichen.
10. **Remediation-Tabelle:** genau zehn Bedingungen, jede einzeln false; keine Task/Branchmutation; alle true erlaubt nur die transaktionale Materialisierung. Zwei Connections/Prozesse fuer denselben Source-Key, Spezifikationskonflikt sowie Crash vor Insert, nach Insert, vor Commit und Antwortverlust nach Commit beweisen exakt eine sichtbare Task und dieselbe `created_task_id`. Worker/Reviewer-Trennung.
11. **Branch-CAS:** parallele Worker, Lease-Verlust, protected/default branch, untrusted fork, non-fast-forward, restart; keine unerlaubte Mutation.
12. **Dry-Run:** Snapshot der DB-/GitHub-Fake-Zähler vor/nach; bitgleich null Writes und vollständiger deterministischer Report.
13. **E2E:** temp `HERMES_HOME`, reale `projects.db`/Board-DB, Fake-GitHub-Port, CLI→Poller→Task→revalidation→Result sowie Worker-Commit→neuer Key→neuer Request. Keine Mocks für DB-/Config-Auflösung.
14. **Regression:** mindestens die inventarisierten Kanban-, Review-, Dispatch-lock- und Gateway-Watcher-Tests; anschließend `npm run check` und sinnvoller voller `scripts/run_tests.sh`-Lauf.
15. **Live GitHub:** erst nach Contract-/Security-Freigabe in einem berechtigten Testrepo/Fork. Exakte PR-/Comment-/Label-/Base-/Head-/CI-IDs dokumentieren; fehlende Berechtigung wird `BLOCKED/NOT_RUN`, nie simuliertes PASS.

## 18. Betrieb, Aktivierung und Deaktivierung

Vor Aktivierung MUSS ein Operator:

1. Den Provenance-Gate aus Abschnitt 21 ausfuehren und das unabhaengige Contract-/Security-Review durch `agency-security-reviewer` als PASS nachweisen, gebunden an dieselben kanonischen Upstream-/Publikations-Repositories und exakt denselben finalen Commit, Remote-Ref, Pfad, Blob-SHA-256 und frischen Upstream-`main`-Basis-SHA.
2. GitHub-Write-Rechte, Label-Existenz, Ruleset-/Checks-Lesbarkeit und den tatsächlichen Fork/Remote verifizieren.
3. Binding über die explizite CLI in `projects.db` anlegen, read-back validieren und Board-Metadaten vergleichen.
4. `validate-bindings` und einen vollständigen `--dry-run --json` mit `writes_performed: 0` archivieren.
5. Tests einschließlich Race/Restart ausführen.
6. Erst danach `enabled: true` setzen und genau einen Gateway-Supervisor für das Profil verwenden.

Deaktivierung setzt `enabled: false` und startet/reloadet den Gateway auf dem unterstützten Weg. Sie löscht keine Zyklen, Tasks, Comments oder Auditdaten. In-flight Kanban-Reviews bleiben sichtbar und werden manuell abgeschlossen/blockiert; es erfolgt kein Rollback von GitHub-Historie.

## 19. Nicht-Ziele

- Kein automatischer Merge, kein Approval allein durch Automatisierung und kein Schreiben auf Base-/Default-Branches.
- Kein GitHub-Webhook in Schema 1; Polling ist die einzige Admission. Webhooks können später lediglich Wake-up-Signale sein und müssen denselben Poll-/Revalidate-Pfad verwenden.
- Kein Core-Model-Tool, keine LLM-Klassifikation, kein LLM-Routing und kein neuer globaler Reviewer/Worker/Modellwert.
- Keine Reviewer-Auswahl, Teamzuordnung oder Modellkonfiguration im Poller.
- Kein Fallback auf aktuelle/default/zuletzt genutzte Boards oder `kanban.orchestrator_profile`.
- Kein Ersatz des bestehenden Kanban-Review-Lifecycles; der Dispatcher materialisiert Intake und revisionsgebundene Auditdaten.
- Keine Ausführung untrusted PR-Codes mit privilegierten Secrets.
- Keine automatische Auflösung von Marker-/Binding-/Resultkonflikten.
- Keine Produktivaktivierung durch Migration oder Installationsupdate; Default bleibt aus.

## 20. Konsequenzen, Risiken und offene Annahmen

Positive Konsequenzen: eine enge, testbare Domänengrenze; genau-ein-Zyklus durch DB-Constraint; bestehender Gateway-/Kanban-Lifecycle bleibt Eigentümer der Workerprozesse; keine permanente Model-Tool-Schemafläche.

Kosten: additive Tabellen in zwei Stores; GitHub-Schreibvorgänge bleiben außerhalb von SQLite und benötigen Reconciliation; eine stabile Kommentar-ID erfordert explizite Konfliktbehandlung; Scheduler-Verfügbarkeit hängt am korrekt profilierten Gateway.

Vor Implementierung erneut zu verifizieren:

- Der inventarisierte Upstream-`main`-SHA ist nur die Architekturbasis und kann vor Implementierung fortgeschritten sein.
- Upstream `NousResearch/hermes-agent` gewaehrt diesem Actor nur READ. Das Publikations-Repository `Mateo817/hermes-agent` ist inzwischen als GitHub-Fork des Upstreams mit Schreibrecht verifiziert; diese Feststellung ersetzt weder den frischen Remote-Readback noch die erneute Fork-Pruefung im Provenance-Gate. Das Triggerlabel fehlte beim Inventar; Hooks waren wegen Scope nicht inventarisierbar.
- Die konkrete `gh api`-Antwort für Required Checks unter kombinierten Branch-Protection- und Ruleset-Konfigurationen muss gegen ein berechtigtes Repository validiert werden.
- Der bestehende unassigned Task-/Orchestrierungsweg muss für das konfigurierte Projekt beweisbar sein. Fehlt er, ist eine separate, geprüfte Orchestrierungsintegration nötig; der Poller darf nicht selbst einen Assignee einsetzen.
- GitHub-Kommentarupdate bietet kein serverseitiges Body-CAS. Schema 1 kompensiert durch Read/BodHash/Update/Read und Branch-/Key-Revalidation; echte konkurrierende Kommentarautoren können weiterhin einen sichtbaren `STALE`/Konflikt erzwingen, aber keine Freigabe.
- Filelocks auf Netzwerkdateisystemen sind nicht universell zuverlässig. Korrektheit beruht deshalb zusätzlich auf SQLite-Transaktionen und Unique Constraints.

Änderungen an Key-Feldern, Normalisierung, Markerformat, Gate-Semantik, den zehn Remediation-Bedingungen oder Routingautorität erfordern eine neue Schema-/Vertragsversion und erneutes unabhängiges Architektur-/Security-Review. Additive Logfelder und unbekannte optionale JSON-Felder dürfen kompatibel ergänzt werden, sofern sie keine Autorität tragen.

## 21. Verbindlicher Provenance- und Release-Gate

Unmittelbar vor jeder Implementierungsaufnahme oder -fortsetzung MUSS ein fail-closed, maschinenpruefbarer Gate-Lauf:

1. Aus dem Release-Manifest die kanonischen GitHub-Identitaeten fuer Upstream/Basis und Publikation lesen; fuer Schema 1 muessen sie exakt `NousResearch/hermes-agent` und `Mateo817/hermes-agent` sein. GitHub muss das Publikations-Repository frisch als Fork genau dieses Upstreams ausweisen. Lokale Remote-Namen werden nur als Transportkonfiguration protokolliert und niemals als Identitaetsbeweis verwendet.
2. `main` direkt vom genannten Upstream-Repository fetchen und den danach aufgeloesten vollen Commit als Live-Basis protokollieren; ein zuvor gespeicherter SHA oder nur ein lokaler Tracking-Ref genuegt nicht. Den finalen Nicht-Default-Ref separat direkt vom genannten Publikations-Repository fetchen.
3. Den im unabhaengigen PASS genannten finalen vollen Commit, Remote-Ref `refs/heads/...`, Pfad `docs/kanban/github-pr-review-dispatcher-contract.md`, finalen Blob-SHA-256 und Basis-SHA exakt aus dem Release-Manifest lesen. Abgekuerzte SHAs, lokale-only Refs, implizite Branches oder ein Ref in einem anderen Repository sind verboten.
4. Per Remote-Readback gegen das namentlich gebundene Publikations-Repository beweisen, dass der genannte Nicht-Default-Ref exakt den genannten Commit aufloest, und beweisen, dass der Commit vom genannten Upstream-Basis-SHA abstammt. Wenn Upstream-`main` seit dem PASS fortgeschritten ist, muss die Basis auf der neuen Spitze sauber neu hergestellt, der Kandidat neu gebunden, erneut publiziert und unabhaengig erneut reviewed werden; ein alter PASS darf nicht uebertragen werden.
5. Den Blob am genannten Commit/Pfad lesen und dessen SHA-256 exakt vergleichen; ausserdem beweisen, dass der gesamte Diff von Basis bis Kandidat als einzige Datei genau diesen Contract-Pfad enthaelt, und dass der Blob die erwartete Contract-Version nennt. Der Singleton-Changed-File-Scope ist eine aus Basis/Commit abgeleitete Invariante, kein sechstes Release-Manifest-Feld.
6. Mit `git merge-base --is-ancestor` beweisen, dass der verbotene Commit `aad0cbd55e9fef41cad79f7ca6f75b0e14a74ff6` kein Vorfahr des finalen Kandidaten ist. Merge, Cherry-pick oder sonstiger Import seiner Ancestry ist verboten. Die verworfene v1.0.0-Bindung bleibt ausschliesslich historische Evidenz und kann nie Release-Autoritaet sein.
7. Ein explizites, unabhaengiges `PASS` von `agency-security-reviewer` lesen, das dieselben zwei Repository-Identitaeten und genau dieselben fuenf finalen Bindungswerte nennt und keine offenen P0/P1/P2-Contract-Findings enthaelt. Taskstatus `done`, ein PASS zu einem anderen Blob oder Schweigen sind kein PASS.
8. Bei jeder fehlenden Remote-Berechtigung, jedem Fork-/Fetch-/Readback-/Hash-/Ancestry-/Scope-/Reviewer-Mismatch und jedem nicht aufloesbaren Ref mit `DO_NOT_IMPLEMENT` abbrechen. Es gibt keinen lokalen, gecachten, manuellen, Remote-Alias- oder Default-Branch-Fallback.

Der Gate-Report enthaelt die zwei kanonischen Repository-Identitaeten, die fuenf finalen Bindungswerte, Fetch-Zeit, Remote-Readback, Fork- und Ancestry-Ergebnisse, Reviewer-Verdikt und `implementation_release_authorized: true|false`, aber keine Credentials. Nur ein vollstaendig positives Ergebnis darf die separate Implementierungs-Task manuell freigeben; dieser Architektur-Task startet sie niemals selbst.
