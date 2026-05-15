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

- **T009** — Полноценный `dreamteam update` (diff/merge) — заменяет
  текущий MVP `run_copy(..., overwrite=True)` на three-way merge,
  чтобы derived проекты могли подтягивать новые правила методики
  без потери локальных правок. Phase 0 активен: spec в
  `specs/T009-full-update/spec.md` (Draft, ждёт Clarify ответов
  Разработчика).

## Done

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. Очищено при release cut
     1.3.0 — 2026-05-15. -->
