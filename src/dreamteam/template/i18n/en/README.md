---
translated_from: i18n/ru/README.md
source_hash: 842f573b30c91a69865c2efc4561a61f4f41462b1ddffac2f729edf40afcd348
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
translation_updates:
  - date: 2026-10-16
    engine: openai/gpt-6.1-sol
    scope: OpenCode startup and recovery section; remove duplicated runtime name
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
# {{ project_name }}

{{ project_description }}

<!-- The 1-3 sentences above were filled in from `dreamteam init`
     answers. Expand as needed. Architectural decisions go in
     DECISIONS.md, history in CHANGELOG.md. -->

## Quick start

Dependency and environment manager: **`{{ pm_name }}`** (chosen at
`dreamteam init`).

```bash
{{ pm_install }}                       # install dependencies
{{ pm_run }}python src/main.py     # run
```

## Working with OpenCode

Use OpenCode 1.19.0; this project uses Ensemble 0.18.0. Providers, models and
credentials belong in personal configuration, not project roles.
Start one server: `dt serve .`; attach from another terminal with `dt run .`.
Additional clients attach to the same server. After an interruption, inspect
`dt recover .` on the server host first; resume only the preserved member,
lead-session and task. Reconcile an uncertain action's actual result before
retrying: a timeout does not prove it did not execute.

## Dependencies
{% if package_manager == 'uv' %}
```bash
uv add <pkg>                  # runtime
uv add --dev <pkg>            # dev
```
{%- elif package_manager == 'poetry' %}
```bash
poetry add <pkg>              # runtime
poetry add --group dev <pkg>  # dev
```
{%- elif package_manager == 'pdm' %}
```bash
pdm add <pkg>                 # runtime
pdm add -dG dev <pkg>         # dev
```
{%- elif package_manager == 'hatch' %}
Hatch manages dependencies via `pyproject.toml`. Runtime — add to
`[project.dependencies]`. Dev — add to
`[tool.hatch.envs.default.dependencies]`. After edits:
`hatch env prune && hatch env create`.
{%- else %}
```bash
.venv/bin/pip install <pkg>   # then add the package to pyproject.toml [project.dependencies] yourself
```
{%- endif %}

## Pre-push checks

```bash
{{ pm_run }}ruff check .
{{ pm_run }}ruff format --check .
{{ pm_run }}mypy <code path>
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
- `AGENTS.md` — project rules for OpenCode.

## Methodology

The project was created from the
[vlakir/dreamteam](https://github.com/vlakir/dreamteam) template.
Detailed methodology (scope discipline, the spec/clarify/analyze
ritual for big features, pre-push gating) — see the template repo.

<!-- Project-specific sections follow: API, deployment, DB schemas,
     module docs, contacts, etc. -->
