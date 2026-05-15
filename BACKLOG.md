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

<!-- T013 (multilang) переехала в BOARD.md → Doing 2026-05-15.
     Spec phase активен: specs/T013-multilang/spec.md. -->

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

