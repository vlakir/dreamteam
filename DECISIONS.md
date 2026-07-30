# Architecture decisions (dreamteam package)

Архитектурные решения `dreamteam`-пакета (scaffolding CLI на Copier),
ADR-Lite. В derived projects — свой `DECISIONS.md` (из
`src/dreamteam/template/`), они не пересекаются.

Формат и принципы: решения фиксируются и не редактируются после
принятия; новый блок при пересмотре. Исторические упоминания
`TEMPLATE-*.md` в старых ADR ниже **не правлены** — immutable history.

---

## Решения

<!-- Новые решения добавляются сюда, новые сверху. -->

### 2026-07-30 — T038: `dt task find`, веса полей, морфология по общему префиксу

- **Контекст.** T038 — поиск задачи по человеческой фразе (`dt task find`),
  точка входа E1 (карточка T006, `deps: T034`). Агент-сценарий §326: от
  свободной фразы к ID, назвать кандидата, дождаться подтверждения. Без
  эмбеддингов и внешних сервисов. Спека — `specs/T038-task-find/spec.md`.
- **Решение 1 — `find_tasks` в `dt/tasks.py` (typer-free, git-free).**
  Чистая функция рядом с `load_all_tasks`/`check_tasks`; Typer-обёртка —
  команда `find` в `task_cli.py` под под-приложением `task`. Токенизация
  `re.findall(r'\w+', text.casefold())` (Unicode-aware, кириллица), один
  токенайзер для запроса и всех полей.
- **Решение 2 — морфология-толерантный матч по общему префиксу (опросник).**
  Токены совпадают, если длина общего префикса (`os.path.commonprefix`) ≥ 4;
  токены короче 4 — только точное равенство (чтобы «cli» не ловил «client»).
  Так `«курсор»~«курсора»`, `«полноэкранный»~«полноэкранном»` — пример
  дизайна §326 работает без стеммера. Компромисс recall↑/precision↓ уместен:
  агент называет кандидата, человек подтверждает. Отвергнуты «точное
  совпадение» (пропускает словоформы) и «подстрока» (не ловит разные
  окончания).
- **Решение 3 — веса полей и статус-множитель, max-по-полю.** `title=3 >
  tags=2 = branch=2 > body=1`; статус active (`todo`/`doing`/`review`) ×1.0,
  иначе (`done`/`dropped`) ×0.5. Каждый query-токен даёт **максимальный**
  вес поля, где попал (не сумму по полям) — иначе длинное тело с повтором
  перебивало бы заголовок. Сортировка `score`→`updated`→ID. `dropped` из
  выдачи не исключаются (найти отменённую полезно), но ×0.5 держит их ниже.

### 2026-07-30 — T037: `dt board`, модель доски отдельной функцией, рендер секциями

- **Контекст.** T037 — текстовое представление kanban-доски (`dt board`),
  точка входа E1 (карточка T005, `deps: T034`). Ключевое требование дизайна
  (§604): сборка модели вынесена в отдельную функцию, переиспользуемую
  графической доской E10. Спека — `specs/T037-board/spec.md`.
- **Решение 1 — модель в `dt/board.py`, отделена от форматирования.**
  `board_model(store)` — чистая (git-free, typer-free) функция: `load_all_tasks`
  → отсев `dropped` → сортировка по `updated` убыв. (None — в конец, tiebreak
  по ID); возвращает плоский список `Task`. `board_columns(model)` группирует
  по статусу в порядке потока `todo→doing→review→done`. Отсев `dropped` — в
  одной точке (`board_model`), чтобы E10 не повторял правило. Typer-обёртка —
  `board_cli.py`.
  - *Альтернативы:* грузить+фильтровать прямо в CLI (E10 продублировал бы
    правило dropped и сортировку); класть в `dt/tasks.py` (board — отдельная
    презентационная подсистема, как worktrees).
- **Решение 2 — рендер секциями столбиком, не side-by-side (опросник).**
  Каждый статус — блок сверху вниз (`todo→doing→review→done`), внутри задачи
  по `updated` убыв. Отклонение от буквы дизайна («колонки в терминал»):
  side-by-side обрезает длинные RU-заголовки и ломается на узком терминале.
  `--json` = `{columns: {...}}` даёт машинную структуру. Пустые колонки
  показываются заголовком (стабильная форма доски).
- **Решение 3 — `dt board` как top-level команда, не sub-app.** Регистрируется
  `app.command('board')` (не `add_typer`): у `dt board` пока нет подкоманд.
  `dt board serve` придёт в E10 — тогда возможна конверсия в группу с
  `invoke_without_command`. Сейчас вводить группу преждевременно (scope).

### 2026-07-30 — T036: `dt worktree`, вычисляемый путь, консервативный prune

- **Контекст.** T036 — размещение и жизненный цикл рабочих копий задач
  (`dt worktree path/root/list/prune`), четвёртая задача E1 (карточка T004,
  `deps: T033`). Даёт агенту источник пути до worktree задачи (лечит
  подстановку основной копии, design §E12) и безопасную уборку. Спека —
  `specs/T036-worktrees/spec.md`.
- **Решение 1 — трёхслойное разбиение по образцу T034/T035.** Чистое ядро
  `dt/worktrees.py` (classify_arg, вычисление пути, сопоставление
  worktree↔задача, планировщик prune) — **typer-free И git-free**: git-данные
  (`git worktree list --porcelain`, `merge-base --is-ancestor`,
  `status --porcelain`, автодетект base, `worktree remove`, `branch -d`)
  добываются в `dt/paths.py` (продолжение линии `git_context` из T035) и
  подаются в ядро параметрами. Обёртки — новый `src/dreamteam/worktree_cli.py`,
  монтируется `add_typer` рядом с `task_app`.
  - *Альтернативы:* git-вызовы в ядре (размыло бы git-free инвариант,
    усложнило тесты — прогонять реальный git на каждый юнит); команды в
    `task_cli.py` (worktree — отдельная подсистема, не операции над записями).
- **Решение 2 — `path` auto-detect аргумента (согласовано опросником).**
  Точный `^T[0-9]{3,}$` → task ID (читаем поле `branch`, ошибка если пусто —
  ветку выставляет `dt task start`, T039); иначе → literal branch. Держит
  генерацию slug в T039 (scope) и одновременно делает `path` полезной до его
  появления. Фактический путь — из `git worktree list` по ветке, иначе
  вычисленный `$DT_HOME/worktrees/<branch>` (нигде не хранится).
- **Решение 3 — prune: managed-only, слитую ветку удаляем, merged-guard
  консервативен (опросник + Analyze).** `prune` трогает **только** worktree
  под `$DT_HOME/worktrees/` (ручной worktree в другом месте не сносится);
  при уборке удаляет worktree **и** слитую локальную ветку (`git branch -d`,
  safe). Слитость — `git merge-base --is-ancestor <branch> <base>` против
  **локальной** base (автодетект `origin/HEAD` → `main`/`master`; офлайн-
  дружелюбно). Все три guard (задача в `done`/`dropped`, ветка слита, дерево
  чисто) обязательны; провал — пропуск с перечислением **всех** причин,
  exit 0.
  - *Известное ограничение (Analyze A2):* squash-merge не детектируется
    `--is-ancestor` (коммиты ветки не предки base) → prune консервативно
    считает такую ветку «не слитой» и **пропускает**. Безопасный отказ:
    неслитую работу не теряем ценой того, что после squash-merge worktree
    убирается вручную (ритуал методики и так это делает). Точная squash-aware
    детекция — возможный follow-up, вынесен из scope T036.
- **Note — «осиротевшие».** `list` выделяет managed-worktree без задачи;
  `prune` их пропускает (статус done/dropped подтвердить нельзя). Посторонние
  worktree вне managed-каталога (основная копия, ручные) осиротевшими не
  помечаются — легитимны.

### 2026-07-30 — T035: `check`/`ready`, git-осведомлённость spec-проверки

- **Контекст.** T035 — валидация целостности графа задач (`dt task check`) и
  готовность к работе (`dt task ready`), третья задача E1 поверх операций
  T034. Спека — `specs/T035-task-validation/spec.md`; дизайн — раздел E1
  «Валидация» и карточка T003.
- **Решение 1 — git-контекст входит в `check_tasks` параметром, не
  добывается внутри.** Чистый слой `dt/tasks.py` остаётся не только
  typer-free, но и **git-free**: `check_tasks(store, *, repo_root,
  current_branch)` принимает git-контекст извне. Добывает его
  git-осведомлённый `dt/paths.py` — helper `git_context()` (best-effort
  `(repo_toplevel, current_branch)`, `(None, None)` вне репозитория,
  detached HEAD → ветка `None`). CLI подставляет, тесты передают напрямую
  (детерминизм, без монтирования git).
  - *Альтернативы:* шелить git прямо в `tasks.py` — размыло бы инвариант
    «чистый слой без внешних вызовов», усложнило тесты.
- **Решение 2 — spec-проверка мягкая с эскалацией на своей ветке.**
  Отсутствие spec-файла — WARNING (спека может жить только на ветке своей
  задачи); ESCALATE в ERROR, только если `task.branch` == текущая
  выгруженная ветка (файл обязан быть здесь). Путь резолвится относительно
  **текущей** рабочей копии (`show-toplevel`), не main. Без git-контекста
  (`repo_root is None`) проверка пропускается — путь не резолвится.
  - *Обоснование:* прямое следование дизайну §199 (критерий приёмки E1).
    Ложная тревога на чужой ветке (спека законно отсутствует) недопустима,
    но пропущенная спека на своей — реальная ошибка.
- **Решение 3 — подключение в pre-push = CI-шаг напрямую.** `uv run dt task
  check` добавлен в `ci.yml` рядом с `translate_check` (критерий приёмки 5).
  Отдельный wrapper-скрипт (как `scripts/translate_check.py`) не вводим —
  команда сама и есть проверка, обёртка дублировала бы CLI.
- **Note — `blocks`-целостность покрыта проверкой `deps`.** Поле `blocks`
  в записи не хранится (T034 транслирует `--blocks` в `deps` цели), поэтому
  отдельной ветки валидации `blocks` нет — она эквивалентна проверке `deps`.
- **Note — микро-нит валидатора ID свёрнут сюда.** `_ID_RE` переведён с
  `\d` на `[0-9]` (ASCII-цифры; unicode-цифры вроде `T۰۰۱` больше не дают
  валидный-но-странный filename). Не security-фикс (path-traversal закрыт
  ещё в T034), а робастность; согласовано как fold в T035, не отдельный PR.

### 2026-07-30 — T034: CLI-слой `dt task`, выдача ID через `O_EXCL`

- **Контекст.** T034 — первые пользовательские команды оперативного слоя
  (`dt task new/show/move/split`) поверх фундамента T033. Закладывает паттерн,
  которому последуют остальные `dt`-команды E1 (T035–T042). Спека —
  `specs/T034-task-ops/spec.md`.
- **Решение 1 — чистый слой операций в `dt/tasks.py`, Typer-обёртки в
  `task_cli.py`.** Логика (`allocate_id`/`new_task`/`move_task`/`split_task`/
  `show_task`) живёт в `dt/` (typer-free — импортируема из хуков/statusline);
  Typer-команды — в отдельном `src/dreamteam/task_cli.py`, подключены к
  общему `app` через `add_typer`. Команды доступны и как `dt task …`, и как
  `dreamteam task …` (оба console-script указывают на один `app`).
  - *Альтернативы:* Typer-команды прямо в `dt/` (нарушило бы typer-free
    инвариант T033); в разбухшем `cli.py` (смешивало бы scaffolding и
    оперативный слой — разные подсистемы). Отдельный модуль — точка роста
    для T035+ без цикла импорта (`task_cli` импортирует только `dt/*`).
- **Решение 2 — атомарная выдача ID: `counter` + `O_CREAT|O_EXCL`.** Файл
  записи `T<NNN>.md`, создаваемый с `O_EXCL`, — арбитр гонки: два worktree
  стартуют от общего `counter`, но номер достаётся лишь одному, проигравший
  берёт следующий. `counter` — water-mark-подсказка (`max(current, n)`, назад
  не откатывается), не источник истины. Коллизии номеров невозможны по
  построению (хранилище одно на репозиторий).
  - *Альтернативы:* счётчик с flock (лишняя зависимость от блокировок,
    Windows-деградация); UUID вместо номеров (нечитаемо, ломает конвенцию
    `T<NNN>`).
- **Решение 3 — валидация ссылок до выделения ID; `--blocks` мутирует цель.**
  `new` проверяет существование всех `--deps`/`--parent`/`--blocks` **до**
  `allocate_id` — битая ссылка не оставляет «дыру» в нумерации (hard error).
  `--blocks B` означает «новая задача блокирует B» → B получает dep на новую
  и бампит `updated` (единственная в T034 операция над чужой записью,
  предписана дизайном E9.2; идемпотентна).
  - *Альтернативы:* soft-режим (создавать с висячей ссылкой, ловить в
    `check` T035) — отвергнут: store единственный источник истины, опечатки
    ловим сразу.
- **Note.** Пустой store самого dreamteam → `dt task new` выдал бы `T001`,
  конфликтуя с markdown-T-ID репозитория. Осознанно: реконсиляция — `migrate`
  (T042, точка невозврата). До неё T034 обкатывается на изолированных store,
  задача T034 ведётся в markdown как обычно.

### 2026-07-30 — T033: подпакет `dt/`, pydantic-модель задачи, ruff-конфиг для pydantic-аннотаций

- **Контекст.** T033 — фундамент эпика E1 (оперативный слой состояния):
  резолв `$DT_HOME`, ленивое создание хранилища, `<slug>` рабочей копии,
  модель записи задачи с round-trip, сохраняющим неизвестные поля. Первый
  код новой арки; закладывает соглашения, на которые опрётся весь E1
  (T034–T056). Спека — `specs/T033-store-core/spec.md`.
- **Решение 1 — код оперативного слоя в подпакете `src/dreamteam/dt/`.**
  `dt/paths.py` (пути + создание), `dt/model.py` (модель + I/O); позже
  `dt/commands/`. Отделено от scaffolding-CLI `cli.py` (init/update/apply):
  это разные подсистемы, а слой будет расти (`task`/`worktree`/`board`/
  `context`/`resume`/`run`). `dt/` не импортирует copier/typer — остаётся
  лёгким и импортируемым из хуков/statusline.
  - *Альтернативы:* плоские модули рядом с `cli.py` (смешивало бы две
    подсистемы по мере роста E1); всё внутри `cli.py` (не масштабируется —
    `cli.py` уже большой).
- **Решение 2 — модель записи на `pydantic` (новая runtime-зависимость).**
  `Task(BaseModel)` с `extra='allow'` даёт бесплатное сохранение
  неизвестных полей frontmatter (forward-compat формата) и валидацию
  `status`/типов. Осознанно принята зависимость `pydantic>=2.9` вопреки
  минимализму пакета (до этого — только copier/typer/pyyaml).
  - *Альтернативы:* `@dataclass` + extra-bag (без новой зависимости, но
    руками валидация и extra); голый dict round-trip (теряем типизацию,
    на которую обопрётся E1). Выбор pydantic — сознательное решение
    Разработчика; триггер пересмотра: если вес зависимости во frozen/CLI
    начнёт мешать.
- **Решение 3 — `[tool.ruff.lint.flake8-type-checking]
  runtime-evaluated-base-classes = ["pydantic.BaseModel"]`.** pydantic
  резолвит аннотации полей модели в рантайме, поэтому импорты, на которые
  ссылаются поля (`datetime` в `dt/model.py`), обязаны жить на уровне
  модуля. Без этой настройки автофикс ruff (TC003) переносит `datetime`
  в `TYPE_CHECKING`-блок и **ломает** сборку модели
  (`PydanticUserError: not fully defined`). Это конфигурация корректности
  под семантику pydantic, а не подавление — стандартная интеграция
  ruff+pydantic. `ignore`/`per-file-ignores` не расширялись.
- **Границы T033.** Никаких Typer-команд (T034+), счётчика/`O_EXCL`
  (T034), `git worktree list`-резолва (T036), валидации целостности
  (T035), миграции (T042) — только библиотечный слой + юнит-тесты
  (24 теста, coverage `dt/` ≈ 100%/97%).

### 2026-07-30 — Разворот к оперативному слою состояния: дорожная карта v0.3 → v1.0 (T033–T056)

- **Контекст.** Анализ обзора «Армия в терминале»
  (habr.com/ru/articles/1063558) применительно к `vlakir/dreamteam`.
  Пакет сегодня — тонкий Copier-CLI (init/update/apply). Задачи и доска
  ведутся markdown-канбаном (BOARD/BACKLOG), который: агент ненадёжно
  парсит; конфликтует при параллельной правке в разных worktree; не даёт
  машиночитаемого ответа «что брать в работу»; существует в каждом
  worktree в своей редакции, поэтому картина параллельной работы нигде
  не собирается целиком. Полный разбор и декомпозиция —
  **`specs/roadmap-v0.3-v1.0/design.md`**.
- **Решение (архитектурный разворот, отдельной аркой задач, не «заодно»).**
  Ввести **оперативный слой состояния** в каталоге-соседе
  `<repo>.dt/` (`$DT_HOME`, override `DT_HOME`), вне git: записи задач
  (frontmatter + markdown), счётчик ID (`O_EXCL`), реестр сессий
  (файл-на-задачу), привязки `by-worktree/<slug>/`. Долговременная
  память (BACKLOG/CHANGELOG/DECISIONS/CONCEPT/specs) остаётся в git.
  Поверхность `dt task/worktree/board/context/resume/run` +
  SessionStart/PreCompact-хуки + statusline. Целевой harness — **только
  Claude Code**, нейтральность к вендору сознательно отдана; методика
  как текст от этого не зависит (страховка — секции-файлы E2).
- **Ключевые под-решения** (каждое — с триггером пересмотра, §5.3
  дизайн-документа):
  - **BOARD.md исключается из git** — версионируемый снимок волатильных
    данных; заменяется `dt board` (текст) и `dt board serve` (проекция).
  - **`<repo>.dt/` — каталог-сосед**, не внутри `.git/`, не внутри репо,
    не в общемашинном каталоге (обоснование — 1.6 дизайн-документа).
  - **Языки методики сокращаются до `ru` + `en`** (E2); триггер
    возврата — появление пользователей, которым нужны остальные.
  - **`layout=workspace`** влияет только на инструментальный слой; второй
    методики не порождает.
  - **Графическая доска — чистая проекция** `$DT_STORE/tasks/`, не
    диспетчер; не знает о процессах и не запускает их (anti-scope, E10).
  - **CI-брифинг (E5.2), MCP (E7), метрики (E8) — отложены** до факта
    потребности.
- **Anti-scope (сознательно не делаем).** Диспетчер сессий; своя
  песочница/runtime; meta-harness над несколькими агентами; облачный
  сервис/демон; автономный «правь пока CI не позеленеет» без человека;
  абстракция над системами сборки (профили npm/cargo/go); заявления об
  ускорении без замера.
- **Альтернативы.** Beads-подобная БД + демон + авто-извлечение задач —
  отвергнуто: plain files достаточно, демон противоречит anti-scope.
  Состояние в git — отвергнуто: конфликты слияния на волатильных данных.
  Нейтральность к вендору через слой абстракции — отвергнуто: методика
  насквозь инструментальна, абстракция дала бы вторую систему, а не
  чистую методику.
- **Внедрение и откат.** Догфудинг на самом dreamteam, без формального
  пилота. Откат дёшев: `dt state export` + генерация BOARD.md обратно —
  именно потому, что долговременный слой лежит в git отдельно.
- **Нумерация.** Локальные T001–T024 дизайн-документа → репозиторные
  T033–T056 (`+32`; `max()` был T032, ID не переиспользуются). Таблица
  соответствия и `deps` — в `BACKLOG.md`.
- **Триггер пересмотра всей арки:** смена основного harness обесценивает
  интеграционный слой (хуки/statusline/slash/agents); методика-как-текст
  уцелеет, второй harness — это адаптер поверх секций, а не разбор
  монолита.

### 2026-07-30 — Мьютекс-обёртка тяжёлых тест-прогонов + лёгкий дефолт в шаблоне (T031)

- **Контекст:** derived-проекты по нашей методике ведут несколько задач
  параллельно, каждую в своём `git worktree` на одной машине (T030).
  Общий ресурс — оперативная память: полный / coverage-прогон держит
  заметный RSS, и два-три одновременно (рядом с тяжёлой IDE) стекаются
  в **OOM / зависание** (ловили на реальной 16-ГБ машине, опыт `calque`
  T168/T169). До T031 у сгенерённого проекта не было дисциплины «не
  стекать тяжёлые прогоны», а дефолтный `pytest` тащил coverage-трассировщик
  (лишний RSS/CPU) на каждой локальной итерации.
- **Решение (три части, самодостаточно в derived-проекте):**
  1. **Мьютекс-обёртка** `src/dreamteam/template/scripts/pytest-guard.sh` —
     drop-in префикс к прогону, сериализует тяжёлые прогоны между ВСЕМИ
     worktree через общий per-user `flock`-лок
     (`${TMPDIR:-/tmp}/{{ project_name }}-pytest-<uid>.lock`, concurrency
     1, блокирующее ожидание). Раннер подставляется по `package_manager`
     (Jinja `{{ pm_run }}pytest "$@"`), не хардкодом.
     Сериализуется только запуск — код и незакоммиченное состояние сессий
     не трогаются.
  2. **Вынос coverage из дефолтного `addopts`** (`template/pyproject.toml`):
     дефолтный `pytest` — лёгкий (`-q --tb=short`); порог ≥ 80% на `src/`
     держится **явной командой** через обёртку в pre-push-гейте (шаг 4) и
     CI. Порог не ослаблен — только вынесен из дефолта.
  3. **Правило в генерируемом `CLAUDE.md`** (source `ru` + re-bootstrap
     `en/fr/de/zh`): тяжёлый / coverage / pre-push-прогон — через обёртку;
     точечный однофайловый — напрямую; CI — напрямую.
- **Обобщения (НЕ тащим calque-специфику):** нейтральные термины;
  раннер — через `package_manager`, не завязка на `uv`; **опциональный**
  mem-cap `PYTEST_GUARD_MEM_MAX` (systemd-run cgroup на Linux, no-op вне
  Linux/systemd) вынесен как opt-in (по умолчанию выключен → обёртка =
  чистый мьютекс); **кроссплатформенность**: без `flock` (Windows)
  обёртка деградирует в прямой прогон с одной строкой-уведомлением, не
  падает. Qt/PySide-специфика T168 (`gc.disable()` и пр.) сознательно не
  переносилась.
- **Альтернативы:**
  - **Pure-Python обёртка** (кроссплатформенный dir-lock на stdlib) —
    отвергнута: `flock` — правильный инструмент, обкатан на `calque`;
    Python-мьютекс с поллингом тянет stale-lock edge-cases и попадает под
    ruff/mypy. bash + graceful degradation проще и покрывает целевой
    (Linux) сценарий.
  - **Оставить coverage в дефолте** — отвергнута: трассировщик раздувает
    RSS ровно там, где идёт частая локальная итерация; дублирует
    CI-проверку.
  - **Hard-fail без `flock`** вместо no-op — отвергнута: ломала бы
    Windows-derived-проекты на ровном месте.
- **Последствия:** derived-проект из коробки получает `scripts/pytest-guard.sh`
  (executable) + самодостаточный раздел «Тяжёлые тест-прогоны — через
  мьютекс-обёртку» в проектном `CLAUDE.md`. Гейт 4 и цепочка pre-push
  переписаны на обёртку. Инвариант закреплён интеграционно:
  `test_template` гонит обёртку с coverage на сгенерённом проекте,
  `test_multilang` проверяет наличие + executable во всех 5 языках. ADR
  только documentation/скрипт — структура рендер-пайплайна не менялась.
  Релиз — MINOR (новый шаблонный файл + правило).

### 2026-07-30 — `CPY001` в `ignore`-листе шаблона (T032)

- **Контекст:** свежий `ruff` вывел правило `CPY001` (flake8-copyright,
  «Missing copyright notice at top of file») из preview в стабильный
  набор, а шаблон использует `select = ["ALL"]`. В результате
  **каждый** сгенерённый `dreamteam init` проект стал падать на своём же
  pre-push `ruff check .` — единственной ошибкой `CPY001` на
  `src/main.py`. Integration-тесты `test_template` / `test_multilang`
  (×5 языков) покраснели. Регресс чисто от bump'а `ruff`, не от кода.
- **Решение:** добавить `CPY001` в `[tool.ruff.lint] ignore` шаблона.
- **Почему ignore, а не copyright-нотис:** личные проекты Разработчика
  (целевая аудитория шаблона) не ведут per-file copyright-заголовки;
  требовать их «из коробки» — шум, а не польза. Настройка
  `[tool.ruff.lint.flake8-copyright]` с обязательным нотисом навязала бы
  boilerplate в каждый файл каждого derived-проекта.
- **Альтернативы:** (1) конфиг `flake8-copyright` с нотисом — отвергнут
  как навязывание boilerplate; (2) точечный `# noqa` в шаблонном
  `src/main.py` — отвергнут (per-file noqa против политики, и не
  покрывает будущие файлы derived-проекта).
- **Инвариант:** политика `select = ["ALL"]` + точечный `ignore`
  сохранена; `CPY001` — очередное осознанное исключение в общем ряду.

### 2026-07-06 — `dreamteam update` через `git merge-file`, а не `copier run_update` (T029)

- **Контекст:** T028 (снизу) выпущен в 1.6.1, но багрепорт вскрыл, что
  он лечил не тот дефект. Пока `dreamteam update` вообще запускает
  copier `run_update` **на живом репозитории**, остаются два фатальных
  бага: (1) copier по ходу апдейта пишет в `.git/objects/info/commit-graph`
  (git создаёт его read-only `0444` при штатном maintenance) и падает с
  `PermissionError` — snapshot/restore `.git` из T028 этого не
  предотвращает; (2) крэш случается **после** того, как copier уже
  переписал файлы рабочего дерева, а `finally` восстанавливает только
  `.git` — дерево остаётся разгромленным (реальный `src/main.py`
  заменён шаблонной заглушкой) без отката и без предупреждения. Корень
  обоих — сам факт прогона `run_update` на настоящем репо.
- **Решение:** убрать `run_update` из update-пути полностью. Трёхсторонний
  merge делаем сами через **`git merge-file`** — штатный merge-движок git:
  рендерим шаблон на **базовой** версии (`_commit`) и на **текущей** в
  throwaway temp-папки (только `run_copy` — та же безопасная операция,
  что и `init`), затем по каждому template-managed файлу
  `git merge-file -p ours base theirs` пишет слитый результат с
  git-style конфликт-маркерами. Весь merge считается в temp и в память,
  и применяется к рабочему дереву **только** после полного успеха
  (атомарность на дереве). `.git` пользователя **не читается и не
  пишется вообще** — история/ветка/remotes/config сохраняются
  by construction, а read-only `commit-graph` физически недостижим
  (`.git` исключён из набора файлов через `_relfiles`).
- **Ревизия T028 и T009:** T028-ADR отверг «свой overlay-merge» по двум
  причинам — «потеря конфликт-маркеров» и «большой объём». Обе оказались
  ложными: `git merge-file` **даёт** стандартные маркеры (и точнее
  copier — они ложатся ровно на изменённую строку, а не на Jinja-строку,
  см. quirk в T009-ADR), а код компактен (`_plan_merge` + `_merge_file`,
  ~60 строк). Поэтому T029 отменяет snapshot/restore `.git` из T028 и
  `run_update`-путь из T009 целиком (удалены `_copier_merge_inplace`,
  `_merge_inplace_full`, `_restore_git`, monkeypatch
  `worker.subproject.last_answers`).
- **Альтернативы:**
  - **Оставить copier `run_update`, но запретить ему `.git/**` +
    добавить откат дерева** — отвергли: лечит симптом (commit-graph), не
    корень; откат дерева повторяет хрупкость T028 (нужен снапшот всего
    дерева), а деструктивные git-мутации copier остаются.
  - **`merge3` (pure-Python PyPI)** — отвергли (как и в T009): лишняя
    зависимость, менее обкатано, чем `git merge-file`; git и так уже
    hard-требование update-пути.
  - **Требовать git-репо только как техническую нужду** — merge
    `git merge-file` в git-репозитории **не нуждается**. Но требование
    оставили как **safety-net**: запись в дерево обратима через
    `git restore`, только если проект git-tracked. Сообщение ошибки
    переписано с «нужно для merge» на «нужно для recovery».
- **Последствия:** `update` больше не может испортить ни `.git`, ни (при
  крэше) рабочее дерево. Стоимость — 2 рендера + 1 клон бандла на апдейт
  (~3–5 c). `--dry-run` упростился (merge и так в temp — preview больше
  не нужно git-init'ить). Инвариант закреплён регрессом
  `test_update_preserves_user_source_and_readonly_commit_graph` (real
  bundle: пользовательский `src/main.py` + read-only `commit-graph`);
  git-safety T028-регресс `test_update_preserves_target_git_state`
  проходит тем более (git не трогается вовсе). Релиз — PATCH.

### 2026-07-06 — `dreamteam update` не трогает git пользователя: snapshot/restore `.git` (T028)

- **Контекст:** багрепорт (severity High, потеря данных). `dreamteam
  update` через copier `run_update` работает прямо на репозитории
  проекта; copier рендерит клон бандла как **local git-repo template** и
  по ходу мутирует git субпроекта — переписывает `origin` на временный
  клон (потом удаляемый), двигает ветку на снапшот шаблона, оставляет
  detached HEAD, конвертирует в partial clone. Реальный URL remote и
  указатель на историю теряются. Ирония: методика запрещает прямые
  мутации `main`, а апдейт нарушал это радикальнее всего.
- **Решение:** снапшотить весь `.git` целевого репо во временную папку
  на том же ФС **до** merge и восстанавливать **после** (в `finally`).
  copier по-прежнему бежит на реальном репо, но его мутации git
  откатываются. Слитые файлы остаются в рабочем дереве незакоммиченным
  diff'ом. Восстановление — `rmtree(.git)` + `move(backup → .git)`
  (rename на том же ФС).
- **Альтернативы:**
  - **Sandbox + overlay** (merge на throwaway-копии рабочего дерева,
    файлы обратно) — отвергли: copier'у для diff-применения нужна
    **настоящая git-история** субпроекта; свежий single-commit git
    ломается на полнофайловых конфликтах (`git checkout` pathspec
    error). Реальный репо такой историей обладает — на нём copier
    отрабатывает штатно.
  - **Транзакция на refs/config** (снять и восстановить только HEAD,
    ветку, remotes, partial-clone-ключи) — отвергли: whack-a-mole,
    copier может тронуть что-то ещё; полный снапшот `.git` бронебойнее.
  - **Заменить `run_update` своим overlay-мерджем** — отвергли: потеря
    качества three-way merge (конфликт-маркеры), большой объём.
- **Последствия:** после `update` — HEAD/ветка/remotes/config
  байт-в-байт как были; изменения видны как uncommitted diff (юзер
  ревьюит и коммитит). Плата — копия `.git` на время апдейта (для
  крупного репо — заметно, но корректность важнее). Инвариант закреплён
  регрессом `test_update_preserves_target_git_state` (было пусто: старые
  update-тесты не имели `origin` и не проверяли git-состояние — поэтому
  баг и проскочил). Релиз — PATCH 1.6.1.

### 2026-07-05 — Роли команды: Архитектор (субагент) + Дизайнер (MCP) (T026)

- **Контекст:** каждый derived-проект должен получать переиспользуемый
  контур сотрудничества поверх методики — лид (сессия Claude Code) +
  read-only Архитектор + внешний Дизайнер (Claude Design). Требование:
  фича подхватывается на старых проектах по `dreamteam update` без
  ручных шагов и без конфликтов на нетронутых файлах. Полная спека —
  `specs/T026-team-roles/spec.md`.
- **Решение:**
  - Роли поставляются шаблоном **по умолчанию** (без copier-флагов
    `include_*`); выбор использования — runtime лида, не build-time.
  - **Архитектор** — субагент `.claude/agents/architect.md` (авто-
    дискавери Claude Code, read-only Read/Glob/Grep). **Дизайнер** —
    прямой user-scope MCP, не оборачивается в субагент.
  - Источник истины ролей — файлы методики проекта (`DECISIONS.md`,
    `specs/`, …). Внешняя память допустима как зеркало, но не как
    замена канона.
  - **Рендер шапка+тело.** Функциональный frontmatter субагента
    собирается из данных, переводимое тело — partial под `_exclude`
    (виден для `{% include %}`, не эмитится), склейка — Jinja-сборщик
    со `strip_frontmatter`.
  - **Гарантия импорт-строки** `@.claude/team-roles.md` — идемпотентный
    пост-апдейт-хук в `cli.py` (`_ensure_team_roles_import`), не copier
    `_migrations` (те не срабатывают на `run_copy`-based update).
- **Альтернативы (носитель тела субагента):**
  - **Гнать субагент штатным i18n-конвейером** — отвергли: `_tasks_post_render`
    срезает ведущий frontmatter, а субагенту он нужен как функциональная
    шапка. Отсюда расщепление на два потока.
  - **Тело-партиалы под `i18n/`** (как в раннем черновике) — отвергли:
    i18n **рендерится и переносится** в корень, тело утекло бы отдельным
    файлом. Свойство «виден для include, не эмитится» есть только у
    `_exclude` → партиалы в `partials/**`.
- **Альтернативы (расположение Jinja-расширения — обнаружено в Phase 1):**
  - Спека (§5.5) закладывала `template/extensions/` в расчёте, что copier
    кладёт корень шаблона на `sys.path`. **По факту copier 9.15.1 этого
    не делает** — расширение не импортировалось ни на init, ни на update.
  - **Расширение в установленном пакете** `src/dreamteam/_jinja_ext/`,
    ссылка installed-путём `dreamteam._jinja_ext.frontmatter.…` — принято.
    copier импортирует из окружения (где `dreamteam` всегда установлен) →
    одинаково на init (wheel) и update (клон `.bundle`); в `.bundle`
    тащить расширение не нужно. Бонус: файл под ruff/mypy (не исключён
    вместе с `template/`).
- **Альтернативы (`name`/`tools` субагента — обнаружено в Phase 1):**
  - Спека держала их copier-переменными `_architect_*` с `when:false`.
    Ключи с ведущим `_` copier резервирует под свои настройки — в
    Jinja-контекст не попадают (рендерились пустыми). Так как это
    неизменяемые константы — **зашиты в сборщик**. Переменной осталась
    только `architect_model` (default `inherit`).
- **Альтернативы (носитель `description`):**
  - HTML-комментарий первой строкой тела vs YAML-ключ в переводческом
    frontmatter. Выбран **HTML-комментарий** — ru-источник остаётся без
    frontmatter (инвариант), `description` поднимается фильтром и покрыт
    тем же `source_hash`-гардом, что и тело (не нужен отдельный чек
    полноты).
- **Последствия:**
  - Новые файлы шаблона: `.claude/agents/architect.md` (сборщик),
    `partials/architect.body.{ru,en,fr,de,zh}.md`, i18n
    `.claude/team-roles.md` + `specs/design-brief-template.md`,
    одна `@import`-строка в `CLAUDE.md`.
  - Новое в репо: `src/dreamteam/_jinja_ext/`, copier-переменная
    `architect_model` + `_jinja_extensions` + `_exclude += partials/`,
    пост-апдейт-хук в `cli.py`, скан `partials/` в `translate_check.py`.
  - `dreamteam update` на старом проекте доставляет роли чистыми новыми
    файлами; импорт-строка гарантирована хуком даже при переписанном
    `CLAUDE.md`. Версионирование — MINOR.

### 2026-05-15 — `dt apply` для наложения template на существующий проект (T018)

- **Контекст:** разработчик создал проект через **другой
  инструмент** (PyCharm new-project wizard, `poetry new`,
  `hatch new`, manual `mkdir`), у него уже есть
  `pyproject.toml` / `.venv/` / возможно `src/` / `tests/`,
  и теперь он хочет применить методологию dreamteam **поверх**
  существующего scaffolding-а. Текущие команды не покрывают:
  - `dt init <path>` — рендерит в пустой каталог; ругается /
    конфликтует на non-empty target.
  - `dt update <path>` — требует `.copier-answers.yml`
    (присутствует только в проекте, ранее `dt init`-нутом).
  Это реальный usability gap, surfaced когда Vladimir создал
  `efactory` через PyCharm + uv и спросил «как одной командой
  применить dreamteam?». T018 закрывает gap новой командой
  `dt apply`.
- **Альтернативы (CLI surface — Q1):**
  - **`dt init --existing` flag** — same command name, flag
    hints intent. Отвергли — flag obscure без `--help`; users
    проблему не предсказывают, и `init` с побочным режимом
    путает API contract.
  - **Auto-detect в `dt init`** (empty → init, non-empty
    без answers → apply, with answers → error «use update»).
    Отвергли — implicit behavior surprising в CI scripts;
    user не контролирует path однозначно.
  - **Выбран `dt apply <path>`** — third top-level verb рядом
    с init / update. Explicit; users учат три глагола, но
    каждый делает одну вещь.
- **Альтернативы (conflict UX — Q2):**
  - **Copier's native Y/N prompt** (через `overwrite=False,
    defaults=False`) — менее rich, только keep/overwrite, no
    diff. Отвергли в пользу 4-way prompt с `[d]iff` option.
  - **Auto save-as `.dt-new` + warning** (non-interactive
    friendly) — отвергли как default. User мог не заметить
    `.dt-new` рядом, если работает быстро. Сохранили как
    explicit option через `--on-conflict save-as-new`.
  - **Выбран per-file 4-way interactive prompt**: `[k]eep /
    [o]verwrite / [d]iff / [s]ave-as-new`. `[d]iff` —
    informational, loops back. Default `keep` (least-destructive).
- **Альтернативы (already-dreamteam target — Q3):**
  - **Auto-redirect to `dt update`** — convenience, но риск
    что user не понял, какая команда фактически выполняется.
  - **Force re-init** — overwrite all answers (опасно).
  - **Выбран error + suggest `dt update`** (Q3 → option a).
    Minimum surprise; user знает что делает.
- **Альтернативы (`package_manager` detection — Q7):**
  - **Auto-detect из существующего `pyproject.toml`** (через
    `[tool.poetry]` / `[tool.hatch.*]` / отсутствие → uv) —
    intelligent, но complex и легко confused (что если в
    pyproject `[tool.hatch.envs]` И `[tool.poetry]`?). Отложили
    как stretch goal (отдельный T-ID при появлении pattern).
  - **Выбрано: всегда prompt** (default `uv`). Predictable.
- **Альтернативы (semantic merge `pyproject.toml` — Q9):**
  - **Special-case** TOML-level union user's `[project.dependencies]`
    + template's `[tool.ruff]` / `[tool.mypy]` — сложно,
    edge cases multiply; **отвергли** как out of MVP.
  - **Выбрано: универсальное правило**, `pyproject.toml`
    обрабатывается как любой другой template-managed файл
    через per-file conflict prompt.
- **Альтернативы (version bump — Q10):**
  - **MINOR (1.5.0 → 1.6.0)** — strict semver: new CLI command
    = new public surface = MINOR.
  - **Выбрано: PATCH (1.5.0 → 1.5.1)** — Vladimir's call.
    Framing: T018 это «закрытие usability gap / refinement of
    init use case», не principally new feature на уровне
    T009 / T017. Explicit departure от strict semver
    documented здесь — для consistency future T-задачи,
    которые добавят новый command, тоже могут получить PATCH
    bump если framing similar.
- **Реверс-discovered issues (during impl):**
  - 🟡 **Non-TTY interactive prompt** crash risk → mitigation:
    `sys.stdin.isatty()` detect + require `--on-conflict` для
    non-interactive runs. Реализовано.
  - 🟡 **Diff output volume** на large files → mitigation:
    в текущем MVP diff просто dump-ится в stdout. Если станет
    проблемой — добавить paging через `less` (отдельный T-ID).
- **Последствия:**
  - **`cli.py`:** new `apply` command + helpers
    (`_render_apply_preview`, `_classify_apply_files`,
    `_resolve_conflict`, `_prompt_conflict_choice`,
    `_execute_apply_decisions`, `_print_apply_summary`).
    `import sys` added (for `isatty()` check).
  - **`apply` validates target** — exists/dir/no
    `.copier-answers.yml`/`--on-conflict` for non-TTY — exits
    1 with specific message before any rendering work.
  - **`--dry-run`** включает both write-skip и interactive-
    prompt-skip (dry-run NEVER prompts, всегда выдаёт
    «conflict-dry» count).
  - **`.copier-answers.yml` always written** на successful
    apply (Q6 → option a) — subsequent `dt update` works.
  - **Bundle re-tag** через `scripts/update_bundle.py` —
    `1.5.1` tag добавлен; main advanced.
  - **`tests/test_t018_phase2.py`:** integration matrix 12
    cases. Marked `@pytest.mark.integration`; fast suite не
    затронут.
  - **Version:** `1.5.0 → 1.5.1` (PATCH per Q10).
  - **Phase split** в Implementation: Phase 0 (spec, PR #55),
    Phase 1+2+3 combined в одном PR (T017 pattern, CodeRabbit
    rate-limit economy).

### 2026-05-15 — Параметризованный выбор package manager (T017)

- **Контекст:** derived projects shipped с hardcoded `uv`-командами
  в narrative-файлах (×11 в CLAUDE.md, ×7 в README) + в
  pyproject.toml. T016 install-via-pip smoke выявил: pip- /
  poetry-user после `pip install dreamteam-cli && dt init proj`
  видел в Claude советы по uv-инструментарию, которого у него
  нет на машине. Параметризация через новый
  `package_manager` prompt + conditional Jinja rendering.
- **Альтернативы (set managers — Q1, expanded после consultation):**
  - **Только `uv` + `poetry` + `pip`** (initial spec proposal) —
    отвергли в пользу расширения. `pdm` и `hatch` оба
    PEP 621-native и активные; `hatch` особенно естественен —
    наш build-backend `hatchling` уже от тех же maintainer-ов.
  - **Полный landscape (`uv` + `poetry` + `pdm` + `hatch` +
    `pip` + `pipenv` + `pixi` + `conda` + `rye`)** — отвергли.
    `pipenv` declining (Pipfile-based, не PEP 621-native);
    `pixi` niche; `conda`/`mamba` другая парадигма (env + pkg
    объединены), требует отдельного `env_manager` prompt;
    `rye` superseded by `uv` (Astral acquired).
  - **Выбран `uv` + `poetry` + `pdm` + `hatch` + `pip` (5 managers).**
    Покрывает весь PEP-621-стек от opinionated-fast (uv) до
    bare (pip).
- **Альтернативы (default — Q2):**
  - **`pip` (most universal)** — отвергли. Slower workflow;
    confusing для current uv-first users.
  - **Выбран `uv`.** Current behavior, no surprises.
- **Альтернативы (conditional rendering arch — Q3):**
  - **Inline `{% if %}` blocks per command** — отвергли. Verbose,
    `{% if pm == 'uv' %}uv run pytest{% elif ... %}{% endif %}`
    блоки выглядят как шум в narrative.
  - **Separate per-manager file fragments + post-render
    selection** — отвергли. Работает для self-contained файлов,
    не для inline-heavy narrative (CLAUDE.md имеет много
    inline-команд).
  - **Выбраны single-variable Jinja macros** (`{% set pm_run =
    {...}[package_manager] %}` + body uses `{{ pm_run }}pytest`).
    DRY, scales до 5+ managers без quadratic growth текста.
- **Альтернативы (`pyproject.toml` template — Q4):**
  - **Три+ отдельных файла** (`pyproject.uv.toml`, etc.) +
    post-render rename — отвергли. Maintenance burden grows
    linearly, риск drift-а.
  - **Выбран single Jinja file с conditional sections.** Matches
    Q3 (single Jinja source). Per-manager блоки внутри `{% if %}`
    ladder. Build-system + `[tool.poetry]` / `[tool.hatch.*]`
    appear conditionally.
- **Альтернативы (build-system per manager — Q5):**
  - **uv:** `hatchling`.
  - **poetry:** `poetry-core`.
  - **pdm:** `pdm-backend`.
  - **hatch:** `hatchling` (own ecosystem).
  - **pip:** `hatchling` (modern PyPA-supported choice;
    `setuptools` не выбран — менее modern для new projects).
- **Альтернативы (lock-file generation в init — Q6):**
  - **Опциональный flag `--install`** — отвергли. Усложняет
    init flow, edge cases (manager not installed → failure).
  - **Always** — отвергли. Hard requirement.
  - **Выбрано: не генерировать в MVP.** User сам делает
    `{{ pm_install }}` после init; documented в derived README.
- **Альтернативы (backward compat — Q9, simplified после
  consultation):**
  - **Warning при missing answer** — отвергли. Cron-friendliness
    pain.
  - **Hard error «add --data package_manager=... explicitly»**
    — отвергли. UX burden.
  - **Migration command `dreamteam migrate --to <manager>`** —
    отвергли. Heavy work для edge case.
  - **Выбрано: ничего специального** (Vladimir's call —
    «проект молодой, не заморачиваться»). Copier standard
    silent default → `uv` для existing derived projects без
    `package_manager` answer.
- **Альтернативы (integration test scope — Q10):**
  - **Cut матрица** (5 × 1 en + 1 uv × 4 langs = 9 cases) —
    отвергли. Защита от drift weaker.
  - **Полная матрица 5 × 5 = 25 cases**, ~100s в integration
    suite. Acceptable budget; combined с multilang ~130s
    under 5-min CI timeout.
- **Reverse-discovered issue (CodeRabbit на #51 spec):** spec
  изначально предписывал bare `ruff check .` для pip — CodeRabbit
  flagged как flake risk (pre-push hook runs without shell
  activation). **Fixed:** pip pre-push command chain использует
  `.venv/bin/ruff check .` style.
- **Реверс-discovered issue (during impl):** Jinja `{%- ... -%}`
  whitespace-trim eat newline после frontmatter end-delim, что
  ломало `_tasks_post_render.py:_strip_frontmatter` (looking for
  exact `\n---\n` pattern). **Fixed:** функция accepts both
  `\n---\n` (standard) и `\n---` followed by any non-newline
  char (Jinja-trimmed case).
- **Последствия:**
  - **`copier.yml`:** новый prompt `package_manager` с 5
    choices, default `uv`, display names с native-tool наименованиями.
  - **`pyproject.toml` template:** conditional build-system +
    manager-specific `[tool.*]` sections (5 ветвей).
  - **`i18n/ru/{CLAUDE,README}.md`:** Jinja set-macros (`pm_run`,
    `pm_install`, `pm_name`) на верху файла, body uses
    substituted variables + `{% if %}` blocks для major-divergent
    sections (typical commands, dependency add).
  - **`i18n/{en,fr,de,zh}/{CLAUDE,README}.md`:** AI-regenerated
    через Claude Code session с обновлённым `source_hash`. 32
    ok через `translate_check.py`.
  - **`_tasks_post_render.py`:** `_strip_frontmatter` принимает
    Jinja-trimmed end-marker.
  - **`scripts/update_bundle.py`:** push main с `--force`
    (single-writer scenario; `--force-with-lease=ref` без
    expect-value ломается).
  - **`tests/test_t017_phase2.py`:** 5×5 integration matrix
    (verify rendered output, not actual install).
  - **Bundle re-tag:** `1.5.0` добавлен в `.bundle/`.
  - **Version:** `dreamteam-cli` 1.4.0 → 1.5.0 (MINOR;
    backward-compat через silent default `uv` для existing
    derived without `package_manager` answer).
  - **Phase split:** Phase 0 (spec, PR #51), Phase 1+2+3
    combined в одном PR для economy на CodeRabbit's hourly
    rate-limit (T007 trial обнаружил pattern).

### 2026-05-15 — Full `dreamteam update` с three-way merge (T009)

- **Контекст:** MVP-вариант `dreamteam update` (T006) выполнял
  `copier.run_copy(..., overwrite=True)` — re-rendered template
  поверх derived проекта, **затирал** локальные правки пользователя
  в template-managed файлах (`CLAUDE.md`, `BACKLOG.md`,
  `CHANGELOG.md`, `pyproject.toml`, `hooks/pre-push`). Известное
  ограничение, документировано в command docstring и в ADR T006.
  T009 — follow-up, заменяющий MVP-overwrite на полноценный
  three-way merge с сохранением правок и git-style conflict
  markers.
- **Альтернативы (layout — Q2, `i18n/<lang>/` interaction):**
  - **Runtime AI-merge через `anthropic` SDK** — отвергли. У
    Разработчика Claude Max subscription (не API), и runtime
    зависимость от LLM делает поведение update-а
    недетерминированным.
  - **Pure-Python merge (`merge3` PyPI)** — отвергли как fallback
    для git-absent сценария (Q3). Дополнительная dependency для
    редкого случая, менее обкатано чем `git merge-file`. Вместо
    этого — fall back to MVP overwrite + WARNING.
  - **Diff-based check** (просто проверять что other-language
    файлы тоже изменены) — отвергли. PR может cheat-нуть
    `touch`-ом.
- **Альтернативы (хранение base state — Q2):**
  - **Pip-download предыдущей версии** на update — отвергли.
    Сетевой доступ при runtime противоречит **MUST NOT:
    требовать сетевого доступа в runtime** из spec.md
    (caught CodeRabbit-ом в spec PR #44 ranee как противоречие).
  - **Hash-based + versioned history в wheel** (separate
    `dreamteam/_history/` с each snapshot) — отвергли.
    Линейный рост wheel-а с каждой версией; ~150% уже при 4
    версиях.
  - **Two-way merge без base** (только theirs vs ours) —
    отвергли как слишком неточный для overlapping kanban-edits;
    user правки и template changes часто пересекаются в
    BACKLOG/BOARD/CHANGELOG.
  - **Выбран bundled bare git repo** в
    `src/dreamteam/template/.bundle/` (Q2 → option a). Каждый
    release добавляет один annotated tag (`1.3.0`, `1.4.0`, …)
    через `scripts/update_bundle.py`. Wheel вырастает ~50 KB →
    ~165 KB (acceptable; rough ~3× против оценки в Analyze
    Warning ~5×).
- **Альтернативы (формат тегов — обнаружено в Phase 1):**
  - **`v`-prefixed теги** (`v1.3.0`, `v1.4.0`) — естественный
    git-style, но **dunamai** внутри copier-а использует
    `Pattern.DefaultUnprefixed` для определения версии. Отвергли
    в пользу PEP-440 unprefixed (`1.3.0`, `1.4.0`).
  - **Выбран PEP 440 без prefix-а**. `scripts/update_bundle.py`
    отклоняет `v`-prefixed input с понятной ошибкой.
- **Альтернативы (`Subproject.template` source — обнаружено в Phase 1):**
  - **Bundle как `_src_path` в answers напрямую** — отвергли.
    Bare repo не имеет working tree, copier-овский Template
    class на нём ломается («Updating is only supported in
    git-tracked templates»).
  - **Переписать `_src_path` в answers перед update** — отвергли.
    Запись на диск делает derived dirty, copier отказывается
    обновлять dirty subproject.
  - **Выбрано: pre-populate `worker.subproject.__dict__['last_answers']`
    с указанием temp clone path** до вызова `run_update`. Это
    bypass-ит cached_property без записи на диск. Documented
    как hack-зависимый от copier internals; работает на 9.x.
- **Альтернативы (conflict resolution UX — Q1):**
  - **`.rej` файлы** (`patch -R` стиль) — отвергли. Чище в
    основном файле, но нестандартный для git-developers; IDE
    merge tools не подхватывают.
  - **Дублирующие `.theirs.<lang>` файлы** — отвергли. Менее
    интрузивно, но user сам делает 3-way merge через IDE.
    Дополнительная нагрузка.
  - **Выбрано: git-style in-file markers**
    (`<<<<<<< before updating` / `=======` / `>>>>>>> after updating`).
    Стандарт, vimdiff/VSCode/IDE merge tools понимают.
- **Альтернативы (`git` absent — Q3):**
  - **Hard error** + «install git first» — отвергли. Min friction
    при dev-environments без git (редкий случай).
  - **Pure-Python merge fallback** (`merge3` PyPI) — отвергли,
    см. выше.
  - **Выбрано: fall back to MVP `run_copy(..., overwrite=True)`
    с явным WARNING** в stderr.
- **Альтернативы (atomicity — Q9):**
  - **All-or-nothing** через tempdir + swap — отвергли.
    Откат успешных мержей из-за одного конфликта — плохой UX;
    user должен сам решать сохранять ли progress частично.
  - **Выбрано: best-effort**. Per-file успех/конфликт/error;
    итоговый exit code mirrors самый серьёзный исход (0 / 1 / 2).
- **Альтернативы (`--dry-run` UX — Q8):**
  - **Только summary line** — отвергли. Без diff пользователь не
    знает что именно изменится.
  - **Только per-file unified diff** — отвергли. Без summary
    сложно быстро оценить scope.
  - **Выбрано: both** — top-line summary с 5 bucket-ами + per-file
    unified diff через `difflib.unified_diff`. Target никогда не
    модифицируется.
- **Последствия:**
  - **`dreamteam update`** теперь по умолчанию делает three-way
    merge через `copier.Worker.run_update`. Старое поведение
    доступно через `--force`.
  - **`--dry-run`** даёт preview без записи.
  - **Bundle** упакован в wheel, реrender при release через
    `scripts/update_bundle.py`. Maintainer запускает скрипт на
    каждый release cut.
  - **Exit codes**: `0` clean / `1` error / `2` conflicts.
    CI-friendly: PR в derived проекте может условно блокировать
    merge при unresolved conflicts.
  - **`_commit` в `.copier-answers.yml`** теперь PEP-440 без
    prefix-а (`1.4.0`, не `dreamteam-1.4.0`). Legacy
    `dreamteam-<X.Y.Z>` mapped в `_resolve_base_version_tag` для
    backward-compat (пре-1.3.0 проекты падают в overwrite
    fallback т.к. bundle не имеет таких тегов).
  - **`__version__`** теперь из `importlib.metadata.version()`
    — single source of truth, синхронизирован с pyproject.toml.
  - **Открытые упстрим quirks** (документированы в test
    comments, не блокеры):
    - Copier diff-ит Jinja-source против rendered subproject
      content; conflict markers могут попасть на Jinja-only
      line (`{{ project_name }}`) вместо semantically
      затронутой line.
    - Conflict resolution внутри `i18n/<lang>/` файлов трипает
      copier `git checkout -- <path>` staging step (rendered
      path ≠ template path после `_tasks_post_render.py`
      rename). Workaround в Phase 2 test — использовать
      root-level файл для conflict scenario. Multilang merge
      без overlap-а работает корректно.
  - **Version bump:** `1.3.0 → 1.4.0` (MINOR; backward-compatible
    — default flow изменился, но `--force` сохраняет MVP-поведение
    для тех кто на него полагался).
  - **Phase split** в Implementation: Phase 0 (spec, PR #44),
    Phase 1 (skeleton + merge backend, PR #46), Phase 2
    (synthetic-bundle integration tests, PR #47), Phase 3
    (`--dry-run`, PR #48), Phase 4 (docs + version + bundle
    re-tag, этот PR).

### 2026-05-15 — Multilang: Variant A + ru = source of truth + manual translation (T013)

- **Контекст:** narrative-файлы методики (`CLAUDE.md`, `README.md`,
  `CONCEPT.md`, kanban-файлы, `specs/spec-template.md`)
  поставлялись только на английском. Это работает для англоязычных
  пользователей, но создаёт барьер для non-English разработчиков
  — особенно когда суть документов — narrative описание методики,
  а не код. Решаем расширить шаблон на 5 языков (`en`/`ru`/`fr`/
  `de`/`zh`).
- **Альтернативы (layout — Variant A vs B vs C, см. spec.md Q1–Q2):**
  - **Variant B (runtime AI-translation в `dreamteam init`)** —
    отвергли. Требует `anthropic` SDK как build- или runtime-
    зависимость, у Разработчика Claude Max subscription (не API
    access), generation на каждый `dreamteam init` нестабилен и
    дорог.
  - **Variant C (hybrid mixed-language файлы — narrative на ru,
    headings на en в одном файле)** — отвергли. Нечитаемая каша,
    contributor confusion.
  - **`_subdirectory` copier-механизм с дублированием технических
    файлов в каждой `i18n/<lang>/`** — отвергли. Duplication
    burden: одно изменение в `pyproject.toml` → 5 файлов.
  - **Выбран Variant A:** `src/dreamteam/template/i18n/<lang>/`
    с narrative; технические файлы — на root template уровне;
    post-render task (`_tasks_post_render.py`) переносит
    `i18n/<выбранный>/*` → root и удаляет `i18n/`.
- **Альтернативы (source of truth — ru vs en, см. spec.md Q7):**
  - **English source + ru/fr/de/zh AI-перевод** (industry default)
    — отвергли. Разработчик monolingual maintainer (русскоязычный),
    редактировать методику на en и затем переводить на ru через
    AI — лишний этап с потерей качества именно в ru (родном языке
    Разработчика).
  - **Выбран ru = source of truth** + AI-перевод на остальные 4
    языка. Trade-off: en теряет «source language privilege» —
    теперь это AI-перевод равного trust-level с zh/fr/de. UX
    expectation `default: en` сохранён (стандарт для CLI tools);
    ru = source — внутренний maintenance detail.
- **Альтернативы (AI engine — scripted API vs manual session, см.
  spec.md Q8):**
  - **`scripts/translate.py` с Anthropic SDK** (scripted CLI:
    `python scripts/translate.py` → API call → переводы) —
    отвергли. Требует `ANTHROPIC_API_KEY` env var, расходы на API
    при каждом regen, `anthropic` package в `[dependency-groups]
    .dev` — у Разработчика API не подключен.
  - **AI translation as CI step** (auto-regenerate на CI с API key
    в GitHub secrets) — отвергли. Race conditions при concurrent
    PR, API costs на каждый CI run, secret management.
  - **Выбран manual flow через Claude Code session.** Разработчик
    правит `i18n/ru/<file>.md`, в Claude Code session просит
    «переведи на en/fr/de/zh, обнови frontmatter». Claude
    (`claude-opus-4-7`) использует стандартные Read/Write tools,
    computes `sha256(ru_bytes)` через stdlib `hashlib`, пишет
    переводы с frontmatter. Trade-off: каждое изменение требует
    session interaction (не one-line CLI), но zero API cost
    (covered Max subscription), нет key management, нет новых
    dependencies.
- **Альтернативы (drift mitigation — diff vs hash, см. spec.md Q7):**
  - **Diff-based check** (CI проверяет, что other-language файлы
    тоже изменились) — отвергли. Cheap, но PR может «cheat»-нуть
    `touch`-ом файла без реального перевода.
  - **AI translation как CI auto-regen** — см. выше, отвергли.
  - **Выбран hash-based check** (`scripts/translate_check.py`,
    pure stdlib + PyYAML). Каждый не-русский файл несёт
    frontmatter с `source_hash` (sha256 of ru source at translation
    time); CI step после pytest пересчитывает hash актуального
    `i18n/ru/<same>.md` и сравнивает. Mismatch → PR fail с
    указанием конкретного файла + hint regenerate. Отсутствие
    frontmatter → warning + skip (Q9 — soft-fail, чтобы не
    блокировать community manual edits / bootstrap partial state).
- **Последствия:**
  - **Структура `src/dreamteam/template/`:** narrative-файлы
    переехали в `i18n/{ru,en,fr,de,zh}/`. ru остаётся
    единственным редактируемым вручную набором. Технические файлы
    (pyproject.toml, src/, tests/, hooks/, .gitignore, copier.yml)
    не дублируются.
  - **`copier.yml`:** новый prompt `language` (первый, до
    `project_name`), choices `[en, ru, fr, de, zh]`, default `en`,
    display names с native variants (`en (English)` / `ru
    (Русский)` / …). `_tasks` step запускает
    `_tasks_post_render.py {{ language }}` после рендера.
  - **`_tasks_post_render.py`** в template root: перемещает
    `i18n/<lang>/*` в корень derived-проекта, strip-ит translation
    frontmatter (derived users получают clean markdown), удаляет
    `i18n/` и сам себя.
  - **`cli.py`:** `unsafe=True` в `Worker` / `run_copy` (template —
    package-data, доверяем `_tasks`); новый `--data key=value`
    (repeatable) на `dreamteam init` для прокидывания answers в
    copier (нужен для `--data language=ru`).
  - **`scripts/translate_check.py`** (stdlib `hashlib` + PyYAML,
    который уже в copier dependencies). Запускается локально и
    как step в `.github/workflows/ci.yml` после pytest. 32 ok при
    зелёном состоянии (4 языка × 8 файлов).
  - **`tests/test_translate_check.py`** — 8 unit-кейсов
    (valid / mismatch / missing-fm / partial-fm / missing-source
    / round-trip / dir-skip / live-repo-state).
  - **`tests/test_multilang.py`** — fast render-per-language тесты
    + `@pytest.mark.integration` e2e (uv sync + 4 pre-push на
    каждом из 5 derived проектов, ~16 секунд suite total).
  - **Frontmatter format** в каждом `i18n/{en,fr,de,zh}/<file>.md`:
    ```yaml
    ---
    translated_from: i18n/ru/<file>.md
    source_hash: <sha256 of ru at translation time>
    translation_engine: claude-opus-4-7
    translation_date: 2026-05-15
    ---
    ```
  - **Maintainer flow при правке методики:**
    1. Vladimir правит `i18n/ru/<file>.md`.
    2. В Claude Code session: «переведи изменения в `i18n/ru/<file>.md`
       на en/fr/de/zh, обнови `source_hash`».
    3. Claude reads ru-source, computes `hashlib.sha256(ru_bytes)
       .hexdigest()`, пишет переводы с обновлённым frontmatter.
    4. Vladimir commits ru + регенерированные переводы.
    5. CI guard verify hash sync.
  - **Cosmetic ru-edits** (typo, whitespace, реструктуризация
    переносов) меняют hash и формально требуют regenerate. Workflow
    на этот случай: «обнови только `source_hash` во всех 4 языках,
    перевод не трогай — изменения cosmetic». Claude применяет
    `hashlib.sha256` и обновляет frontmatter без regeneration
    content. Manual judgment per change.
  - **Версия пакета:** `dreamteam-cli` 1.2.0 → 1.3.0 (MINOR).
    Default `en` сохраняет поведение для existing derived
    проектов; после `dreamteam update` те получат `language: en`
    в `.copier-answers.yml` и rendered narrative на en — то же,
    что у них и так было.
  - **Quality risk** (warning из Analyze): все 4 не-русских языка
    — AI-generated, теоретически возможно правило в `CLAUDE.md`
    на en/zh означает противоположное ru. Mitigation:
    (1) do-not-translate list в practice (ruff/mypy/ADR/имена
    файлов/code blocks/kanban keywords оставляются как есть);
    (2) frontmatter traceability; (3) Google Translate roundtrip
    smoke на ключевые правила по желанию; (4) long-term —
    bilingual community reviewers.
- **Phase split (исторический):**
  - **Phase 1** — skeleton + ru source + bootstrap всех 5 языков
    + unit/integration tests (PR #38).
  - **Phase 2** — CI guard step в workflow (PR #39, stacked).
  - **Phase 3** — этот ADR + CHANGELOG + README + version bump
    (этот PR, stacked на Phase 2).
  - Опциональный **smoke PR** (after Phase 2 merged into main) —
    edit `i18n/ru/<file>.md` без regen на отдельной ветке,
    показать CI fail на live runner; не merge-ить.

### 2026-05-15 — Удаление `PROJECT.md` из шаблона (T014)

- **Контекст:** `PROJECT.md` в template был задуман как «паспорт
  проекта» (цель / статус / стек / артефакты / открытые вопросы /
  история). Каждый из этих блоков **дублируется** более
  специализированным документом: цель и статус — в `README.md`,
  открытые вопросы — в `BACKLOG.md`, история — в `CHANGELOG.md`,
  стек и зависимости — в `pyproject.toml` / `[project.urls]`,
  архитектурные решения — в `DECISIONS.md`. Catch-all-документ без
  чёткой роли — гарантированный drift.
- **Альтернативы:**
  - **Оставить как есть** — отвергли. Drift между `PROJECT.md` и
    `README.md` / `BACKLOG.md` / `CHANGELOG.md` неизбежен; дополнительная
    дисциплина без выгоды.
  - **Расширить роль `PROJECT.md`** (например, заменить ARCHITECTURE.md)
    — отвергли. Для текущего масштаба проектов лишняя сущность.
  - **Merge в `README.md`** (один большой README) — отвергли.
    README превратится в state-dump, что портит quick-start
    природу. Стандартное ожидание Python community — README
    компактный, для onboarding.
- **Последствия:**
  - `src/dreamteam/template/PROJECT.md` удалён.
  - `src/dreamteam/template/CLAUDE.md` — в «Что прочитать в начале
    сессии» `PROJECT.md` заменён на `README.md` (current state
    теперь там); в разделе про CONCEPT — упоминание `PROJECT.md`
    заменено на `README.md`.
  - `src/dreamteam/template/README.md` — `PROJECT.md` убран из
    «Структуры проекта»; вместо него добавлен `CONCEPT.md`
    (immutable initial vision — раньше отсутствовал в списке).
  - `src/dreamteam/template/CONCEPT.md` — ссылка «Текущее
    состояние ведётся в `PROJECT.md`» заменена на `README.md`.
  - Версия `dreamteam-cli`: `1.0.0 → 1.1.0` (MINOR — template
    change; existing проекты на v1.0.0 с PROJECT.md остаются как
    есть, `dreamteam update` не удаляет файл).
  - Итоговая методическая картина: **6 специализированных файлов
    без catch-all**: CONCEPT (immutable vision), README (public +
    current state), CLAUDE (правила для Claude), BACKLOG (идеи),
    BOARD (текущая работа), CHANGELOG (история), DECISIONS (ADR).

### 2026-05-14 — PyPI naming: `dreamteam-cli` вместо `dreamteam` (T011)

- **Контекст:** При первой попытке publish (T011) обнаружено, что
  имя `dreamteam` на PyPI занято с 2019 года: squatter-аккаунт с
  single-version 0.0.1, заброшен (last upload 2019-09-12, владелец
  не отвечает на запросы по аналогичным случаям). Имя нужно сейчас.
- **Альтернативы:**
  - **PEP 541 reclamation** (запрос реклемации заброшенного package
    у PyPI admins) — отвергли: процесс на недели, требует emails
    к admins + период ожидания response от original maintainer.
    Несовместимо с темпом релиза.
  - **`dreamteam-scaffold`, `dreamteamkit`, `dreamteamx`, прочие** —
    отвергли в пользу `dreamteam-cli`: последний более self-
    descriptive (CLI tool) и следует распространённой Python
    конвенции (`django-cli`, `kubernetes-cli` и т.п.).
- **Последствия:**
  - **PyPI name:** `dreamteam-cli`. `pip install dreamteam-cli`,
    `uvx --from dreamteam-cli dreamteam ...`.
  - **Command name** остаётся `dreamteam` (через `[project.scripts]
    dreamteam = "dreamteam.cli:app"`). Brand сохраняется в
    повседневной работе.
  - **Import name** остаётся `dreamteam` (папка `src/dreamteam/`).
    Python permits PyPI name ≠ import name; common pattern.
  - **Repo name** остаётся `vlakir/dreamteam` (GitHub).
  - В `README.md` явно прописан note про PyPI name vs command name
    distinction.
  - Известный артефакт: бесполезный squatter package `dreamteam`
    0.0.1 продолжает существовать на PyPI; наш `dreamteam-cli` —
    отдельная запись, никаких коллизий.

### 2026-05-14 — Publish flow: `scripts/publish.sh` + `.secrets` (hybrid: twine check + uv publish) (T011)

- **Контекст:** Для регулярных публикаций dreamteam-cli на PyPI
  нужен скрипт. Передавать токен в командной строке каждый раз —
  опасно (попадает в shell history); хранить токен в коде —
  нельзя. Validation артефактов перед upload желательна (PyPI
  не позволяет re-upload одной версии, ошибка в metadata = bump
  version).
- **Альтернативы:**
  - **Чистый `uv publish` без validation step** — отвергли. `uv
    publish` не имеет аналога `twine check`; ошибка в metadata
    обнаружится после irrevocable upload. Bump-and-republish —
    плохой UX для первой публикации.
  - **Чистый `twine upload`** — отвергли. Заменять `uv publish`
    на twine в пользу одного дополнительного шага не нужно.
    Hybrid берёт лучшее из обоих.
  - **Inline команды без скрипта** (как было сначала) — отвергли.
    Токен в командной строке + shell history + повторение при
    каждом релизе.
  - **`.env` вместо `.secrets`** — отвергли. У Разработчика уже
    устоявшаяся конвенция `.secrets` family (от dynaconf-эпохи
    старых проектов).
- **Последствия:**
  - **`scripts/publish.sh`** (bash, `set -euo pipefail`):
    1. Source `.secrets` (export PYPI_TOKEN / PYPI_TEST_TOKEN).
    2. `rm -rf dist/ && uv build`.
    3. `uv run twine check dist/*` (validation).
    4. `UV_PUBLISH_TOKEN=$TOKEN uv publish` (или с
       `--publish-url https://test.pypi.org/legacy/` при `--test`).
    5. Print verify-команду.
  - **`.secrets`** в `.gitignore` (явно, поскольку `.secrets.*`
    pattern не покрывает bare `.secrets`).
  - **`.secrets.example`** в git (через negation
    `!.secrets.example` в `.gitignore`) — template для onboarding.
  - **`twine`** добавлен в `[dependency-groups].dev`.
  - Usage: `cp .secrets.example .secrets`, paste tokens, run
    `scripts/publish.sh` (или `--test` для TestPyPI).

### 2026-05-14 — MIT License для `dreamteam` package (T010)

- **Контекст:** `dreamteam` — scaffolding CLI, ориентирован на широкую
  adoption и использование в любых проектах (включая proprietary).
  Перед публикацией на PyPI (T011) требуется явная license; до сих
  пор её не было.
- **Альтернативы:**
  - **Apache 2.0** — permissive + explicit patent grant. Отвергли:
    для small CLI tool patent grant overkill; больше boilerplate.
    Может быть пересмотрено при росте проекта / контрибьюторов.
  - **GPL-3.0** — copyleft, viral. Отвергли: для scaffolding tool
    блокирует использование в proprietary derived projects, что
    противоречит главной цели (широкая adoption).
  - **BSD-3-Clause** — like MIT + non-endorsement clause. Отвергли:
    extra clause без значимой выгоды для small Python tool.
- **Последствия:**
  - `LICENSE` file в корне репо со standard MIT text (Copyright (c)
    2026 vlakir).
  - В `pyproject.toml`: `license = "MIT"` + `license-files = ["LICENSE"]`
    (PEP 639 syntax). License classifier из `[project.classifiers]`
    **не дублируется** — PEP 639 запрещает.
  - Wheel автоматически включает LICENSE через hatchling +
    `license-files` directive.
  - Снимает блокер T011 (PyPI publish).
  - **Discrete от derived projects:** template/ не содержит LICENSE.
    Пользователь `dreamteam init` сам решает что добавить (или
    оставить unlicensed). Если в будущем хотим предложить license
    choice в `dreamteam init` — отдельная задача.

### 2026-05-14 — `TEMPLATE-*.md` → default names в корне репо

- **Контекст:** Префикс `TEMPLATE-` для мета-документов (BACKLOG,
  BOARD, CHANGELOG, DECISIONS) был введён в T005 для разделения
  «мета шаблона» vs «заготовки для derived» в одном репо. После
  T006 заготовки уехали в `src/dreamteam/template/` как package
  data; в корне репо остались только мета-документы — коллизия
  исчезла, префикс стал избыточным.
- **Альтернативы:**
  - **Оставить префикс** — отвергли. Избыточен после T006, делает
    файлы менее обычными для нового читателя репо.
  - **Перенести мета-документы в `meta/` подпапку** — отвергли.
    Default позиция меты — корень репо (как везде в Python проектах).
- **Последствия:**
  - `TEMPLATE-BACKLOG.md → BACKLOG.md`,
    `TEMPLATE-BOARD.md → BOARD.md`,
    `TEMPLATE-CHANGELOG.md → CHANGELOG.md`,
    `TEMPLATE-DECISIONS.md → DECISIONS.md` (через `git mv`).
  - Live references (в README, pyproject `[project.urls] Changelog`,
    intro секциях самих файлов) обновлены на default-names.
  - Historical entries в CHANGELOG (внутри версий) и в этом
    DECISIONS (внутри старых ADR), а также `specs/T006-.../spec.md`
    — **не правлены**. Это immutable history.
  - Глобальный `~/.claude/CLAUDE.md` обновлён: scope правила
    нумерации T-ID для репо шаблона теперь по `BACKLOG.md`/`BOARD.md`/
    `CHANGELOG.md` (без `TEMPLATE-`-префикса).
  - Файлы в `src/dreamteam/template/` (внутри template для derived)
    не затронуты — там и были без префикса.

### 2026-05-14 — Миграция на Copier + PyPI-distributed CLI (T006)

- **Контекст:** Шаблон распространялся как GitHub Template Repository.
  Каждый новый проект требовал 9 ручных шагов очистки (`rm TEMPLATE-*`,
  очистка примеров, копирование `README.template.md`, замена
  плейсхолдеров). Это трение в самый ценный момент — старт проекта.
- **Альтернативы:**
  - **Остаться на gh-template** — отвергли. Трение растёт с
    методикой.
  - **Cookiecutter** — отвергли. Нет нативного `update`, экосистема
    стагнирует на фоне `copier`.
  - **Свой CLI с нуля** — отвергли. 1-2 недели работы vs 1 день с
    `copier`-инфраструктурой. Reinventing the wheel.
  - **Чистый `copier copy gh:vlakir/dreamteam`** (без своего CLI и
    PyPI) — отвергли. Привязка к `gh:`-reference нарушает правило
    «методика универсальная, не привязанная к платформе».
- **Последствия:**
  - `dreamteam` — Python-package на PyPI, тонкий Typer CLI поверх
    `copier`. Команды: `dreamteam init <path>`, `dreamteam update`.
  - Template живёт в `src/dreamteam/template/` (package-data),
    `copier` вызывается через Python API.
  - **`dreamteam update` ограничен на MVP** — re-applies template
    с stored answers (`overwrite=True`), не делает diff/merge. Full
    diff/merge через `copier.run_update` требует git-tracked
    template, что нетривиально для PyPI-distributed package.
    Планируется отдельной задачей.
  - **`Worker` from copier** используется для capture user answers
    (run_copy возвращает None). Worker помечен как internal API,
    deprecation warning принимается до публичного API.
  - Файлы методики в корне репо удалены (Phase 7) — они теперь
    только в `src/dreamteam/template/`. Корень репо: package +
    tests + `TEMPLATE-*.md` meta-docs + specs + README + .gitignore +
    pyproject + uv.lock.
- **Process для release на PyPI** (для maintainer):
  ```bash
  # 1. Локально проверить build
  uv build
  unzip -l dist/dreamteam-1.0.0-py3-none-any.whl   # sanity check

  # 2. TestPyPI (sanity check)
  # Требует API token на test.pypi.org, переменная UV_PUBLISH_TOKEN
  uv publish --publish-url https://test.pypi.org/legacy/

  # 3. Verify install из TestPyPI работает
  pip install --index-url https://test.pypi.org/simple/ \
              --extra-index-url https://pypi.org/simple/ \
              dreamteam

  # 4. Основной PyPI (после OK на TestPyPI)
  # Требует API token на pypi.org
  uv publish
  ```
- **Versioning policy** для `dreamteam` package:
  - Semver. `1.0.0` — первый release с Copier/CLI архитектурой.
  - `MAJOR` bump при breaking changes методики (изменения, которые
    `dreamteam update` не может применить безопасно).
  - `MINOR` — новые правила / features в шаблоне (backward-compatible
    через `update`).
  - `PATCH` — fix-ы / documentation / tooling без изменения шаблона.

### 2026-05-14 — Branch Protection на `main` через GitHub-side enforcement (T001)

- **Контекст:** правило «не пушить напрямую в `main`» было
  поведенческим + локальный `hooks/pre-push` как опциональная
  защита. Сервер пропускал прямой push, если поведенческое правило
  было нарушено. Это «дыра» в дисциплине: один неосторожный
  `git push origin main` — и история запачкана.
- **Альтернативы:**
  - **Только поведенческое правило + локальный hook** — отвергли.
    Локальный hook нужно установить вручную (`cp hooks/pre-push
    .git/hooks/pre-push`), а если разработчик забыл — защиты нет.
    Сервер всё разрешит.
  - **GitHub Actions check** (workflow проверяет каждый push на
    main) — отвергли. Это reactive (фиксирует факт), а не
    preventive (не позволяет случиться).
  - **Branch Protection без `enforce_admins`** — отвергли по
    результатам smoke-теста: admin (владелец репо) bypass'ит
    защиту с warning «Bypassed rule violations», push проходит.
    Acceptance не достигается.
- **Последствия:**
  - На `vlakir/dreamteam` через `gh api .../branches/main/
    protection -X PUT` включена защита со следующими настройками:
    - `required_pull_request_reviews: { required_approving_review_count: 0 }`
      — push в `main` запрещён, мерджить можно через PR без
      обязательных approvals (Разработчик один, не имеет смысла
      требовать approval себя самого).
    - `enforce_admins: true` — защита применяется и к владельцу
      репо. **Autonomous decision** после первого smoke-теста,
      когда `enforce_admins=false` оказался дырявым.
    - `required_status_checks: null` — checks не требуются пока
      не настроим CI (`T007` после миграции на copier).
    - `restrictions: null` — нет ограничений по push users.
    - `allow_force_pushes: false`, `allow_deletions: false` —
      от автомата.
  - Через `gh repo edit --enable-merge-commit=false
    --enable-rebase-merge=false` оставлен только Squash-merge.
    Это enforces правило «один PR — один коммит» через GitHub UI.
  - Acceptance verified: `git push origin main` напрямую
    отклоняется сервером с `GH006: Protected branch update
    failed for refs/heads/main. Changes must be made through a
    pull request.`
- **Known artifact** в истории `main`: коммит `49bbebe` «T001
  smoke-test: this should be rejected by branch protection» —
  пустой коммит, попавший в main во время первого smoke-теста с
  `enforce_admins=false`. Не revert-ил, чтобы не нарушать своё же
  правило «не force-push в main». Остаётся как историческое
  свидетельство bootstrap процесса.
- **Платформо-специфично:** настройка через `gh` — для GitHub.
  Для других хостингов (GitLab, GitFlic, Forgejo) — аналоги
  через UI или API соответствующей платформы. Behavioral правило
  «не пушить напрямую в main» остаётся универсальным.

### 2026-05-14 — Префикс `TEMPLATE-*` для мета-файлов шаблона (T005)

- **Контекст:** Файлы шаблона несли двойную нагрузку: заготовка для
  derived users **И** место для нашей реальной работы над шаблоном.
  В `BACKLOG.md` лежали как пример для пользователя, так и наши
  задачи (T001-T005); в `DECISIONS.md` — пример SQLite и наши
  реальные ADR (uv, src/, logging); в `BOARD.md` — пример и T001.
  Именование непоследовательное: `META-CHANGELOG.md` (для шаблона)
  и `README.template.md` (для derived) — разные суффиксы для
  концептуально одинаковых ролей.
- **Альтернативы:**
  - **Двойной набор файлов в одном каталоге без явного префикса** —
    отвергли. Невозможно с одним именем хранить два смысла; путаница
    остаётся.
  - **Отдельная директория `.template-meta/`** — отвергли. При
    template-create копируется наравне с прочим; требует явного
    удаления; всё равно нужен маркер.
  - **Два репозитория** (`vlakir/dreamteam` для шаблона +
    `vlakir/dreamteam-meta` для разработки) — отвергли. Один
    разработчик, два репо — overhead координации.
  - **GitHub Issues / Projects для меты** — отвергли, нарушает
    принцип «методика универсальная, не привязанная к платформе»
    (см. правило `feedback_tasks_in_markdown_not_platform.md`).
- **Последствия:**
  - Введён префикс **`TEMPLATE-*`** для всех мета-файлов разработки
    шаблона. Default-имена (без префикса) — заготовки для derived.
  - Файлы созданы / переименованы:
    `META-CHANGELOG.md → TEMPLATE-CHANGELOG.md`;
    новые `TEMPLATE-BACKLOG.md`, `TEMPLATE-BOARD.md`,
    `TEMPLATE-DECISIONS.md`.
  - Накопленные данные шаблона перенесены в `TEMPLATE-*`;
    default-name файлы очищены до заготовок.
  - `README.md` — единственное исключение от schema (github
    отображает его на странице репо). В derived перезаписывается
    через `README.template.md`.
  - В инструкции «Как использовать» шаблона добавлен шаг
    `rm TEMPLATE-*.md` — стоит **перед** финальной перезаписью
    `README.md` через `README.template.md`, чтобы оставшиеся шаги
    setup не исчезли при overwrite.
  - В проектном `CLAUDE.md` добавлен раздел «Специфика репозитория
    `vlakir/dreamteam`» с явной пометкой «НЕ применяется в derived».
  - Scope правила `max()` для T-ID контекстен: в шаблоне —
    по `TEMPLATE-*`, в derived — по default-names.

### 2026-05-13 — CLI-style logging: DEBUG/INFO → stdout, WARNING+ → stderr

- **Контекст:** `logging.basicConfig(level=...)` без явного `stream=`
  пишет все логи (включая INFO/DEBUG) в `sys.stderr`. PyCharm и
  большинство терминалов красят stderr красным независимо от уровня —
  обычные информационные сообщения выглядят как ошибки. Кроме того,
  стандартный pipe `2>/dev/null` глушит и реальные ошибки, и
  безобидные INFO-логи — разделить их без перенастройки нельзя.
- **Альтернативы:**
  - **Оставить дефолт `basicConfig`** (всё в stderr) — отвергли.
    Визуальный шум в IDE, никакого pipe-контроля.
  - **Всё в stdout** (`stream=sys.stdout` в basicConfig) — отвергли.
    Ошибки уходят туда же, куда обычный вывод; пайплайны смешивают
    значимое и неважное.
- **Последствия:**
  - В `src/main.py` корневой logger конфигурируется двумя
    `StreamHandler`-ами: stdout (DEBUG/INFO, отсечено фильтром
    `_stdout_filter` по `record.levelno < WARNING`) и stderr
    (WARNING и выше).
  - `python src/main.py 2>/dev/null` — только информационные логи.
  - `python src/main.py >/dev/null` — только ошибки и предупреждения.
  - В PyCharm красным окрашивается только то, что реально требует
    внимания.
  - Конвенция распространяется на все новые проекты из шаблона.
    Сложные логгеры (структурные, ротация файлов и т.п.) — отдельный
    выбор по месту, но базовая разводка stdout/stderr сохраняется.

### 2026-05-13 — `src/` как корень исходников

- **Контекст:** Стартовый `main.py` лежал в корне проекта рядом с
  `pyproject.toml`, `README.md`, документами методики. По мере роста
  проекта корень захламляется, исходники смешиваются с инфраструктурой.
- **Альтернативы:**
  - **Flat layout** (исходники в корне) — отвергли. Корень
    превращается в свалку, нужно вручную исключать всё лишнее в
    `ruff exclude` / `mypy`.
  - **Пакет в корне** (`<project_name>/main.py` в корне) — отвергли.
    Имя пакета лезет в имя репозитория, при ренейме надо двигать
    директорию; коллизии с типичными именами модулей.
- **Последствия:**
  - Все исходники приложения живут в `src/` — это конвенция для
    всех новых проектов.
  - Запуск: `uv run python src/main.py`.
  - В `pyproject.toml` указан `mypy_path = "src"` — тип-чекинг
    находит модули из `src/` без `from src.* import`.
  - Имя проекта (`name` в `pyproject.toml`) можно менять без
    перестановки директорий.
  - Тесты, документация и инфраструктура остаются в корне или в
    собственных папках (`tests/`, `docs/`, `.github/` и т.п.).

### 2026-05-13 — `uv` как менеджер зависимостей и окружений

- **Контекст:** Шаблон стартовал на `poetry` (привычка Разработчика,
  все старые проекты на poetry). На первой же настройке линтеров
  всплыла проблема: poetry-стиль `^3.14` в `[project].requires-python`
  невалиден по PEP 621, ruff упал на парсинге. Дополнительно: `poetry
  install` в 10–100× медленнее, чем `uv sync` — для AI-workflow
  с частыми пересборками окружений это ощутимо.
- **Альтернативы:**
  - **Остаться на `poetry`** — отвергли. Замедляет работу с AI,
    несовместимости с PEP 621 будут всплывать снова, экосистема
    уверенно мигрирует на uv.
  - **Гибрид** — отвергли. Два стандарта в одном репо = путаница
    и двойная поддержка.
- **Последствия:**
  - Новые проекты из этого шаблона стартуют на `uv`.
    - В `pyproject.toml` используется чистый PEP 621 `[project]` без
    poetry-секций. Build-system намеренно не задан (применимо к
    приложениям; для библиотек — добавить отдельно).
  - При работе с PyCharm: интерпретатор указывается на `./.venv/bin/python`
    (PyCharm автоматически распознаёт `.venv` в корне проекта).
