# Spec: T018 — Apply dreamteam template to an existing project

**Статус:** Analyzed (Q1–Q10 resolved 2026-05-15)
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

## Clarify

### Resolved (2026-05-15)

- **Q1 (CLI surface) → (a) `dt apply <path>`** — new top-level
  command. Explicit, third verb рядом с init / update —
  acceptable burden для clarity.

- **Q2 (conflict resolution UX) → (a) per-file 4-way interactive
  prompt** — `[k]eep / [o]verwrite / [d]iff / [s]ave-as-`.dt-new``.
  Полный контроль для user, симметрично git merge UX.
  Non-interactive use case (через `--data`) разрешается отдельно
  через флаг `--on-conflict <keep|overwrite|save-as-new>` (Q2
  stretch, можно отложить).

- **Q3 (already dreamteam project) → (a) error + suggest
  `dt update`** — minimum surprise. Exit code 1 с понятным
  hint-сообщением.

- **Q4 (`--dry-run` support) → (a) да**, симметрично
  `dt update --dry-run`. Output: per-file decision plan
  (create / conflict / unchanged), ничего не пишется.

- **Q5 (`--data` для apply) → (a) да**, identical signature к
  `dt init` — `dt apply <path> --data key=value` (repeatable).
  Заглушает соответствующие prompts.

- **Q6 (`.copier-answers.yml` after apply) → (a) always write**
  в конце. Если у target был стейл answers — overwrite (predict-
  able state; subsequent `dt update` будет работать).

- **Q7 (`package_manager` detection) → (a) всегда prompt**
  (default `uv`). Predictable, no magic. Auto-detection из
  существующего `[tool.poetry]` / `[tool.hatch.*]` — stretch
  goal, можно добавить отдельной задачей если pattern окажется
  частым.

- **Q8 (test matrix) → (b) cut**: 1 manager (uv) × 3 source-
  states (empty / PyCharm scaffold / poetry scaffold) +
  5 managers × empty = 8 integration cases. Защита от drift
  основных путей при appropriate budget (~20s в integration
  suite).

- **Q9 (preserve user `pyproject.toml`) → (a) универсальное
  правило, no special-case**. `pyproject.toml` обрабатывается
  как любой другой template-managed файл через per-file
  conflict prompt. Semantic merge (TOML-level union) явно
  откладывается (см. Out of Scope).

- **Q10 (version bump) → 1.5.0 → 1.5.1 (PATCH)**. Vladimir's
  call (отступление от strict semver, который бы предписал
  MINOR для new command): T018 воспринимается как
  «доработка / закрытие usability gap», а не «принципиально
  новая фича на уровне T009/T017». PATCH bump signals
  incremental refinement.

---

## Analyze (2026-05-15)

### Issues

- 🟡 **Warning — interactive prompt UX в CI / non-TTY**.
  `[k]/[o]/[d]/[s]` prompt требует terminal с stdin. В CI или
  при piping stdin отсутствует → команда должна detect
  non-interactive context и fail loudly (или fall back на
  default «keep existing»). **Mitigation**: добавить flag
  `--on-conflict <keep|overwrite|save-as-new>` (mentioned
  под Q2) — full non-interactive mode. Auto-detect через
  `sys.stdin.isatty()`: если false и flag не указан → exit 1
  с сообщением «non-interactive run requires --on-conflict».

- 🟡 **Warning — diff output volume для multi-MB файлов**.
  Опция `[d]iff` теоретически показывает unified diff
  существующего vs rendered. Для большого `pyproject.toml`
  с длинными dependency lists или для будущих случаев multi-KB
  файлов — терминал затопит output. **Mitigation**: paging
  через `less` (если в TTY) или ограничение длины diff
  (truncate с hint «pipe to less for full»).

- 🟡 **Warning — copier поведение при non-empty target**.
  Copier's `run_copy` с `overwrite=False, defaults=False` уже
  делает per-file prompt при коллизии. Это работает «из
  коробки» — но prompt — Y/N (overwrite или нет), не 4-way.
  Для 4-way UX (Q2 (a)) надо либо: (i) свой conflict handler
  поверх copier; (ii) использовать copier's `--conflict
  rej` mode и потом обрабатывать `.rej` файлы; (iii) принять
  copier's 2-way и dropped «diff»/«save-as-new» к stretch
  goals MVP. **Decision in Phase 1 design**: попробовать (i)
  через `Worker` hook (если copier exposes file-level
  interception) или fallback к (iii) с обоснованием в ADR.

- 🟡 **Warning — `dt apply` не должен трогать `.git/`**.
  Copier'ed `_exclude` патчинг применяется к template, не к
  user's project. Если template содержит `.gitignore`-like
  file для `.git/`, мы должны убедиться copier не пытается
  записать поверх target's `.git/`. Тривиально решается
  exclude pattern в command-level (preserve-set из spec) и
  явной проверкой в pre-write hook.

- 🟢 **Note — naming consistency**.
  Команда `apply` рядом с `init` / `update` — естественное
  Английское трио. Альтернативы `adopt` / `attach` хуже
  читаются. Apply — winner.

- 🟢 **Note — `dt apply --dry-run` уже не должен спрашивать
  ничего interactive**. Dry-run = pure report. Если user
  заберёт `--dry-run` — это автоматически означает «не
  спрашивать».

- 🟢 **Note — PATCH bump 1.5.0 → 1.5.1 vs strict semver**.
  Новая CLI команда technically значит MINOR bump (new public
  API surface). Vladimir's call to call it PATCH — acceptable
  if framed как «refinement of init use case». Document
  rationale в ADR. Не блокер.

### Verdict

Все 10 Clarify questions resolved (Q10 — отступление от
strict semver, документировано). 0 🔴 critical блокеров, 4
🟡 warnings (все с mitigation в Phase 1 design), 3 🟢 notes
к памяти. Spec **moves to Analyzed**, готов к implementation.

---

## Implementation Plan

**Phase 0** — этот PR: spec drafting + Clarify + Analyze
(complete на merge).

**Phase 1+2+3 — combined PR** (T017 pattern для economy на
CodeRabbit rate limit):
- `cli.py`: new `apply` command. Internal flow:
  1. Validate target exists, не имеет `.copier-answers.yml`
     (если имеет — error «use `dt update`»).
  2. Detect TTY; если non-interactive и нет `--on-conflict` →
     exit 1.
  3. Build full answers через `--data` + interactive prompts
     для missing.
  4. Run copier `Worker.run_copy` с custom conflict handler
     (per-file 4-way prompt в TTY mode, `--on-conflict` value
     в non-interactive).
  5. Write `.copier-answers.yml` (full answers + `_commit =
     __version__` + `_src_path = <bundle>`).
  6. Print summary «N created, K conflicts resolved (kept/
     overwrote/saved-as-new), unchanged M».
- `--dry-run` flag: same flow, без writes; print decision
  plan.
- `--on-conflict <keep|overwrite|save-as-new>` flag.
- Tests:
  - 8 integration cases (Q8 cut matrix).
  - Unit: TTY detection, conflict handler decisions.
- `pyproject.toml`/`uv.lock`: version 1.5.0 → 1.5.1 (Q10
  PATCH per Vladimir's call).
- `CHANGELOG.md` `[Unreleased]` → Added.
- `DECISIONS.md`: ADR T018 — covers Q1-Q10 resolutions +
  rejected alternatives + 🟡 mitigation choices + PATCH
  vs MINOR rationale.
- `README.md`: new «Apply to existing project» section.
- `BOARD.md`: T018 → Doing → cleared on close.
- Bundle re-tag через `scripts/update_bundle.py`.
