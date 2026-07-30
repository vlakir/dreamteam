---
translated_from: i18n/ru/CLAUDE.md
source_hash: cc4fd8b518658944cdb1fc86c6b77cff6331a1a52d6e8ab6b90b82fe9c0ace43
translation_engine: claude-opus-4-8
translation_date: 2026-07-30
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
# Projektregeln für Claude

Diese Datei enthält die projektspezifischen Regeln für Claude
(Claude Code). Die globalen Regeln (`~/.claude/CLAUDE.md`) gelten
immer; hier — nur das, was für dieses Projekt spezifisch ist.

## Was zu Sitzungsbeginn zu lesen ist

1. `CONCEPT.md` (falls vorhanden) — die ursprüngliche Vision des
   Projekts, ein unveränderliches Dokument. Monate später als
   Ankerpunkt nützlich.
2. `README.md` — aktuelle Beschreibung / Quick Start / Projektstatus.
3. `DECISIONS.md` — bereits getroffene Architekturentscheidungen.
4. `BACKLOG.md` — was in der Warteschlange liegt.
5. Bei Arbeit an einem großen Feature — die zugehörige
   `specs/T<NNN>-*/spec.md`.

## Ritual zum Ausfüllen von `CONCEPT.md` (für ein neues Projekt)

Zu Beginn eines neuen Projekts hilft Claude dem Entwickler beim
Ausfüllen von `CONCEPT.md` — einem unveränderlichen Dokument der
ursprünglichen Vision. Dies ist ein Ritual von Gegenfragen,
analog zu `clarify` für die Spec eines großen Features:

1. Der Entwickler schreibt einen ersten Entwurf (oder formuliert
   einfach die Idee).
2. Claude stellt Gegenfragen zu blinden Flecken:
   - **Ziel:** welchen Schmerz / welche Aufgabe löst das Projekt?
   - **Nutzer:** wer, in welchem Kontext?
   - **Kernfunktionalität:** MVP-Minimum vs. nice-to-have?
   - **Out of scope:** was wir BEWUSST NICHT bauen
     (Hauptabschnitt — Schutz vor scope creep vom ersten Tag an).
   - **Einschränkungen und Annahmen:** Plattform, Stack, Last,
     Annahmen über Umgebung / Nutzer.
3. Die Antworten werden in `CONCEPT.md` eingenäht, das
   Erstellungsdatum wird vermerkt.
4. **Nach dem Ausfüllen wird `CONCEPT.md` nicht mehr bearbeitet.**
   Der aktuelle Stand wird in `README.md` geführt. Ändert sich das
   Konzept grundlegend (selten, Pivot) — wird eine neue Version
   angelegt: `concepts/v2-...md`, `v3-...md` (ADR-Pattern, aber
   für Konzepte).

**Die Struktur ist ein Fragebogen, kein Contract.** Die Abschnitte
oben (Ziel / Nutzer / Kernfunktionalität / Out of scope /
Einschränkungen) sind **leading questions für ein leeres
`CONCEPT.md`**, keine Pflichtform des finalen Dokuments. Hat das
Projekt bereits ein inhaltliches `CONCEPT.md` / Lastenheft / eine
Vision in irgendeiner Form — **akzeptiert Claude es, wie es ist**, und
führt `clarify` zu den blinden Flecken seines Inhalts durch, **ohne**
ein Umgießen in die Vorlagen-Überschriften **zu verlangen**. Das
einzige Pflichtelement des Rituals ist **clarify** (Gegenfragen). `Out
of scope` bleibt der wertvollste Abschnitt (Schutz vor scope creep),
kann aber in beliebiger Form innerhalb des bestehenden Dokuments
ausgedrückt werden. Die Unveränderlichkeits-Invariante (nach dem
Festschreiben nicht mehr bearbeitet) gilt in jedem Fall.

`CONCEPT.md` wird entweder bei der Projekterstellung über
`dreamteam init` (Claude stellt die Gegenfragen) oder später per
Hand ausgefüllt.

## Projektbeschreibung

{{ project_description }}

## Stack

**Basisstack der Vorlage (für Python-Projekte):**
- Python 3.14+ (`requires-python` in `pyproject.toml`).
- Dependency- und Environment-Manager: **`{{ pm_name }}`** (bei
  `dreamteam init` über das `package_manager`-Prompt gewählt;
  Alternativen: `uv` / `poetry` / `pdm` / `hatch` / `pip`).
- Linter: `ruff` (Regel `select = ["ALL"]` mit festgelegtem
  `ignore`).
- Type-Checker: `mypy` mit `mypy_path = "src"`.
- Test-Stack: `pytest` + `pytest-cov` + `pytest-asyncio`. Coverage-
  Schwelle ≥ 80 % Line-Coverage auf `src/`
  (`--cov-fail-under=80` in `[tool.pytest.ini_options]`).
- **Source-Wurzel — `src/`** (immer, in allen Projekten).
- Tests — in `tests/` im Wurzelverzeichnis (`ruff` schließt es
  aus, aber `pytest` findet sie über `testpaths = ["tests"]`).

**Typische Kommandos (für das gewählte `{{ pm_name }}`):**
{%- if package_manager == 'uv' %}
- `uv sync` — Dependencies installieren (legt `.venv` beim ersten
  Lauf an).
- `uv add <pkg>` / `uv add --dev <pkg>` — Runtime- / Dev-
  Dependency hinzufügen.
- `uv run python ...` — innerhalb von `.venv` ausführen, ohne es
  zu aktivieren.
- `uvx <tool>` — CLI-Tool ohne lokale Installation ausführen.
{%- elif package_manager == 'poetry' %}
- `poetry install` — Dependencies installieren (legt venv beim
  ersten Lauf an).
- `poetry add <pkg>` / `poetry add --group dev <pkg>` — Runtime- /
  Dev-Dependency hinzufügen.
- `poetry run python ...` — im poetry venv ausführen, ohne es zu
  aktivieren.
- `poetry env activate` — Sub-Shell mit aktivem venv öffnen.
{%- elif package_manager == 'pdm' %}
- `pdm install` — Dependencies installieren (legt `.venv` beim
  ersten Lauf an).
- `pdm add <pkg>` / `pdm add -dG dev <pkg>` — Runtime- / Dev-
  Dependency hinzufügen.
- `pdm run python ...` — im `.venv` ausführen, ohne es zu
  aktivieren.
{%- elif package_manager == 'hatch' %}
- `hatch env create` — Environment `default` mit Dev-Deps
  erzeugen.
- Dependencies werden in `[tool.hatch.envs.default.dependencies]`
  in `pyproject.toml` gepflegt.
- `hatch run <cmd>` — Befehl im `default`-Env ohne Aktivierung
  ausführen.
- Scripts werden in `[tool.hatch.envs.default.scripts]` definiert
  und über `hatch run <script>` aufgerufen.
{%- else %}
- `python -m venv .venv && .venv/bin/pip install -e .[dev]` —
  ein venv anlegen und Dev-Deps installieren.
- `.venv/bin/pip install <pkg>` — Paket installieren (dann selbst
  in `pyproject.toml` eintragen; pip aktualisiert das Manifest
  nicht automatisch).
- `.venv/bin/python ...` oder das venv aktivieren
  (`source .venv/bin/activate`) und `python ...` starten.
{%- endif %}

Vor jedem `git push` **vier** Prüfungen mit 0 Fehlern:
1. `{{ pm_run }}ruff check .`
2. `{{ pm_run }}ruff format --check .`
3. `{{ pm_run }}mypy <code>`
4. `{{ pm_run }}pytest` (inkl. Coverage-Schwelle ≥ 80 %).

**Als eine Kette ausführen**, damit ein Fail in irgendeinem
Schritt den Commit abbricht:

```bash
{{ pm_run }}ruff check . && \
{{ pm_run }}ruff format --check . && \
{{ pm_run }}mypy <code> && \
{{ pm_run }}pytest && \
git add -A && git commit -m "..." && git push
```

**Catch-it-at-the-output:** wenn du in der Ausgabe des vorherigen
Kommandos `FAILED`, `Error`, `1 failed` oder ähnliche Marker
siehst — **geh nicht weiter**, prüfe die Ursache. Und unterdrücke
nicht den Exit-Code: `pytest | tail -5` gibt den Exit-Code von
`tail` zurück, nicht von `pytest` — ein Fail rutscht still in den
`git commit`.

Keine `# noqa` / `# type: ignore` / Erweiterungen der
`ignore`-Sektion ohne explizite Absprache mit dem Entwickler.
Details — in der globalen `~/.claude/CLAUDE.md`, Abschnitte
„Linter" und „Testing".

## Git-Workflow

Basisregeln des Prozesses (gelten in diesem Projekt immer):

- **Aufgaben werden nummeriert.** Jeder Eintrag in `BOARD.md` /
  `BACKLOG.md` hat eine ID `T<NNN>`; der Branch ist
  `T<NNN>-<slug>`; der PR ist `T<NNN>: <title>`. Ausnahme — PRs
  zur Methodik, die die Regeln selbst ändern (ohne `T`-ID).
- **Direkter Push auf `main` / `master` ist verboten.** Jede
  Änderung — über einen Feature-Branch und eine PR/MR.
- **Eine PR — ein Commit.** Auf einem Feature-Branch kann man
  beliebig committen, wie es für die Arbeit bequem ist; vor dem
  Merge wird gesquashed.
- **Abschluss einer Aufgabe — in ihrer eigenen PR.** Das Verschieben
  des Eintrags von `BOARD.md → Doing` nach `Done` geschieht **im selben
  Squash-Commit** der Aufgaben-PR, nicht in einer separaten Chore-PR
  (nach dem Merge ist die Aufgabe ohnehin Done — `BOARD.md` spiegelt
  nur die Realität wider). PR-Grenzen folgen der logischen Kohärenz der
  Aufgabe; zusammenhängende Änderungen nur für eine „kürzere PR" zu
  zerteilen ist ein Anti-Pattern (zusätzlicher Review-Overhead, Verbrauch
  des Review-Bot-Kontingents).
- **Jede PR durchläuft ein Code-Review** vor dem Merge. Ist im Projekt
  ein funktionierender automatischer Review-Bot angebunden (CodeRabbit,
  qodo-code-review oder ähnlich, der jede PR reviewt) — ist er das
  Baseline, und **eine separate Self-Review durch Claude ist
  standardmäßig nicht erforderlich**. Claudes Self-Review ist in drei
  Fällen nötig: (1) **Docs / Methodik** — eine PR, die nur Markdown /
  Regeln / Specs ändert (Bots reviewen Prosa schlecht) → Self-Review
  bleibt der Default; (2) **nicht-trivialer Code** — eine gezielte
  Deep-Review der Risikozone (Architektur, Sicherheit, komplexer Scope),
  auf Wunsch des Entwicklers oder auf Claudes Initiative; (3)
  **Fallback** — der Bot ist nicht verfügbar (Rate-Limit, ausgefallen,
  kein Bericht in einem angemessenen Zeitfenster). Self-Review-Checkliste:
  Scope / Architektur / Code / Linter / Doku / Konventionen / Sicherheit.
- **Drittanbieter-Reviews nicht ignorieren.** Bots wie CodeRabbit /
  `qodo-code-review` lesen, analysieren, mit dem Entwickler
  besprechen; die Entscheidung wird festgehalten (annehmen /
  verwerfen / verschieben).

## Planungsdisziplin

Ohne Scrum-Zeremonien (Sprints, Story Points, Velocity, Burndown).
Wir behalten nur die nützlichen Elemente:

- **Milestone-basiertes Versioning.** `[Unreleased]` in
  `CHANGELOG.md` sammelt Änderungen. Der Sprung zu einer neuen
  Version `[N.M.0]` erfolgt, wenn **sinnvoll abgeschlossen**
  (weiches Kriterium): signifikante Änderungen eingeführt, ODER
  ein logisch zusammenhängender Aufgabenzyklus abgeschlossen, ODER
  „genug" für einen Speicherpunkt angesammelt. Der Entwickler
  entscheidet endgültig; eine formale Metrik gibt es nicht — das
  widerspräche dem Prinzip „kein Scrum-Cargo". Versionsformat —
  Keep a Changelog (`## [N.M.0]`, ohne `v`-Präfix).
- **Retrospective als Ritual** nach dem Schließen eines
  Milestones. Ein kurzes Debriefing in drei Punkten:
  - was funktioniert hat (work-as-expected oder eine angenehme
    Überraschung),
  - was nicht funktioniert hat (Bundling, Slips, unnötiger
    Overhead),
  - Anpassungen der Methodik (was in `~/.claude/CLAUDE.md` /
    Projekt-`CLAUDE.md` / der Vorlage zu ändern ist).
  Platzierung: **Abschnitt `### Retrospective`** innerhalb des
  zugehörigen Versionseintrags in `CHANGELOG.md`. Keine separate
  Datei — die Retro hängt eng mit dem Milestone zusammen und
  liest sich praktisch direkt daneben.
- **Akzeptanzkriterien** sind Pflicht für Aufgaben größer als ein
  einzeiliger Edit — direkt in `BOARD.md` / `BACKLOG.md` als
  kurzer Block vermerkt (`Acceptance: <was erreicht sein muss,
  damit die Aufgabe als abgeschlossen gilt>`) oder in
  `specs/T<NNN>-*/spec.md` für große Features. Ohne explizite
  Akzeptanzkriterien gilt die Aufgabe nicht als reif für den
  Übergang `BACKLOG → BOARD → Doing`.
- **WIP-Limit** in `BOARD.md → Doing`: maximal 1-2 Aufgaben. Mehr
  — und der Fokus geht verloren (klassische Kanban-Regel).

Hat der Entwickler ein globales `~/.claude/CLAUDE.md` konfiguriert
— dort liegt die erweiterte Fassung dieser Regeln (Abschnitte
„Niemals direkt auf main pushen", „Eine PR — ein Commit", „Code-
Review für jede PR"). Die Kurzfassung oben reicht als
eigenständige Quelle.

## Projektspezifische Regeln

## Was in diesem Projekt üblicherweise in BACKLOG.md geht, nicht in den aktuellen Edit


## Team-Rollen (Architekt + Designer)

Dieses Projekt bringt einen wiederverwendbaren Kollaborationskreis mit:
den Lead (diese Session), einen schreibgeschützten Architekt-Subagenten
und einen externen Designer (Claude Design). Wie man sie ruft, das
Beratungsritual und die Schleife „vorgeschlagen → Mensch entscheidet
→ ADR“ liegen in einer eigenen Datei:

@.claude/team-roles.md
