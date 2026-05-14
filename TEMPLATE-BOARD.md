# Template development board

Kanban-доска **разработки самого шаблона** `vlakir/dreamteam`. Этот
файл — мета-документ; в derived projects он **удаляется** (см.
`rm TEMPLATE-*.md` в `README.md`).

Структура и правила — те же, что и у пользовательского `BOARD.md`:
три колонки (To Do / Doing / Done), один-два WIP в Doing, FIFO в
To Do (можно поднимать приоритетное).

**Scope правила нумерации:** `max()` для T-ID считается по
`TEMPLATE-BACKLOG.md`, `TEMPLATE-BOARD.md` и
`TEMPLATE-CHANGELOG.md` (не по default-name файлам).

---

## To Do

<!-- Здесь — задачи готовые к взятию. Сейчас пусто (после закрытия
     T001). Следующая по плану — T006 (copier migration), но она
     требует spec/clarify/analyze. -->

## Doing

- **T006** — Миграция шаблона на Copier (взята в работу 2026-05-14).
  Spec: `specs/T006-copier-migration/spec.md` (Analyzed). План
  реализации — 5 фаз в spec. Текущая фаза: подготовка spec / pre-
  implementation. Следующий шаг: Phase 1 — copier bootstrap.

## Done

<!-- Закрытые задачи, ждущие переноса в TEMPLATE-CHANGELOG.md
     при следующем релизе. После переноса — очищаем. -->
