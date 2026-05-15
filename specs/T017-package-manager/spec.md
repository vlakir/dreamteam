# Spec: T017 — Package-manager parametrization для derived projects

**Статус:** Draft
**Дата создания:** 2026-05-15
**Связанные документы:**
- `DECISIONS.md` → «`uv` как менеджер зависимостей и окружений»
  (current default, T002-era ADR в template-эпохе).
- T016 (PR #50) — `dt` alias, latest in-tree change.

---

## 1. Overview

Шаблон derived-проектов сейчас жёстко вшит на **`uv`**: команды
вроде `uv sync`, `uv run pytest`, `uv add --dev`, `uv build`
встречаются в каждом из 5 языковых вариантов
`src/dreamteam/template/i18n/<lang>/CLAUDE.md` (~11 occurrences
per file) и `README.md` (~7), плюс ссылки в `hooks/pre-push` и
комментариях `pyproject.toml`. Если пользователь работает на
`poetry` / `pip` / `pdm` / `hatch` / `pixi`, эти инструкции не
подходят, и Claude в derived-проекте получает противоречивые
сигналы: «uv» из шаблона vs реальный tooling в репо
(`poetry.lock`, `requirements.txt`, и т. п.).

T017 параметризует выбор менеджера через **новый `package_manager`
prompt в `copier.yml`** и заменяет hardcoded `uv` команды на
условный rendering из per-manager шаблонных fragments. Default
остаётся `uv` (existing derived projects не затронуты при
`dreamteam update`; new init без явного `--data` тоже получает
`uv`).

## 2. User Stories

- **Как новый user, работающий на poetry, я хочу** `dreamteam init`
  предложить мне выбрать `package_manager: poetry`, и получить
  derived project с инструкциями `poetry install` / `poetry run
  pytest` вместо uv-only, **чтобы** Claude в проекте говорил на
  языке моего tooling и не путал команды.
- **Как существующий uv-user, я хочу** `dreamteam init` по умолчанию
  выбрать `uv` (Enter → default), **чтобы** ничего не менять в моём
  привычном workflow.
- **Как user смешанного tooling (uv для venv, pip для install в
  prod)**, я хочу указать `package_manager: pip` для базовой совместимости
  + добавить uv-команды в проектные правила вручную, **чтобы** не
  навязывать команды коллегам, которым uv недоступен.
- **Как maintainer dreamteam-cli, я хочу** один источник правды
  per language (как сейчас с multilang) + условные fragments per
  manager, **чтобы** не множить 5 lang × N managers независимых
  файлов с риском drift-а.

## 3. Functional Requirements

- **ДОЛЖНА:** `copier.yml` содержать prompt `package_manager`
  типа `str` с `choices: [uv, poetry, pip]` (минимальный
  поддерживаемый набор для MVP — Q1) + display-имена в help-
  тексте, default `uv`.
- **ДОЛЖНА:** narrative-файлы (`CLAUDE.md`, `README.md`,
  `hooks/pre-push`, любые другие с командами) рендериться с
  правильными командами для выбранного менеджера через Jinja-
  conditional (`{% if package_manager == 'uv' %}` … `{% endif %}`)
  ИЛИ через single substitution variable (`{{ pm_run_pytest }}`)
  — выбор архитектуры в Q3.
- **ДОЛЖНА:** `pyproject.toml` рендериться с минимальным
  manager-specific блоком: для `uv` — pure PEP 621 (как сейчас);
  для `poetry` — добавить `[tool.poetry]` секцию + `poetry-core`
  build-backend; для `pip` — только `[project]` + `[build-system]
  hatchling` (Q4).
- **ДОЛЖНА:** `pre-push` chain команд адаптироваться к выбранному
  менеджеру: для uv — `uv run ruff check . && uv run ruff format
  --check . && uv run mypy . && uv run pytest`; для poetry —
  `poetry run ruff check . && poetry run ruff format --check . &&
  poetry run mypy . && poetry run pytest`; для pip — `ruff check
  . && ruff format --check . && mypy . && pytest` (assumed venv
  активирован).
- **ДОЛЖНА:** `dt update` / `dreamteam update` без явного
  `--data package_manager=` сохраняет ранее выбранный manager из
  `.copier-answers.yml` (стандартный copier behavior). При
  отсутствии answer (legacy v1.x projects) — fallback to `uv`
  (соблюдает backward compat).
- **ДОЛЖНА:** ru-source (`i18n/ru/`) — single source of truth с
  conditional Jinja-блоками; en/fr/de/zh — AI-regenerate как
  обычно через Claude Code session, обновлённый `source_hash` в
  каждом frontmatter. Manager-specific fragments переводятся раз и
  кэшируются как обычный narrative content.
- **ДОЛЖНА:** integration test для каждой комбинации
  `package_manager` × `language` (sanity matrix, не полная — см.
  Analyze про test matrix).
- **МОЖЕТ:** в будущем расширять `choices` до `pdm`, `hatch`,
  `pixi` (Q1 stretch — отвергнуто в MVP, но архитектура должна
  это позволять).
- **НЕ ДОЛЖНА:** автомиграция existing v1.x derived projects с
  hardcoded uv-commands в их CLAUDE.md/README.md (= manual user
  action; `dreamteam update --force` поверх с явным
  `--data package_manager=<choice>` ИЛИ оставить как есть).
- **НЕ ДОЛЖНА:** генерировать lock-files на стороне dreamteam-cli
  (`uv sync` / `poetry install` производят их при первом запуске
  user-ом). См. Q6.

## 4. Success Criteria

- `dreamteam init /tmp/foo --defaults` → `package_manager: uv` в
  `.copier-answers.yml`, derived контент идентичен текущему (no
  behavior change for the default user).
- `dreamteam init /tmp/foo --data package_manager=poetry` →
  `pyproject.toml` содержит `[tool.poetry]` секцию + `poetry-core`
  build-backend; `CLAUDE.md` использует `poetry run` команды;
  `dt init` → `cd derived && poetry install && poetry run pytest`
  проходит на freshly generated project (smoke).
- `dreamteam init /tmp/foo --data package_manager=pip` →
  `pyproject.toml` — pure PEP 621 + hatchling, без manager-
  specific секций; `CLAUDE.md` использует bare commands (без
  prefix); `python -m venv .venv && .venv/bin/pip install -e .[dev]
  && .venv/bin/pytest` smoke passes.
- 4 pre-push проверки (ruff / format / mypy / pytest) проходят
  на сгенерированном derived **для каждого** `package_manager` ×
  `language` combination в integration suite.
- `dreamteam update` сохраняет manager choice из answers; не
  навязывает миграцию.
- `translate_check.py` остаётся зелёным после param-edits ru-
  source (re-translated и `source_hash` обновлён).

## 5. Key Entities

### `copier.yml`: новый prompt

```yaml
package_manager:
  type: str
  help: "Package manager for the generated project (uv = fast, opinionated default; poetry = traditional, pyproject-only; pip = bare, no extra tooling)"
  choices:
    "uv (Astral)": uv
    "poetry": poetry
    "pip (vanilla)": pip
  default: "uv"
```

### Conditional rendering — два кандидата (Q3)

**Option A — Single-variable substitution.** Define в `copier.yml`
extra vars (или в `_macros`) typed на `package_manager`:

```jinja
{# in CLAUDE.md template #}
{% if package_manager == 'uv' %}{% set pm_run = 'uv run' %}{% set pm_install = 'uv sync' %}
{% elif package_manager == 'poetry' %}{% set pm_run = 'poetry run' %}{% set pm_install = 'poetry install' %}
{% else %}{% set pm_run = '' %}{% set pm_install = 'pip install -e .[dev]' %}{% endif %}

To run tests: `{{ pm_run }} pytest` (or just `pytest` если venv активирован).
```

**Option B — Inline conditional blocks per command.** Каждое
вхождение `uv run pytest` оборачивается в `{% if ... %}` ladder.
Verbose, но без macro overhead.

**Option C — Separate per-manager file fragments.** `template/
i18n/<lang>/pre-push.uv.sh`, `pre-push.poetry.sh`, `pre-push.pip.sh`
и `copier.yml _tasks` выбирает нужный + rename. Только для
полу-self-contained файлов; для CLAUDE.md/README c многими
inline-командами не подходит.

### `pyproject.toml` template — два кандидата (Q4)

**Option A — Single Jinja file** с conditional sections:

```toml
[project]
name = "{{ project_name }}"
...

{% if package_manager == 'poetry' %}
[tool.poetry]
package-mode = false  # for app, not library

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
{% else %}
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
{% endif %}
```

**Option B — Three files** (`pyproject.uv.toml`, `pyproject.poetry.toml`,
`pyproject.pip.toml`) + `_tasks` post-render rename. Cleaner
templates, но три копии в репо.

### Lock file generation — Q6

После `dreamteam init`, derived project не содержит lock file.
Стандартно — user сам выполняет `uv sync` / `poetry install` /
`pip install -e .[dev]`. Опционально (out of MVP):
post-render `_tasks` step выполняет lock command автоматически.
Минусы автогенерации: требует manager installed в user's PATH в
момент `dreamteam init`, замедляет init, может failure для
edge cases. Рекомендация: не делать в MVP, документировать в
README.

### Test matrix — Q10

Полная матрица: 3 managers × 5 languages = **15** integration
cases. На каждый — full `uv build` (или manager analog) + 4
pre-push checks. ~3-5 sec per case × 15 = ~60s. Acceptable. Plus
fast-suite tests на `_resolve_*` helpers и conditional render
output verify.

## 6. Assumptions & Constraints

- Python 3.14+ доступен пользователю (current requirement).
- User имеет выбранный package manager installed (`uv`, `poetry`,
  или `pip`); `dreamteam init` не verify presence (Q6 stretch).
- Conditional Jinja в `copier.yml`-rendered files works
  cross-platform.
- T013 multilang flow остаётся неизменным: ru-source + 4
  AI-translations. Manager-conditional fragments переводятся как
  обычный текст (английские команды типа `uv run` остаются
  английскими во всех языках — это identifiers).

## 7. Out of Scope

- **Поддержка `pdm`, `hatch`, `pixi`, `conda`** — отвергнуты в
  MVP T017. Архитектура (conditional Jinja или macro
  approach) должна позволять расширение в будущем без
  переписывания файлов.
- **Lock-file авто-генерация** при `dreamteam init` (Q6 out of
  scope).
- **Auto-migration of v1.x derived projects** к параметризованной
  template-эпохе.
- **`dreamteam init --to <manager>` для existing projects** — не
  делаем; это `dreamteam update --data package_manager=...` work,
  и derived user должен сам обновлять pyproject.toml.
- **Detection of installed managers на user machine** — копир не
  enforced.
- **CI sample workflows per manager** — `.github/workflows/ci.yml`
  в derived (если будет; сейчас нет) — отдельная следующая T-ID.

---

## Clarify (для Vladimir-а)

### Open questions

- **Q1 (supported managers в MVP):**
  - (a) **`uv` + `poetry` + `pip`** (минимально-разнообразный set:
    fast-modern + traditional + bare). Default uv. Голос автора.
  - (b) Только **`uv` + `poetry`** — pip is essentially «no
    manager» и может вызывать confusion (build-system Жётко
    нужен).
  - (c) Расширенный set (`uv`, `poetry`, `pdm`, `hatch`, `pip`).
    5 × 5 = 25 test cases — много в MVP.

- **Q2 (default):**
  - (a) **`uv`** — current behavior, no surprises for existing
    users.
  - (b) `pip` — most universal, lowest barrier для casual users.
    Но даёт slower workflow.

- **Q3 (conditional rendering architecture):**
  - (a) **Single-variable substitution через Jinja macros**
    (`{% set pm_run = ... %}` at template top) — DRY, scales к
    дополнительным managers.
  - (b) **Inline conditional blocks per command** (`{% if pm ==
    'uv' %}uv run pytest{% else %}…{% endif %}`) — verbose, но
    explicit.
  - (c) **Separate per-manager file fragments + post-render
    selection** — work для pyproject.toml, не для inline-heavy
    narrative.

- **Q4 (`pyproject.toml` template strategy):**
  - (a) **Single Jinja file с conditional sections** — DRY,
    matches Q3 (a).
  - (b) **Three separate files** (`pyproject.uv.toml`, etc.) +
    post-render rename. Cleaner per-file, but maintenance burden
    grows linearly.

- **Q5 (build-system per manager):**
  - **uv:** `hatchling` (current). Confirm.
  - **poetry:** `poetry-core` build-backend.
  - **pip:** `hatchling` (same as uv but без `[tool.uv]` секций).
    OR `setuptools`? Setuptools historically default, hatchling
    более modern. Я голосую hatchling everywhere.

- **Q6 (lock file generation в init):**
  - (a) **Не генерировать в MVP** — user сам делает после init.
    Документировать в README.
  - (b) **Опциональный flag** `--install` который запускает
    `uv sync` / `poetry install` / `pip install -e .[dev]` после
    render.
  - (c) **Always** — может ломаться на edge cases (manager not
    installed, network issues, etc.).

- **Q7 (legacy projects на uv hardcoded):**
  - (a) **Nothing** — they stay uv. `dreamteam update` без
    `--data package_manager=` сохраняет (отсутствие = legacy =
    uv).
  - (b) **One-shot migration command** `dreamteam migrate
    --to <manager>` — out of scope для T017?
  - (c) **Warning при `dreamteam update`** если answers без
    `package_manager` — suggest user runs with `--data
    package_manager=...`.

- **Q8 (translation overhead для manager-specific fragments):**
  - Manager-specific text (commands, build-system names) — это
    English identifiers, не переводятся. Surrounding prose
    переводится per language (5 lang). Поскольку commands
    остаются английскими — diff в text minimal.
  - Q: при изменении commands в одном manager (например, `uv run` →
    `uv x` в будущей версии) — re-translate всех 5 lang? Или
    только ru + propagate diff?
  - Голос автора: standard multilang flow (T013) — edit ru,
    AI-regenerate, hash check.

- **Q9 (backward compat при `dreamteam update`):**
  - Existing v1.x derived projects не имеют `package_manager` в
    answers. При `dreamteam update`:
    - (a) **Silent default to `uv`** (matches T013 multilang
      behavior для отсутствующего `language` answer).
    - (b) **Prompt user даже в non-interactive update** —
      нарушает cron-friendliness.
    - (c) **Require explicit `--data package_manager=...`** — UX
      burden для existing users.
  - Голос автора: (a) silent default uv — preserves existing
    derived projects.

- **Q10 (integration test scope):**
  - Полная матрица: 3 managers × 5 langs = 15. Time per case
    ~3-5s = ~60s total в integration suite.
  - Cut матрица: 3 managers × en (full coverage) + 1 manager (uv)
    × 4 other langs (sanity) = 7 cases.
  - Голос автора: **полная матрица** (60s acceptable в integration
    suite; защита от drift).

### Resolved (заполняется по мере ответов)

- ...

---

## Analyze (заполняется Claude после Clarify Resolved)

<!-- Issues с пометками 🔴 / 🟡 / 🟢. -->

- ...

---

## Implementation Plan (черновой)

**Phase 0** — этот PR (spec drafting, Clarify, Analyze).

**Phase 1** — `copier.yml` prompt + Jinja macros / conditional
substitution architecture (depending on Q3). Update **только
`i18n/ru/`** narrative files в Phase 1; re-render `i18n/{en,fr,de,
zh}/` later through standard multilang flow. Implement
`pyproject.toml` conditional sections (Q4 winner). Unit tests
для conditional render.

**Phase 2** — Multilang re-bootstrap: AI-regenerate
`i18n/{en,fr,de,zh}/` через Claude Code session с updated ru
content; refresh `source_hash` в frontmatters. Integration
matrix test (3 managers × 5 langs).

**Phase 3** — Docs / ADR / CHANGELOG / version bump 1.4.0 →
1.5.0 (MINOR — backward-compat через silent default `uv` for
missing answer).
