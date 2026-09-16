# Deterministischer GitHub-PR-Review-Dispatcher: Architekturvertrag

Status: additive Architektur- und Adapterklarstellung, Schema 1; Implementierung bis gebundenem unabhängigen Release-Review-`PASS` verboten
Vertragsversion: `github-pr-review-dispatcher/v1.1.2`
Architektur-Task: `t_2c09a856` (CI-Provenance-Korrektur von `t_78d82a35`; Klarstellung von `t_8a99f79d`, Remediation von `t_48b63e1b`)
Inventar-Task: `t_58d44561`
Inventarisierte Upstream-Revision: `682a95258ce9e877cfb607a5ada6436183efdebb`
Inventar: `github-kanban-scheduler-inventory-2026-09-16.md`, 19149 Bytes, SHA-256 `bc29b43dc5c556698b3f3ecb0c0442a45c794cc847695039b6d04f0a90676d2f`
Kanonisches Upstream-/Basis-Repository: GitHub `NousResearch/hermes-agent`; frische Klarstellungsbasis nach direktem Remote-/Base-Ref-Read am 2026-09-16: `784d5c3f9c2cb77698d8a9d2e72b1d106a38ea88`
Dauerhaftes Publikations-Repository: GitHub `Mateo817/hermes-agent`, von GitHub als Fork von `NousResearch/hermes-agent` ausgewiesen; autoritativer Nicht-Default-Ref wird als `refs/heads/contracts/github-pr-review-dispatcher-v1.1.2-from-2e6999f` publiziert. Der unveränderliche v1.1.1-Vorgänger ist Commit `2e6999f945836b4fe43e5127d3068222e297c6eb` auf `refs/heads/contracts/github-pr-review-dispatcher-v1.1.1-base-784d5c3` und darf weder verschoben noch überschrieben werden.
Verworfene Evidenzbindung (keine Autoritaet): Commit `bf2c55cdd8777d0c3e45095ea3a76e939d33fc5e`, Ref `refs/heads/contracts/github-pr-review-dispatcher-v1.0.0`, Blob-SHA-256 `4108af3c8a8abd75c98acf165a2843301e4a5287a32865aff89b9c81a7dccb39`, verbotener Parent `aad0cbd55e9fef41cad79f7ca6f75b0e14a74ff6`
Byte-identischer Transfer auf sauberer Basis: Commit `ca1ebca7097461383301f5b66b90795c3ad3bde4`, SHA-256 erneut `4108af3c8a8abd75c98acf165a2843301e4a5287a32865aff89b9c81a7dccb39`

### 1.1.2-Klarstellung und Kompatibilitätsgrenze

Version 1.1.2 ändert weder die acht Review-Key-Felder noch deren Reihenfolge, Marker oder `schema_version: 1`. Sie übernimmt alle Klarstellungen aus 1.1.1 und schließt ausschließlich die dort offene Producer-Provenance für Required CI sowie die Installations-Evidenzformulierung. Bei einem Widerspruch ist diese Klarstellung normativ:

1. Maschinenlesbarer Request Schema 1 ist ausschließlich genau eine Markerzeile, unmittelbar gefolgt von genau einem `json`-Codeblock. Der flache Feldblock aus Workflow-Skill v5 ist Human-/Legacy-Dokumentation, kein zweites Wire-Format und wird nicht auto-akzeptiert. Eine künftige inkompatible Syntax benötigt `schema_version: 2`, explizite Parallel-Lesephase und neues Security-Review; es gibt keinen heuristischen Adapter.
2. Öffentliche Gate-Ergebnisse sind ausschließlich `APPROVED|CHANGES_REQUIRED|BLOCKED|FAILED`. Die interne Engine darf `PASS` und Checkzustand `NOT_RUN` führen. Erst der Result-Adapter mappt internes `PASS` nach vollständiger Read-E-Revalidation und allen Gates zu öffentlichem `APPROVED`. `NOT_RUN` wird nie als öffentliches positives Gate publiziert.
3. Vor Read C existiert nur ein Review-Zyklus in review-spezifischer Persistenz. Es wird weder ein nativer Kanban-Task noch ein nativer Status `admission_pending` angelegt. Erst nach erfolgreichem Read C und erneuter Binding-Revalidation wird ein regulärer nativer Task materialisiert und zurückgelesen. Danach bleiben native Decomposition, Dependencies, Readiness, Dispatch, Retry, Review und Eskalation unverändert.
4. Es werden keine globalen Guards in native Task-/Dispatch-Schreiber eingebaut. Review-spezifische Unique Constraints, CAS und Revalidation schützen nur Review-Zyklen und deren einmalige native Materialisierung. Autoritätsänderungen werden durch frische Werte/Fingerprint erkannt, nicht durch eine neue systemweite Statusmaschine.
5. Die zwölf Einzelbedingungen aus Workflow v5 sind kumulativ und autoritativ. Frühere zehn Aggregate bleiben nur deprecated Diagnostik und dürfen keine Remediation autorisieren.
6. GitHub-Refidentität ist byte-/codepoint-exakt. Validatoren dürfen Syntax ablehnen, aber weder Case Folding noch Unicode-Normalisierung oder andere Transformation anwenden. Mehrdeutigkeit oder eine transformierbare Abweichung blockiert.
7. Der aktuelle Base-Tip stammt aus einem frischen expliziten Read des von GitHub gemeldeten Base-Refs. Historisches PR-`.base.sha` und Merge-Base sind keine Base-Tip-Quelle.
8. Der Poller löst ausschließlich Repository → Projekt → Board → konfigurierte Orchestrierung auf. Er wählt keine globale Orchestrator-, Reviewer-, Worker-, Provider- oder Modellidentität und nutzt keinen Default.
9. Ein Request gilt erst nach bestätigter nativer Task-Erzeugung und Feld-Readback als erfolgreich verarbeitet. Crash/Retry vor diesem Punkt reconciled denselben Zyklus anhand des exakten Review-Keys; er erzeugt keinen zweiten Zyklus oder Task.
10. Required CI kann nur aus einer vollständig lesbaren, für den aktuellen Base-Ref anwendbaren GitHub-Policy positiv bewertet werden. Jede erforderliche Prüfung muss das exakte Tupel `(context_name, producer_kind=github_app, producer_app_id)` mit positiver numerischer App-ID liefern; Name oder Status-Context allein ist nie Producer-Identität.
11. CI-Evidenz stammt ausschließlich aus vollständig paginierten Check-Suite-/Check-Run-Reads für den exakten Candidate-Head. Exakter Name, `check_run.app.id`, Suite-ID und frisch gelesener `check_suite.head_sha` müssen übereinstimmen; Commit Statuses werden in dieser Version nicht als Required-CI-Nachweis akzeptiert.
12. Kanonische Policy- und Observation-Digests sowie sämtliche Quell-/Producer-/Suite-/Run-Identitäten werden persistiert und in Read D und Read E erneut gelesen. Jede Digest- oder Identitätsabweichung setzt den Lifecycle `STALE`; unlesbare/unsupported Policy ist `BLOCKED`, nachweislich untrusted oder negativ abgeschlossene Evidenz ist `FAILED`.

## 1. Zweck, Geltung und harte Grenzen

Dieser Vertrag definiert genau eine minimale Integrationsfläche für einen deterministischen, modellfreien Poller, der explizit angeforderte GitHub-Pull-Request-Reviews als bestehende Hermes-Kanban-Aufgaben materialisiert. Er ist revisionsgebunden an das oben bezeichnete Inventar; die Implementierung muss Abweichungen zur tatsächlichen Implementierungsbasis erneut prüfen.

Dieser Text allein autorisiert keine Implementierung. Die einzige Implementierungsfreigabe ist ein explizites Review-Verdikt `PASS` des fuer diesen Vertrag vorgeschriebenen unabhaengigen Reviewers `agency-security-reviewer` zu einem externen Release-Manifest; dieses Review-Verdikt ist kein öffentliches PR-Gate aus Abschnitt 5.2. Das Manifest nennt die beiden kanonischen GitHub-Repository-Identitaeten (Upstream/Basis und Publikation) sowie exakt neun Bindungswerte: finaler voller Release-Commit-SHA, dauerhaft publizierter Nicht-Default-Ref, Contract-Pfad und -Blob-SHA-256, Skill-Pfad und -Blob-SHA-256, Decision-Note-Pfad und -Blob-SHA-256 sowie unmittelbar vorher frisch gelesener Upstream-`main`-Basis-SHA. Lokale Remote-Namen wie `origin`, `upstream` oder `fork` sind Aliase und tragen keine Autoritaet. Fehlt ein Wert, weicht er ab, ist der Ref im genannten Publikations-Repository nicht remote lesbar, ist dessen Fork-Beziehung zum genannten Upstream nicht belegbar oder nennt das PASS nur die verworfene Evidenzbindung, bleibt die Implementierung verboten.

Normative Begriffe `MUSS`, `DARF NICHT`, `SOLL` und `KANN` sind verbindlich. Bei fehlenden, widersprüchlichen oder mehrdeutigen Daten gilt fail-closed: keine Task-Erzeugung, keine Review-Freigabe und keine Branch-Mutation.

Feststehende Grenzen:

- Trigger sind gleichzeitig das GitHub-Label `hermes-review-requested` und genau ein stabiler Issue-Kommentar mit `<!-- hermes-review-request -->` und Schema 1.
- Der Poller liest Repository, PR, Base und Head selbst von GitHub. Kommentarwerte sind Behauptungen, keine Autorität.
- Pro Review-Key existiert höchstens ein Review-Zyklus.
- Routing erfolgt ausschließlich über eine eindeutige Repository→Hermes-Projekt→Kanban-Board→konfigurierte-Orchestrierung-Bindung.
- Es gibt keinen Namensheuristik-, aktuellen-Board-, `default`-, `hermes-system`-, letzten-Board- oder globalen Orchestrator-Fallback.
- Der Poller wählt und setzt keine Reviewer-, Review-/Remediation-Worker-, Provider- oder Modellidentität. Die einzige Task-Identität, die er überträgt, ist das unverändert aus der kanonischen Binding-Zeile gelesene `orchestration_profile` als Intake-Routingziel; dafür existiert kein Default. Er merged nicht und schreibt nie auf eine Default-/Base-Branch.
- Öffentlicher Gate-Zustand und technischer Lifecycle sind getrennt. `STALE` ist ausschließlich Lifecycle und niemals ein Gate-Ergebnis. Kanban `done` ist niemals gleichbedeutend mit internem `PASS` oder öffentlichem `APPROVED`.
- Pflicht-CI in `PENDING`, `QUEUED`, `IN_PROGRESS`, fehlend, übersprungen, neutral, abgebrochen, stale, action-required, timed-out, fehlproduziert oder unbekannt ist nicht `PASS`.
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
| `hermes_cli/kanban_db.py` | Additive Tabellen/Operationen für Zyklen, Attempts, Events und TODOs; pre-task Admission nur in Review-Persistenz; einmalige native Task-Materialisierung nach Read C | review-spezifische Durable State im Ziel-Board |
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
- `read_required_check_policy(repository, base_ref, base_tip) -> RequiredCheckPolicySnapshot`
- `read_check_suites(repository, head_sha) -> list[CheckSuiteSnapshot]`, `read_check_suite(repository, suite_id) -> CheckSuiteSnapshot` und `read_check_runs(repository, suite_id, filter="all") -> list[CheckRunSnapshot]`; Listenoperationen müssen vollständig paginieren
- `remove_label(repository, number, label)` und `add_label(...)`
- `update_comment(repository, comment_id, body, expected_body_hash=None)`
- `create_result_comment(...) -> CommentIdentity` nur wenn noch kein persistierter Result-Kommentar existiert
- `read_branch_protection(...)` und `compare_branch_head(...)` für Remediation

Die Implementierung SOLL vorhandenes authentifiziertes `gh api` als Subprozessgrenze verwenden, weil `gh` inventarisiert ist und keine neue Python-Abhängigkeit nötig ist. Alle Aufrufe verwenden Argumentlisten ohne Shell, feste `GET`-Endpunkte, `Accept: application/vnd.github+json`, explizite unterstützte `X-GitHub-Api-Version`, vollständige Pagination über `Link`/`gh api --paginate` und striktes JSON-Parsing; Token, Header, vollständige Prozessumgebung und rohe Fehlkörper werden nicht geloggt. Response-Status, GitHub Request-ID, Retrieval-Zeit und ETag (wenn vorhanden) werden als Evidenz geführt. Ein ETag darf zur Optimierung dienen, ersetzt aber nie den normativen frischen Read.

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

`repository` ist der kanonische GitHub-Name `owner/name` in lowercase. `project_id` zeigt auf genau einen nicht archivierten `projects`-Datensatz. Das Zielboard ist ausschließlich dessen nichtleeres `projects.board_slug`; es wird nicht in der Binding-Tabelle dupliziert. `orchestration_profile` ist das projektspezifisch konfigurierte Routingziel und nichtleer. `project_repository_binding_versions` ist ein nie gelöschtes High-Water-Ledger. Jede Änderung über die explizite Binding-API reserviert in deren `BEGIN IMMEDIATE`-Transaktion `last_revision + 1`; erstmalige Anlage beginnt bei 1. Delete deaktiviert/entfernt nur die Binding-Zeile, nie das Ledger, sodass Recreate keine Revision wiederverwendet. Änderungen der aufgelösten Projekt-/Boardwerte werden bei jedem Guard aus den Live-Werten in den Fingerprint aufgenommen und lösen bei Abweichung `BINDING_CHANGED` aus; native Schreiber werden nicht global ersetzt oder gesperrt. Es gibt bewusst keine globale Orchestrator-Konstante und `kanban.orchestrator_profile` ist kein Fallback. Der Poller übernimmt ausschließlich das exakt gebundene `orchestration_profile` als native Intake-Assignee; dies ist Datenweitergabe der kanonischen Route, keine Auswahl eines globalen Orchestrators, Reviewers, Remediation-Workers, Providers oder Modells.

Das Board selbst MUSS anhand des expliziten Slugs geöffnet werden. Seine Metadaten MÜSSEN `project_id` gleich dem gebundenen Projekt ausweisen. Auflösungen über `get_current_board()`, persistierten current-board pointer, Umgebungsvariable ohne Binding, `default` oder Namensgleichheit sind verboten.

### 4.2 Binding-Validierung

Beim Aktivieren, beim manuellen Poll und vor jeder Task-Transaktion werden alle folgenden Bedingungen geprüft:

1. Repository erfüllt exakt `^[a-z0-9](?:[a-z0-9_.-]{0,38})/[a-z0-9](?:[a-z0-9_.-]{0,99})$` nach lowercase-Normalisierung; `.git`, URL, SSH-Syntax und Unicode werden abgelehnt.
2. Genau eine Binding-Zeile existiert und `enabled=1`.
3. Das Projekt existiert, ist nicht archiviert und hat absoluten, existierenden `primary_path` sowie nichtleeren `board_slug`.
4. Das Board existiert unter dem kanonischen Kanban-Home, ist nicht archiviert und seine Metadaten enthalten dieselbe `project_id`.
5. `orchestration_profile` ist ein kanonischer installierter Profilname und ist nicht leer. Es wird nach Read C unverändert als Assignee des nativen Orchestrierungs-Intake-Tasks weitergegeben; der Poller darf keinen anderen oder globalen Wert wählen.
6. Keine zweite aktivierte Binding-Zeile oder zweite Projektidentität beansprucht dasselbe Repository. Wegen `PRIMARY KEY(repository)` ist dies lokal ausgeschlossen; inkonsistente importierte Stores blockieren dennoch.

Jeder Fehler ergibt `BINDING_MISSING`, `BINDING_AMBIGUOUS` oder `BINDING_INVALID`, schreibt keinen Task und löst keine Board-/Profil-Defaults aus.

### 4.3 Kanonischer Binding-Fingerprint und Binding-Guard

Nach erfolgreicher Aufloesung wird eine immutable Authority-Snapshot-Version erzeugt. Das Preimage besteht aus genau sechs UTF-8-Feldern in dieser Reihenfolge, mit genau fuenf ASCII-LF und ohne trailing LF:

```text
binding/v1\nrepository\nproject_id\nboard_slug\norchestration_profile\nbinding_revision
```

Repository ist lowercase; `project_id`, `board_slug` und Profil sind die unveraenderten kanonischen Persistenzwerte; `binding_revision` ist positive kanonische Dezimaldarstellung. `binding_fingerprint = sha256(preimage).hexdigest()` in lowercase. Version, Fingerprint und alle aufgeloesten Felder werden gemeinsam im Cycle und im Task-Body gespeichert. Ein Timestamp ist kein Versionsersatz.

Binding-Schreiber reservieren `binding_revision` in der vorhandenen Projekt-Persistenz. Der Reviewpfad liest unmittelbar vor dem pre-task Cycle-Commit und erneut nach Read C alle aufgelösten Authority-Werte und berechnet den Fingerprint aus den tatsächlich gelesenen Werten. Projekt-/Board-/Profilwerte werden nicht gecacht. Es gibt keinen neuen globalen Guard für fremde Projekt-, Board-, Task- oder Dispatch-Schreiber und keine Cross-DB-Transaktion, die eine nicht vorhandene Atomizität vortäuscht.

Der review-spezifische Guard wird zweimal ausgeführt: unmittelbar vor dem dauerhaften pre-task Cycle-Commit und unmittelbar vor der nativen Task-Materialisierung nach Read C. Beim zweiten Lauf müssen Revision, Fingerprint und alle aufgelösten Identitäten bytegleich mit dem gespeicherten Snapshot sein. Mutation oder Mismatch erzeugt `BINDING_CHANGED`, setzt den Cycle `STALE` und erzeugt keinen Task. Eine spätere Binding-Änderung kann einen gestarteten Review nicht umleiten; Read D muss ihn vor fachlicher Arbeit erneut gegen den gespeicherten Fingerprint revalidieren und andernfalls ohne positives Gate `STALE` setzen.

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

Der Kommentar besteht vollständig aus der Markerzeile, unmittelbar gefolgt von genau einem als `json` markierten Codeblock; außer Whitespace ist vor, zwischen oder nach diesen beiden Elementen kein Inhalt zulässig. Der flache v5-Feldblock ist keine alternative Syntax. Unbekannte Top-Level-Felder im JSON-Objekt werden für Vorwärtskompatibilität ignoriert, aber nicht in den Review-Key aufgenommen.

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
- Repositorywerte werden nach GitHubs kanonischem `nameWithOwner` lowercase geführt; Full-SHAs sind exakt 40 lowercase Hexzeichen. Base-/Head-Refs werden als von GitHub gelieferte UTF-8-Codepointfolge bytegleich übernommen. Sie werden weder case-folded noch Unicode-normalisiert oder anderweitig transformiert. Syntaxprüfung darf Steuerzeichen, LF, NUL, `..`, führenden/trailing Slash und Git-verbotene Refsequenzen ablehnen; eine nur nach Transformation gültige oder kollidierende Form ist `REQUEST_MISMATCH`/`BLOCKED`.
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
  "gate": "APPROVED|CHANGES_REQUIRED|BLOCKED|FAILED",
  "lifecycle": "COMPLETED|STALE|BLOCKED",
  "required_ci": "PASS|FAIL|PENDING|MISSING",
  "ci_policy": {
    "base_ref": "main",
    "base_tip": "<40 lowercase hex>",
    "digest": "<64 lowercase hex>",
    "retrieved_at": "<RFC3339 UTC>",
    "sources": [{"kind": "ruleset", "id": "14161644", "api_url": "<canonical API identity>", "retrieved_at": "<RFC3339 UTC>", "etag": "<optional>"}]
  },
  "ci_observations": [{
    "context": "All required checks pass",
    "expected_app_id": 15368,
    "check_run_id": 1,
    "check_suite_id": 2,
    "observed_app_id": 15368,
    "observed_name": "All required checks pass",
    "observed_run_head_sha": "<40 lowercase hex>",
    "observed_suite_head_sha": "<40 lowercase hex>",
    "status": "completed",
    "conclusion": "success",
    "completed_at": "<RFC3339 UTC>",
    "details_url": "https://github.com/...",
    "run_retrieved_at": "<RFC3339 UTC>",
    "run_etag": "<optional>",
    "suite_retrieved_at": "<RFC3339 UTC>",
    "suite_etag": "<optional>",
    "digest": "<64 lowercase hex>"
  }],
  "task_id": "t_<id>",
  "review_run_ids": [1],
  "finding_ids": ["F-001"],
  "generated_at": "<RFC3339 UTC>"
}
```

`STALE`, internes `PASS` und Checkzustand `NOT_RUN` sind im öffentlichen Feld `gate` nicht zulässig. Die additiven CI-Objekte sind für v1.1.2 bei jedem terminalen Resultat verpflichtend und enthalten die vollständigen persistierten Quellen/Beobachtungen; kein Kommentarwert ist CI-Autorität. Resultate sind eine Projektion aus persistiertem Kanban-/Reviewzustand und GitHub-Revalidation, keine Eingabe, die einen Gate-Zustand autorisiert. Nur der Result-Adapter mappt internes `PASS` nach erfolgreicher letzter Read-E-Revalidation einschließlich identischer Policy-/Observation-Digests zu `APPROVED`; interne terminale technische/CI-Fehler werden `FAILED`, externe Fähigkeit, Unsupported Policy oder unlesbare/mehrdeutige Autorität wird `BLOCKED`, Findings werden `CHANGES_REQUIRED`. Der Writer speichert die von GitHub zurückgegebene `result_comment_id`, Actor-ID und Body-Hash. Ein später gelesener Result-Kommentar ist nur konsistent, wenn ID, Key und Hash mit der Persistenz übereinstimmen. Ein fremder/duplizierter Marker blockiert die Veröffentlichung; er kann niemals `APPROVED` erzeugen. Bei ungewissem Write-Ausgang wird zuerst per ID beziehungsweise exakt persistiertem Key/Actor/Hash reconciled und nicht blind erneut erstellt.

## 6. Review-Key Schema 1

### 6.1 Normalisierung

Die acht Felder werden exakt wie folgt erzeugt:

1. `schema_version`: ASCII `1`.
2. `repository`: GitHub `nameWithOwner`, getrimmt, lowercase.
3. `pr_number`: kanonische positive Dezimaldarstellung ohne Vorzeichen oder führende Nullen.
4. `base_ref`: von GitHub gelesener Refname, byte-/codepoint-exakt, kein Case Folding, keine Unicode-Normalisierung und kein Trim außer Ablehnung von umgebendem Whitespace.
5. `base_sha`: aktueller Tip aus einem separaten, frischen GitHub-Read exakt dieses Base-Refs zum Zeitpunkt des Snapshots, vollständige 40-Hex-SHA, lowercase. Es ist ausdrücklich weder historisches PR-`.base.sha`, PR-Merge-Base, Merge-Commit noch bei PR-Erstellung gespeicherter SHA.
6. `head_repository`: GitHub `headRepository.nameWithOwner`, getrimmt, lowercase.
7. `head_ref`: von GitHub gelesener Head-Ref, byte-/codepoint-exakt, kein Case Folding, keine Unicode-Normalisierung und kein Trim außer Ablehnung von umgebendem Whitespace.
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
    engine_gate             TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS pr_review_ci_policy_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    review_key          TEXT NOT NULL REFERENCES pr_review_cycles(review_key),
    boundary            TEXT NOT NULL CHECK (boundary IN ('EVALUATION','READ_D','READ_E')),
    base_ref            TEXT NOT NULL,
    base_tip            TEXT NOT NULL,
    retrieved_at        TEXT NOT NULL,
    etag                 TEXT,
    policy_digest       TEXT NOT NULL,
    canonical_json      TEXT NOT NULL,
    evidence_json       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pr_review_ci_observations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_snapshot_id  INTEGER NOT NULL REFERENCES pr_review_ci_policy_snapshots(id),
    context_name        TEXT NOT NULL,
    producer_kind       TEXT NOT NULL CHECK (producer_kind = 'github_app'),
    expected_app_id     INTEGER NOT NULL CHECK (expected_app_id > 0),
    check_run_id        INTEGER,
    check_suite_id      INTEGER,
    observed_app_id     INTEGER,
    observed_name       TEXT,
    observed_run_head_sha   TEXT,
    observed_suite_head_sha TEXT,
    status              TEXT,
    conclusion          TEXT,
    completed_at        TEXT,
    details_url         TEXT,
    run_retrieved_at    TEXT NOT NULL,
    run_etag             TEXT,
    suite_retrieved_at  TEXT,
    suite_etag           TEXT,
    observation_digest  TEXT NOT NULL,
    canonical_json      TEXT NOT NULL
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

`lifecycle`, internes `engine_gate`, `required_ci`, attempt status und TODO status werden zusätzlich in Python gegen die geschlossenen Mengen dieses Vertrags validiert; SQLite-`CHECK`s SOLLEN diese Mengen spiegeln. Migrationen dürfen bestehende Tasktabellen oder Statusmengen nicht umdeuten.

`admission_status` ist die review-interne geschlossene Menge `PENDING_READ_C`, `MATERIALIZING_TASK`, `MATERIALIZED`, `STALE`; kein Wert davon ist ein nativer Taskstatus. Für Remediation-TODOs ist `status` mindestens `MATERIALIZING`, `TASK_CREATED`, `CLAIMED`, `COMPLETED`, `BLOCKED`; `materialization_hash` ist SHA-256 der kanonischen immutable Task-Spezifikation. Zusätzlich MÜSSEN migrationsgeprüfte partielle Unique-Indizes auf `tasks(idempotency_key)` über alle Task-Lifecycle-Zustände einschließlich `archived` höchstens einen Task für jeden nichtleeren Key mit Prefix `pull_request_review:` beziehungsweise `pull_request_remediation:` zulassen; die Prädikate sind feste Schema-1-Konstanten, nicht vom Aufrufer wählbar. Findet die Migration bereits Duplikate, bricht sie fail-closed ab und publiziert keinen davon als gültigen Review-/Remediation-Task. Archivierung autorisiert keinen Ersatz-Task für denselben Review- oder Source-Key.

### 7.2 Task-Typ und immutable Metadaten

Das bestehende `tasks`-Schema besitzt keinen Task-Typ. Daher wird ein regulärer Kanban-Task erzeugt und `pull_request_review` revisionssicher in `pr_review_cycles.task_type` sowie in einem kanonischen JSON-Block im Task-Body abgebildet. Der Block enthält mindestens:

- `task_type: pull_request_review`, `schema_version: 1`, `review_key`
- Repository/PR URL und Nummer
- Base-/Head-Repository, Refs und volle SHAs
- `request_comment_id` und Request-Body-Hash
- `project_id`, expliziter `board_slug`, `binding_revision`, `binding_fingerprint` und die vier kanonischen Authority-Felder
- Handoff: Summary, Changed Files, Testbefehle, bekannte Risiken
- Pflichtaktionen: GitHub frisch lesen; vor Review und vor Gate revalidieren; CI prüfen; kein Merge
- CI-Policy-Quellen mit Kind/ID/API-Identität, Base-Ref/Tip, Retrieval-Zeit/ETag, kanonischem Digest und allen `(context_name, github_app, producer_app_id)`-Tupeln; pro Tupel vollständige Check-Run-/Suite-Evidenz und Observation-Digest
- Audit-IDs und erlaubte Gate-/Lifecycle-Werte

Der Task erhält `project_id`, den vorhandenen projektgebundenen `workspace_kind=worktree`-Pfad, `idempotency_key="pull_request_review:" + review_key` und exakt den gebundenen `orchestration_profile` als Orchestrierungs-Assignee. Dieses Feld ist ein konfiguriertes Routingziel, keine Pollerentscheidung über Reviewer oder ausführenden Remediation-Worker. `skills`, `model_override`, `provider_override`, `reasoning_effort` und Reviewer bleiben NULL/leer. Die gebundene Orchestrierung muss den Intake über ihren bestehenden, separat verantworteten Ablauf weiter routen. Falls dieses Profil nicht installiert oder nicht als Orchestrierungsweg verwendbar ist, ist die Binding-/Orchestrierungsfähigkeit `BINDING_INVALID` und kein Task wird erzeugt.

## 8. Transaktionen, Idempotenz und Admission

`tasks.idempotency_key` ist derzeit nur normal indexiert; `create_task()` dokumentiert eine akzeptierte Race, bei der konkurrierende Inserts Duplikate erzeugen können. Diese Semantik reicht für Review-Key-Exactly-Once nicht aus. Die Review-Tabelle mit `review_key PRIMARY KEY` und `task_id UNIQUE` ist daher die normative Idempotenzgrenze.

Pre-task Admission und anschließende native Materialisierung im explizit gebundenen Board:

1. GitHub-Read A und erste Binding-Validierung erfolgen außerhalb der Write-Transaktion.
2. Unmittelbar vor dem Write wird GitHub als Read B erneut gelesen und der Snapshot bytegenau verglichen.
3. Der review-spezifische Binding-Guard aus 4.3 liest die Autorität erneut und vergleicht Revision, aufgelöste Werte und Fingerprint; er führt keinen globalen nativen Schreib- oder Dispatch-Guard ein.
4. `BEGIN IMMEDIATE` über den vorhandenen Board-`write_txn` startet.
5. `pr_review_subjects` wird auf stabile Comment-ID geprüft/eingefügt.
6. Ausschließlich `pr_review_cycles` wird mit `lifecycle='CLAIMED'`, `admission_status='PENDING_READ_C'`, `engine_gate='NOT_RUN'`, Binding-Version und Fingerprint eingefügt. Ein Unique-Konflikt bedeutet deterministisches `ALREADY_EXISTS`, nicht Retry/Create. Es existiert noch keine Zeile in `tasks`.
7. Review-Events werden in derselben Board-Transaktion geschrieben und der Cycle-Commit wird bestätigt.
8. Erst nach bestätigtem Cycle-Commit darf der Poller das Triggerlabel für exakt diesen Key entfernen und Read C ausführen. Bis dahin und während Read C existiert kein nativer Task, also auch kein Claim, `task_run`, Worker-PID oder Workspace-Start.
9. Nach erfolgreichem Read C und zweiter Binding-Revalidation startet eine neue `BEGIN IMMEDIATE`-Board-Transaktion. Per CAS `PENDING_READ_C -> MATERIALIZING_TASK` erzeugt eine connection-scoped Primitive genau einen regulären nativen Task mit `idempotency_key="pull_request_review:" + review_key`, dem konfigurierten Orchestrierungsziel und den normalen nativen Feldern. Sie erfindet keinen Status und umgeht keine native Parent-/Readiness-Semantik.
10. Der Task wird anhand ID, Status, Assignee, `project_id`, Body-Key, Binding-Fingerprint und Idempotency-Key zurückgelesen. Erst nach vollständigem Readback setzt derselbe Commit `task_id`, `admission_status='MATERIALIZED'` und Lifecycle `IN_REVIEW` und schreibt Task-/Review-Events. Ein Insert-Konflikt wird nur durch exakten Readback derselben Task reconciled; Feldabweichung ist `INTERNAL_INVARIANT`.

Jeder Fehler vor dem pre-task Commit rollt den Cycle zurück. Crash nach Cycle-Commit vor Label-Entfernung oder Read C ist sicher: der nächste Lauf findet denselben Review-Key und reconciled die ausstehende Label-Projektion; ein Task existiert noch nicht. Crash oder verlorene Antwort während der Materialisierung wird anhand Review-Key, Cycle-`task_id` und unique Task-Idempotency-Key gelesen; nur exakter Readback darf Erfolg melden. Kein Request wird vor diesem Readback als verarbeitet markiert. Es gibt keinen Delete-and-recreate-Pfad und keinen alternativen nativen Status.

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
8. Atomare pre-task Cycle-Erzeugung als `admission_status=PENDING_READ_C`; es wird noch kein nativer Task erzeugt.
9. GitHub-Write: Triggerlabel für genau diesen Key entfernen. Der Request-Kommentar bleibt als stabile Historie bestehen.
10. Read C liest nach dem Write PR-Node-ID, open/draft, Base-/Head-Repository/Ref/SHA, aktuellen Base-Tip, Labelzustand, stabile Comment-ID, Body-Hash/`updated_at` und Result-Marker erneut. Alle Identitaets- und Requestwerte muessen Read B entsprechen und nur das erwartete Triggerlabel darf entfernt sein.
11. Nach erfolgreichem Read C wird die Binding-Revalidation erneut ausgeführt. Eine Board-Transaktion materialisiert per review-spezifischem CAS und unique Idempotency-Key genau einen regulären nativen Task, liest ihn vollständig zurück und markiert erst dann den Cycle `MATERIALIZED/IN_REVIEW`. Der vorhandene native Kanban-Lifecycle entscheidet dessen normale Readiness und alle Folgeschritte.
12. Scheitert Read C oder der zweite Binding-/CAS-Check permanent, setzt eine Board-Transaktion den Cycle `STALE`; es existiert kein Task. Bei transient/ungewissem Read-C-Ausgang bleibt `PENDING_READ_C` unverändert und wird read-before-retry reconciled. Kein Fehlerpfad darf einen Task, Claim oder Worker erzeugen.

Vor Beginn eines menschlichen/agentischen Reviews MUSS der Review-Worker über eine schmale `revalidate_for_review(review_key)`-Operation Read D durchführen. Vor jedem Gate-/Result-Write MUSS `revalidate_for_gate(review_key)` Read E durchführen. Beide lesen zusätzlich die vollständige Required-CI-Policy und alle Check-Suite-/Check-Run-Beobachtungen nach Abschnitt 12 neu und vergleichen aktuelle Base-/Head-/Request-/Bindingwerte, Key, Quellidentitäten und beide Digestarten. Jede Abweichung, auch Producer-Rotation, Ruleset-/Branch-Protection-Änderung, hinzugefügter/entfernter Check, Run-/Suite-Austausch oder Beobachtungsänderung, setzt Lifecycle `STALE`, lässt `engine_gate` unverändert (`NOT_RUN`, `CHANGES_REQUIRED`, `BLOCKED`, `FAILED` oder historisches `PASS`) und verbietet die Verwendung des alten Resultats für den aktuellen PR. Ein unveränderter Digest aus einem Cache ist kein Read D/E.

## 11. Lifecycle-, Label- und Gate-State-Machines

### 11.1 Lifecycle

Geschlossene Menge:

`DISCOVERED`, `CLAIMED`, `IN_REVIEW`, `REMEDIATION_PENDING`, `REMEDIATING`, `REREVIEW_REQUESTED`, `COMPLETED`, `BLOCKED`, `STALE`.

Erlaubte Übergänge:

- `DISCOVERED -> CLAIMED`; erst erfolgreiche Read-C-/Binding-Revalidation plus bestätigte native Task-Materialisierung erlaubt `CLAIMED -> IN_REVIEW`
- `IN_REVIEW -> COMPLETED` bei terminalem, revalidiertem Gate
- `IN_REVIEW -> REMEDIATION_PENDING -> REMEDIATING`
- `REMEDIATING -> STALE` für den alten Key, nachdem ein Worker-Commit einen neuen Head erzeugt hat
- Neuer Key: `DISCOVERED -> ... -> REREVIEW_REQUESTED -> IN_REVIEW`
- Jeder nichtterminale Zustand -> `BLOCKED` bei permanentem externen/Vertragsfehler
- Jeder nichtterminale oder terminale alte Zyklus -> `STALE` bei Base-/Head-/Request-Drift; historische Felder bleiben erhalten

`STALE` ist terminal für genau diesen Key; es kann nicht zurück nach `IN_REVIEW`. Ein neuer Commit ist ein neuer Zyklus.

### 11.2 Admission

`PENDING_READ_C -> MATERIALIZING_TASK -> MATERIALIZED` ist nur durch die in Abschnitt 10 beschriebenen review-spezifischen CAS-Schritte erlaubt. `PENDING_READ_C|MATERIALIZING_TASK -> STALE` ist terminal, sofern exakter Task-Readback nicht bereits einen committed Erfolg beweist. Vor `MATERIALIZED` existiert kein nativer Task. Nach `MATERIALIZED` gelten ausschließlich die vorhandenen nativen Status- und Dispatcherregeln; dieser Vertrag ergänzt keine Statusmenge und keinen globalen Dispatch-Guard.

### 11.3 Gate

Interne geschlossene Menge `engine_gate`: `NOT_RUN`, `PASS`, `CHANGES_REQUIRED`, `BLOCKED`, `FAILED`. Öffentliche geschlossene Menge: `APPROVED`, `CHANGES_REQUIRED`, `BLOCKED`, `FAILED`.

- Internes `PASS` erfordert aktuelle Revalidation, unabhängige geforderte Reviews, keine offenen P0/P1, Pflicht-CI vollständig `PASS`, konsistenten Request/Result und offenen, nicht gemergten PR. Ausschließlich der Result-Adapter publiziert es danach als `APPROVED`.
- `CHANGES_REQUIRED` beschreibt fachliche Findings; es ist nicht dasselbe wie Lifecycle `STALE`.
- `BLOCKED` beschreibt fehlende externe Fähigkeit, mehrdeutige Identität oder Vertragsverletzung.
- `FAILED` beschreibt einen terminalen negativen technischen/CI-Ausgang, nicht einen nicht ausgeführten Check.
- `NOT_RUN` ist nur interner Check-/Enginezustand und nie öffentlich positiv.
- Ein historisches Gate wird nie in `STALE` umbenannt. Die aktuelle Gültigkeit ergibt sich aus dem Lifecycle und exakt passendem Key.

### 11.4 Triggerlabel

- Label + valider Request sind gemeinsam Admission.
- Vor erfolgreichem pre-task Cycle-Commit bleibt das Label bei transienten und permanenten Fehlern unverändert, damit kein Request verloren geht.
- Nach bestätigtem Cycle-Commit wird das Label idempotent entfernt und anschließend Read C ausgeführt. Fehler beim Entfernen werden retrybar auditiert; der persistierte Key verhindert Doppelverarbeitung. Erfolgreich verarbeitet ist der Request erst nach nativer Task-Materialisierung und exaktem Readback.
- Ein Worker-Commit aktualisiert zuerst den stabilen Request-Kommentar auf den neuen, frisch gelesenen Key und setzt danach das Label erneut. Schlägt einer dieser Schritte ungewiss fehl, erfolgt Read/Reconcile statt blindem Wiederholen.
- Der Poller setzt kein Label aufgrund einer Heuristik und entfernt nie Labels von einem abweichenden aktuellen Key.

## 12. CI-Gate

### 12.1 Unterstützte Policy-Quelle und Discovery

Policy ist ausschließlich Repository-/Base-Ref-Daten von GitHub. Sie darf niemals aus Checknamen, Commit Statuses, PR-Kommentaren, Workflow-Ausgabe, Development-Agent-Eingabe, Projektähnlichkeit, historischer Evidenz oder einem Default abgeleitet werden.

Für jeden Snapshot wird zuerst der aktuelle Base-Tip separat gelesen. Danach müssen mindestens folgende `GET`s mit expliziter API-Version und vollständiger Pagination ausgeführt werden:

1. `GET /repos/{owner}/{repo}/rules/branches/{base_ref}?per_page=100` liefert alle aktiven anwendbaren Repository-/Organization-Ruleset-Regeln einschließlich `ruleset_source_type`, `ruleset_source`, `ruleset_id` und `required_status_checks[].{context,integration_id}`. Der exakte Ref wird als ein URL-Pathsegment percent-encoded, niemals normalisiert. Nur `type=required_status_checks` mit jedem `integration_id` als positivem Integer wird unterstützt. `type=workflows` ist in v1.1.2 unsupported, weil dessen REST-Identität keinen erforderlichen Check-Producer-Tupel garantiert, und ergibt `BLOCKED`.
2. `GET /repos/{owner}/{repo}/branches/{base_ref}/protection` beziehungsweise der darin bezeichnete Required-Status-Checks-Read liefert klassische Branch-Protection-Policy. Aus `required_status_checks.checks[].{context,app_id}` werden Tupel nur bei positivem Integer-`app_id` gebildet. `contexts` ohne deckungsgleiches producergebundenes `checks`-Element, `app_id=null`, `app_id=-1` oder fehlende Status-Check-Policy sind nicht positiv auswertbar.

Ein `404` auf Branch Protection darf nur als „keine klassische Policy“ behandelt werden, wenn der verwendete Actor separat mit Repository-Administration-Read/Admin-Fähigkeit autoritativ nachgewiesen ist; andernfalls ist `404` wegen der Ununterscheidbarkeit von „nicht vorhanden“ und „nicht sichtbar“ `BLOCKED`. `401`, `403`, unvollständige Pagination, unbekannte Regeltypen mit CI-Wirkung, malformed JSON oder fehlende Quellfelder sind stets `CI_POLICY_UNREADABLE/BLOCKED`. Operatoraktion: dem dedizierten GitHub-App-/Fine-grained-Token mindestens lesenden Zugriff auf Repository Administration/Rulesets sowie Checks/Contents/Metadata geben, Organization-/Enterprise-Rulesets für den Actor sichtbar machen und den vollständigen Policy-Read erneut ausführen; niemals einen Namen oder App-ID als Ersatz konfigurieren.

Alle Quellen werden zu einer Menge von `(context_name, producer_kind="github_app", producer_app_id)` vereinigt. Identische Tupel aus mehreren Quellen dürfen dedupliziert werden, wobei jede Quelle erhalten bleibt. Derselbe `context_name` mit verschiedenen App-IDs, widersprüchliche überlappende Policies, legacy context-only requirements, leere Tupelmenge/keine Required Checks oder irgendeine unsupported Required-Workflow-Identität ergeben `CI_POLICY_UNSUPPORTED/BLOCKED`, nie `PASS`. Die unterstützte Teilmenge ist damit bewusst nur producergebundene Branch-Protection-`checks.app_id` und Ruleset-`required_status_checks.integration_id`.

### 12.2 Kanonische Policy-Evidenz

Der Policy-Snapshot enthält: kanonische Source-Kind-/ID-/API-Identität (bei Rulesets zusätzlich Source-Type/Source; bei Branch Protection die Protection-/Status-Checks-URL), exakten Base-Ref, frischen Base-Tip, Retrieval-Zeit, pro Response ETag wenn vorhanden und alle sortierten Tupel. Canonical JSON ist UTF-8 `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` über ausschließlich JSON-Strings, Integer, Bool, Arrays und Objekte; Source-Liste sortiert nach `(kind,id,api_identity)`, Tupel nach `(context_name,producer_kind,producer_app_id)`. Volatile Retrieval-Zeiten, ETags, Request-IDs und Transportheader werden im Evidence JSON auditiert, aber aus dem Digest-Preimage ausgeschlossen, damit ein inhaltlich identischer frischer Read denselben Digest erzeugt. `policy_digest = sha256(b"ci-policy/v1\n" + canonical_json_bytes).hexdigest()`. Canonical JSON, vollständiges Evidence JSON und Digest werden gemeinsam als append-only Snapshot mit Boundary `EVALUATION|READ_D|READ_E` persistiert; ein Digest ohne Preimage oder ein überschriebenes früheres Snapshot ist ungültig.

### 12.3 Check-Suite-/Check-Run-Beobachtung

Für den exakten Candidate-`head_sha` werden `GET /repos/{owner}/{repo}/commits/{head_sha}/check-suites?per_page=100` vollständig paginiert und anschließend jede zurückgegebene Suite ohne Vorfilter auf App oder Namen per `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}` frisch gelesen. Für jede Suite werden Runs über `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}/check-runs?per_page=100&filter=all` vollständig paginiert; nur so bleiben same-name Runs eines falschen Producers sichtbar. Der direkte Commit-Check-Runs-Endpunkt darf ergänzend genutzt werden, ersetzt wegen seines dokumentierten 1000-Suite-Limits und Default-`filter=latest` aber nicht diese Suite-Enumeration. Commit Statuses sind in v1.1.2 nie erfüllende Evidenz.

Für jedes Policy-Tupel muss genau ein Check Run existieren, der gleichzeitig erfüllt:

- `check_run.name == context_name` (exakte UTF-8-Stringgleichheit),
- `check_run.app.id == producer_app_id` als positiver Integer,
- `check_run.check_suite.id == check_suite.id`,
- frisch gelesenes `check_suite.head_sha == candidate head_sha` und zusätzlich `check_run.head_sha == candidate head_sha`,
- `check_run.status == "completed"`, `check_run.conclusion == "success"` und nichtleeres valides `completed_at`.

Es wird nicht „latest“ gewählt. Mehr als ein passender Run, derselbe Name von einer anderen App, geänderte/fehlende App-ID, fehlende/abweichende Suite-ID, fehlender Suite-Read, fehlender/falscher Head, malformed Provenance oder unbekannte Conclusion sind absichtlich nicht mehrdeutig auflösbar. Jeder gefundene gleichnamige Run wird als eigene append-only Beobachtung unter dem Boundary-Snapshot gespeichert, damit Spoof/Duplicate-Evidenz nicht verloren geht; ein fehlender Run erhält eine explizite MISSING-Beobachtung mit null Run-/Suite-Feldern. Pro Beobachtung werden Context, erwartete App-ID, Run-ID, Suite-ID, beobachtete App-ID/Name/Run-Head/Suite-Head/Status/Conclusion/`completed_at`/`details_url` sowie getrennte Run-/Suite-Retrieval-Zeiten und ETags persistiert. Canonical JSON verwendet dieselbe Serialisierung, schließt aber wie die Policy volatile Retrieval-/Transportmetadaten aus; `observation_digest = sha256(b"ci-observation/v1\n" + canonical_json_bytes).hexdigest()`.

### 12.4 Zustandsabbildung und Revalidation

- Exakt eine vollständige vertrauenswürdige Beobachtung mit `completed/success` für jedes Tupel und keine gleichnamige Spoof-/Duplikatbeobachtung ergibt `required_ci=PASS`.
- `queued|in_progress|waiting|requested|pending` ergibt `required_ci=PENDING`; es wird kein terminal positives Gate geschrieben.
- Kein Run für ein Tupel ergibt `required_ci=MISSING`; bei terminaler Resultbewertung mappt dies auf `engine_gate=FAILED`, nicht auf PASS.
- `completed` mit `failure|cancelled|timed_out|action_required|stale|neutral|skipped`, same-name wrong producer, Producer-Wechsel, Duplicate/Ambiguität, fehlende App-/Suite-/Head-Provenance oder falscher Head ergibt `required_ci=FAIL` und terminal `engine_gate=FAILED`. „Untrusted“ ist damit konsistent ein nachweislich negativer CI-Ausgang.
- Unlesbare/unvollständige Policy oder Beobachtung, fehlende API-Fähigkeit, unsupported Policyform oder nicht auflösbare Autoritätsambiguität ergibt `engine_gate=BLOCKED`; „unreadable/unsupported“ ist nie `FAILED`, weil kein verlässlicher negativer CI-Ausgang beobachtet wurde.

Read D und Read E wiederholen Policy- und Observation-Discovery vollständig. Jede Änderung an Base-Tip, Source-Menge/-Identität, Policy-Tupeln/Digest, Producer-ID, Run-/Suite-ID oder Observation-Digest setzt den Zyklus `STALE`; der aktuelle Read kann erst in einem neuen bzw. explizit neu bewerteten aktuellen Zyklus Gate-Evidenz liefern. Drift zwischen Read D und Read E darf nicht als `BLOCKED` oder `FAILED` das historische Gate überschreiben.

## 13. Remediation: exakt zwölf kumulative Bedingungen

Eine automatische Remediation ist nur geeignet, wenn alle folgenden zwölf Bedingungen einzeln `true` sind. Das Prädikat ist pure/deterministisch und persistiert für jede nummerierte Bedingung Bool plus Evidenz. Die früheren zehn Aggregate dürfen zusätzlich als deprecated Diagnose ausgegeben werden, sind aber weder vollständig noch autorisierend.

1. Die Änderung behebt ein konkret dokumentiertes Review-Finding mit eindeutiger Finding-ID, aktuellem Source-Review-Key und Source-Head.
2. Der bestehende PR-Scope wird nicht erweitert.
3. Es entsteht keine neue Produktanforderung.
4. Es ist keine neue Architekturentscheidung erforderlich.
5. Keine öffentliche API oder CLI wird wesentlich verändert.
6. Kein persistiertes Schema oder Engineering-IR wird wesentlich verändert.
7. Keine Sicherheits-, Trust- oder Berechtigungsgrenze wird verändert.
8. Es wird keine neue externe Integration eingeführt.
9. Das Ergebnis ist anhand bestehender Tests oder vollständig bestimmter Akzeptanzkriterien prüfbar.
10. Die Änderung kann ausschließlich auf der bestehenden PR-Head-Branch erfolgen; Base-/Default-/protected Write, Merge und History Rewrite bleiben verboten.
11. Branch und Head-Repository sind frisch als für Hermes beschreibbar und vertrauenswürdig bestätigt; unmittelbar vor Write gilt `current_head_sha == expected_head_sha == source_head_sha`, ein exklusiver Branch-Claim besteht und untrusted/privilegierte Fork-Ausführung ist ausgeschlossen.
12. Die Änderung ist lokal und technisch klar abgegrenzt; die konfigurierte Orchestrierung liefert einen vom autorisierenden Review getrennten Worker, und nach Commit sind Tests, Audit-Handoff, frischer Base-/Head-Read, neuer Review-Key, aktualisierter Request und unabhängiges Re-Review verpflichtend.

Scheitert eine Bedingung, wird keine Remediation-Task erzeugt. Das Gate bleibt/werden `CHANGES_REQUIRED` oder bei externer Unfähigkeit `BLOCKED`; der normale Entwicklungsprozess übernimmt.

## 14. TODO-/Audit-Vertrag, Branch-CAS und Re-Review

Jeder Remediation-TODO-Datensatz enthält die in `pr_review_todos` dargestellten Felder. Sein Kanban-Body spiegelt mindestens TODO-ID, Finding-ID, Source-Key/Head, Ziel, Scope, Komponenten, Acceptance, Tests, Branch, von der Orchestrierung gelieferten Worker, Workspace und expected Head. `idempotency_key` ist `pull_request_remediation:<source_review_key>:<finding_id>`.

### 14.1 Exactly-once-Materialisierung je Remediation-Quelle

Nach Nachweis aller zwölf Bedingungen materialisiert genau eine neue DB-Operation TODO und Task. Sie darf den bestehenden vor-transaktionalen `create_task()`-Fast-Path weder aufrufen noch als Idempotenzbeweis verwenden:

1. Kanonischer Source-Key ist das Tupel `(source_review_key, finding_id)`; daraus werden deterministisch `todo_id`, Idempotency-Key und `materialization_hash` der vollstaendigen immutable Spezifikation berechnet.
2. Eine einzige `BEGIN IMMEDIATE`-Board-Transaktion umfasst Claim/Insert, Task-Insert, Readback, `created_task_id` und Events. `INSERT ... ON CONFLICT DO NOTHING` fuer den durch `UNIQUE(source_review_key, finding_id)` geschuetzten TODO wird mit einem neuen unvorhersagbaren Attempt-Token als `claim_owner`, einer begrenzten `claim_expires` und Status `MATERIALIZING` ausgefuehrt, danach wird genau diese Zeile gelesen. Eine bestehende unvollstaendige Zeile darf nur nach abgelaufener Lease per CAS auf einen neuen Attempt-Token uebernommen werden; waehrend einer lebenden Lease liefert sie `OVERLAP_SKIPPED` ohne Write.
3. Bei bestehender Zeile muessen Source Head, Branch, Worker, Workspace, gesamter Spezifikationshash und Idempotency-Key exakt passen. Abweichung ist `REMEDIATION_CONFLICT`, nicht Update, Delete oder zweite Task.
4. Ist `created_task_id` gesetzt, muss genau dieser eine Task unabhaengig von seinem Lifecycle mit passendem Idempotency-Key, Body-Source-Key, Assignee, Projekt, Workspace und Hash existieren. Exakt dieser Task wird idempotent zurueckgegeben; null, mehr als einer oder ein Feldmismatch ist `INTERNAL_INVARIANT` und exponiert keine weitere Task.
5. Ist `created_task_id` NULL und gehoert die Zeile dem aktuellen Attempt-Token, fuehrt die Operation genau einen direkten Task-Insert ueber eine neue connection-scoped Primitive ohne eigene Lookup-/Commit-Grenze aus und liest den Task in derselben Transaktion anhand seiner neuen ID und des unique Remediation-Idempotency-Key zurueck. Erst nach vollstaendig erfolgreichem Readback werden `created_task_id` und TODO-Status `TASK_CREATED` per CAS auf denselben Attempt-Token gesetzt, die Claim-Felder geloescht und beide Events geschrieben.
6. Ein Insert-Konflikt auf Source-Key oder Remediation-Idempotency-Key wird innerhalb derselben Transaktion durch erneutes Lesen reconciled. Nur eine exakt passende, bereits gebundene Zeile darf Erfolg liefern; sonst Rollback/fail-closed. Es gibt keinen zweiten Insert, kein Suffix und kein Delete-and-recreate.
7. Crash vor Commit hinterlaesst weder TODO noch Task. Crash beziehungsweise verlorene Antwort nach Commit wird beim Restart ueber Source-Key gelesen und liefert dieselbe `created_task_id`. Die partielle Unique-Grenze und `BEGIN IMMEDIATE` beweisen auch bei zwei Connections/Prozessen, dass fuer diesen Source-Key insgesamt nie mehr als eine Task erzeugt oder sichtbar wird.

Erst eine spätere, getrennte CAS darf `TASK_CREATED -> CLAIMED` ausführen, nachdem Branch-Head und alle zwölf Bedingungen frisch bestätigt wurden. Materialisierung selbst startet keinen Worker.

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
- `BINDING_CHANGED|ADMISSION_FAILED`: keine Materialisierung; Cycle `STALE` oder weiterhin `PENDING_READ_C`, kein Task.
- `DB_BUSY`: bounded Retry; unbekannter Commit-Ausgang wird per Review-Key/Task-ID gelesen, nicht wiederholt.
- `LOCK_UNAVAILABLE`: Tick schreibt nichts; Alarm/Audit.
- `TASK_CREATE_FAILED`: Transaktion rollt Claim und Task zurück; retrybar nur nach Fehlerklassifikation.
- `CI_PENDING|CI_MISSING|CI_FAILED`: nie PASS; pending/missing wird später erneut gelesen, nachweislich negativer/spoofed/ambiguous Producer oder terminaler Nicht-Erfolg ist FAILED.
- `CI_POLICY_UNREADABLE|CI_POLICY_UNSUPPORTED|CI_OBSERVATION_UNREADABLE`: externe Fähigkeit, vollständige Pagination oder unterstützte Autorität fehlt; `BLOCKED` mit der konkreten Permission-/Policy-Migrationsaktion.
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

Daher werden DBs read-only geöffnet und Migrationsbedarf als `MIGRATION_REQUIRED` berichtet. Reportfelder: Repository/PR, Comment-ID-Konflikte, die acht kanonischen Key-Felder (Refs unverändert), escaped Preimage plus Preimage-SHA, berechneter Key, Binding/Projekt/Board/Orchestrierung, vorhandener Cycle/Task, geplante Transition/Writes, CI-Zustand, vollständige Policy-Quellen/Tupel/Digest und Check-Run-/Suite-Beobachtungen/Digests, alle zwölf Remediation-Bools, deprecated Aggregate nur als Diagnose, Skip-/Fehlerklasse und `writes_performed: 0`.

### 16.2 Strukturierte Logs

Events mindestens: `tick_start`, `tick_end`, `candidate`, `skip`, `binding`, `key_computed`, `comment_consistency`, `cycle_claim`, `task_created`, `label_reconcile`, `retry_scheduled`, `stale`, `pre_review_revalidate`, `pre_gate_revalidate`, `ci_gate`, `remediation_eligibility`, `remediation_cas`, `result_reconcile`, `error`.

Pflichtfelder: `event`, `correlation_id`, `repository`, `pr_number`, `review_key` (wenn berechenbar), `task_id` (wenn vorhanden), `error_class`, `retryable`, `dry_run`, `duration_ms`; CI-Events enthalten Source-Kind/ID/API-Identität, Base-Ref/Tip, Retrieval-Zeit/ETag, Policy-Digest, Context/Expected-App-ID, Run-/Suite-ID, beobachtete App/Name/Run-Head/Suite-Head/Status/Conclusion/Completed-at/Details-URL und Observation-Digest. Keine Tokens, Authorization-Header, Cookie, vollständige Prozessumgebung, Kommentar-/Task-Body-Rohtexte, Secrets, private Clone-URLs oder unredigierte subprocess stderr. GitHub Request-ID darf gespeichert werden.

## 17. Test- und Nachweismatrix

Alle Python-Tests laufen über `scripts/run_tests.sh`, nie direkt über `pytest`.

1. **Key-Golden Tests:** UTF-8, genau sieben LF, kein trailing LF, Repository/SHA lowercase, Refs case-preserving, Dezimal-PR; Base-Tip statt Merge-Base.
2. **Parser:** duplicate JSON keys, extra Marker, falsche Schema-Version, Unicode/control chars, SHA/ref/path limits, null/mehrere Kommentare, persistierte ID mismatch.
3. **Binding:** exakte Auflösung, archiviertes/fehlendes Projekt, fehlendes/mismatched Board, unbekanntes Profil, mehrere Claims; Beweis, dass current/default/last board und globale Orchestratorwerte nicht konsultiert werden.
4. **DB-Migration:** bestehende Boards/Projekte migrieren additiv und idempotent; alte Daten unverändert.
5. **Intake-Race und Admission:** zwei Prozesse/Connections für denselben Key; genau ein Cycle und nach erfolgreichem Read C höchstens ein Task. Ein kontrollierter Pause-Hook nach Cycle-Commit und vor/während Read C lässt native Dispatcher-Ticks laufen; weil keine Taskzeile existiert, entsteht kein Claim/Run/PID/Worker. Read-C-Mutation bleibt `STALE` ohne Task; nur erfolgreiche Binding-Revalidation plus Task-Insert/Readback setzt `MATERIALIZED`.
6. **Scheduler:** exakt 300 Sekunden, non-overlap, Lockfehler fail-closed, Stop/Restart, mehrere Gateways, kein LLM-/Worker-Aufruf.
7. **State-Machines:** jede erlaubte und verbotene Transition; `STALE` nie Gate; `done` nie PASS; alte PASS nach Drift ungültig.
8. **Revalidation/TOCTOU:** Base-Tip-, Head-, Label-, Comment-, Binding-, Policy-, Ruleset-, Producer-, Run- und Suite-Drift zwischen A/B/C, Read D und Read E. Zwei Connections aktualisieren Binding-/Projekt-/Boardwerte vor und während Admission/Materialisierung; frischer Authority-Read plus Fingerprint-CAS liefern Rollback oder `STALE` ohne Task, niemals Routing unter alter Projekt-/Board-/Orchestrierungsautorität. Policy-/Observation-Drift an jeder Revalidation-Grenze liefert `STALE`, nie Gate-Upgrade.
9. **CI-Policy und Provenance:** same-name spoofed producer; fehlende/geänderte App-ID; duplicate trusted match; legacy context-only requirement; gleichnamige konfliktäre Rulesets/Protection; Required Workflow; keine Required Checks; 401/403/ambiguous-404; partielle Pagination; malformed Source; fehlende Suite/Run-/Suite-Head-Daten; falscher Head; fehlender Run; queued/in-progress/pending; skipped/neutral/cancelled/timed_out/action_required/stale/failure; Commit-Status-only. Jeder Fall hat exakt die Zuordnung aus 12.4 und kann nie PASS werden. Nur alle producergebundenen Tupel mit genau einer vollständigen `completed/success`-Beobachtung am exakten Head können PASS ermöglichen; Canonical-JSON-/Digest-Golden-Tests sind erforderlich.
10. **Remediation-Tabelle:** genau zwölf autoritative Bedingungen, jede einzeln false; keine Task/Branchmutation; zehn deprecated Aggregate allein autorisieren nie. Alle zwölf true erlauben nur die transaktionale Materialisierung. Zwei Connections/Prozesse für denselben Source-Key, Spezifikationskonflikt sowie Crash vor Insert, nach Insert, vor Commit und Antwortverlust nach Commit beweisen exakt eine sichtbare Task und dieselbe `created_task_id`. Worker/Reviewer-Trennung.
11. **Branch-CAS:** parallele Worker, Lease-Verlust, protected/default branch, untrusted fork, non-fast-forward, restart; keine unerlaubte Mutation.
12. **Dry-Run:** Snapshot der DB-/GitHub-Fake-Zähler vor/nach; bitgleich null Writes und vollständiger deterministischer Report.
13. **E2E:** temp `HERMES_HOME`, reale `projects.db`/Board-DB, Fake-GitHub-Port, CLI→Poller→Task→revalidation→Result sowie Worker-Commit→neuer Key→neuer Request. Keine Mocks für DB-/Config-Auflösung.
14. **Regression:** mindestens die inventarisierten Kanban-, Review-, Dispatch-lock- und Gateway-Watcher-Tests; anschließend `npm run check` und sinnvoller voller `scripts/run_tests.sh`-Lauf.
15. **Live GitHub:** erst nach Contract-/Security-Freigabe in einem berechtigten Testrepo/Fork. Exakte PR-/Comment-/Label-/Base-/Head-/CI-IDs dokumentieren; fehlende Berechtigung wird `BLOCKED/NOT_RUN`, nie simuliertes PASS.

## 18. Betrieb, Aktivierung und Deaktivierung

Vor Aktivierung MUSS ein Operator:

1. Den Provenance-Gate aus Abschnitt 21 ausfuehren und das unabhaengige Contract-/Security-Review durch `agency-security-reviewer` als Review-Verdikt `PASS` nachweisen, gebunden an Vertragsversion v1.1.2, dieselben kanonischen Upstream-/Publikations-Repositories und exakt dieselben neun Manifestwerte für Commit, Ref, drei Pfad/Blob-Hash-Paare und frischen Upstream-`main`-Basis-SHA.
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
- Offizielle REST-Semantik und ein Live-Read am 2026-09-16 bestätigen für `GET /rules/branches/main` `ruleset_source_type`, `ruleset_source`, `ruleset_id` sowie `required_status_checks[].context/integration_id`; Check-Suite- und Check-Run-Reads bestätigen numerische `app.id`, Suite-ID, `head_sha`, Status, Conclusion, Completed-at und Details-URL. Das repository-gestützte `hermes_cli/kanban_pr_acceptance.py` besitzt bereits `_api()` mit `gh api`, Pagination und percent-encoded Rules-Branch sowie `collect_acceptance()` für GraphQL-Branch-Protection. Seine bestehende positive Semantik ist für diesen Vertrag ausdrücklich nicht wiederverwendbar: sie akzeptiert `app_id in (None,-1)`, Commit Statuses, `filter=latest`, liest keine Suite per ID/`head_sha` und verliert Duplicate-/Producer-Ambiguität. Die Implementierung darf den Transport extrahieren/erweitern, muss aber die schmalen v1.1.2-Ports und Tests separat erfüllen und darf weder dieses bestehende `ok` noch `gh pr checks`/`statusCheckRollup` als Provenance-Beweis behandeln. Klassische Branch Protection blieb mit dem aktuellen nicht-administrativen Actor 404/mehrdeutig und belegt gerade den vorgeschriebenen BLOCKED-Fall, nicht deren Abwesenheit.
- Der bestehende native Task-/Orchestrierungsweg muss das exakt gebundene `orchestration_profile` als Intake-Assignee für das konfigurierte Projekt beweisbar übernehmen. Fehlt dieser Weg, ist eine separate, geprüfte Orchestrierungsintegration nötig; der Poller darf keinen globalen/default Assignee, Reviewer oder Worker wählen.
- GitHub-Kommentarupdate bietet kein serverseitiges Body-CAS. Schema 1 kompensiert durch Read/BodHash/Update/Read und Branch-/Key-Revalidation; echte konkurrierende Kommentarautoren können weiterhin einen sichtbaren `STALE`/Konflikt erzwingen, aber keine Freigabe.
- Filelocks auf Netzwerkdateisystemen sind nicht universell zuverlässig. Korrektheit beruht deshalb zusätzlich auf SQLite-Transaktionen und Unique Constraints.

Änderungen an Key-Feldern, exakter Refidentität, Markerformat, öffentlicher Gate-Semantik, den zwölf Remediation-Bedingungen oder Routingautorität erfordern eine neue Schema-/Vertragsversion und erneutes unabhängiges Architektur-/Security-Review. Additive Logfelder und unbekannte optionale JSON-Felder dürfen kompatibel ergänzt werden, sofern sie keine Autorität tragen.

## 21. Verbindlicher Provenance- und Release-Gate

Unmittelbar vor jeder Implementierungsaufnahme oder -fortsetzung MUSS ein fail-closed, maschinenpruefbarer Gate-Lauf:

1. Aus dem Release-Manifest die kanonischen GitHub-Identitaeten fuer Upstream/Basis und Publikation lesen; fuer Schema 1 muessen sie exakt `NousResearch/hermes-agent` und `Mateo817/hermes-agent` sein. GitHub muss das Publikations-Repository frisch als Fork genau dieses Upstreams ausweisen. Lokale Remote-Namen werden nur als Transportkonfiguration protokolliert und niemals als Identitaetsbeweis verwendet.
2. `main` direkt vom genannten Upstream-Repository fetchen und den danach aufgeloesten vollen Commit als Live-Basis protokollieren; ein zuvor gespeicherter SHA oder nur ein lokaler Tracking-Ref genuegt nicht. Den finalen Nicht-Default-Ref separat direkt vom genannten Publikations-Repository fetchen.
3. Die im unabhängigen PASS genannten neun Werte exakt aus dem Release-Manifest lesen: finaler voller Release-Commit; Remote-Ref `refs/heads/contracts/github-pr-review-dispatcher-v1.1.2-from-2e6999f`; Pfad und finaler Blob-SHA-256 für `docs/kanban/github-pr-review-dispatcher-contract.md`; Pfad und finaler Blob-SHA-256 für `docs/kanban/github-hermes-development-workflow-SKILL-v5.1.md`; Pfad und finaler Blob-SHA-256 für `docs/kanban/github-pr-review-dispatcher-v1.1.2-decisions.md`; Basis-SHA. Abgekürzte SHAs, lokale-only Refs, implizite Branches oder ein Ref in einem anderen Repository sind verboten.
4. Per Remote-Readback gegen das namentlich gebundene Publikations-Repository beweisen, dass der genannte Nicht-Default-Ref exakt den genannten Commit aufloest, und beweisen, dass der Commit vom genannten Upstream-Basis-SHA abstammt. Wenn Upstream-`main` seit dem PASS fortgeschritten ist, muss die Basis auf der neuen Spitze sauber neu hergestellt, der Kandidat neu gebunden, erneut publiziert und unabhaengig erneut reviewed werden; ein alter PASS darf nicht uebertragen werden.
5. Alle drei Blobs am genannten Commit/Pfad lesen und ihre SHA-256 exakt vergleichen; ausserdem beweisen, dass der gesamte Diff von Basis bis Kandidat als geschlossene Menge genau die drei manifestierten Pfade enthaelt, dass der Contract die erwartete Vertragsversion v1.1.2 und der Skill Version `5.1.1` nennt. Der Exact-Changed-File-Scope ist eine aus Basis/Commit abgeleitete Invariante, kein weiterer Release-Manifest-Wert.
6. Mit `git merge-base --is-ancestor` beweisen, dass der verbotene Commit `aad0cbd55e9fef41cad79f7ca6f75b0e14a74ff6` kein Vorfahr des finalen Kandidaten ist. Merge, Cherry-pick oder sonstiger Import seiner Ancestry ist verboten. Die verworfene v1.0.0-Bindung bleibt ausschliesslich historische Evidenz und kann nie Release-Autoritaet sein.
7. Ein explizites, unabhaengiges Review-Verdikt `PASS` von `agency-security-reviewer` lesen, das dieselben zwei Repository-Identitaeten und genau dieselben neun finalen Bindungswerte nennt und keine offenen P0/P1/P2-Contract-Findings enthaelt. Taskstatus `done`, ein PASS zu einem anderen Blob/Artefaktset oder Schweigen sind kein PASS.
8. Bei jeder fehlenden Remote-Berechtigung, jedem Fork-/Fetch-/Readback-/Hash-/Ancestry-/Scope-/Reviewer-Mismatch und jedem nicht aufloesbaren Ref mit `DO_NOT_IMPLEMENT` abbrechen. Es gibt keinen lokalen, gecachten, manuellen, Remote-Alias- oder Default-Branch-Fallback.

Der Gate-Report enthaelt die zwei kanonischen Repository-Identitaeten, die neun finalen Bindungswerte, Fetch-Zeit, Remote-Readback, Fork- und Ancestry-Ergebnisse, Reviewer-Verdikt und `implementation_release_authorized: true|false`, aber keine Credentials. Nur ein vollstaendig positives Ergebnis darf die separate Implementierungs-Task manuell freigeben; dieser Architektur-Task startet sie niemals selbst.

Eine spätere Runtime-Installation des manifestierten Skills verwendet `hermes -p <exact-profile> skills inspect <immutable-url>` ausschließlich als URL-/Trust-Preview; `Trust: community` ist kein PASS und kein Security-Scan. Erst `skills install` ohne `--force` führt Quarantäne-/Security-Scanning aus. Scan- oder Quarantänefehler blockieren; nach Erfolg müssen die installierten Bytes aus dem exakt aufgelösten Profilpfad erneut gelesen und gegen Manifest-Hash und Version `5.1.1` geprüft werden. Diese Regel autorisiert in diesem Architektur-Task keine Installation.
