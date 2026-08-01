# Backlog (dreamteam package)

Парковка идей и задач **разработки самого `dreamteam`-пакета**
(scaffolding CLI на Copier). В derived projects (создаваемых через
`dreamteam init`) — свой собственный `BACKLOG.md` с другим
содержимым; они не пересекаются, потому что репо `dreamteam`
содержит template как **package data** в `src/dreamteam/template/`,
не как файлы в корне.

Структура и правила: порядок имеет значение (сверху — что
планируется ближайшим), формат —
`- **T<NNN>** — [<дата>] <описание>`. Когда задача берётся в работу
— переезжает в `BOARD.md → To Do`.

**Scope правила нумерации:** `max()` для T-ID считается по
`BACKLOG.md`, `BOARD.md` и `CHANGELOG.md` этого репо. Раньше
(до v1.0.0) файлы имели префикс `TEMPLATE-`; ADR об обратном
ренейме — в `DECISIONS.md`.

## Items

### Дорожная карта v0.3 → v1.0

Полный дизайн-документ: **`specs/roadmap-v0.3-v1.0/design.md`**
(позиционирование, anti-scope, эпики, критерии приёмки, декомпозиция).
Разворот пакета: из «тонкий Copier-CLI» в stateful-инструмент с
**оперативным слоем состояния** (`<repo>.dt/`). Зонтичный ADR — в
`DECISIONS.md` (2026-07-30).

**Соответствие ID.** T-ID в дизайн-документе (`T001`–`T024`) —
локальные метки; репозиторные — `T033`–`T056` (сдвиг `+32`, т.к.
`max()` был `T032`, ID не переиспользуются). `deps` ниже уже
переведены в репозиторные ID.

**Точки входа (без зависимостей):** T043, T048, T050 (T033–T041 + T051
закрыты; T042 разблокирован — deps T034+T040 выполнены — но это точка
невозврата, брать после T051–T053; следующие по крит.пути — T052 → T053).
**Критический путь:** T033 → T034 → T051 → T052 → T053.
**Рекомендованный порядок** и оговорки — §6.4 дизайн-документа
(T042 = точка невозврата, брать после T051–T053; T056 — раньше графа;
T050 — дешёвый первый подопытный через саму новую машинерию).

#### v0.3 — E1: оперативный слой состояния задач

<!-- T034 (базовые операции), T035 (валидация), T036 (worktree),
     T037 (доска dt board), T038 (поиск dt task find), T039 (старт
     dt task start), T040 (синхронизация BACKLOG.md dt backlog sync),
     T041 (перенос состояния dt state export/import) закрыты —
     см. BOARD.md → Done и CHANGELOG [Unreleased]. -->
- **T042** — [2026-07-30] Миграция существующих проектов
  `dt migrate tasks`; парсинг BOARD/BACKLOG, `.bak`, удаление BOARD.md
  из репо. **Точка невозврата** — после T051–T053. deps: T034, T040.

#### v0.3 — E2: разбиение методики на секции

- **T043** — [2026-07-30] Разбиение методики на секции-источники
  `i18n/<lang>/methodology/*.md`; сборка CLAUDE.md из секций,
  CI-проверка наличия обязательных секций. deps: —.
- **T044** — [2026-07-30] Сокращение языков до `ru` + `en`; удаление
  fr/de/zh, `translate_check.py` → `publish.sh`. deps: T043.
- **T045** — [2026-07-30] Переписывание README: честное
  позиционирование как личного инструмента для Claude Code. deps: T044.

#### v0.3 — E6: ритуалы как команды

- **T046** — [2026-07-30] Slash-команды из секций методики
  `.claude/commands/`: clarify, analyze, review, retro, handover.
  deps: T043.

#### v0.3 — E9: связывание сессий и задач

<!-- T051 (dt context — ориентация сессии) закрыт — см. BOARD.md → Done
     и CHANGELOG [Unreleased]. -->
- **T047** — [2026-07-30] Секция методики `sessions` — правила
  поведения агента (find перед стартом, привязка, 4 сценария рождения
  задачи, Handover по событиям). deps: T043, T038, T039.
- **T052** — [2026-07-30] SessionStart-хук и реестр сессий;
  `sessions/<TASK_ID>.json` файл-на-задачу, бюджет 2000 симв., ошибка
  → код 0. deps: T051. spec: `specs/T052-session-registry/spec.md`.
- **T053** — [2026-07-30] `dt resume` — восстановление раскладки,
  `--tmux` скрипт, проверка существования файла сессии. deps: T052,
  T036.
- **T054** — [2026-07-30] Statusline — shell-скрипт читает
  `context.line` по `<slug>`, < 50 мс, без Python. deps: T051.
- **T055** — [2026-07-30] Handover как живая секция; обновление по
  событиям, PreCompact-хук, детект устаревания. deps: T051, T043.

#### v0.3 — E11: профиль workspace

- **T048** — [2026-07-30] Профиль `layout=workspace` (copier-вопрос):
  корневой `[tool.uv.workspace]`, единый pre-push по дереву,
  переключение после создания не поддерживается. deps: —.
  spec: `specs/T048-workspace-layout/spec.md`.
- **T049** — [2026-07-30] `dt apply` на существующий workspace;
  распознавание корневого `[tool.uv.workspace]`, вложенные
  `pyproject.toml` не трогаются. deps: T048.

#### v0.3 — E5.1: защита от озеленения тестов

- **T050** — [2026-07-30] Pre-push защита от озеленения тестов: число
  собираемых тестов ≥ базы (`$DT_STORE/test-baseline`), новые
  skip/xfail только с записью в DECISIONS.md, порог `--cov-fail-under`
  не понижен. deps: —.

#### v0.3 — E12: запуск из правильного каталога

- **T056** — [2026-07-30] `dt run` — запуск целей `[tool.dreamteam.run]`
  из каталога задачи; **отказ** при запуске из чужого worktree, обход
  только `--here`. deps: T036, T051. spec: `specs/T056-run/spec.md`.

#### Находки по дороге

- **T057** — [2026-07-30] Валидация `DT_HOME`-override против путей git
  (находка CodeRabbit в T033). Сейчас override принимается verbatim:
  если пользователь укажет `DT_HOME` внутрь рабочей копии или `.git/`,
  `ensure_store()` создаст там оперативное состояние — нарушение
  инварианта «никогда не создавать внутри git». Инвариант выполняется
  для *вычисленного* дефолта (каталог-сосед по построению); под вопросом
  только **явный аварийный override**. Взвесить: policing escape-hatch
  vs. защита от самострела. deps: T033. Acceptance: `ensure_store`
  отказывается (внятная ошибка), если resolved `DT_HOME` лежит внутри
  `git rev-parse --git-common-dir` или любого worktree; тест на отказ.
- **T059** — [2026-08-01] `dt context` показывает висячие `deps` как блокеры
  (находка qodo в T051). Сейчас `build_context` собирает блокеры только из
  существующих `deps` (`dep in tasks`), поэтому dep, отсутствующий в store,
  молча выпадает — задача с единственным висячим блокером покажет «нет
  блокеров», расходясь с `dt task ready` (там висячий dep = не готова) и с
  `dt task check` (ERROR). deps: T051. Acceptance: `ContextModel` несёт
  `missing_deps: list[str]`; `render_human`/`context_json` показывают их
  отдельно (напр. `блокеры: T003 [doing]; отсутствуют: T999`); тест на задачу
  с висячим dep.

#### v0.4 → v1.0 — эпики без декомпозиции

Берутся в работу после v0.3; T-ID присваиваются при декомпозиции
(правило: ID появляется, когда задача созрела для взятия). См.
дизайн-документ, Часть 3.

- **E3** (v0.4) — слой политики: `.claude/settings.json` deny/allow/ask,
  PreToolUse-хуки, профиль изоляции, `SECURITY-NOTES.md`.
- **E10** (v0.4) — графическая доска `dt board serve` (проекция, не
  диспетчер; без сгенерированных файлов, без процессов).
- **E4** (v0.5) — роли как артефакты `.claude/agents/*.md` (≤ 4:
  reviewer, spec-writer, test-writer, translator).
- **E5.2** (v0.5, по факту потребности) — брифинг по CI `dt ci
  status/brief`.
- **E7 / E8** (после v1.0, по потребности) — MCP-сервер; метрики
  методики (требуют журнала событий).

<!-- Историческая справка: завершённые задачи T002–T005 ушли в
     CHANGELOG → [0.2.0], T001/T006 — в CHANGELOG → [1.0.0]. Все
     завершённые задачи лежат в CHANGELOG.md. Records ниже —
     актуальный backlog. -->

<!--
- **T006** — [2026-05-14] Миграция шаблона на **Copier** для
  устранения «мусора в корне» derived projects.

  **Контекст.** Сейчас инструкция «Как использовать» содержит 9
  ручных шагов (rm TEMPLATE-*.md, очистка BACKLOG/BOARD/DECISIONS/
  CHANGELOG до заготовок, копирование README.template.md, замена
  плейсхолдеров в pyproject.toml, и т.д.). Copier инкапсулирует
  это в `copier copy gh:vlakir/dreamteam ./my-project`. Главная
  фишка copier vs cookiecutter — `copier update`: можно
  подтягивать новые правила методики в уже созданные проекты.

  **Состав:**
  - Перевод репозитория шаблона в Copier-template формат
    (`copier.yml`, папка `template/` с jinja-переменными).
  - Перенос текущих `TEMPLATE-*` и default-name файлов в
    copier-структуру; default-name становятся результатом
    скаффолдинга, а не отдельно лежащими заготовками.
  - Интерактивные prompts: имя проекта, цель (для `CONCEPT.md`),
    стек (Python только / другое), нужен ли pytest / mypy / hooks.
  - Поддержка `copier update` flow.
  - Тесты через pytest: `copier copy` создаёт ожидаемую структуру,
    `copier update` подтягивает изменения.
  - Решить про PyPI публикацию (опционально, на этапе clarify).

  **Требует:** spec в `specs/T006-copier-migration/spec.md` с
  ритуалами clarify + analyze (крупная фича > 1 дня работы).

  **Acceptance:**
  - `copier copy gh:vlakir/dreamteam ./new-project` создаёт чистый
    derived-проект **без TEMPLATE-* мусора**, со всеми методическими
    файлами на месте.
  - `copier update` подтягивает изменения шаблона в существующий
    проект (с возможностью merge user changes).
  - Все 4 pre-push проверки (ruff/format/mypy/pytest) проходят
    на сгенерированном проекте по умолчанию.
  - Сама миграция версионируется как `v1.0.0` (semver major —
    архитектурная переориентация).

  **Приоритет:** после T001 (Branch Protection).
-->

<!-- T013 (multilang) уехала в CHANGELOG → [1.3.0] 2026-05-15.
     T009 (full update diff/merge) переехала в BOARD.md → Doing
     2026-05-15. Spec phase активен:
     specs/T009-full-update/spec.md.
     T007 (qodo replacement) закрыта 2026-05-15: выбран CodeRabbit
     + manual Claude Code hybrid. Запись в CHANGELOG → [Unreleased]
     → Notes. -->

<!-- T021, T022 уехали в CHANGELOG → [1.5.2] 2026-05-15. -->

<!-- T031 (дисциплина тяжёлых тест-прогонов при параллельных worktree)
     закрыта в PR T031-pytest-guard — см. CHANGELOG → [Unreleased] →
     Changed и ADR в DECISIONS.md. -->

<!-- T030 закрыта в PR T030-worktree-methodology (методика
     параллельных worktree + memory-agnostic принцип) — см.
     CHANGELOG → [Unreleased] → Changed. -->

<!-- T023, T024, T025 закрыты в PR T023-methodology-shakedown
     (методика после первой обкатки) — см. CHANGELOG → [Unreleased]
     → Changed. -->

<!-- T026 (Роли команды: Архитектор + Дизайнер) взята в работу
     2026-07-05 — переехала в `BOARD.md → Doing`. Полный контекст и
     фазы — в `specs/T026-team-roles/spec.md`. -->

<!-- T027 (актуализация README) закрыта в PR T026 — см. CHANGELOG
     [Unreleased] → Changed. -->



