---
translated_from: i18n/ru/README.md
source_hash: 6cbcb2749f1ac3d91c54f37a9d58d667a6b46afb505129c142e310d7e61b76b1
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# {{ project_name }}

{{ project_description }}

<!-- The 1-3 sentences above were filled in from `dreamteam init`
     answers. Expand as needed. Architectural decisions go in
     DECISIONS.md, history in CHANGELOG.md. -->

## Quick start

```bash
uv sync                       # create .venv and install dependencies
uv run python src/main.py     # run
```

## Dependencies

```bash
uv add <pkg>                  # runtime
uv add --dev <pkg>            # dev
```

## Pre-push checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy <code path>
```

All three must pass with 0 errors. Workarounds (`# noqa`,
`# type: ignore`, extending the `ignore` section) — only by prior
agreement.

## Project structure

- `src/` — source root.
- `CONCEPT.md` — initial project vision (immutable).
- `DECISIONS.md` — architectural decisions with rationale (ADR-Lite).
- `BOARD.md` — working Kanban board (To Do / Doing / Done).
- `BACKLOG.md` — parking lot for ideas and side findings.
- `CHANGELOG.md` — log of notable changes.
- `specs/` — specifications of large features.
- `CLAUDE.md` — project rules for Claude (Claude Code).

## Methodology

The project was created from the
[vlakir/dreamteam](https://github.com/vlakir/dreamteam) template.
Detailed methodology (scope discipline, the spec/clarify/analyze
ritual for big features, pre-push gating) — see the template repo.

<!-- Project-specific sections follow: API, deployment, DB schemas,
     module docs, contacts, etc. -->
