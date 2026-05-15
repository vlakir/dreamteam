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

- **T018** — Команда для применения dreamteam-template к
  **уже-созданному** проекту (PyCharm new project, `poetry new`,
  `hatch new`, etc.). Пробел между `dt init` (нужен пустой
  каталог) и `dt update` (требует `.copier-answers.yml`).
  Цель: одной командой, конфликты решаются per-file по мере
  возникновения. Phase 0 завершён: spec в
  `specs/T018-apply-to-existing/spec.md` (Analyzed; Q1-Q10
  resolved; 0 🔴 / 4 🟡 / 3 🟢; готов к combined Phase 1+2+3
  implementation — new `dt apply` command, 4-way conflict
  prompt, version bump 1.5.0 → 1.5.1).

## Done

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. Очищено при release cut
     1.3.0 — 2026-05-15. -->
