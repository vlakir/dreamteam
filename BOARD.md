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

## Done

- **T012** — Создан `CLAUDE.md` в корне репо для разработки `dreamteam`-
  пакета (отдельный документ от `src/dreamteam/template/CLAUDE.md`,
  который попадает в derived проекты через `dreamteam init`).
  Готово к переносу в `CHANGELOG.md → [Unreleased]` при следующем
  релизе.

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. -->
