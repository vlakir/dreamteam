# Template development backlog

Парковка идей и задач **для разработки самого шаблона**
`vlakir/dreamteam`. Этот файл — мета-документ; в derived projects он
**удаляется** (см. инструкцию `rm TEMPLATE-*.md` в `README.md`).

Структура и правила — те же, что и у пользовательского `BACKLOG.md`:
порядок имеет значение (сверху — что планируется ближайшим),
формат — `- **T<NNN>** — [<дата>] <описание>`. Когда задача берётся
в работу — переезжает в `TEMPLATE-BOARD.md → To Do`.

**Scope правила нумерации для шаблона:** `max()` для T-ID считается
по `TEMPLATE-BACKLOG.md`, `TEMPLATE-BOARD.md` и
`TEMPLATE-CHANGELOG.md`. Default-name файлы (`BACKLOG.md` /
`BOARD.md` / `CHANGELOG.md`) — заготовки для derived users, их
содержимое в формуле `max()` для шаблона **не участвует**.

## Items

<!-- Завершённые задачи v0.2.0 (T002, T003, T004, T005) перенесены
     в TEMPLATE-CHANGELOG.md → [0.2.0]. Записи ниже — план v0.3.0. -->

<!-- T006 — Миграция на Copier — переехала в TEMPLATE-BOARD → Doing.
     Spec в specs/T006-copier-migration/spec.md. -->

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

- **T011** — [2026-05-14] Опубликовать `dreamteam` v1.0.0 на PyPI.

  `uv build` готов (см. `TEMPLATE-DECISIONS.md → T006 ADR →
  Process для release на PyPI`). Нужно: PyPI API tokens
  (TestPyPI + real), затем `uv publish --publish-url
  https://test.pypi.org/legacy/`, smoke-test через `pip install
  --index-url=test`, затем `uv publish` на основной.

  **Блокер:** требует ручного действия Разработчика (credentials).

- **T010** — [2026-05-14] Выбрать и добавить LICENSE.

  README ссылается на «to be added». Перед PyPI publish (T011)
  нужен license file (LICENSE) в корне + classifier в `pyproject.
  toml`. Кандидаты: MIT (permissive, common), Apache-2.0 (with
  explicit patent grant), GPL-3.0. Выбор Разработчика.

- **T009** — [2026-05-14] Полноценный `dreamteam update` (diff/merge).

  Текущий MVP update делает `run_copy(..., overwrite=True)` —
  re-applies template, теряет user-edits в template-managed
  файлах. Полноценный `copier.run_update` требует git-tracked
  template, чего нет у PyPI-distributed package.

  Подходы: (1) bundle bare git repo внутри `src/dreamteam/template/`,
  (2) temp-clone-with-git перед update, (3) другая стратегия.
  Требует spec.

- **T007** — [2026-05-14] Найти замену для qodo-code-review.

  **Контекст.** qodo исчерпал monthly quota к концу ночной сессии
  14 мая (PR #14 прошёл без стороннего review). Чтобы поддерживать
  правило «сторонние ревью не игнорировать», нужна стабильная
  замена.

  **Опции для оценки:**
  - **GitHub Apps:** CodeRabbit, Sweep AI, Sonarcloud (free tier).
  - **Self-hosted:** запуск Claude API через GitHub Actions на
    `pull_request` событие (вызов anthropic SDK, comment в PR).
  - **Hybrid:** разные сервисы для разных типов проверок (например,
    Sonarcloud для security + свой бот для process compliance).

  **Acceptance:**
  - На новом PR в `vlakir/dreamteam` появляется content-aware
    review (не просто «LGTM») без quota-ограничений, либо с
    бесплатным quota достаточным для 1-2 PR/день.
  - Содержательное качество замечаний хотя бы сопоставимо с qodo
    (по результатам обкатки на 3-5 PR).

  **Приоритет:** ниже T006 — но не низкий: без стороннего review
  методика теряет «второй взгляд» как ритуал.

