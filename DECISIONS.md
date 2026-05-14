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
