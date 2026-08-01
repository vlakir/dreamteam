# Changelog (dreamteam package)

Журнал эволюции `dreamteam`-пакета (scaffolding CLI на Copier).
В derived projects (создаваемых через `dreamteam init`) — свой
собственный `CHANGELOG.md` для их истории; они не пересекаются.

Формат — упрощённый
[Keep a Changelog](https://keepachangelog.com/) с группировкой по
версиям и категориям (Added / Changed / Fixed / Removed) + секция
`### Retrospective` при закрытии milestone.

> **Note про префиксы:** до v1.0.0 этот файл назывался
> `TEMPLATE-CHANGELOG.md` (как и `TEMPLATE-BACKLOG/BOARD/DECISIONS`).
> Префикс `TEMPLATE-` был введён в T005 для разделения мета-документов
> шаблона от заготовок для derived. После T006 заготовки уехали в
> `src/dreamteam/template/` как package data, коллизия исчезла,
> префикс убран — см. соответствующий ADR в `DECISIONS.md`.
> Исторические упоминания `TEMPLATE-*.md` в записях ниже **не
> правлены** — это immutable history.

---

## [Unreleased]

<!-- Накопление следующего цикла. -->

### Added

- **T041 — перенос состояния между машинами** (`dt state export/import`, точка
  входа E1, `deps: T034`). Оперативный слой не ездит с git (§233) — явный
  ручной канал переноса **только записей задач и счётчика** (§209):
  - `dt/state.py` (pure, git-free): `export_bundle` (читает только `tasks/` +
    `counter`, `sessions/`/`by-worktree/` исключены по построению);
    `serialize`/`parse` — JSON `{dt_state_version, counter, tasks:[...]}` с
    round-trip записи (unknown-поля + тело), версия проверяется (новее →
    отказ); `import_bundle` — pre-check ID (валидация + дубли) и конфликтов
    **до** записи, политика `--on-conflict skip|overwrite` (без флага —
    прерывание со списком всех конфликтных ID, ни одной записи), счётчик после
    импорта поднят до `max(локальный, bundle, наибольший импортируемый номер)`.
  - `state_cli.py`: `dt state export <file>` / `import <file>
    [--on-conflict …] [--json]`; `-` = stdout/stdin для прямого канала
    `export - | ssh other 'dt state import -'`.
  - публичный API в `tasks.py`: `read_counter`, `advance_counter`,
    `record_path` (валидирует ID → защита от path traversal); переиспользуется
    T042. Спека `specs/T041-state-transfer/spec.md` (Analyzed), ADR.
- **T040 — синхронизация BACKLOG.md** (`dt backlog sync`, точка входа E1,
  `deps: T034`). Под оперативным слоем `BACKLOG.md` — статус-независимая
  проекция store в git-слой (design §215–216):
  - `dt/backlog.py` (pure, git-free): `backlog_items` — незавершённые задачи
    (`todo`/`doing`/`review`, без `done`/`dropped`) по **числовому** ID;
    `render_item`/`render_block` — формат `- **T<NNN>** — [<created>] <title>
    (deps: …; spec: …)`; `sync_backlog` рвёт только регион между маркерами
    `<!-- dt:backlog:begin/end -->`, сохраняя ручную прозу, self-bootstrap при
    отсутствии маркеров, идемпотентно (regex с функцией-заменой — заголовки с
    `\`/`\g` не интерпретируются).
  - `backlog_divergence(store, backlog_text) → (added, removed)` — чистая
    функция расхождения BACKLOG↔store для будущего `dt context` (T051):
    `added` — заведённые вне блока, `removed` — завершённые/выброшенные в блоке.
    Построена сейчас по декомпозиции дизайн-карточки T008; CLI у неё нет.
  - `dt backlog sync [--force]` в `backlog_cli.py`: отказ вне основной ветки
    (`default_base_branch`, detached HEAD и «вне git» — тоже) без `--force`,
    иначе две ветки дают merge-конфликт BACKLOG.md; `--json` `{backlog,tasks}`.
    Пишет `repo_root/BACKLOG.md`. Спека `specs/T040-backlog-sync/spec.md`
    (Analyzed), ADR в `DECISIONS.md`.
- **T039 — композитный старт задачи** (`dt task start T<NNN>`, точка входа
  E1, `deps: T034, T036`). Одна команда сворачивает рутину начала работы
  (design §326/§336, карточка T007):
  - `dt/slug.py` (pure) — транслитерация заголовка ru→lat + нормализация
    в ASCII-slug; `branch_name` строит `T<NNN>-<slug>`
    (`«Композитный старт задачи»` → `T039-kompozitnyi-start-zadachi`),
    пустой slug → ветка `T<NNN>`. Уникальность даёт префикс, коллизии slug
    безвредны.
  - `dt/starts.py` (pure) — `plan_start` (decision-table worktree/ветка →
    какой git-вызов), `context_line` для statusline, `extract_handover`
    (секция `## Handover` для `--json`), `write_binding`.
  - `dt/tmux.py` — best-effort `rename-window` внутри CLI при `$TMUX`;
    вне tmux/без бинаря — тихий no-op, никогда не бросает (§419).
  - git-хелперы в `paths.py`: `local_branch_exists`, `add_worktree`
    (с `-b` от локальной base без fetch, либо attach к существующей ветке);
    `start_task` в `tasks.py` (статус→`doing` + `branch` + `updated`).
  - Команда `dt task start` в `task_cli.py`: идемпотентна (переиспользует
    существующий worktree/ветку), пишет привязку под slug **нового**
    worktree, `--json` `{id,status,branch,worktree,worktree_created,
    branch_created,spec,handover,tmux_renamed}`. Спека
    `specs/T039-task-start/spec.md` (Analyzed), ADR в `DECISIONS.md`.
- **T058 — `dt task check` ловит дрейф frontmatter `id` ↔ имя файла**
  (follow-up к ревью T038). Имя файла — канонический ID; T038 канонизировал
  `load_all_tasks` (`id = path.stem`), из-за чего рассогласование стало
  невидимо проверкам. `check_tasks` теперь сравнивает **сырой**
  `load_task(path).id` (single-load не канонизирует) с именем файла и на
  расхождении выдаёт **WARNING** (не ERROR — стор самоисцеляется, гейт валить
  нельзя; но пользователю сообщаем, чтобы поправил запись). ADR в `DECISIONS.md`.
- **T038 — поиск задачи по фразе** (`dt task find "<фраза>"`, точка входа E1).
  Путь от человеческой формулировки к ID (агент-сценарий design §326):
  - `find_tasks(store, query)` в `dt/tasks.py` (typer-free, git-free) —
    ранжирование по 4 полям с весами `title=3 > tags=2 = branch=2 > body=1`,
    статус-множитель active `×1.0` / `done`·`dropped` `×0.5`; каждый
    query-токен даёт **макс** вес поля (не сумму); сортировка
    `score`→`updated`→ID; только `score>0`.
  - Токенизация `re.findall(r'\w+', casefold)` (Unicode, кириллица),
    токены < 2 симв. отброшены. Матч **морфология-толерантный** по общему
    префиксу ≥ 4 (`курсор`~`курсора`, `полноэкранный`~`полноэкранном`);
    короче 4 — точное равенство. Без эмбеддингов и внешних сервисов.
  - `dt task find` (под `task`): вывод `T<NNN> [status] title (branch)`;
    `--json` — полные записи + `score`; пусто/нет совпадений → «no matches».
  - Спека — `specs/T038-task-find/spec.md`; ADR в `DECISIONS.md`.
- **T037 — текстовое представление доски** (`dt board`, точка входа E1).
  Kanban-обзор задач в терминал:
  - `dt/board.py` — чистая (git-free, typer-free) модель: `board_model(store)`
    (загрузка всех записей, отсев `dropped`, сортировка по `updated` убыв.,
    None — в конец, tiebreak по ID) + `board_columns(model)` (группировка по
    статусу в порядке потока `todo→doing→review→done`). Модель отделена от
    рендера — переиспользуется графической доской E10 (design §604).
  - `dt board` — top-level команда (`board_cli.py`): секции столбиком
    (заголовок статуса + `T<NNN> [status] title`), пустые колонки показаны.
    `--json` = `{columns: {todo, doing, review, done}}` с полными записями.
  - Спека — `specs/T037-board/spec.md`; ADR в `DECISIONS.md`.
- **T036 — размещение и жизненный цикл worktree** (`dt worktree
  root/path/list/prune`, четвёртая задача E1). Даёт агенту источник пути до
  рабочей копии задачи (лечит подстановку основной копии) и безопасную уборку:
  - `dt worktree root` — печатает `$DT_HOME/worktrees` для репозитория.
  - `dt worktree path <id|branch>` — путь рабочей копии: auto-detect аргумента
    (точный `T<NNN>` → task ID, читаем поле `branch`; иначе literal branch);
    фактический из `git worktree list --porcelain`, иначе вычисленный
    `$DT_HOME/worktrees/<branch>` (нигде не хранится). `--json` =
    `{branch, path, exists}`.
  - `dt worktree list` — сопоставление worktree с задачами (по полю `branch`,
    фолбэк — префикс `T<NNN>`); отдельно «осиротевшие» managed-worktree без
    задачи. Посторонние (основная копия, ручные) не помечаются. `--json` =
    `{matched, orphaned}`.
  - `dt worktree prune` — сносит managed-worktree задач в `done`/`dropped` со
    слитой веткой и чистым деревом, удаляя и worktree, и слитую локальную
    ветку (`git branch -d`); **никогда** не трогает грязный/неслитый —
    пропускает с перечислением всех причин. `--json` =
    `{removed, skipped, errors}`.
  - `dt/worktrees.py` — чистое ядро (typer-free И git-free): classify/resolve
    path, сопоставление, планировщик prune над предвычисленными git-фактами.
    Git-вызовы (`list_worktrees`/`branch_merged`/`worktree_dirty`/
    `remove_worktree`/`delete_branch`/автодетект base) — в `dt/paths.py`;
    Typer-обёртки — `worktree_cli.py`.
  - Известное ограничение: слитость через `merge-base --is-ancestor` не
    детектит squash-merge → такая ветка консервативно «не слита» и prune её
    пропускает (безопасный отказ; ручная уборка методики компенсирует).
  - Спека — `specs/T036-worktrees/spec.md`; ADR в `DECISIONS.md`.
- **T035 — валидация и готовность** (`dt task check` / `dt task ready`,
  третья задача E1). Целостность графа задач и вопрос «что можно брать»:
  - `dt task check` — валидация: висячие ссылки `deps`/`parent` (ERROR),
    циклы в `deps` (ERROR, three-colour DFS, каждый цикл один раз, self-loop
    — цикл длины 1), существование spec-файла (мягко: WARNING, но ERROR если
    ветка задачи выгружена — путь резолвится относительно текущей рабочей
    копии). `--json` = `{errors, warnings}`; код ≠ 0 при любой ошибке.
  - `dt task ready` — задачи `todo`, у которых все `deps` существуют и в
    `done` (без deps — готова; висячий dep не делает готовой). `--json` —
    полные записи.
  - `dt/tasks.py` (typer-free И git-free): `check_tasks`/`ready_tasks`/
    `load_all_tasks`; git-контекст (`repo_root`/`current_branch`) входит
    параметром, добывается в `dt/paths.py` (`git_context`, best-effort,
    `(None, None)` вне git / detached HEAD → ветка `None`).
  - Подключение в pre-push: CI-шаг `uv run dt task check` в `ci.yml` рядом
    с `translate_check` (критерий приёмки E1 №5); на пустом store dreamteam
    проходит vacuously до догфудинга `migrate` (T042).
  - Свёрнут микро-нит из ревью T034: `_ID_RE` `\d`→`[0-9]` (ASCII-цифры,
    unicode `T۰۰۱` отвергается). Робастность, не security.
  - Спека — `specs/T035-task-validation/spec.md`; ADR в `DECISIONS.md`.
- **T034 — базовые операции над задачами** (`dt task new/show/move/split`,
  вторая задача E1). Первые пользовательские команды оперативного слоя
  поверх фундамента T033:
  - `dt/tasks.py` — чистый слой операций (typer-free, как весь `dt/`):
    атомарная выдача ID (`counter` + `O_CREAT|O_EXCL` на файле записи как
    арбитр гонки — параллельные worktree не могут получить один номер);
    `new_task` (валидация всех ссылок `--deps`/`--parent`/`--blocks` **до**
    выделения ID; `--blocks B` дописывает новый ID в `B.deps` и бампит
    `B.updated`); `move_task` (статус + `updated`); `split_task` (ребёнок с
    `parent`, родитель не трогается); `show_task`.
  - `task_cli.py` — Typer-обёртки, под-приложение `task` подключено к общему
    `app` (доступно как `dt task …` и `dreamteam task …`); `--json` отдаёт
    полную запись (агент-facing), человекочитаемый вывод по умолчанию.
  - `TASK_STATUSES = get_args(TaskStatus)` в `dt/model.py` — единственный
    источник допустимых статусов (валидация `move`, тест против дрейфа).
  - Робастность (по ревью qodo): валидация ID `^T\d{3,}$` на всех входах
    (защита от path-traversal — `dt task show ../x` отвергается до обращения
    к ФС, инвариант «не оперировать внутри git»); `OSError` при записи
    маппится в чистую CLI-ошибку; отрицательный `counter` считается битым.
  - 34 теста (чистый слой + CLI через `CliRunner`). ADR — `DECISIONS.md`
    (2026-07-30); спека — `specs/T034-task-ops/spec.md`.
- **T033 — каркас хранилища и модель задачи** (фундамент E1, оперативный
  слой состояния). Новый подпакет `src/dreamteam/dt/`:
  - `dt/paths.py` — резолв `$DT_HOME` = `${DT_HOME:-<main-worktree>.dt}`
    от git-common-dir (одинаков из любого worktree; override `DT_HOME`;
    краевой случай bare-репозитория); `<slug>` рабочей копии (8 hex sha1
    абсолютного пути); ленивое идемпотентное создание дерева `store/`
    (`tasks/`, `sessions/`, `by-worktree/`) и `worktrees/` с одной
    строкой в stderr при самом первом создании; внятная `DtHomeError`
    с подсказкой про `DT_HOME` при недоступном каталоге / отсутствии git.
  - `dt/model.py` — pydantic-модель `Task` (`extra='allow'` сохраняет
    неизвестные поля frontmatter при round-trip; валидация `status`);
    `parse_task`/`dump_task`/`load_task`/`save_task` с детерминированной
    сериализацией (канон-порядок ключей, минимальный frontmatter).
  - Новая зависимость `pydantic>=2.9`; ruff-конфиг
    `runtime-evaluated-base-classes = ["pydantic.BaseModel"]`.
  - 24 юнит-теста (реальные git-репо + linked-worktree). ADR — `DECISIONS.md`
    (2026-07-30); спека — `specs/T033-store-core/spec.md`.
  - Пользовательских команд `dt task/…` пока нет — приезжают в T034.

### Changed

- **Приземлена дорожная карта v0.3 → v1.0** (методический PR, без T-ID).
  Разворот пакета из тонкого Copier-CLI в stateful-инструмент с
  оперативным слоем состояния (`<repo>.dt/`). Дизайн-документ —
  `specs/roadmap-v0.3-v1.0/design.md`; зонтичный ADR — `DECISIONS.md`
  (2026-07-30); 24 задачи v0.3 заведены в `BACKLOG.md` как T033–T056
  (локальные T001–T024 дизайн-документа, сдвиг `+32`); эпики v0.4+
  (E3, E10, E4, E5.2, E7, E8) — без декомпозиции до взятия в работу.
  Кода ещё нет: это фиксация плана и архитектурных решений перед
  реализацией по критическому пути (T033 → T034 → T051 → T052 → T053).

---

## [1.7.0] — 2026-07-30 — Параллельные worktree + дозревание методики после обкатки

MINOR-веха, консолидирующая тему **параллельной работы в нескольких git
worktree** и первое дозревание методики после обкатки на живых
derived-проектах (`efactory`, `calque`). Методические правила
(T023 / T024 / T025) доведены до шаблона; добавлены методика параллельных
worktree + memory-agnostic принцип (T030) и дисциплина тяжёлых
тест-прогонов через мьютекс-обёртку (T031); попутно починен pre-push
сгенерённых проектов под свежим `ruff` (T032). Все правки методики — по
схеме source `ru` + re-bootstrap `en/fr/de/zh` под `source_hash`-гардом.

### Changed

- **Дисциплина тяжёлых тест-прогонов при параллельных worktree в шаблоне**
  (T031). Продолжение T030 (параллельные worktree): общий ресурс —
  оперативная память, полный / coverage-прогон в двух-трёх worktree
  одновременно стекается в OOM/зависание. Зашито в шаблон самодостаточно
  (source `ru` + re-bootstrap `en/fr/de/zh`):
  - **Мьютекс-обёртка** `scripts/pytest-guard.sh` — drop-in префикс к
    прогону, сериализует тяжёлые прогоны между ВСЕМИ worktree через общий
    per-user `flock`-лок (concurrency 1, блокирующее ожидание). Раннер
    подставляется по выбранному `package_manager`, не хардкодом. Без
    `flock` (Windows) — деградирует в прямой прогон, не падает.
    Опциональный mem-cap `PYTEST_GUARD_MEM_MAX` (systemd cgroup на Linux,
    no-op иначе).
  - **Лёгкий дефолтный прогон** — coverage вынесен из дефолтного
    `addopts` (`template/pyproject.toml`); порог ≥ 80% на `src/` держится
    явной командой через обёртку в pre-push-гейте (шаг 4) и CI. Порог не
    ослаблен.
  - **Правило в проектном `CLAUDE.md`** — новый раздел «Тяжёлые
    тест-прогоны — через мьютекс-обёртку» (что через обёртку, что
    напрямую; CI — напрямую) + переписаны гейт 4 и pre-push-цепочка.
  - Интеграционные тесты: `test_template` гонит обёртку с coverage на
    сгенерённом проекте, `test_multilang` проверяет наличие + executable
    во всех 5 языках. ADR в `DECISIONS.md`.
- **Методика после первой обкатки — три правила доведены до шаблона**
  (T023 + T024 + T025). Source-of-truth
  `template/i18n/ru/CLAUDE.md` + `CONCEPT.md`, re-bootstrap переводов
  `en/fr/de/zh` (обновлён `source_hash`) и проектный `CLAUDE.md`:
  - **T023** — ритуал `CONCEPT.md`: структура разделов подана как
    **leading questions для пустого concept**, не обязательная форма.
    Содержательный существующий `CONCEPT.md` / ТЗ принимается как
    есть, `clarify` идёт по его содержимому; обязателен только
    `clarify` + `Out of scope` в любой форме; immutable-инвариант
    сохранён.
  - **T024** — code review: при подключённом рабочем ревью-боте
    (CodeRabbit и аналоги) он baseline, self-review Claude'а по
    умолчанию не требуется. Self-review остаётся дефолтом для
    docs/методика-PR, как targeted deep-review нетривиального кода и
    как fallback при недоступности бота.
  - **T025** — закрытие задачи `Doing → Done` переносится в том же
    squash-коммите задачного PR (не парным chore-PR); границы PR — по
    логической связности, дробление ради «PR покороче» — anti-pattern.
- **Методика параллельных git worktree + memory-agnostic принцип в
  шаблоне** (T030). В генерируемый проектный `CLAUDE.md` (source-of-truth
  `ru` + re-bootstrap `en/fr/de/zh`) добавлены два самодостаточных
  раздела:
  - **«Где живёт знание о проекте (memory-agnostic)»** — durable-знание
    живёт ВНУТРИ репо (`CLAUDE.md`/`DECISIONS.md`/`docs/`/`specs/`); любая
    внешняя память ассистента (если есть) — опциональный дубль, методика
    работает без неё; сначала факт в файлы проекта, потом опционально
    вовне.
  - **«Параллельная работа в нескольких git worktree»** — реестр
    (`git worktree list`), ритуал старта, изоляция (ветка / окружение /
    журналы+rebase), жизненный цикл, уборка-с-запросом, общие dev-сервисы
    «один экземпляр на пользователя», ловушка «память ≠ общая между
    папками». Формулировки нейтральны (без личных имён / `mem0` /
    хостинг-специфики).

### Fixed

- **Сгенерённые проекты снова проходят свой pre-push `ruff check`**
  (T032). Свежий `ruff` вывел `CPY001` (flake8-copyright) из preview в
  стабильный набор; при `select = ["ALL"]` это ломало **каждый**
  `dreamteam init` проект (`CPY001 Missing copyright notice` на
  `src/main.py`) и красило integration-тесты `test_template` /
  `test_multilang` (×5). Фикс: `CPY001` добавлен в `ignore`-лист шаблона
  (`src/dreamteam/template/pyproject.toml`) — личные проекты не ведут
  per-file copyright-заголовки. ADR в `DECISIONS.md`.

### Retrospective

- **Что зашло.** Обкатка на живых проектах окупилась: механика T031
  пришла из реального `calque` (T168/T169) уже проверенной — в шаблон
  переносили обобщение, а не изобретали; правила T023/T024/T025 — прямой
  урок первой обкатки. Re-bootstrap i18n под `source_hash`-гардом прошёл
  гладко на всех правках `CLAUDE.md` (`translate_check` 44 ok каждый раз);
  locality правок (ru-source + 4 перевода) держалась. Правило T025
  (closing `BOARD → Done` в задачном PR) самоподтвердилось — применялось к
  самим этим PR.
- **Что не зашло.** `BOARD → Done` копился и не чистился между релизами:
  T026 завис с 1.6.0, доска рассинхронизировалась с `CHANGELOG` — поймали
  только на срезе 1.7.0. `[Unreleased]` накопил шесть задач без
  промежуточного среза: крупный changelog-блок за раз, мелкие
  методические партии (T023/T024/T025) можно было резать раньше.
- **Правки методики.** На каждом release cut явно опустошать
  `BOARD → Done` (инвариант «после среза Done пуст»). Не копить
  `[Unreleased]` бесконечно — резать MINOR при завершении логически
  связной группы, не дожидаясь «ещё пары задач».

---

## [1.6.2] — 2026-07-06 — Hotfix: `dreamteam update` больше не портит рабочее дерево

### Fixed

- **`dreamteam update` больше не портит целевой проект** (T029, severity
  High, класс потери данных — второй багрепорт подряд по update-пути).
  1.6.1 (T028) чинил потерю git-конфига, но оставлял два фатальных
  дефекта, пока update вообще прогонял copier `run_update` на живом
  репо: (1) copier писал в read-only `.git/objects/info/commit-graph`
  (git создаёт его `0444` при штатном maintenance) и падал с
  `PermissionError`; (2) крэш случался после того, как copier уже
  переписал файлы рабочего дерева шаблонными заглушками, а откатывался
  только `.git` — дерево оставалось разгромленным без предупреждения.
  Фикс: `run_update` убран из update-пути целиком. Трёхсторонний merge
  теперь делает `git merge-file` — рендерим шаблон на базовой и текущей
  версии в temp (только безопасный `run_copy`), мержим по файлам с
  git-style конфликт-маркерами, считаем всё в temp и применяем к дереву
  только после полного успеха. `.git` пользователя не читается и не
  пишется вообще, поэтому read-only `commit-graph` физически
  недостижим, а история/ветка/remotes сохраняются by construction.
  Регресс `test_update_preserves_user_source_and_readonly_commit_graph`.
  ADR в `DECISIONS.md` (ревизирует T028/T009).

### Removed

- **Snapshot/restore `.git` из T028 и `run_update`-путь из T009** — вся
  деструктивная copier-update-машинерия (`_copier_merge_inplace`,
  `_merge_inplace_full`, `_restore_git`, monkeypatch
  `worker.subproject.last_answers`) удалена; заменена компактным
  `git merge-file`-движком (T029).

### Retrospective

- **Что не зашло:** два data-loss бага в `update` подряд (1.6.1 и
  1.6.2). T028 чинил симптом (потеря git-конфига), оставив нетронутой
  корневую опасную операцию — прогон copier `run_update` на живом репо.
  Пока она оставалась, следующий отказ (commit-graph + разрушение
  дерева) был вопросом времени.
- **Что зашло:** решение не «обмазать guard'ом», а **убрать опасную
  операцию целиком** (свой merge через `git merge-file`) закрыло сразу
  весь класс. Проверка на реальном сценарии багрепорта (а не только на
  синтетике) поймала бы оба бага раньше.
- **Правка методики:** для багов класса «потеря данных» дефолт —
  **устранять** опасную операцию, а не защищать её; и обязательный
  прогон живого сценария из багрепорта (real bundle / real user files)
  до релиза, а не только unit-тестов на синтетике.

---

## [1.6.1] — 2026-07-06 — Hotfix: `dreamteam update` no longer touches your git

### Fixed

- **`dreamteam update` разрушал git-состояние целевого проекта** (T028,
  severity High, класс потери данных — по багрепорту пользователя).
  Copier'овский `run_update`, работая прямо на репозитории проекта,
  переписывал `remote.origin.url` на временный клон шаблона (который
  затем удалялся), двигал ветку на снапшот шаблона, оставлял detached
  HEAD и конвертировал репо в partial clone — теряя реальный URL remote
  и указатель на историю. Фикс: merge выполняется на реальном репо (так
  copier'у доступна настоящая git-история для diff-применения), но `.git`
  снапшотится до и восстанавливается после — copier мутирует только
  refs/config, а слитые файлы живут в рабочем дереве. Итог: изменения
  приезжают незакоммиченным diff'ом, а HEAD / ветка / remotes / config
  остаются ровно как были. Регрессионный тест
  (`test_update_preserves_target_git_state`) фиксирует инвариант.

### Changed

- **README: процедура подключения Дизайнера прописана явно** — три
  пронумерованных шага (`claude mcp add` → `/design-login` → `claude mcp
  list`) с пояснением каждого, требованиями по планам и fallback'ом.

---

## [1.6.0] — 2026-07-05 — Team roles (Architect + Designer)

Первый MINOR после серии 1.5.x: крупная фича методологии — роли команды
(Архитектор + Дизайнер) в шаблоне (T026) — плюс актуализация README
(T027).

### Added

- **Роли команды: Архитектор + Дизайнер** (T026). Каждый derived-проект
  получает read-only субагент-Архитектор (`.claude/agents/architect.md`,
  авто-дискавери Claude Code) и методику ролей (`.claude/team-roles.md`,
  импортируется из `CLAUDE.md`), подключающую внешнего Дизайнера (Claude
  Design MCP), плюс бриф `specs/design-brief-template.md`. Функциональная
  шапка субагента собирается Jinja-сборщиком из данных, переводимое тело —
  partial под `_exclude` со `strip_frontmatter` (`src/dreamteam/_jinja_ext/`).
  Обе роли ставятся по умолчанию; авто-пикап на `dreamteam update` (новые
  файлы + идемпотентный пост-апдейт-хук строки `@import` в `cli.py`).
  Переводы тел и методики под `source_hash`-гардом (`translate_check.py`
  сканирует `partials/`). Спека: `specs/T026-team-roles/spec.md`,
  ADR в `DECISIONS.md`.

### Changed

- **README актуализирован под текущее состояние** (T027). Секция
  «Status» переписана (было «v0.x (pre-1.0)» → факт: `1.5.2`,
  опубликован на PyPI, история релизов 1.0.0→1.5.2); сверены команды,
  скрипты (`sandbox.sh` / `publish.sh`), ссылка на CI и версия Python —
  расхождений не найдено. Свёрстано в PR T026 по просьбе Разработчика.

### Retrospective

- **Что зашло.** Спека с analyze-проходом окупилась: §5 (расщепление
  шапка/тело) собрался почти по замыслу. Сверка допущений спеки по
  реальному коду поймала три неверных предположения (§5.5 про
  `sys.path`, `_`-переменные как copier-настройки, носитель
  `description`) **до** того, как они стали багами. Разбивка на фазы
  отдельными коммитами держала scope.
- **Что не зашло.** Фаза-план §8 не пережил контакт с тестами:
  fast-suite рендерит `init`, поэтому «машинерия без тел» (phase 1) не
  зелёная — пришлось складывать §8.2 в §8.1. А §5.5 стояла на
  непроверенном допущении про `sys.path` copier — стоило поймать на
  analyze, а не на implement.
- **Правки методики.** При analyze крупной фичи, завязанной на внешние
  механизмы (copier internals), — проверять допущения о поведении
  зависимостей эмпирически (мелкий спайк), не только «сверкой по коду».
  Фазовый план, где «каждый коммит зелёный», сверять с тем, что реально
  гоняет fast-suite, до фиксации.

---

## [1.5.2] — 2026-05-15 — Bootstrap fixes after efactory shakedown

Короткий PATCH-цикл из обкатки методики на первом реальном
derived-проекте (`efactory`, 2026-05-15). Два bootstrap-фикса в
template (T021, T022) + out-of-band методическая cleanup от
устаревших артефактов (T020). T023 и T024 поднялись в backlog
к следующему MINOR-циклу (1.6.0).

### Fixed

- **`template/hooks/pre-push` теперь пропускает initial push**
  (T021). Hook отклонял любой push в `refs/heads/main` /
  `refs/heads/master`, не различая bootstrap-сценарий (когда
  ветка ещё не существует на remote) и обычный push в
  protected branch. На практике это заставляло использовать
  `--no-verify` при первой публикации свежесозданного проекта
  (всплыло в `efactory` bootstrap). Новое поведение: если
  `remote_sha == 40 zeros` (стандартный Git-маркер «ветки нет
  на remote») — push разрешён с info-сообщением
  `Initial push detected — allowing bootstrap of '<branch>'`.
  Обычный push в существующую protected branch по-прежнему
  блокируется. Unit-тест `tests/test_pre_push_hook.py`
  (8 кейсов: initial main/master, regular reject, feature
  branch, empty stdin, mixed refs — оба направления).

- **`template/.gitignore` теперь покрывает плоский `.secrets`**
  (T022). В секции «Secrets / config» три строки `.env` /
  `.secrets.*` / `.secrets.toml` / `secrets.env` оставляли gap:
  файл с именем `.secrets` без расширения (sourceable shell
  secrets — ровно тот формат, что использует
  `scripts/publish.sh` шаблона для PyPI токенов) не попадал ни
  под один паттерн. На свежем `dt init` это значило риск
  закоммитить токены в первый же commit, если разработчик
  кладёт их по той же конвенции, что и сам шаблон.
  Сконсолидировано в `.secrets*` (покрывает плоский `.secrets`,
  `.secrets.toml`, `.secrets.env`, `.secrets.local` и т.п.);
  `.env` оставлен отдельно как другой класс файла; `secrets.env`
  (без leading dot) оставлен — отдельная sh-export конвенция.
  Fast unit-тест `tests/test_gitignore_secrets.py` (6 кейсов:
  plain `.secrets`, dotted variants, `.env`, `secrets.env`,
  sanity check на не-секрет).

### Notes

- **Bundle re-tag**: `1.5.2` тег добавлен в `.bundle/`; main
  advanced; `scripts/update_bundle.py` без изменений.

- **Out-of-band методическая cleanup: stale упоминания
  `PROJECT.md`** (T020). После T014 (v1.1.0, удаление
  `PROJECT.md` из template) три durable-источника, которые
  Claude загружает в начале каждой сессии, продолжали описывать
  `PROJECT.md` как живой элемент методики. Это всплыло при
  обкатке методики на первом derived-проекте (`efactory`):
  Claude предложил создать `PROJECT.md`, прочитав устаревшие
  инструкции. Правки **вне репо dreamteam** (не влияют на
  wheel / package-data):
  - `~/.claude/CLAUDE.md` — 3 места в разделах «Признак нового
    проекта», «Работа в проекте с шаблонной структурой»,
    «Ритуал составления `CONCEPT.md`». Заменены на актуальный
    набор файлов (проектный `CLAUDE.md` как главный признак,
    `README.md` как current state — см. ADR T014).
  - `~/.claude/projects/-home-vlakir-programming-dreamteam/memory/project_template_dreamteam.md`
    — обновлён список файлов template и порядок чтения в
    начале сессии.
  - `~/.claude/projects/-home-vlakir-programming-dreamteam/memory/project_src_layout.md`
    — список файлов в корне.
  Иммутабельные упоминания (в `CHANGELOG`, `DECISIONS`,
  `specs/T006-*`, `memory/feedback_validation_blocks_chain.md`)
  оставлены как исторический контекст. T020 не требует version
  bump и публикации — правки чисто в личной configuration
  Разработчика.

### Retrospective

- **Что зашло:**
  - **«Обкатка → grooming → fixes» в одной сессии** сработала.
    `efactory` shakedown 2026-05-15 19:41 → backlog grooming
    T020-T024 → закрытие T020 + T021 + T022 + release cut 1.5.2
    — всё в одной сессии. Контекст не размывается между
    обнаружением проблемы и фиксом.
  - **T024 conditional flow** (только что захваченное в backlog
    и не выкаченное в durable-источники) применился
    поведенчески через memory сразу — поведенческая память как
    мост между «обсудили правило» и «выкатили в CLAUDE.md»
    работает.
  - **Catch-it-at-the-text** сработал на «Гвидо» → «Claude» в
    backlog entries T023/T024 — правило нейтральных ролей
    поймалось до commit (grep, не post-merge).
- **Что не зашло:**
  - **CodeRabbit rate-limit три раза подряд** (PRs #59, #60,
    #61 — все три ушли в Claude self-review fallback по T024).
    «Usage credits run out» — paid quota не infinite, burst
    PR-ов её сожрал. Это уже **второй** retrospective подряд с
    этим паттерном (см. [1.5.0]), но lesson не учтён. Mitigation:
    либо упорядочивать темп PR-ов, либо batch fixes (но это
    конфликт с «один PR — одна задача»), либо рассмотреть
    upgrade плана. Подсветить Разработчику.
  - **T020 PR содержал backlog grooming T021-T024 как побочно** —
    formal нарушение strict «один PR — одна задача». Оправдано
    тем, что добавление T-ID в backlog — пред-условие T020
    closure, но pattern на грани scope discipline. Альтернатива
    — `meta/backlog-grooming-*` отдельным PR — добавляет
    церемонию для рутинной правки.
- **Правки методики:**
  - Memory entry о **CodeRabbit usage-credit cap** (отдельно от
    hourly rate-limit) — добавить в репо memory как явное
    предупреждение «burst PR-ов сжигает квоту, planning needed».
  - Если темп требует 3+ PR-ов в час → **явно рассмотреть
    combined-PR** даже когда задачи разные, описав в PR
    body, что объединение сделано ради ботового quota economy.
    Это уже было применено для T017 (Phase 1+2+3 combined) —
    закрепить как стандарт для bot-quota-constrained
    obstreloved сессий.

---

## [1.5.1] — 2026-05-15 — Apply template to an existing project

Короткий PATCH-цикл после 1.5.0: единственная фича — **`dt apply`**,
закрывающая usability gap между `dt init` и `dt update` для
проектов, скаффолженных другим инструментом (PyCharm new-project,
`poetry new`, `hatch new`, manual `mkdir`). T018 spec + impl;
T019 — UX-refinement (default `path = .` для `dt apply`, паритет
с `dt update`).

PATCH вместо MINOR — explicit departure от strict semver, framing
«закрытие usability gap», не principally new feature на уровне
T009 (full update) / T017 (multi-PM). Зафиксировано в ADR.

### Changed

- **`dt apply` без аргумента = `.`** (T019). `path` теперь имеет
  default `Path()` (текущая директория), идентично уже-работающему
  поведению `dt update`. Сценарий «зашёл в свежесозданный проект и
  одной командой накатил template» теперь работает без явного
  пути: `cd my-project && dt apply`. Backward-compatible —
  явный path продолжает работать как раньше.

### Added

- **`dt apply` — наложить dreamteam-template на уже-созданный
  проект** (T018, v1.5.1). Закрывает пробел между `dt init`
  (требует пустой каталог) и `dt update` (требует
  `.copier-answers.yml` от предыдущего init): теперь
  разработчик, создавший проект через PyCharm new-project /
  `poetry new` / `hatch new` / `mkdir`, одной командой
  накатывает методологию dreamteam поверх существующего
  scaffolding-а. `.venv/`, `.git/`, user code и любые не-
  template-managed файлы не трогаются.

  **Flow:**
  1. Render template в tempdir (используя copier + `--data` /
     `--defaults` / prompts для answers).
  2. Walk preview tree, сравнить с target file-by-file:
     - отсутствует в target → `create`;
     - идентично rendered → `unchanged`;
     - расхождение → conflict, see resolution below.
  3. Записать `.copier-answers.yml` (full answers + `_commit
     = 1.5.1` + `_src_path = <bundle>`), так что subsequent
     `dt update` работает штатно.
  4. Итоговая summary line: «`N created, M unchanged, K kept,
     L overwritten, X saved as .dt-new`».

  **Resolution per conflict (Q2 → 4-way interactive prompt):**
  - `[k]eep` — keep target version (default).
  - `[o]verwrite` — write template version.
  - `[d]iff` — print unified diff, loop back to prompt.
  - `[s]ave-as-new` — write template content to
    `<file>.dt-new`; original stays.

  **`--on-conflict <keep|overwrite|save-as-new>`** flag для
  non-interactive runs (CI / scripts / `--data`-driven). При
  `sys.stdin.isatty() == False` без `--on-conflict` — exit 1
  с ошибкой «non-interactive run requires --on-conflict».

  **`--dry-run`** — plan-only output без записи (включая
  `.copier-answers.yml`). Полезно для preview перед actual
  apply.

  **Уже-dreamteam проект** (target содержит
  `.copier-answers.yml`) → exit 1, message «use `dt update`».

  **Integration test matrix** (`tests/test_t018_phase2.py`):
  5 managers × empty target (sanity per package_manager) +
  3 scaffold-states × uv (PyCharm-like / Poetry-like /
  Hatch-like, exercise все три conflict resolutions) +
  4 sanity (`--dry-run`, already-dreamteam, apply→update
  pipeline, invalid `--on-conflict`). 12 cases, all green.

  **Version bump:** `dreamteam-cli` **1.5.0 → 1.5.1**
  (PATCH). Strict semver-чтение предписало бы MINOR для нового
  CLI-command, но T018 в этом цикле framed как «refinement /
  закрытие usability gap», не principally new feature на
  уровне T009 (full update) / T017 (multi-PM). Explicit
  departure документирован в ADR. Backward-compatible:
  существующие `dt init` / `dt update` не затронуты.

  **Bundle re-tag**: `1.5.1` тег добавлен в `.bundle/`; main
  advanced; `scripts/update_bundle.py` без изменений.

  **Rejected alternatives** (см. ADR в `DECISIONS.md`):
  - **`dt init --existing` flag** (vs new command) — flag
    obscure без `--help`.
  - **Auto-detect в `dt init`** (empty → init, non-empty →
    apply) — implicit behavior, surprising для CI runs.
  - **Copier's native Y/N prompt** (vs custom 4-way) — менее
    rich UX, no diff option.
  - **Auto-save `.dt-new` без prompt** — non-interactive
    friendly, но user не видит conflicts без проверки рядом.
  - **Semantic merge `pyproject.toml`** (TOML-level union) —
    out of MVP scope; добавит сложность без явной выгоды на
    текущем сценарии.

  Phase split (для CodeRabbit's hourly rate-limit economy,
  T017 pattern): Phase 0 spec (PR #55) + Phase 1+2+3 combined
  (этот PR).

### Retrospective

- **Что зашло:**
  - **T018 разобран на 2 PR-а** (#55 spec + #56 combined
    Phase 1+2+3) вместо четырёх — combined pattern из T017
    закрепился как дефолт для нетяжёлых фич с готовой spec.
    CodeRabbit не упёрся в rate-limit ни разу за цикл.
  - **CodeRabbit catch на T018 spec (#55)** — несколько
    🟡-замечаний на edge-кейсы (non-TTY UX, diff volume,
    copier 2-way vs 4-way, `.git/` guard); 3 из 4 вылилось в
    реальные mitigations в impl (`sys.stdin.isatty()` guard,
    documented diff-paging follow-up, 4-way prompt rationale
    в ADR). Spec-phase ботом доносится не хуже code-PR.
  - **Fast tests параллельно integration**: новые helpers в
    `apply` (8 функций) покрыты unit-тестами с mocked `typer.
    prompt`/`isatty()` — coverage поднялся обратно до 86%
    после провала на 60% (integration matrix хорош, но не
    запускается в fast suite). Pattern для будущих фич:
    «integration matrix + unit helpers» вместе.
  - **T019 как немедленный follow-up к T018** — Vladimir
    спросил «а зачем `dt apply .` если я уже в проекте?» —
    добавлен default за 5 строк, 1 fast test, ≤24 часа от
    merge T018. Маленький UX win без церемонии. Scope-
    дисциплина: формальный T-ID + отдельный PR, а не
    «заодно».
- **Что не зашло:**
  - **PATCH-vs-MINOR пограничный** — T018 это новая публичная
    команда, что по strict semver = MINOR. Чтобы сохранить
    1.5.x как «refinement-цикл» 1.5.0, framing — «закрытие
    usability gap, не principally new feature». Risk: если
    следующая фича получит такой же framing, мы по факту
    будем игнорировать MINOR-границу. Mitigation: ADR
    зафиксировал rationale и явно сказал, что departure
    sustainable только при подобной framing-аргументации.
  - **Test coverage drop до 60% после Phase 1+2** — fast
    suite не покрывал новые helpers, и `--cov-fail-under=80`
    остановил pre-push. Pattern: integration-only coverage
    обманчив для дефолтного pytest run. **Lesson:** при
    добавлении нового модуля / большого блока helpers —
    сразу планировать fast unit tests параллельно
    integration matrix, не «доберём, если что».
  - **`copier.Worker` deprecation warning** появляется
    громче — каждый apply/init/update тест в pytest output.
    Не блокер, но шумно. Можно (a) суппрессировать на
    уровне `pyproject.toml [tool.pytest.ini_options]
    filterwarnings`, либо (b) подождать стабильного
    public alternative у copier и мигрировать. Отложили.
- **Правки методики:**
  - **Default «fast unit + integration matrix»** для нового
    модуля. Зафиксировать в репо-CLAUDE.md под «pre-push
    contract» примечание: integration coverage не считается
    за основной 80%-gate; pytest run по умолчанию использует
    fast suite.
  - **Combined-PR pattern как дефолт** для combined Phase
    1+2+3 после Phase 0 spec — закреплено как стандарт
    workflow в нашем проекте, не только workaround для
    rate-limit. PR boundaries: spec-PR (Phase 0) и
    impl-PR (Phase 1+2+3) — две границы review-внимания.
  - **Hot-follow-up T-ID-ы** разрешены и предпочтительны
    перед «заодно». T019 как пример: маленькая UX-правка
    получила формальный ID, отдельный PR, отдельный review.
    Scope discipline не страдает; история PRs читается
    линейно.

---

## [1.5.0] — 2026-05-15 — Full update flow + package-manager choice + CLI ergonomics

Накопленные изменения через bump-серию `1.3.0 → 1.4.0 → 1.5.0`.
Центральные две задачи цикла — **T009** (полноценный
`dreamteam update` с three-way merge, заменивший MVP overwrite)
и **T017** (параметризация выбора package manager в derived
template). Плюс ergonomic win T016 (`dt` alias) и organizational
change T007 (qodo → CodeRabbit как стандартный external bot).

### Added

- **Параметризованный выбор package manager** для derived
  projects (T017, v1.5.0). Закрывает cross-pollination concern,
  обнаруженный во время T016 install-via-pip smoke: derived
  projects shipped hardcoded `uv` команды в narrative-файлах
  (×11 в CLAUDE.md, ×7 в README, на каждый из 5 языков), и
  pip- / poetry-user видел в Claude советы по uv-инструментарию,
  которого у него нет.

  **Новый prompt `package_manager` в `copier.yml`** с 5 choices:
  `uv` (default, fast-modern) / `poetry` (traditional) / `pdm`
  (PEP 621-native alt) / `hatch` (PyPA-recommended) / `pip`
  (bare). Default `uv` сохраняет existing behavior для new
  inits без явного `--data package_manager=...`.

  **Conditional rendering**:
  - `pyproject.toml` template содержит conditional `[build-system]`
    + manager-specific `[tool.<mgr>]` секции:
    - **uv:** `hatchling` build-backend + `[dependency-groups]`.
    - **poetry:** `poetry-core` build-backend +
      `[tool.poetry.group.dev.dependencies]`.
    - **pdm:** `pdm-backend` build-backend + `[dependency-groups]`.
    - **hatch:** `hatchling` build-backend +
      `[tool.hatch.envs.default]` + `[...scripts]`.
    - **pip:** `hatchling` build-backend + `[dependency-groups]`.
  - Narrative-файлы (`CLAUDE.md`, `README.md` × 5 langs) используют
    Jinja set-macros `{{ pm_run }}`, `{{ pm_install }}`,
    `{{ pm_name }}` для command-prefix substitution. pre-push chain
    рендерится с правильным prefix: `uv run ruff check .` /
    `poetry run ruff check .` / `pdm run ruff check .` /
    `hatch run ruff check .` / `.venv/bin/ruff check .` (pip
    использует explicit `.venv/bin/` paths — git pre-push hook
    запускается без shell activation, bare commands флакают).

  **`_strip_frontmatter` в `_tasks_post_render.py`** обновлён —
  теперь принимает как `\n---\n` (стандартный end-marker), так
  и `\n---` следующий за любым не-newline char (Jinja whitespace
  trim `{%- ... -%}` ест trailing newline после closing
  delimiter, когда set-macros идут сразу после frontmatter).

  **Multilang re-bootstrap**: 8 файлов (`i18n/{en,fr,de,zh}/{CLAUDE,README}.md`)
  re-translated через Claude Code session с обновлённым
  `source_hash` (matching new ru-source content). 32 ok через
  `translate_check.py`.

  **Integration matrix test**: `tests/test_t017_phase2.py`
  — 5 managers × 5 langs = 25 cases + 2 sanity (default uv,
  pip explicit venv-bin paths) = 27 cases, all green. Verify
  rendered output (command prefix + build-backend +
  manager-specific TOML sections), не actual install (CI
  runner may not have all managers pre-installed).

  **Bundle re-tag**: `1.5.0` тег добавлен в `.bundle/`; main
  advanced; `scripts/update_bundle.py` обновлён — push main с
  `--force` (вместо `--force-with-lease=...` без expect-value,
  который ломался на single-writer scenarios).

  **Rejected alternatives** (см. ADR в `DECISIONS.md`):
  `pipenv` (declining, Pipfile-based), `pixi` (niche, conda
  compat), `conda`/`mamba` (другая парадигма, потребует
  отдельный `env_manager` prompt), `rye` (superseded by `uv`).

  **Version bump:** `dreamteam-cli` 1.4.0 → 1.5.0 (MINOR;
  backward-compat через silent default `uv` для existing
  derived projects без `package_manager` answer — copier
  standard mechanism).

  Phase split (документировано в ADR): Phase 0 spec (PR #51),
  Phase 1+2+3 combined в одном PR (этот) для economy на
  CodeRabbit's hourly rate-limit.

- **Короткий console-script alias `dt`** (T016). `pip install
  dreamteam-cli` теперь регистрирует две entry-точки:
  `dreamteam` и `dt`, обе указывают на `dreamteam.cli:app`.
  `dt init my-project` / `dt update --dry-run` / `dt --version`
  работают эквивалентно полному имени. Trade-off: PATH-namespace
  `dt` теперь занят на машине пользователя — известный risk
  collision с другими `dt`-named утилитами (на типовых Debian/
  Ubuntu installs ничего стандартного нет). README обновлён;
  smoke-test через `importlib.metadata.entry_points` верифицирует,
  что обе entry-точки зарегистрированы при install и указывают
  на тот же callable.

- **Полноценный `dreamteam update` с three-way merge** (T009,
  v1.4.0). Заменяет MVP-overwrite (`run_copy(..., overwrite=True)`),
  который клобберил пользовательские правки template-managed
  файлов. Новое поведение: при обычном вызове `dreamteam update`
  делает three-way merge между *base* (template-снапшот на
  момент `dreamteam init` или предыдущего update, из bundled
  bare git репо), *theirs* (новый template state из установленного
  пакета) и *ours* (текущее состояние derived-проекта). Конфликты
  отмечаются git-style markers (`<<<<<<<` / `=======` / `>>>>>>>`),
  exit code 2; clean merge → exit 0; жёсткие ошибки → exit 1.

  **Новые флаги:**
  - `--force` — пропускает merge, делает MVP overwrite (escape hatch
    «throw away local edits and re-apply template clean»).
  - `--dry-run` — рендерит would-be outcome в tempdir, печатает
    per-file unified diff к stdout + summary line с пятью bucket-ами
    (`N would change, M unchanged, K added, L removed, X conflicts`).
    Target никогда не модифицируется. Exit 0 если 0 conflicts, 2
    если есть `<<<<<<<` в preview.

  **Bundled bare git repo** в `src/dreamteam/template/.bundle/` —
  упакован в wheel как package-data, хранит все template snapshots
  как git-tags (PEP-440 unprefixed, dunamai требование copier-а:
  `1.3.0`, `1.4.0`, …). Reproducible build через `scripts/
  update_bundle.py` (fixed commit dates, `git gc --aggressive`,
  `.gitkeep` sentinels в `refs/heads/` и `refs/tags/` для
  переживания fresh clone). Wheel вырос ~50 KB → ~165 KB.

  **Fallback chain** (warning + MVP overwrite):
  - `--force` явно запрошен пользователем.
  - `git` не найден в PATH.
  - Bundle отсутствует в установленном пакете (старый wheel).
  - Base version tag отсутствует в bundle (derived проекты до
    v1.4.0, например с `_commit: dreamteam-1.0.0` legacy формата).

  **Реализация выехала четырьмя PR-ами:**
  - **Phase 0** (PR #44, spec) — `specs/T009-full-update/spec.md`,
    статус Analyzed, Q1–Q10 resolved.
  - **Phase 1** (PR #46) — bundled bare git repo, `Worker.run_update`
    backend, `--force`, exit codes, conflict scan через `<<<<<<<`,
    `__version__` → `importlib.metadata`. Fix .gitkeep ref dirs
    после CI flake.
  - **Phase 2** (PR #47) — synthetic two-tag bundle test fixture,
    Scenario A/B/C/D integration coverage (`tests/test_t009_phase2.py`,
    marked `@pytest.mark.integration`).
  - **Phase 3** (PR #48) — `--dry-run` с per-file unified diff
    (`difflib.unified_diff`), summary line, target safety
    invariant, helper-level unit tests.
  - **Phase 4** (этот PR) — ADR, CHANGELOG, version bump,
    README, bundle re-tag.

  **`scripts/update_bundle.py`** — maintainer-tool для добавления
  тега в bundle при release cut. Idempotent (skips если tag уже
  есть, `--force` для overwrite); fixed dates; `--force-with-lease`
  на main для single-writer scenario.

  **`pyproject.toml`** ignore-list расширен на S603
  (`subprocess-without-shell-equals-true`) — bandit overly-
  conservative для `list[str]` argv; subprocess-вызовы используют
  `shutil.which`-resolved абсолютные пути (S607 закрыт
  структурно). Pre-approved с Разработчиком.

  **ADR** в `DECISIONS.md` фиксирует все 10 Q-разрешений
  (Variant A vs B/C, ru-as-source vs English, manual Claude Code
  session vs scripted Anthropic SDK, hash-based vs diff-based —
  see ADR for full breakdown).

### Changed

- **`README.md` "Updating an existing project"** — описание
  переписано под new three-way merge default; MVP limitation note
  удалён.

- **Сторонний code review: qodo → CodeRabbit** (T007). qodo
  monthly quota иссякла к концу ночной сессии T015 (см.
  retrospective в `[1.3.0]`), что временно нарушило правило
  «сторонние ревью не игнорировать» для одного PR. Замена —
  **CodeRabbit** GitHub App, free tier для public OSS repos
  (`vlakir/dreamteam` подходит). Обкатано на T009 spec phase
  PR (#44): 4 findings (1 🟠 Major «Q2 option (b) network vs
  MUST NOT» — реальное противоречие, 1 🟡 Minor «v1.2.0
  version reference», 2 💤 Nitpicks про terminology), 3 из 4
  auto-resolved subsequent commits-ом, 1 fixed targeted commit.
  Quality findings сопоставимо с qodo; плюс — auto-resolution
  tracking на subsequent push, и CodeRabbit выставляет
  собственный CI status check. Hybrid стратегия: **CodeRabbit
  как automatic baseline на каждый PR + manual deep review
  через Claude Code session** для нетривиальных PR
  (architecture, security).

### Retrospective

- **Что зашло:**
  - **T009 four-phase stacked PRs** (#44 spec → #46 backend →
    #47 tests → #48 dry-run → #49 docs) — clean review boundaries,
    каждый PR держит фокус. Один-два «фикс по чужой логике»
    дополнения не нарушили рабочий ритм.
  - **CodeRabbit catch 🔴 critical bug в T009 Phase 1
    (`_bundle_has_tag` silent failure → potential data loss).**
    Без бота этот silent fallback клобберил бы user edits в
    реальном usage. T007 trial оправдал hybrid strategy на
    первой же substantive code-PR.
  - **CodeRabbit catch на T017 spec (pip pre-push without venv
    activation flakes).** Реальный bug в spec phase — fix
    применён до начала implementation. Demonstrates value
    bot-review на content-PR тоже.
  - **Combined-PR pattern** для T017 (Phase 1+2+3 в одном PR
    после Phase 0 spec) — workaround к CodeRabbit's hourly
    rate-limit. Сэкономило ~3 retrigger cycles.
  - **`dt` console alias** — trivial change (one line в
    pyproject) с outsized UX win. «Помилуем пальцы».
  - **Multilang re-bootstrap flow** scales: T017 потребовал
    регенерации 8 файлов × 4 languages — ~10 min Claude Code
    session, hash sync через `translate_check.py` 32 ok.
  - **Stacked PR + `--delete-branch` memory entry** оказался
    немедленно полезным (T009 series, потом T017 series).
- **Что не зашло:**
  - **CodeRabbit hourly rate-limit** хитaнут дважды (на #48,
    #49 — третий-четвёртый PR в час). Free tier OSS Pro plan
    имеет nondisclosed cap; mem0 запись добавлена. Workaround
    через combined-PR (T017) сработал; rate-limit для бурстов
    остаётся ограничением.
  - **PR #39 auto-closed** при `--delete-branch` стейкд-base
    ветки (T009 Phase 1 → Phase 2 stack). Пришлось пересоздавать
    как #41. Один из первых случаев в стек-PR паттерне; memory
    entry зафиксирован.
  - **`test_template.py` тихо ломался на main** до T017 — был
    integration-marked, в CI не запускался; T017 work выявил и
    починил (косвенно, через `[build-system] hatchling`
    эксперимент → откат). CI должен иметь knob для опционального
    integration run перед release-cut.
  - **`[build-system] hatchling`** для uv-mode сломал `uv sync`
    (`src/main.py` не пакет → auto-detect fail) — поймано только
    после running test_template. **Lesson:** при добавлении в
    template build-system всегда мысленно прокручивать
    «installer pipeline» (uv sync / poetry install / pip
    install -e .) на minimal derived structure.
  - **Jinja `{%- ... -%}` whitespace-trim** съел newline после
    frontmatter end-delim → frontmatter leaked в derived files,
    20/27 T017 integration tests failed до фикса `_strip_frontmatter`.
    Subtle Jinja semantics; lesson learned.
- **Правки методики:**
  - **mem0 entries** о CodeRabbit characteristics (5 facts —
    free tier, retrigger, line-proximity auto-resolution,
    output endpoints, hybrid strategy + rate-limit).
  - **Combined-PR strategy** для bot economy: при reviews >2
    PR-ов в час, рассмотреть combined PR. Зафиксировать в
    проектном CLAUDE.md → «when to combine phases».
  - **Test invariant**: при изменениях в template build-system
    или pyproject.toml — обязательно прогнать `test_template.py`
    integration tests (currently запускаются только локально).
    Можно добавить в pre-push контракт.
  - **Jinja whitespace-control awareness**: при использовании
    `{%- ... -%}` в файлах с frontmatter или другой
    delimiter-sensitive content — проверить rendered output на
    leaks. Можно зафиксировать как note в template development
    guide.

---

## [1.3.0] — 2026-05-15 — Multilang methodology + maturation

Накопленные изменения через серию bump-ов `1.0.0 → 1.1.0 → 1.2.0
→ 1.3.0` (без промежуточных release cuts; PyPI на 1.0.0, следующая
публикация прыгнет сразу к 1.3.0). Главное событие цикла — T013
multilang, плюс созревание процесса (CI workflow, MIT License,
publish flow, root CLAUDE.md, PROJECT.md retirement, validation-
chain pattern).

### Added

- **Multilang поддержка методических документов** (T013, v1.3.0).
  При `dreamteam init` появляется prompt `language` со списком `en
  / ru / fr / de / zh` (default `en`); narrative-файлы (`CLAUDE.md`,
  `README.md`, `CONCEPT.md`, `BACKLOG.md`, `BOARD.md`, `CHANGELOG.md`,
  `DECISIONS.md`, `specs/spec-template.md`) рендерятся на выбранном
  языке. Технические файлы (`pyproject.toml`, `src/`, `tests/`,
  `hooks/`) и kanban-keyword'ы (`To Do` / `Doing` / `Done`)
  одинаковы для любого языка. Внутри шаблона narrative лежит в
  `src/dreamteam/template/i18n/<lang>/`; post-render task
  (`_tasks_post_render.py`) переносит выбранный язык в корень
  derived-проекта и удаляет `i18n/`. **ru — source of truth**;
  `en/fr/de/zh` — AI-перевод через Claude Code session (не runtime
  API), с frontmatter (`translated_from`, `source_hash`,
  `translation_engine`, `translation_date`). CI guard
  `scripts/translate_check.py` (pure stdlib + PyYAML) сверяет
  sha256 ru-source с `source_hash` в каждом не-русском файле — drift
  в ru без regeneration переводов блокирует PR. Step добавлен в
  `.github/workflows/ci.yml` после pytest. Реализация выехала
  четырьмя PR-ами: Phase 0 (spec — PR #37), Phase 1 (skeleton + ru
  source + bootstrap всех 5 языков + unit/integration tests —
  PR #38), Phase 2 (CI guard step — PR #41), Phase 3 (CHANGELOG +
  ADR + README + version bump — PR #40). Spec —
  `specs/T013-multilang/spec.md` (Analyzed, Q1–Q9 resolved). ADR
  в `DECISIONS.md` фиксирует Variant A vs B/C, ru-as-source vs
  English-source, manual Claude Code session vs scripted Anthropic
  SDK, hash-based vs diff-based drift check.

- **CI workflow (GitHub Actions) для PR-проверок** (T015, v1.2.0+).
  `.github/workflows/ci.yml` запускает 4 проверки (`ruff check`,
  `ruff format --check`, `mypy src`, `pytest`) на каждый
  `pull_request` к `main` и `push` в `main`. Concurrency group
  cancel-in-progress на новые пуши в одну ветку. Использует
  `astral-sh/setup-uv@v3` с cache по `uv.lock`, Python 3.14,
  `uv sync --frozen`. Timeout 5 минут. После merge → Branch
  Protection обновлён через `gh api` — required status check
  `ruff + format + mypy + pytest` блокирует merge при fail
  (закрывает gap, проявившийся на slip T014, когда failing test
  замержился в main без CI).

- **Pattern `validation && commit` в шаблонном `CLAUDE.md`**
  (методический PR, v1.2.0). В Pre-push секцию добавлен chained
  example (все 4 проверки + `git add && commit && push` через `&&`)
  и заметка про **catch-it-at-the-output**: видишь `FAILED` /
  `1 failed` в выводе — стоп. `pytest | tail` НЕ годится (pipe
  возвращает exit-код tail, не pytest). Урок выучен на slip T014:
  failing test замержился в main, потому что bash chain не
  блокировал pytest fail.

- **Скрипт публикации** `scripts/publish.sh` + `.secrets` file для
  токенов (T011). Hybrid flow: source `.secrets` → `rm -rf dist/
  && uv build` → `twine check dist/*` → `UV_PUBLISH_TOKEN=… uv
  publish` (опционально `--test` для TestPyPI). Подробности — ADR
  в `DECISIONS.md` → «Publish flow: scripts/publish.sh + .secrets».

- **MIT License** (T010). `LICENSE` файл в корне репо со
  стандартным MIT-текстом (Copyright (c) 2026 vlakir). В
  `pyproject.toml`: `license = "MIT"` + `license-files =
  ["LICENSE"]` (PEP 639 syntax). README обновлён с линком на
  LICENSE и note про derived projects (которые license-choice не
  наследуют). ADR в `DECISIONS.md` фиксирует выбор и rejected
  alternatives (Apache 2.0, GPL-3.0, BSD-3-Clause). Снял блокер
  T011 (PyPI publish).

- **`CLAUDE.md` в корне репо** для разработки `dreamteam`-пакета
  (T012). Отдельный документ от `src/dreamteam/template/CLAUDE.md`
  (который попадает в derived проекты через `dreamteam init`).
  Этот CLAUDE.md описывает правила работы над **самим пакетом**:
  стек (Python 3.14, uv, hatchling, typer, copier), команды
  разработки (uv sync / pytest / dreamteam init smoke / uv build),
  pre-push контракт (4 проверки), специфика репо (two CLAUDE.md,
  template exclude из ruff/mypy, copier.Worker deprecation, MVP
  update limitation), task numbering (T<NNN>), Git workflow
  (Branch Protection, squash merge, code review). Глобальные
  правила в `~/.claude/CLAUDE.md` применяются как есть; этот файл
  — только специфика репо.

### Changed

- **`TEMPLATE-*.md` → default names** в корне репо. После того как
  в T006 заготовки для derived переехали в
  `src/dreamteam/template/`, префикс `TEMPLATE-` стал избыточным —
  `BACKLOG.md` / `BOARD.md` / `CHANGELOG.md` / `DECISIONS.md` в
  корне репо теперь однозначно относятся к разработке самого
  `dreamteam`-пакета. Live references в README / pyproject /
  самих файлах обновлены; historical entries в CHANGELOG /
  DECISIONS / spec.md **не** правлены (immutable).

### Removed

- **`PROJECT.md` из шаблона** (T014, v1.1.0). Catch-all-документ,
  дублировавший README / BACKLOG / CHANGELOG / DECISIONS /
  pyproject. Удалён ради чёткого «один документ — одна роль»
  (см. ADR). Backward-compatible: existing derived проекты на
  v1.0.0 с PROJECT.md не затронуты, `dreamteam update` не удаляет
  файл.

### Notes

- **2026-05-14:** `dreamteam` v1.0.0 опубликован на PyPI как
  **`dreamteam-cli`** (имя `dreamteam` занято squatter-аккаунтом с
  2019, см. ADR в `DECISIONS.md`). Verify:
  `uvx --from dreamteam-cli dreamteam --version` → `dreamteam 1.0.0`.
  Следующий PyPI publish (1.1.0 / 1.2.0 / 1.3.0) — отложен;
  накопленные минор-bump-ы запакуются под `1.3.0` при следующем
  upload через `scripts/publish.sh`.

### Retrospective

- **Что зашло:**
  - **PyPI publish flow** (T010 + T011) прошёл за один сессионный
    проход. MIT License → `LICENSE` + PEP 639 в pyproject → ADR;
    `scripts/publish.sh` с `.secrets` family + twine validation +
    `uv publish` hybrid. На первой публикации обнаружили squatter
    `dreamteam` на PyPI с 2019 — оперативно решили
    `dreamteam-cli` именованием (ADR с rejected PEP 541 reclamation
    + alternative names), command name `dreamteam` сохранён через
    `[project.scripts]`.
  - **CI workflow (T015)** закрыл gap из T014 slip — failing test
    замержился в main без external CI. Теперь required status check
    блокирует ровно эту ситуацию. Branch Protection T001 +
    GH Actions T015 + Squash-only merge — три слоя защиты main.
  - **T013 multilang stacked PRs** работали хорошо: spec → Phase 1
    (~3000 строк bootstrap) → Phase 2 (3 строки CI step) → Phase 3
    (ADR + CHANGELOG + README + bump). Discrete review boundaries,
    нет «big-bang» PR.
  - **Catch-it-at-the-output паттерн** реально применился: я
    несколько раз останавливался по `FAILED` в выводе перед
    `git push`, успешно — slip T014-style случаев не повторилось.
  - **Frontmatter + hash-based CI guard** (T013) — простое и
    durable решение для drift problem. Pure stdlib + PyYAML,
    никаких сетевых зависимостей.
- **Что не зашло:**
  - **T014 slip:** failing test замержился в main до того, как CI
    встал. Lesson: CI должен быть впереди методики; вводить рутины
    проверки сразу при stacked-PR-фазах, не post-hoc.
  - **qodo monthly quota исчерпана** к концу ночной сессии T015 —
    PR без стороннего review. Заметили слишком поздно. T007
    (qodo replacement) остался в backlog с приоритетом «не очень
    срочно», но фактически стал «нужно решить, пока snapshot CI
    единственная защита».
  - **Stacked PR + `--delete-branch` auto-closes dependents** —
    свежий урок 2026-05-15. При merge T013 Phase 1 удалил
    `T013-multilang-phase1` ветку, которая была base для Phase 2
    PR — GitHub auto-closed его без возможности reopen, пришлось
    создавать replacement (#41). Memory entry добавлена в
    `~/.claude/projects/.../memory/feedback_stacked_pr_delete_branch.md`.
  - **Stale `PROJECT.md` reference в root README** прожил до Phase
    3 T013 — должен был быть починен ещё в T014. Lesson: при
    удалении файла grep по репо на его имя, не только по template
    структуре.
  - **`copier.Worker` остаётся deprecation warning** — internal
    API copier, используем для capture answers. Известный
    artifact; T009 (full update flow) может это исправить, но
    остаётся в backlog.
- **Правки методики:**
  - Memory entry «stacked PR + --delete-branch» добавлена,
    применяется во всех repos.
  - T007 (qodo replacement) — поднять приоритет до «следующий
    после T009».
  - T013 spec process (spec → clarify → analyze → 3 implementation
    phases) — успешный шаблон для будущих крупных фич; включить
    в `~/.claude/CLAUDE.md` как «образец крупной фичи» в случае
    review.

---

## [1.0.0] — 2026-05-14 — PyPI-distributed CLI architecture

Архитектурная переориентация: шаблон стал полноценным CLI-инструментом
`dreamteam` на PyPI, на смену GitHub Template Repository.

### Added

- **Python-package `dreamteam`** с Typer-based CLI (`init`,
  `update`, `--version`). Установка: `pip install dreamteam-cli` или
  `uvx dreamteam` (zero-install).
- **Команда `dreamteam init <path>`** создаёт чистый derived
  project одной командой — без 9 ручных шагов очистки. Внутри —
  `copier.run_copy` через `Worker` (для capture user answers).
- **Команда `dreamteam update`** re-applies template к существующему
  проекту с stored answers. MVP-режим: `overwrite=True`, без
  diff/merge — это known limitation (документировано в command
  docstring и в ADR).
- **`src/dreamteam/template/`** — copier-template как package-data:
  все методические файлы (CLAUDE/PROJECT/CONCEPT/DECISIONS/CHANGELOG/
  BACKLOG/BOARD/spec-template, hooks/pre-push, src/main.py, tests/
  test_main.py, pyproject.toml, .gitignore, README.md). Jinja-
  substitution в нужных файлах (`{{ project_name }}`, `{{
  project_description }}`, `{{ author_name }}`, `{{ author_email }}`).
- **`.copier-answers.yml`** в derived проекте — пишется вручную в
  init (copier не auto-create для unversioned local templates).
- **Integration tests** `tests/test_template.py` — e2e:
  `dreamteam init` → `uv sync` → ruff/format/mypy/pytest на
  результате. Маркер `integration`, opt-in. Self-validating template.

### Changed

- **Branch Protection на `main`** через GitHub-side enforcement
  (T001). На репозитории `vlakir/dreamteam` включена защита:
  `gh repo edit` оставил только Squash merge; `gh api .../branches/
  main/protection` блокирует прямой push (включая admin —
  `enforce_admins=true`). Acceptance verified: `git push origin
  main` напрямую → `GH006: Protected branch update failed`.
  ADR в `TEMPLATE-DECISIONS.md`.

### Notes

- В истории `main` остался artefact `49bbebe` («T001 smoke-test:
  this should be rejected by branch protection») — пустой коммит,
  попавший в main во время первого smoke-теста с
  `enforce_admins=false`. Не revert-ил, чтобы не нарушать своё
  же правило «не force-push в main». Lesson learned: проверять
  `enforce_admins` до smoke-теста, не после.

### Retrospective

- **Что зашло:**
  - **8-фазный план** T006 (с PR на каждую фазу) сработал хорошо.
    Большая архитектурная задача разбита на читаемые куски, каждый
    с self-review и acceptance. Если бы шло одним PR — обзор был бы
    невозможен.
  - **Copier как зрелый инструмент** — не пришлось писать template
    engine с нуля; jinja, prompts, `--defaults`, `copier-answers`
    готовы из коробки.
  - **Self-validating template** через integration test — generated
    project сам проходит 4-check suite, что гарантирует «дойдёт ли
    user до зелёного pre-push после `dreamteam init`» — гарантирует.
  - **Catch-it-at-the-text работает** — поймал у себя **два**
    noqa-temptation в одном Phase 4: subprocess.run с S603/S607 и
    local `import Worker` с PLC0415. Оба отрефакторил без noqa, до
    коммита.
- **Что не зашло:**
  - **`copier.run_update` не работает** с PyPI-distributed template
    (требует git-tracked template). MVP `dreamteam update` =
    `run_copy` с `overwrite=True`, без diff/merge. Это **известное
    ограничение**, документировано — но всё-таки не «full feature».
    Будущая задача (T009?): bundle template как git repo, или
    temp-clone-with-git approach.
  - **`Worker` from copier** помечен как internal API (deprecation
    warning). Используем потому что run_copy не возвращает answers,
    а нам нужен capture. Решение: hope copier expose public API
    later; если internal API ломается — переписать.
  - **PyPI publish не выполнен** — credentials у Разработчика, не у
    Claude. v1.0.0 build готов локально, документация для publish
    в TEMPLATE-DECISIONS, но actual upload отложен.
  - **License не определена** — README ссылается на TEMPLATE-BACKLOG
    как placeholder. Перед PyPI publish нужен license.
- **Правки методики (в `[Unreleased]` для v1.1):**
  - T009 (новая) — полноценный `dreamteam update` с diff/merge
    через bundled git-template или temp-clone.
  - T010 (новая) — выбрать и добавить license file.
  - T011 (новая) — actually publish to TestPyPI then PyPI.

---

## [0.2.0] — 2026-05-14 — Methodology consolidation

Зрелая инкарнация методики после первого цикла обкатки. Шаблон
получил полный pre-push контроль (4 проверки), формализованную
дисциплину планирования, immutable начальный draft проекта, и
чистое разделение мета-файлов шаблона от заготовок для derived
projects.

### Added

- **`CONCEPT.md` как immutable документ начального видения** (T004).
  Добавлена заготовка `CONCEPT.template.md` со структурой: Цель /
  Пользователь / Ключевая функциональность / Out of scope /
  Ограничения и догадки. После заполнения `CONCEPT.md` **не
  редактируется** — служит исторической точкой опоры. Текущее
  состояние ведётся в `PROJECT.md`; при кардинальной пере-концепции
  (rare, pivot) — `concepts/v2-...md` и далее. Введён **ритуал
  составления** через встречные вопросы Claude (по аналогии с
  `clarify` для спеки). Правило задокументировано в проектном
  `CLAUDE.md` (durable, с шагом в «Что прочитать в начале сессии»
  и отдельным разделом про ритуал) и в глобальном
  `~/.claude/CLAUDE.md`. В инструкцию «Как использовать» в README
  добавлен шаг «Заполнить `CONCEPT.md`» сразу после клонирования.

- **Формализация дисциплины планирования без Scrum-карго** (T003).
  Введены три правила-ритуала: (1) milestone-based versioning —
  переход `[Unreleased] → [N.M.0]` (формат Keep a Changelog, без
  `v`-префикса) по soft criterion «осмысленно завершено»
  (Разработчик решает, формальной метрики нет); (2) retrospective
  как секция `### Retrospective` внутри записи версии в CHANGELOG,
  формат «что зашло / что не зашло / правки методики»; (3)
  acceptance criteria обязательны для задач крупнее однострочной
  правки (уже было фактически, теперь явно). Не вводим:
  sprints/story points/velocity/burndown/daily standup. Правило
  задокументировано в проектном `CLAUDE.md` (durable) и в
  глобальном `~/.claude/CLAUDE.md`. В `CHANGELOG.md` (заготовка
  для derived projects) добавлен пример секции Retrospective как
  HTML-комментарий.
- **Обязательное тестирование через pytest** (T002). Добавлен стек
  `pytest` + `pytest-cov` + `pytest-asyncio` в dev-зависимости.
  Конфигурация в `pyproject.toml` (`[tool.pytest.ini_options]`,
  `[tool.coverage.run]`, `[tool.coverage.report]`). Coverage
  threshold ≥ 80% line coverage на `src/`, `--cov-fail-under=80`
  жёстко. Структура тестов: `tests/` в корне (в ruff `exclude`,
  pytest находит через `testpaths`). Pre-push контроль расширен
  до **четырёх** обязательных проверок: к `ruff check`,
  `ruff format --check`, `mypy` добавлен `uv run pytest`. В шаблон
  включён пример `tests/test_main.py` с покрытием функций
  `main.py` на 100%.
- **Разделение файлов шаблона: `TEMPLATE-*` префикс для меты,
  default names — для derived** (T005). Введён единый принцип:
  файлы, относящиеся **только к разработке самого шаблона**
  dreamteam (бэклог его задач, board, ADR, эволюция версий),
  получают префикс `TEMPLATE-`. Файлы без префикса — заготовки
  для derived projects. Создан `TEMPLATE-BACKLOG.md`,
  `TEMPLATE-BOARD.md`, `TEMPLATE-DECISIONS.md`. Файл
  `META-CHANGELOG.md` переименован в `TEMPLATE-CHANGELOG.md` для
  consistency. Накопленные в default-name файлах данные шаблона
  перенесены в `TEMPLATE-*` варианты; default-name файлы очищены
  до состояния «заготовка с примером для пользователя».
  `README.md` остаётся special case (github-driven, описывает сам
  шаблон) — exception задокументирован.

- **Правило нумерации задач `T<NNN>`** (PR #8). ID присваивается при
  создании; формула — `max(существующих T-ID в BOARD.md, BACKLOG.md
  и CHANGELOG.md) + 1`. Применение — в именах веток
  (`T<NNN>-<slug>`), заголовках PR (`T<NNN>: <title>`), папках спек
  (`specs/T<NNN>-<slug>/spec.md`). Методические PR (правки самих
  правил процесса) идут без `T`-ID — имена веток `rules/<slug>`,
  `meta/<slug>` и аналогичные.
- **Требование T-ID в записях `CHANGELOG.md`** (PR #8). Запись о
  релизе обязательно содержит T-ID завершённой задачи в скобках
  (`Added: Превью постов (T<NNN>).`). Без этого CHANGELOG перестаёт
  быть persistent-источником номеров и формула `max()` ломается на
  первой же ротации доски.

### Changed

- **`BOARD.md` / `BACKLOG.md` — единый источник истины для задач**
  (PR #6). Платформо-нативные issue-трекеры (GitHub Issues,
  GitLab Issues, GitFlic, и т.д.) не использовать без явного
  согласия Разработчика. Цель — не зависеть от хостинга: issues
  теряются при миграции, markdown-файлы переезжают вместе с git.
- **`.gitignore`: точечный игнор служебных файлов Claude Code**
  (PR #7). Добавлены `.claude/*.lock` (служебные lock-файлы
  scheduled-сессий) и `.claude/settings.local.json` (локальные
  per-machine permissions). Конвенция «шарить `.claude/` целиком»
  сохранена для содержательных артефактов: `commands/`, `agents/`,
  `hooks/`, `settings.json`.
- **Порядок шагов «Как использовать» в `README.md`**: разрушительные
  действия (`overwrite README.md`, `delete TEMPLATE-*.md`)
  переставлены в самый конец списка — иначе пользователь, идущий
  сверху вниз, терял оставшиеся инструкции вместе с перезаписанным
  README. (По qodo-замечанию на PR #5.)
- **`hooks/pre-push` теперь ссылается на `CLAUDE.md`**, а не на
  `README.md`. README шаблона перезаписывается в derived repos и
  не может служить durable-источником, CLAUDE.md — может. (По
  qodo-замечанию на PR #3.)

### Fixed

- **Унификация имени папок спек** в документации: 7 точек, оставшихся
  с `specs/NNN-*`, переведены на `specs/T<NNN>-*` (BOARD, BACKLOG,
  проектный CLAUDE, README, глобальный CLAUDE). (По qodo-замечанию
  на PR #8.)
- **Typography**: команды Branch Protection в записи **T001**
  `BOARD.md` перенесены из inline-backticks в fenced ```bash```
  блок — URL разрывался при переносе строки и при copy-paste
  превращался в нерабочий. (По qodo-замечанию на PR #8.)

### Retrospective

- **Что зашло:**
  - **qodo-review цикл** реально находил содержательные баги (3
    замечания на PR #1, 1 на PR #2, 1 на PR #3, 1 на PR #5, 3 на
    PR #8, 3 на PR #10, 3 на PR #11, 1 на PR #12, 3 на PR #13).
    Большинство — настоящие проблемы; в особенности ловил
    повторяющиеся slip-ы Claude.
  - **`TEMPLATE-*` split** (T005): шаблон стал ощутимо чище —
    derived users получают только default-name файлы без мусора
    мета-разработки.
  - **Autonomous overnight** mode сработал: 4 крупные задачи
    закрыты, каждая со self-review, все 4 проверки чистые,
    coverage 100%.
  - **Self-caught slip** в T002 (`# noqa: PLC0415` с локальным
    `import pytest`) — Claude поймал собственное нарушение до
    коммита впервые. Это знак, что повторение правила в auto-
    memory работает.
- **Что не зашло:**
  - **Повторяющиеся slip-ы Claude** на «`README` как канон» —
    qodo ловил эту ошибку на трёх PR подряд (#1, #2, #3) и потом
    ещё раз на PR #8. Auto-memory с правилом «catch-it-at-the-
    text» появилась только после третьего повтора — нужно было
    раньше.
  - **Inconsistency** в форматах между связанными правками
    (porядок шагов в README, версии `vN.0` vs `[N.M.0]`,
    `META-RETRO.md` vs `TEMPLATE-RETRO.md`) — несколько раз
    приходилось делать amend по qodo-замечаниям. Catch-it-at-
    the-text применимо ко всем формулировкам, не только к
    README.
  - **qodo monthly quota исчерпана** к концу ночной сессии
    (PR #14 — без стороннего review). Заметили слишком поздно
    для замены в той же сессии.
- **Правки методики (зафиксированы в [Unreleased] v0.3.0):**
  - `T006` — миграция на Copier, чтобы избавить derived projects
    от ручной чистки и поддерживать обновление методики через
    `copier update`.
  - `T007` — найти замену qodo-code-review (бесплатная или
    своя), чтобы вернуть «второй взгляд» на каждый PR.
  - **Catch-it-at-the-text** уже добавлено в auto-memory
    (PR #13 follow-up) — пересмотрено как универсальное правило
    для любых формулировок, не только про README.

---

## [0.1.0] — 2026-05-13 — Initial methodology bootstrap

Первая собранная версия шаблона. Включает базовую структуру файлов
и весь набор правил методики, выработанной в первом цикле обсуждений.

### Added

**Структура шаблона:**

- `README.md` — описание шаблона и методики.
- `README.template.md` — заготовка проектного README под перезапись.
- `CLAUDE.md` — проектные правила для Claude (самодостаточный свод
  правил Git workflow, ссылки на глобальный `~/.claude/CLAUDE.md` —
  опционально).
- `PROJECT.md`, `DECISIONS.md`, `CHANGELOG.md`, `BACKLOG.md`,
  `BOARD.md` — артефакты методики для проекта.
- `specs/spec-template.md` — шаблон спецификации крупной фичи.
- `META-CHANGELOG.md` — журнал эволюции шаблона (с v0.1.0).
  В T005 (см. `[Unreleased]` выше) переименован в
  `TEMPLATE-CHANGELOG.md` для consistency с прочими `TEMPLATE-*`.

**Python-стек:**

- `pyproject.toml` (PEP 621), `uv.lock`.
- Python 3.14+ как целевая версия.
- `uv` как менеджер зависимостей и окружений (отвергнут `poetry`).
- `ruff` (`select = ["ALL"]` с фиксированным `ignore`-листом) и
  `mypy` как обязательные линтеры.
- `src/main.py` — entry point с CLI-style разделением логов
  (DEBUG/INFO → stdout, WARNING+ → stderr).
- Корень исходников — всегда `src/`.

**Правила процесса:**

- Scope discipline — главное правило, защита от расползания задачи.
- Ритуал крупных фич: Spec → Clarify → Plan → Analyze → Implement.
- Pre-push контроль: `ruff check`, `ruff format --check`, `mypy` — 0
  ошибок обязательно.
- Импорты только на верхнем уровне модуля (PLC0415 НЕ в ignore).
- В публичных артефактах — нейтральные роли «Разработчик» и
  «Claude», без личных имён.
- Ответственность за соблюдение конвенций — на Claude (cам
  представляет методику в начале нового проекта, поднимает флаг
  при предложениях, нарушающих правила).

**Git workflow:**

- Прямой push в `main`/`master` запрещён — только через feature-ветку
  и PR.
- Один PR — один коммит (squash перед merge).
- Code review каждого PR (по умолчанию — Claude, иногда —
  Разработчик).
- Сторонние ревью (qodo, GitGuardian и т.п.) не игнорировать —
  читать, анализировать, обсуждать.
- Универсальная реализация — локальный squash; платформо-специфичные
  ускорители (GitHub «Squash and merge», GitLab аналог) — опциональны.
- `hooks/pre-push` — готовый скрипт для локальной защиты `main`/
  `master`.

**ADR в `DECISIONS.md` шаблона:**

1. CLI-style logging split.
2. `src/` как корень исходников.
3. `uv` как менеджер зависимостей.

### Notes

- v0.1.0 собрана и опубликована как GitHub Template Repository
  (`Use this template` доступен).
- Открытый Issue: #4 «Реализовать защиту main через Branch Protection
  Rules» (платформо-специфичная защита, не часть текущей версии).
