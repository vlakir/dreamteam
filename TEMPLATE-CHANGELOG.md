# Template evolution log

Журнал эволюции **самого шаблона** `vlakir/dreamteam` между версиями.
**Не путать с `CHANGELOG.md`** — тот предназначен для конкретного
проекта, созданного из шаблона.

Этот файл живёт только в репозитории шаблона. При создании нового
проекта из шаблона `TEMPLATE-CHANGELOG.md` **удалить** вместе с
прочими `TEMPLATE-*.md` (см. инструкцию в `README.md`).

Формат — упрощённый
[Keep a Changelog](https://keepachangelog.com/) с группировкой по
версиям шаблона и категориям (Added / Changed / Fixed / Removed).
Дата в заголовке — дата выпуска версии шаблона.

---

## [Unreleased]

Изменения, накопленные после `v0.1.0`. Будут зафиксированы как
следующая версия по завершении текущего цикла. При закрытии
добавится секция `### Retrospective` (по правилу дисциплины
планирования из T003).

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
