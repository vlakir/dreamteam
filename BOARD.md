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

- **T171** — [2026-10-16] Завершить безопасную автоматическую миграцию
  проектов на OpenCode и подготовить stable 2.0.0 после приёмки и гейтов.
  Spec: `specs/T171-complete-opencode-migration/spec.md`; база раунда
  `e32fbe14179588eaa8c8c75d8b61d69809baf758`. Update и unmanaged apply;
  prerequisite OpenCode, сохранность BOTH/custom, recovery и isolated rehearsal.
  Документальный checkpoint не означает приёмку реализации.


<!-- Максимум 1-2 задачи. -->

## Done

- **T170** — [2026-10-15] Полная миграция на OpenCode и Ensemble.
  Spec: `specs/T170-opencode-migration/spec.md`. База: релиз 1.7.0;
  Anthropic Pro/Max исключены, API Claude и ChatGPT Plus/Pro сохраняются.

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. Очищено при release cut
     1.7.0 — 2026-07-30 (T023/T024/T025/T030/T031/T032 → CHANGELOG
     [1.7.0]; T026 уже был в [1.6.0]). -->
