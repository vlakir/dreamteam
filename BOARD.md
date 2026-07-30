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

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. Очищено при release cut
     1.7.0 — 2026-07-30 (T023/T024/T025/T030/T031/T032 → CHANGELOG
     [1.7.0]; T026 уже был в [1.6.0]). -->

- **T033** — Каркас хранилища и модель задачи (фундамент E1: резолв
  `$DT_HOME`, `<slug>`, ленивое создание store, pydantic-модель `Task`
  с round-trip). `[closed 2026-07-30, PR T033-store-core]`
- **T034** — Базовые операции над задачами: `dt task new/show/move/split`,
  выдача ID через `counter` + `O_EXCL`, `--json`, `parent`/`blocks`.
  `[closed 2026-07-30, PR T034-task-ops]`
- **T035** — Валидация и готовность: `dt task check` (циклы `deps`,
  целостность `parent`, мягкая проверка spec), `dt task ready`, подключение
  `check` в CI/pre-push; свёрнут микро-нит валидатора ID.
  `[closed 2026-07-30, PR T035-task-validation]`
