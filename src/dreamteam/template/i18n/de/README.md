---
translated_from: i18n/ru/README.md
source_hash: f96c2ff264d28425416521155c98b10324520cd825e9ded1c0cbe5f3a8289568
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
# {{ project_name }}

{{ project_description }}

<!-- Die 1-3 Sätze oben wurden aus den Antworten von
     `dreamteam init` gefüllt. Bei Bedarf erweitern.
     Architekturentscheidungen — in DECISIONS.md, die Historie —
     in CHANGELOG.md. -->

## Quick Start

Dependency- und Environment-Manager: **`{{ pm_name }}`** (bei
`dreamteam init` gewählt).

```bash
{{ pm_install }}                       # Dependencies installieren
{{ pm_run }}python src/main.py     # ausführen
```

## Dependencies
{% if package_manager == 'uv' %}
```bash
uv add <pkg>                  # Runtime
uv add --dev <pkg>            # Dev
```
{%- elif package_manager == 'poetry' %}
```bash
poetry add <pkg>              # Runtime
poetry add --group dev <pkg>  # Dev
```
{%- elif package_manager == 'pdm' %}
```bash
pdm add <pkg>                 # Runtime
pdm add -dG dev <pkg>         # Dev
```
{%- elif package_manager == 'hatch' %}
Hatch verwaltet Dependencies über `pyproject.toml`. Runtime — in
`[project.dependencies]` einfügen. Dev — in
`[tool.hatch.envs.default.dependencies]` einfügen. Nach
Änderungen: `hatch env prune && hatch env create`.
{%- else %}
```bash
.venv/bin/pip install <pkg>   # dann das Paket selbst in pyproject.toml [project.dependencies] eintragen
```
{%- endif %}

## Prüfungen vor dem Push

```bash
{{ pm_run }}ruff check .
{{ pm_run }}ruff format --check .
{{ pm_run }}mypy <Pfad zum Code>
```

Alle drei müssen mit 0 Fehlern durchlaufen. Umgehungsmanöver
(`# noqa`, `# type: ignore`, Erweiterung der `ignore`-Sektion) —
nur nach vorheriger Absprache.

## Projektstruktur

- `src/` — Source-Wurzel.
- `CONCEPT.md` — ursprüngliche Projektvision (unveränderlich).
- `DECISIONS.md` — Architekturentscheidungen mit Begründungen
  (ADR-Lite).
- `BOARD.md` — Arbeits-Kanban-Board (To Do / Doing / Done).
- `BACKLOG.md` — Parking für Ideen und Seitenfunde.
- `CHANGELOG.md` — Journal nennenswerter Änderungen.
- `specs/` — Spezifikationen großer Features.
- `CLAUDE.md` — Projektregeln für Claude (Claude Code).

## Methodik

Das Projekt wurde aus der Vorlage
[vlakir/dreamteam](https://github.com/vlakir/dreamteam) erstellt.
Eine ausführliche Beschreibung der Methodik (scope discipline,
Ritual spec/clarify/analyze für große Features, Pre-Push-Kontrolle)
— siehe Vorlagen-Repository.

<!-- Unten werden projektspezifische Abschnitte ergänzt: API,
     Deployment, DB-Schemas, Moduldokumentation, Kontakte usw. -->
