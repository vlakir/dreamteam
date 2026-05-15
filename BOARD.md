# Board (dreamteam package)

Kanban-доска разработки `dreamteam`-пакета (To Do / Doing / Done),
один-два WIP в Doing, FIFO в To Do (можно поднимать приоритетное).

**Scope правила нумерации:** `max()` для T-ID считается по
`BACKLOG.md`, `BOARD.md` и `CHANGELOG.md` этого репо.

В derived projects — свой `BOARD.md` (из `src/dreamteam/template/`).

---

## To Do

<!-- Задачи готовые к взятию. Текущий backlog — в `BACKLOG.md`. -->

## Doing

<!-- Максимум 1-2 задачи. -->

- **T017** — Параметризовать выбор package manager в derived
  template (uv / poetry / pip), вместо текущего hardcoded `uv`.
  Закрывает cross-pollination concern: pip-user-у в derived
  проекте не должен видеть `uv sync` в инструкциях для Claude.
  Phase 0 активен: spec в
  `specs/T017-package-manager/spec.md` (Draft, 10 Open Questions
  ждут Clarify).

## Done

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. Очищено при release cut
     1.3.0 — 2026-05-15. -->
