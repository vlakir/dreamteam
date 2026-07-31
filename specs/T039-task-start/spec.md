# Spec: T039 — Композитный старт задачи (`dt task start`)

**Статус:** Analyzed
**Дата создания:** 2026-08-01
**Связанные документы:**
- Дизайн-документ E1: `specs/roadmap-v0.3-v1.0/design.md` (§166 таблица CLI,
  §858–864 карточка T007, §414/§419/§423 поверхности отображения и tmux,
  §326/§336 агент-сценарий; карточка T007 = репозиторный T039).
- Фундамент: `specs/T033-store-core/spec.md` (резолв `$DT_HOME`,
  `by_worktree_dir`, `worktree_slug`, модель `Task` с полем `branch`).
- Предшественники: `specs/T034-task-ops/spec.md` (валидатор `_ID_RE`,
  `load_existing`, `task_cli.py` как образец обёрток),
  `specs/T036-worktrees/spec.md` (`resolve_path`, containment computed-пути,
  git-факты добываются в `paths.py` и подаются параметром).
- ADR этой задачи: `DECISIONS.md` (2026-08-01 — «T039: `dt task start`,
  транслит-slug, привязка нового worktree, tmux внутри CLI»).

---

## 1. Overview

Седьмая задача эпика E1 (карточка T007, `deps: T034, T036`). Свёртывает
рутину начала работы над задачей в **одну команду**: `dt task start T0NN`.
Проблема (design §326/§336): переход «нашли задачу → работаем над ней»
сегодня требует вручную сменить статус, придумать имя ветки, создать
worktree в правильном месте, привязать к нему сессию и переименовать окно
tmux — пять шагов, каждый со своей ошибкой. `dt task start` выполняет их
атомарно, идемпотентно и без единого флага от человека.

Композиция поверх уже готовых кирпичей: статус — T034 (`move`), путь и
containment — T036 (`resolve_path`), запись — модель T033. T039 добавляет
генерацию имени ветки (транслит-slug), создание ветки+worktree и запись
привязки для statusline/`dt context` (T051 читает, не пишет).

- статус задачи → `doing`;
- ветка `T0NN-<slug>` (slug транслитерируется из заголовка) и worktree по
  вычисленному пути `$DT_HOME/worktrees/<branch>` — создаются, если их нет;
- поле `branch` записи заполняется;
- `by-worktree/<slug>/current-task` и `context.line` пишутся под slug
  **нового** worktree;
- при работе внутри tmux — `tmux rename-window` на ID задачи (иначе тихо
  пропускается);
- `--json` с путём к спеке и текстом секции `## Handover`.

## 2. Сценарии использования

- **Опознание → старт (§326).** Агент нашёл задачу через `dt task find`,
  назвал кандидата, человек подтвердил. Одна команда `dt task start T034`
  делает всё: статус, ветку, worktree, привязку, окно tmux; `--json` отдаёт
  агенту путь к спеке и Handover, чтобы сразу сориентироваться.
- **Разведка стала задачей (§336).** Из непривязанного обсуждения
  выкристаллизовалась работа: `dt task new …`, затем `dt task start` —
  создаётся новая ветка и worktree, история обсуждения остаётся в текущей
  сессии, а работа поедет в новом worktree (его привязка уже наполнена).
- **Повторный старт (идемпотентность).** Ветка/worktree уже существуют
  (перезапуск, ручное создание) — `start` не падает и не дублирует:
  переиспользует фактический путь, лишь обновляет статус и привязку.
- **Statusline сразу.** После `start` statusline нового worktree читает
  `context.line` и показывает «задача · статус · ветка» без ожидания
  SessionStart-хука.

## 3. Functional Requirements

### `dt task start <id>`

- ДОЛЖНА: принимать точный task ID `^T[0-9]{3,}$`; несуществующая задача →
  ошибка exit 1 (как `dt task show`).
- ДОЛЖНА: **имя ветки** = поле `branch` записи, если оно уже задано; иначе
  сгенерировать `T0NN-<slug>`, где `<slug>` — транслитерация заголовка
  (ru→lat), lowercase, не-`[a-z0-9]` → одиночный `-`, обрезка по словам до
  разумной длины; пустой slug (заголовок без переводимых символов) →
  ветка = `T0NN` без суффикса.
- ДОЛЖНА: определить фактический/вычисленный путь worktree по ветке через
  `resolve_path` (T036) — фактический из `git worktree list`, иначе
  вычисленный `$DT_HOME/worktrees/<branch>` (с containment-проверкой A7).
- ДОЛЖНА: если worktree на ветке **не существует** — создать его:
  - ветки ещё нет локально → `git worktree add -b <branch> <path> <base>`,
    где `<base>` — локальная default-ветка (`origin/HEAD`→`main`, иначе
    `main`/`master`), **без** сетевого `fetch`;
  - ветка уже есть → `git worktree add <path> <branch>` (без `-b`).
- ДОЛЖНА: если worktree уже существует — переиспользовать его путь, ничего
  не создавая (идемпотентность).
- ДОЛЖНА: перевести статус в `doing`, записать `branch` в запись, обновить
  `updated`; сохранить запись один раз.
- ДОЛЖНА: записать привязку под slug **нового** worktree
  (`worktree_slug(path)`): `by-worktree/<slug>/current-task` = ID задачи,
  `by-worktree/<slug>/context.line` = строка `«<id> [<status>] <title>»`.
- ДОЛЖНА: при наличии `$TMUX` в окружении выполнить
  `tmux rename-window -t "$TMUX_PANE" <id>` (best-effort, ошибка/отсутствие
  tmux/отсутствие `$TMUX` → тихий пропуск, **не** ошибка).
- ДОЛЖНА: `--json` → объект `{id, status, branch, worktree, worktree_created,
  branch_created, spec, handover, tmux_renamed}`; человекочитаемый режим —
  краткая сводка.
- НЕ ДОЛЖНА: делать сетевые вызовы (`fetch`/`push`), переключать ветку в
  текущем worktree, трогать чужие/ручные worktree, парсить транскрипты.

### Общее

- ДОЛЖНА: неинтерактивность; `TaskError`/`DtHomeError`/`OSError` → stderr +
  exit 1 без traceback (образец `_run` из `task_cli`).
- ДОЛЖНА: чистые части (slug, планировщик, форматирование context.line,
  извлечение Handover) — **typer-free И git-free**, git/fs-эффекты в
  `paths.py`/обёртке; повторяет расслоение T035/T036.

## 4. Success Criteria

- `dt task start T0NN` на `todo`-задаче без ветки: создаёт ветку
  `T0NN-<translit-slug>` и worktree в `…/worktrees/<branch>`, статус →
  `doing`, поле `branch` заполнено, привязка нового worktree наполнена.
- Повторный `dt task start T0NN`: не падает, не создаёт второй worktree,
  переиспользует путь, обновляет статус/привязку.
- `dt task start` с уже существующей веткой (без worktree): создаёт worktree
  из существующей ветки (без `-b`), не теряя её историю.
- Вне tmux `tmux_renamed=false`, команда успешна; внутри tmux окно
  переименовано в ID.
- `--json` содержит путь к спеке (поле `spec` записи) и текст `## Handover`
  (пустой, если секции нет).
- Заголовок из кириллицы даёт ASCII-ветку (пример:
  «Композитный старт задачи» → `T039-kompozitnyi-start-zadachi`).
- 4 гейта зелёные; coverage ≥ 80% на новом коде.

## 5. Key Entities

- **branch slug** — транслитерация заголовка задачи ru→lat + нормализация;
  детерминирована, ASCII-only. Живёт в `dt/slug.py`.
- **StartPlan** — результат чистого планировщика: `branch`, `path`,
  `create_worktree: bool`, `create_branch: bool`. Решает decision-table
  «есть ли worktree / есть ли ветка» → какой git-вызов нужен.
- **binding** — пара файлов `by-worktree/<slug>/current-task` (ID задачи) и
  `context.line` (строка для statusline). `<slug>` = 8 hex sha1 от
  абсолютного пути worktree (T033 `worktree_slug`).
- **Task.branch / Task.spec / `## Handover`** — поля/секция записи (модель
  T033): `branch` заполняется здесь, `spec` и Handover только читаются в
  `--json`.
- **base branch** — локальная default-ветка для `-b` (`default_base_branch`,
  T036); сетевой fetch не делается.

## 6. Assumptions & Constraints

- Один worktree = одна ветка = одна задача (методика). Имя ветки уникально
  по построению (префикс `T0NN`).
- `$DT_HOME`/`worktree_slug` вычисляются из git-common-dir (T033) —
  одинаковы из любого worktree.
- `git worktree add` работает из любой рабочей копии репозитория; cwd
  команды — текущая (обычно основная копия, откуда агент вызывает `dt`).
- «От свежего main» обеспечивается **дисциплиной**, а не командой: T039
  ответвляет от **локальной** base без fetch (офлайн, быстро);
  актуализацию base перед PR делает агент отдельно (`git fetch && rebase`).
- tmux — единственный внешний по отношению к репозиторию эффект; выполняется
  **внутри** CLI как subprocess dreamteam (отдельного allow-листа Claude не
  требует; allow-лист `tmux rename-window` в settings.json — задача E3.1).
- `git` в PATH; вне git-репозитория без `DT_HOME` — внятная ошибка (T033).

## 7. Out of Scope

- `dt context`, SessionStart-хук, реестр сессий (`sessions/<id>.json`) —
  T051/T052; T039 только **пишет** `context.line`, потребляют другие.
- Statusline-скрипт, читающий `context.line` — T054.
- `dt resume` и `--tmux`-раскладка — T053.
- Allow-лист `tmux rename-window` в `.claude/settings.json` — E3.1 (v0.4).
- Автоматический `git fetch`/актуализация base, `push`, создание PR.
- Режим «без worktree, ветка в текущей копии» (`--no-worktree`) — возможный
  follow-up (см. BACKLOG), если понадобится in-place-стиль.
- Поддержка отличных от ru/en алфавитов в транслитерации.

---

## Clarify (заполнено — 4 развилки согласованы опросником 2026-08-01)

### Resolved

- **Генерация slug** → «Транслит ru→lat»: `«Композитный старт задачи»` →
  `T039-kompozitnyi-start-zadachi`. Читаемая ASCII-ветка, без сюрпризов в
  git/tmux/CI. Отвергнуты «unicode как есть» (кривые ветки/окна/URL) и «без
  slug» (теряется человекочитаемость).
- **Привязка (slug какого worktree)** → «Нового worktree»: `current-task`/
  `context.line` пишутся под slug создаваемого worktree — там пойдёт работа,
  statusline/`dt context` сразу наполнены; вызывающая (основная) копия не
  привязывается. Резолв задачи в новом worktree и так идёт по ветке `T0NN`.
- **tmux** → «Внутри CLI, тихо»: `dt task start` сам зовёт
  `tmux rename-window -t "$TMUX_PANE" <id>` при заданном `$TMUX`, вне tmux —
  молча пропускает. Subprocess внутри dreamteam, отдельного подтверждения
  Claude не требует; соответствует §863.
- **База ветки** → «Локальный main/master, без fetch»:
  `git worktree add -b <branch> <path> <base>`, `<base>` = локальная
  default-ветка; сетевого fetch нет. Свежесть main — дисциплина методики.

---

## Analyze (Claude)

- 🟢 **A1. Расслоение.** Чистое ядро: `dt/slug.py` (транслит, `slugify`,
  `branch_name`), `dt/starts.py` (`StartPlan`, `plan_start`, `context_line`,
  `extract_handover`, запись привязки). Git-вызовы (`local_branch_exists`,
  `add_worktree`) — в `paths.py` рядом с `list_worktrees`/`default_base_branch`
  (T036). tmux — отдельный узкий модуль `dt/tmux.py` (best-effort, никогда не
  бросает). Мутация записи (`start_task`) — в `tasks.py`. Обёртка — команда
  `start` в существующем `task_cli.py`.
- 🟢 **A2. Decision-table planner.** `plan_start(branch, path,
  worktree_exists, branch_exists)`: `create_worktree = not worktree_exists`;
  `create_branch = create_worktree and not branch_exists`. Чистая функция,
  покрывает все 4 комбинации (worktree есть/нет × ветка есть/нет) без git.
- 🟢 **A3. Идемпотентность.** `resolve_path` возвращает `(path, exists)`:
  `exists=True` → worktree переиспользуется, git не трогаем. `branch` берётся
  из записи, если уже задано — повторный start не генерирует новое имя.
  Статус/привязка обновляются всегда (дёшево, восстанавливает согласованность).
- 🟡 **A4. Транслитерация — приближение, не стандарт.** Простая таблица
  ru→lat (щ→shch, ж→zh, ё→e, ъ/ь→'') без строгого ГОСТ/BGN. Достаточно для
  человекочитаемого имени ветки; коллизии slug безвредны — уникальность даёт
  префикс `T0NN`. Пустой slug (заголовок из одних символов вне таблицы) →
  ветка `T0NN`. Длина slug ограничена (обрезка по словам ~40 симв.), чтобы
  имя ветки/каталога не разрасталось.
- 🟢 **A5. base для `-b` без fetch.** `default_base_branch()` (T036) даёт
  локальное имя (`origin/HEAD`→`main`, иначе локальные `main`/`master`,
  иначе `main`). `git worktree add -b … <base>` от локального ref — офлайн.
  Если локального `main` нет (голый/новый репо) — git вернёт ошибку, она
  всплывёт как `DtHomeError` (exit 1) с внятным текстом; краевой случай.
- 🟢 **A6. Порядок эффектов.** Сначала git (`worktree add`) — самый склонный
  к отказу шаг; при его провале запись/привязка не трогаются (нет
  полу-применённого состояния). Затем `start_task` (запись), затем привязка,
  затем tmux (best-effort). tmux последним и без влияния на exit-код.
- 🟢 **A7. Path traversal.** Имя ветки может быть literal (из поля `branch`).
  Вычисленный путь проходит `resolve_path` с `is_relative_to(managed_root)`
  (T036 A7) — ветка с `..`/абсолютным путём отклоняется до любого git-вызова.
- 🟢 **A8. current-task vs ветка.** В новом worktree резолв задачи и так
  сработает по имени ветки (`T0NN`), поэтому `current-task` там —
  подстраховка; но `context.line` под тем же slug нужен statusline (T054)
  сразу, поэтому пишем оба под slug нового worktree единым действием.
- 🟢 **A9. Статус done/dropped.** `start` переводит в `doing` из любого
  статуса (переоткрытие задачи — легитимно); отдельного гейта нет. Если это
  окажется нежелательно — тонкий guard добавим follow-up-задачей.
