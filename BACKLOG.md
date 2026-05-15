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

- **T015** — [2026-05-15] Настроить CI для PR-проверок (GitHub Actions).

  **Контекст:** Branch Protection на `main` защищает от прямого
  push, но **не запускает** тесты на PR. На T014 PR #32 это
  привело к тому, что failing test замержился в main (потребовался
  hotfix PR #33). Нужна автоматическая verification на каждом PR
  с blocking merge при fail.

  **Состав:**
  - `.github/workflows/ci.yml` (GitHub Actions workflow).
  - Trigger: `pull_request` event + `push` to `main` для consistency.
  - Steps: `uv sync`, `uv run ruff check .`, `uv run ruff format
    --check .`, `uv run mypy src`, `uv run pytest` (fast suite).
  - Cache uv venv для скорости.
  - Integration tests (`-m integration`) — отдельный job или
    on-demand, не блокирующий fast PR.
  - Required status check в Branch Protection: без green CI
    merge кнопка disabled.

  **Acceptance:**
  - PR с failing проверкой не может быть merged (GitHub disables
    merge button или показывает warning).
  - CI fast suite < 2 min on average.
  - Integration suite запускается отдельно (не блокирует PR).
  - Workflow file в репо, документирован.

  **Платформо-нюанс:** GitHub Actions = GitHub. Если когда-то
  мигрируем на GitFlic/GitLab — переписать в их native CI.
  Поведенческое правило («4 проверки 0 ошибок перед push»)
  остаётся universal.

  **Приоритет:** **выше T013 (multilang)** — без CI повторим slip
  T014 на следующих изменениях template. Это foundational gap
  в нашей quality gate.

- **T013** — [2026-05-14] Многоязыковая поддержка методических
  документов в derived projects.

  **Языки (минимум):** English, Русский, Français, Deutsch, 中文.

  **Подход:** **Variant A — N статических копий** каждого
  методического файла per язык. Решение Разработчика 2026-05-14:
  «5 переводов каждого файла — вопрос дисциплины, справимся».
  Альтернативы рассмотрены и отвергнуты:
  - B (AI translation на лету через Anthropic SDK) — dependency на
    провайдера, latency + cost при `dreamteam init`.
  - C (Hybrid: narrative переводится, rules — на английском) —
    mixed-language файлы выглядят странно для пользователя.
  - D (Defer to community) — не решает боли неанглоязычных
    пользователей сейчас.

  **Scope перевода:** narrative content — `CLAUDE.md` intro и блоки
  описаний, `CONCEPT.md` prompts, `PROJECT.md` заголовки секций,
  `README.md`, `BACKLOG.md` / `BOARD.md` / `CHANGELOG.md` /
  `DECISIONS.md` intros, `specs/spec-template.md` структура секций.

  **НЕ переводятся:** технические термины (ruff/mypy/ADR/kanban/
  scope/WIP-limit), имена файлов, имена CLI команд и flags,
  code blocks, имена kanban-колонок (`To Do` / `Doing` / `Done` —
  international keywords), pyproject.toml / src/ / tests/ / hooks/.

  **Структура (предложение для spec):** в `src/dreamteam/template/`
  — папка `i18n/<lang>/` с translated narrative files; common
  files остаются на root template level без перевода. После
  copier render — post-generation task (через copier `_tasks`)
  переносит `i18n/{{ language }}/*` в root проекта и удаляет
  `i18n/` целиком. Альтернативный layout — full duplicate per
  language через `_subdirectory: "{{language}}"` — обсудить
  в spec.

  **Требует:** spec в `specs/T013-multilang/spec.md` с clarify
  (точная структура, fallback при missing translation, обработка
  заголовков kanban-секций, кто проверяет качество переводов) и
  analyze (drift-risk между языками, maintenance burden, bilingual
  reviewer-ы).

  **Acceptance:**
  - В `copier.yml` появляется prompt `language` с choices
    `[en, ru, fr, de, zh]`, default `en`.
  - `dreamteam init <path> --defaults` (без явного language) даёт
    English derived project.
  - `dreamteam init <path>` с выбранным language — derived проект
    с переведённым narrative content; технические части идентичны
    на любом языке.
  - Integration tests verify rendering для каждого из 5 языков.
  - ADR в `DECISIONS.md` фиксирует выбор Variant A с rejected
    alternatives.

  **Приоритет:** ниже T011 (publish) — international scaling имеет
  смысл только после первых пользователей.

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

