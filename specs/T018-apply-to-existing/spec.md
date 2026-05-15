# Spec: T018 — Apply dreamteam template to an existing project

**Статус:** Draft
**Дата создания:** 2026-05-15
**Связанные документы:**
- T009 (`dreamteam update`, full three-way merge): этот flow
  требует ранее-`dt init`-нутый проект (`.copier-answers.yml`
  должен присутствовать).
- T017 (`package_manager` prompt): conditional рендеринг shared с
  init/update — applies-to-existing должен соблюдать тот же
  contract.

---

## 1. Overview

Текущие команды:

| Команда | Состояние target |
|---|---|
| `dt init <path>` | пустой / новый каталог (или path не существует) |
| `dt update <path>` | путь, уже инициализированный через `dt init` (присутствует `.copier-answers.yml`) |

**Не покрытый usecase**: разработчик начал проект через другой
инструмент (PyCharm «new project», `poetry new`, `hatch new`,
`mkdir + git init` руками) — у него уже есть `pyproject.toml`,
`.venv/`, может быть `src/`, `tests/`. Теперь он хочет применить
методологию dreamteam **сверху** существующего scaffolding,
сохранив свой `pyproject.toml`/`.venv` (или дав возможность
выбрать per-file). Сейчас:

- `dt init` отказывается / прерывается на конфликтах.
- `dt update` сразу падает с `No .copier-answers.yml`.

T018 закрывает пробел: одна команда, которая принимает
«проект-без-методики», применяет шаблон поверх, разрешает
конфликты **интерактивно по мере возникновения** (или
through-prompts с разумными default-ами), и в конце записывает
`.copier-answers.yml` так, чтобы будущий `dt update` работал
штатно.

## 2. User Stories

- **Как разработчик, создавший новый проект `efactory` через
  PyCharm + uv**, я хочу одной командой применить методологию
  dreamteam поверх своего пустого скелета, чтобы получить
  `CLAUDE.md`/`README.md`/`BOARD.md`/etc. + методические правила
  — без необходимости удалять или объезжать PyCharm-овский
  `pyproject.toml`/`.venv`.
- **Как разработчик с уже-настроенным `pyproject.toml`** (свой
  список dependencies, custom ruff config), я хочу при коллизиях
  выбрать «оставить моё»/«взять из шаблона»/«показать diff»,
  чтобы не потерять кастом.
- **Как разработчик, применивший шаблон через apply-команду,**
  я хочу, чтобы `dt update` далее работал штатно — то есть
  команда оставляет за собой валидный `.copier-answers.yml`,
  как будто проект был сделан через `dt init` с самого начала.
- **Как maintainer dreamteam-cli**, я хочу минимум новой
  логики — переиспользовать существующий copier flow + per-file
  conflict prompts, не строить параллельный merge engine.

## 3. Functional Requirements

- **ДОЛЖНА**: новая команда (имя — см. Clarify Q1, кандидаты:
  `dt apply` / `dt adopt` / `dt init --existing` / auto-detect
  в `dt init`).
- **ДОЛЖНА**: для каждого template-managed файла:
  - **Файл отсутствует в target** → создать (silent).
  - **Файл есть, содержимое идентично rendered template** →
    no-op (silent).
  - **Файл есть, содержимое отличается** → conflict; user prompt
    (см. Q2 для UX вариантов).
- **ДОЛЖНА**: записать `.copier-answers.yml` в конце — full
  answers map (`_commit`, `_src_path`, `language`,
  `package_manager`, `project_name`, остальные prompts), чтобы
  будущий `dt update` запустился штатно (T009).
- **ДОЛЖНА**: НЕ трогать файлы вне template-managed множества
  (user code в `src/<foo>/`, любые non-template dirs,
  `.venv/`, `.git/`).
- **ДОЛЖНА**: соблюдать существующий contract `package_manager`
  prompt T017 — рендерить шаблон под выбранный manager.
- **МОЖЕТ**: предоставлять `--data key=value` через CLI для
  заглушения prompts (как `dt init`).
- **МОЖЕТ**: предоставлять `--dry-run` — preview конфликтов
  без записи.
- **МОЖЕТ**: автоматически детектить state и роутить —
  empty path → init, dreamteam path (`.copier-answers.yml`
  exists) → update, иначе → apply (см. Q1).
- **НЕ ДОЛЖНА**: молча overwrite-ить существующие файлы (без
  явного `--force-overwrite`-style флага).
- **НЕ ДОЛЖНА**: требовать `git init` в target заранее (apply
  применяется на голый каталог + чужой scaffolding, git
  может отсутствовать).

## 4. Success Criteria

- **Scenario A — пустой target**: `dt apply efactory` (где
  `efactory/` пуст) → identical to `dt init efactory`. `.copier-answers.yml`
  записан.
- **Scenario B — PyCharm scaffold** (`pyproject.toml` +
  `.venv/`): `dt apply efactory` → prompt «pyproject.toml conflict:
  [k]eep / [o]verwrite / [d]iff / [s]ave-as-`.dt-new`»; всё
  остальное (CLAUDE.md, README.md, BACKLOG.md, …) создаётся
  silent потому что в efactory их не было. `.venv/` не тронут.
- **Scenario C — dreamteam-проект** (`.copier-answers.yml`
  присутствует): `dt apply` сообщает «this is already a
  dreamteam project; use `dt update` instead» и exit-1. Или
  auto-redirect — см. Q5.
- **Scenario D — `--dry-run`**: список «would create N, would
  conflict K, untouched M», ничего не записано.
- 4 pre-push проверки на сгенерированном/applied проекте
  проходят (для всех 5 `package_manager` вариантов).
- Subsequent `dt update <applied-path>` работает (full
  three-way merge поверх T009 backend).

## 5. Key Entities

### CLI surface (Q1 candidates)

**Option A — `dt apply <path>`** — new dedicated command.
Pros: explicit; UX clear. Cons: third top-level verb для users
to remember (init / update / apply).

**Option B — `dt init <path> --existing`** — flag-extended init.
Pros: same command name; flag hints intent. Cons: flag obscure
unless user reads `--help`.

**Option C — Auto-detect в `dt init`**:
- target absent / empty → standard init.
- target has `.copier-answers.yml` → error «use update».
- target non-empty без `.copier-answers.yml` → apply mode.

Pros: zero new CLI surface, «just works». Cons: implicit
behavior; user не знает заранее, что произойдёт.

### Conflict resolution UX (Q2 candidates)

**Option A — Per-file 4-way prompt** (interactive only):
```
[?] pyproject.toml differs from template render.
    [k]eep existing  [o]verwrite from template
    [d]iff           [s]ave-as efactory/pyproject.toml.dt-new
    > _
```
Pros: full user control. Cons: requires terminal; `--data` style
non-interactive run сложнее.

**Option B — Copier's native conflict prompt** (`overwrite=False,
defaults=False`). Copier already делает prompt per existing file
с Y/N. Минимальная новая логика. Cons: less rich UX (только
keep/overwrite, без diff/save-as-new).

**Option C — `.dt-new` save-as-new** дефолт + warning at end:
«conflicts saved as foo.dt-new, manually merge». Non-interactive
friendly.

### `.copier-answers.yml` materialization

Final step — write `.copier-answers.yml` с full answers
(matches `dt init` behavior). Critical для T009 update flow.

### Files NOT touched (preserve-set)

- `.venv/`, `.git/`, `__pycache__/`, `.idea/`, `.vscode/`,
  `*.egg-info/`, `dist/`, `build/`.
- Any path matching template's `_exclude` (e.g. `.bundle/`).
- Any path NOT in the rendered template tree (user's `src/`
  packages, custom configs).

## 6. Assumptions & Constraints

- Python 3.14+ available (existing project constraint).
- target path exists и is a directory (apply не создаёт
  каталог; `dt init` это уже делает).
- copier 9.x's `run_copy` поддерживает per-file overwrite
  prompts через `overwrite=False, defaults=False`. Если нет —
  custom conflict resolution layer.
- T017 `package_manager` answer — required для рендера; если
  user не передал `--data package_manager=...`, prompt-им.

## 7. Out of Scope

- **Semantic merge** (e.g. интеллигентный merge `pyproject.toml`
  — TOML-level union of `[project.dependencies]` user-а и
  template-а). Это сложно и unnecessary в MVP. Conflict
  resolution — file-level only.
- **Detection дефолтного PyCharm scaffold** для skipping safe
  overwrites. Не пытаемся быть «умными» — все conflicts
  обрабатываются единообразно.
- **Auto-`git init`** на target если git missing. Apply не
  должен предполагать git workflow.
- **`dt unapply` / rollback** — не делаем.
- **CLI prompt UX через rich/textual** — обычный
  `typer.prompt` достаточно.

---

## Clarify (для Vladimir-а)

### Open questions

- **Q1 (CLI surface):**
  - (a) **`dt apply <path>`** — new top-level command. Голос
    автора.
  - (b) **`dt init <path> --existing`** — flag-extension.
  - (c) **Auto-detect в `dt init`** (empty → init, non-empty
    без answers → apply, with answers → error «use update»).
    Менее explicit, но «just works» UX.

- **Q2 (conflict resolution UX):**
  - (a) **Per-file 4-way interactive prompt** — keep / overwrite
    / diff / save-as-new.
  - (b) **Copier's native Y/N prompt** через `overwrite=False,
    defaults=False`. Минимальная новая логика.
  - (c) **Auto save-as `.dt-new` + warning at end** —
    non-interactive friendly.

- **Q3 (Scenario C — already dreamteam project):**
  - (a) **Error + suggest `dt update`** — minimum surprise.
    Голос автора.
  - (b) **Auto-redirect to `dt update`** — convenience.
  - (c) **Force re-init** — overwrite all answers (опасно).

- **Q4 (`--dry-run` support):**
  - (a) Да — выводить per-file decision plan (create / conflict
    / unchanged) без записи. Симметрично `dt update --dry-run`.
  - (b) Нет — MVP scope. Добавить отдельной задачей если нужно.

- **Q5 (`--data` для apply):**
  - (a) Да, как у init — `dt apply <path> --data key=value`.
    Голос автора.
  - (b) Нет — apply всегда interactive, prompts только для
    отсутствующих answers.

- **Q6 (`.copier-answers.yml` после apply):**
  - (a) **Always write** в конце — даже если у user уже был
    `.copier-answers.yml` (предположим стейл). Голос автора.
  - (b) **Skip если exists** — preserve user's state.

- **Q7 (`package_manager` detection):**
  - Если target имеет `pyproject.toml` с `[tool.poetry]` —
    auto-suggest `package_manager=poetry`? Или всегда prompt?
  - (a) **Всегда prompt** (default uv) — predictable.
  - (b) **Auto-detect и предложить default** — friendlier.
  - (c) **Прочитать существующий `pyproject.toml`, выставить
    `[tool.poetry]`/`[tool.hatch.*]`/etc. detection** —
    intelligent но complex.

- **Q8 (test matrix):**
  - 5 managers × empty / pycharm-scaffold / poetry-scaffold
    cases = 15+ test cases.
  - (a) **Full matrix** в integration suite.
  - (b) **Cut**: 1 manager × 3 source-states + 5 managers × empty
    = 8 cases. Голос автора.

- **Q9 (preserve user `pyproject.toml`?):**
  - Default conflict-handling для pyproject.toml — особый
    случай? Или просто rule «per-file prompt» works одинаково?
  - (a) **Универсальное правило**, no special-case. Голос
    автора.
  - (b) **Special-case `pyproject.toml`** — auto-merge user's
    `[project.dependencies]` + template's `[tool.ruff]` /
    `[tool.mypy]` / etc. Сложно, отложить (см. Out of Scope).

- **Q10 (version bump):**
  - Apply — backward-compatible additive feature. Version bump
    1.5.0 → 1.6.0 (MINOR)? Голос автора.

### Resolved (заполняется по мере ответов)

- ...

---

## Analyze (заполняется Claude после Clarify Resolved)

<!-- Issues с пометками 🔴 / 🟡 / 🟢. -->

- ...

---

## Implementation Plan (черновой)

**Phase 0** — этот PR: spec drafting + Clarify + Analyze.

**Phase 1** — implementation: new CLI command или extension
(Q1), conflict resolution flow (Q2), `.copier-answers.yml`
write, T017 `package_manager` integration. Unit tests + small
integration test (1-2 cases).

**Phase 2** — full integration matrix (Q8). 4 pre-push checks
green на applied проекте для каждого manager.

**Phase 3** — Docs / ADR / CHANGELOG / version bump
1.5.0 → 1.6.0 / README «Quick start: applying to an existing
project» / bundle re-tag.

Trade-off: при relatively-простом implementation (один new
command + conflict prompts) Phase 1+2+3 могут схлопнуться в
один combined PR (как T017), сэкономив CodeRabbit's rate limit.
Решение — после Analyze.
