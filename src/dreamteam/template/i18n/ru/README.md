{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
# {{ project_name }}

{{ project_description }}

<!-- 1-3 предложения выше заполнились из ответов на `dreamteam init`.
     Расширь по необходимости. Архитектурные решения — в DECISIONS.md,
     история — в CHANGELOG.md. -->

## Быстрый старт

Менеджер зависимостей и окружения: **`{{ pm_name }}`** (выбран при
`dreamteam init`).

```bash
{{ pm_install }}                       # поставить зависимости
{{ pm_run }}python src/main.py     # запустить
```

## Зависимости
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
Hatch управляет зависимостями через `pyproject.toml`. Runtime —
добавить в `[project.dependencies]`. Dev — добавить в
`[tool.hatch.envs.default.dependencies]`. После правок:
`hatch env prune && hatch env create`.
{%- else %}
```bash
.venv/bin/pip install <pkg>   # затем впиши пакет в pyproject.toml [project.dependencies] сам
```
{%- endif %}

## Проверки перед push

```bash
{{ pm_run }}ruff check .
{{ pm_run }}ruff format --check .
{{ pm_run }}mypy <путь к коду>
```

Все три должны проходить с 0 ошибок. Обходные манёвры (`# noqa`,
`# type: ignore`, расширение `ignore`-секции) — только по согласованию.

## Структура проекта

- `src/` — корень исходников.
- `CONCEPT.md` — изначальное видение проекта (immutable).
- `DECISIONS.md` — архитектурные решения с обоснованиями (ADR-Lite).
- `BOARD.md` — рабочая Kanban-доска (To Do / Doing / Done).
- `BACKLOG.md` — парковка идей и побочных находок.
- `CHANGELOG.md` — журнал заметных изменений.
- `specs/` — спецификации крупных фич.
- `CLAUDE.md` — проектные правила для Claude (Claude Code).

## Методика работы

Проект создан из шаблона
[vlakir/dreamteam](https://github.com/vlakir/dreamteam). Подробное
описание методики (scope discipline, ритуал spec/clarify/analyze для
крупных фич, pre-push контроль) — см. репозиторий шаблона.

<!-- Ниже добавляются проект-специфичные разделы: API, развёртывание,
     схемы БД, документация модулей, контакты и т.п. -->
