# Spec: T036 — Размещение и жизненный цикл worktree (`dt worktree`)

**Статус:** Analyzed
**Дата создания:** 2026-07-30
**Связанные документы:**
- Дизайн-документ E1: `specs/roadmap-v0.3-v1.0/design.md` (раздел
  «Размещение worktree», таблица команд, критерии приёмки; карточка
  T004 = репозиторный T036).
- Фундамент: `specs/T033-store-core/spec.md` (резолв `$DT_HOME`,
  `worktrees_dir`, модель `Task` с полем `branch`).
- Предшественники: `specs/T034-task-ops/spec.md` (валидатор `_ID_RE`,
  `load_all_tasks`, `task_cli.py` как образец обёрток),
  `specs/T035-task-validation/spec.md` (git-free ядро + git-контекст
  добывается в `paths.py` и передаётся параметром).
- ADR этой задачи: `DECISIONS.md` (2026-07-30 — «T036: `dt worktree`,
  вычисляемый путь, prune с консервативным merged-guard»).

---

## 1. Overview

Четвёртая задача эпика E1 (карточка T004, `deps: T033`). Даёт агенту и
человеку **единый источник пути до рабочей копии задачи** и **безопасную
уборку** отработавших worktree. Проблема (design §E12): агент не знает пути
до worktree задачи и подставляет знакомую основную копию — правка «не
действует», полчаса на выяснение. Лечится тем, что путь можно **спросить**,
а не угадать.

- `dt worktree root` — каталог `$DT_HOME/worktrees` для этого репозитория.
- `dt worktree path <id|branch>` — путь конкретной рабочей копии:
  фактический (если worktree существует) либо вычисленный (куда создавать).
- `dt worktree list` — сопоставление существующих worktree с задачами;
  отдельно — «осиротевшие» (в managed-каталоге, без задачи).
- `dt worktree prune` — удаляет managed-worktree задач в `done`/`dropped`
  со слитой веткой и чистым деревом; **никогда** не трогает грязный или
  неслитый — пропускает с перечислением причин.

Разблокирует T039 (`task start`), T051 (`context`), T053 (`resume`).

**Явно НЕ в этой задаче** (каждое — своя задача): создание worktree и
генерация slug ветки (`dt task start`, T039); строка расхождения
`dt context` (T051); упоминание числа prunable в `dt resume` (T053);
`dt board` (T037). T036 не **создаёт** worktree — только сообщает путь и
убирает отработавшие.

## 2. Сценарии использования

- **«Где живёт задача».** Агент перед запуском приложения/правкой:
  `dt worktree path T034` → печатает каталог worktree T034 (фактический
  из `git worktree list`, если создан; иначе вычисленный). Больше не
  подставляется основная копия.
- **Куда создавать.** T039 при старте задачи спрашивает
  `dt worktree path <branch>` → вычисленный `$DT_HOME/worktrees/<branch>`
  как аргумент `git worktree add`.
- **Обзор параллельной работы.** `dt worktree list` — какие worktree каким
  задачам соответствуют и что осиротело после удаления записи.
- **Уборка.** После череды закрытых задач: `dt worktree prune` — сносит
  отработавшие рабочие копии и слитые ветки, оставляя незавершённое и
  неслитое нетронутым.

## 3. Functional Requirements

### `dt worktree root`

- ДОЛЖНА: печатать абсолютный `$DT_HOME/worktrees` (создаётся через
  `ensure_store`, если ещё нет). `--json` → `{"root": "<path>"}`.

### `dt worktree path <arg>`

- ДОЛЖНА: **auto-detect** аргумента. Точный `^T[0-9]{3,}$` (только ASCII-
  цифры после `T`) → **task ID**: загрузить запись, взять её поле `branch`;
  если `branch` не задан → ошибка со ссылкой на `dt task start`. Любой
  другой аргумент → **имя ветки** буквально.
- ДОЛЖНА: по разрешённой ветке `b` вернуть **фактический** путь, если в
  `git worktree list --porcelain` есть worktree на ветке `b`; иначе
  **вычисленный** `$DT_HOME/worktrees/<b>`.
- ДОЛЖНА: `--json` → `{"branch": "<b>", "path": "<p>", "exists": <bool>}`
  (`exists` — существует ли фактический worktree на этой ветке).
- НЕ ДОЛЖНА: создавать worktree или каталог `<b>` (это делает T039).

### `dt worktree list`

- ДОЛЖНА: перечислять все worktree из `git worktree list --porcelain`.
- ДОЛЖНА: сопоставлять worktree с задачей по её ветке — **сначала** по полю
  `branch` записи, **фолбэк** по префиксу `^T[0-9]{3,}` имени ветки, если
  такой ID есть в store.
- ДОЛЖНА: выделять **osиротевшие** — worktree **под managed-каталогом**
  `$DT_HOME/worktrees/`, не сопоставленные ни с одной задачей.
- ДОЛЖНА: не показывать как осиротевшие worktree вне managed-каталога, не
  сопоставленные с задачей (основная копия, ручные worktree на не-задачных
  ветках) — они не «мусор», а легитимные посторонние.
- МОЖЕТ: `--json` → `{"matched": [{"task","status","branch","path"}],
  "orphaned": [{"branch","path"}]}`.

### `dt worktree prune`

- ДОЛЖНА: рассматривать **только** worktree под managed-каталогом
  `$DT_HOME/worktrees/` (Q3: managed-only).
- ДОЛЖНА: удалять worktree только при выполнении **всех** условий:
  1. сопоставлен с задачей статуса `done` или `dropped`;
  2. ветка **слита** в base (`git merge-base --is-ancestor <branch> <base>`);
  3. дерево **чистое** (`git status --porcelain` пусто).
- ДОЛЖНА: при удалении сносить worktree (`git worktree remove`) **и** слитую
  локальную ветку (`git branch -d`, safe-delete) — Q2.
- ДОЛЖНА: **никогда** не удалять worktree с незакоммиченными изменениями или
  неслитой веткой; такой пропускать с **перечислением всех** применимых
  причин.
- ДОЛЖНА: осиротевший managed-worktree (без задачи) пропускать (причина «нет
  задачи») — статус «done/dropped» подтвердить нельзя, а гадать опасно.
- ДОЛЖНА: код возврата 0 (уборка — не проверка; пропуски не ошибки). Ошибка
  git при самом удалении → сообщение и exit 1.
- МОЖЕТ: `--json` → `{"removed": [{"task","branch","path"}],
  "skipped": [{"branch","path","reasons":[...]}]}`.

### Общее

- ДОЛЖНА: неинтерактивность; ошибки резолва store/git → stderr + exit 1 без
  traceback (образец `_run` из `task_cli`).
- ДОЛЖНА: ядро (`dt/worktrees.py`) — **typer-free И git-free**: git-данные
  (список worktree, merged, dirty, base) добываются в `paths.py` и подаются
  параметрами; планировщик prune — чистая функция над этими данными.

## 4. Success Criteria

- `dt worktree root` печатает `<repo>.dt/worktrees` из любого worktree
  репозитория (одинаково — worktree-независимость `$DT_HOME`).
- `dt worktree path T034` при созданном worktree печатает фактический путь;
  при отсутствующем — вычисленный `…/worktrees/<branch>`; при незаданном
  `branch` — ошибку exit 1.
- `dt worktree path <branch>` печатает путь без записи задачи.
- `dt worktree list` показывает пару «задача ↔ worktree» и отдельно
  осиротевшие managed-worktree; основная копия не помечается осиротевшей.
- `dt worktree prune` на задаче `done` со слитой веткой и чистым деревом —
  сносит worktree и ветку; на грязном / неслитом / не-done — пропускает с
  причинами; неслитую работу не теряет ни при каких условиях.
- 4 гейта зелёные; coverage ≥ 80% на новом коде.

## 5. Key Entities

- **WorktreeInfo** — разбор одной записи `git worktree list --porcelain`:
  `path: Path`, `branch: str | None` (короткое имя; `None` для detached),
  `head: str`, `bare: bool`, `detached: bool`.
- **Managed root** — `$DT_HOME/worktrees` (`paths.worktrees_dir`). Границей
  «managed / посторонний» служит `path.is_relative_to(managed_root)`.
- **Task.branch** — поле записи (модель T033); первичный ключ сопоставления
  worktree↔задача. Фолбэк — префикс `T<NNN>` имени ветки.
- **base branch** — куда проверяется слитость: `origin/HEAD` →
  `main`/`master` (автоопределение), см. Analyze A3.

## 6. Assumptions & Constraints

- Один worktree = одна ветка = одна задача (методика). Ветка каждого
  managed-worktree уникальна; коллизий имён не ждём.
- `$DT_HOME` вычисляется из git-common-dir (T033) — путь `worktrees/`
  одинаков из любого worktree.
- Слитость проверяется `--is-ancestor` (Analyze A2): корректно для merge- и
  rebase-workflow; **squash-merge** ею не детектируется и консервативно
  трактуется как «не слито» → prune пропускает (безопасный отказ, работу не
  теряем). Компенсируется ручной уборкой методики; squash-aware детекция —
  возможный follow-up (см. BACKLOG).
- `git` в PATH; вне git-репозитория без `DT_HOME` — внятная ошибка (T033).

## 7. Out of Scope

- Создание worktree и генерация slug ветки (`dt task start`, T039).
- `dt context` строка «сессия в основной копии, задача живёт в …» (T051).
- Упоминание prunable в `dt resume` (T053).
- Squash-aware детекция слитости (возможный отдельный T-ID).
- Любая правка чужих/ручных worktree вне managed-каталога.

---

## Clarify (заполнено — 3 развилки согласованы опросником 2026-07-30)

### Resolved

- **Аргумент `path`** → «Оба (auto-detect)»: точный `T<NNN>` = task ID
  (читаем `branch`-поле, ошибка если пусто), иначе literal branch. Держит
  генерацию slug в T039 и одновременно годится до его появления.
- **`prune` и локальная ветка** → «worktree + слитую ветку»: safe-delete
  `git branch -d` после сноса worktree (соответствует ритуалу уборки
  методики).
- **Scope `prune`** → «только managed-каталог»: `prune` трогает лишь
  worktree под `$DT_HOME/worktrees/`; ручной worktree задачи в другом месте
  не сносится (философия «ручной worktree продолжает работать»).

### Взято по умолчанию (озвучено, возражений нет)

- Сопоставление worktree↔задача: по полю `branch`, фолбэк — префикс
  `T<NNN>` имени ветки.
- base для «слито»: автоопределение `origin/HEAD` → `main`/`master`.
- `path`/`root`/`list` — read-only; мутирует только `prune`.

---

## Analyze (Claude)

- 🟢 **A1. Разделение слоёв.** Чистое ядро `dt/worktrees.py` (classify_arg,
  computed path, сопоставление, планировщик prune) — git-free; все git-
  вызовы (`worktree list --porcelain`, `merge-base --is-ancestor`,
  `status --porcelain`, `worktree remove`, `branch -d`, автодетект base) —
  в `paths.py` по образцу `git_context` (T035). Обёртки — новый
  `worktree_cli.py`, монтируется `add_typer` рядом с `task_app`.
- 🟡 **A2. Squash-merge и `--is-ancestor`.** В workflow методики merge —
  squash: коммиты ветки не становятся предками base, поэтому
  `--is-ancestor` вернёт false и `prune` пропустит такую ветку («не слито»).
  Это **безопасный** отказ (неслитую работу не теряем), но означает, что в
  самом dreamteam prune после squash-merge не уберёт worktree
  автоматически. Приемлемо: методика и так сносит ветку+worktree сразу
  после merge (ритуал уборки), а `prune` — предохранительная массовая
  чистка (в т.ч. `dropped` и merge/rebase-проектов). Точная squash-aware
  детекция (patch-id/дерево) вынесена в возможный follow-up, чтобы не
  раздувать scope.
- 🟢 **A3. Автодетект base.** `git symbolic-ref --quiet refs/remotes/origin/HEAD`
  → короткое имя (`origin/main` → `main`); при отсутствии — первая из
  существующих локальных `main`, `master`; иначе `main`. Слитость сверяется
  против **локальной** ветки base (не `origin/…`), чтобы работать офлайн.
- 🟢 **A4. `git branch -d` порядок.** Ветку, выгруженную в worktree, git
  удалить не даст; поэтому сперва `worktree remove`, затем `branch -d`.
  `-d` (не `-D`): git сам откажет, если ветка вдруг не слита в HEAD —
  второй слой защиты. Отказ `-d` → worktree уже снесён, сообщаем, exit
  без падения.
- 🟢 **A5. Осиротевшие и prune.** «Осиротевший» = managed-worktree без
  задачи. `list` их показывает; `prune` — пропускает (нельзя подтвердить
  done/dropped). Так осиротевший не удаляется автоматически, но виден для
  ручного решения.
- 🟢 **A6. detached / bare.** Detached-worktree (`branch is None`) не
  сопоставляется с задачей; под managed-каталогом попадёт в «осиротевшие».
  `prune` его пропустит (нет задачи). Bare — только в списке, не под
  managed-каталогом.
- 🟢 **A7. Path traversal.** `path <branch>` собирает `managed_root /
  branch`; имя ветки из-под пользователя. git не допустит ветку с `..`/
  абсолютным путём, но computed-путь всё равно нормализуем и проверяем
  `is_relative_to(managed_root)` перед печатью — как `_spec_present` (T035).
