---
translated_from: i18n/ru/README.md
source_hash: 6cbcb2749f1ac3d91c54f37a9d58d667a6b46afb505129c142e310d7e61b76b1
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# {{ project_name }}

{{ project_description }}

<!-- Die 1-3 Sätze oben wurden aus den Antworten von
     `dreamteam init` gefüllt. Bei Bedarf erweitern.
     Architekturentscheidungen — in DECISIONS.md, die Historie —
     in CHANGELOG.md. -->

## Quick Start

```bash
uv sync                       # .venv anlegen und Dependencies installieren
uv run python src/main.py     # ausführen
```

## Dependencies

```bash
uv add <pkg>                  # Runtime
uv add --dev <pkg>            # Dev
```

## Prüfungen vor dem Push

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy <Pfad zum Code>
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
