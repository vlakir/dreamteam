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

<!-- T002 (тестирование) и T005 (TEMPLATE-* split) завершены и
     перенесены в TEMPLATE-CHANGELOG.md → [Unreleased]. -->

- **T003** — [2026-05-14] Формализовать дисциплину планирования
  без Scrum-карго-культа.

  Состав:
  - **Milestone-based versioning** (не time-based sprints):
    `[Unreleased]` в `TEMPLATE-CHANGELOG.md` накапливает, переход
    к `vN.0` — когда осмысленно завершено (критерий обсудить).
  - **Retrospective как ритуал** после закрытия milestone:
    короткий разбор «что зашло / что не зашло / правки методики»,
    формат и место обсудить (`TEMPLATE-RETRO.md` отдельным файлом
    или секция в `TEMPLATE-CHANGELOG.md`).
  - **Acceptance criteria** обязательны для задач крупнее
    однострочных правок (формат уже есть в записях T001/T002 в
    BOARD).
  - WIP-limit и continuous flow в BOARD сохраняются (уже есть).

  Не вводим: time-boxed sprints, story points, velocity,
  burndown, daily standup, sprint backlog отдельно от product
  backlog.

  Правило в проектном `CLAUDE.md` (durable) и в глобальном
  `~/.claude/CLAUDE.md`.

- **T004** — [2026-05-14] Ввести immutable документ начальной
  концепции проекта (`CONCEPT.md`).

  Создаётся в начале нового проекта (часто совместно с Claude
  через ритуал встречных вопросов), фиксирует «концепцию на
  салфетке»: цель, пользователи, ключевая функциональность,
  out of scope, ограничения. После фиксации НЕ изменяется —
  служит исторической точкой опоры; современное состояние
  ведётся в `PROJECT.md`. При кардинальной пере-концепции —
  папка `concepts/v1-…md`, `concepts/v2-…md`.

  Состав:
  - `CONCEPT.template.md` как заготовка в шаблоне.
  - Ритуал составления концепции в начале нового проекта (Claude
    задаёт встречные вопросы по слепым зонам) — правило в
    проектном `CLAUDE.md` (durable) и в глобальном
    `~/.claude/CLAUDE.md`.
  - Шаг в инструкции «Как использовать» в README шаблона.
