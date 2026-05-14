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

### Added

- **MIT License** (T010). `LICENSE` файл в корне репо со стандартным
  MIT-текстом (Copyright (c) 2026 vlakir). В `pyproject.toml`:
  `license = "MIT"` + `license-files = ["LICENSE"]` (PEP 639 syntax).
  README обновлён с линком на LICENSE и note про derived projects
  (которые license-choice не наследуют). ADR в `DECISIONS.md`
  фиксирует выбор и rejected alternatives (Apache 2.0, GPL-3.0,
  BSD-3-Clause). Снимает блокер T011 (PyPI publish).

- **`CLAUDE.md` в корне репо** для разработки `dreamteam`-пакета
  (T012). Отдельный документ от `src/dreamteam/template/CLAUDE.md`
  (который попадает в derived проекты через `dreamteam init`). Этот
  CLAUDE.md описывает правила работы над **самим пакетом**: стек
  (Python 3.14, uv, hatchling, typer, copier), команды разработки
  (uv sync / pytest / dreamteam init smoke / uv build), pre-push
  контракт (4 проверки), специфика репо (two CLAUDE.md, template
  exclude из ruff/mypy, copier.Worker deprecation, MVP update
  limitation), task numbering (T<NNN>), Git workflow (Branch
  Protection, squash merge, code review). Глобальные правила в
  `~/.claude/CLAUDE.md` применяются как есть; этот файл — только
  специфика репо.

### Changed

- **`TEMPLATE-*.md` → default names** в корне репо. После того как в
  T006 заготовки для derived переехали в `src/dreamteam/template/`,
  префикс `TEMPLATE-` стал избыточным — `BACKLOG.md` / `BOARD.md` /
  `CHANGELOG.md` / `DECISIONS.md` в корне репо теперь однозначно
  относятся к разработке самого `dreamteam`-пакета. Live references
  в README / pyproject / самих файлах обновлены; historical entries
  в CHANGELOG / DECISIONS / spec.md **не** правлены (immutable).

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
