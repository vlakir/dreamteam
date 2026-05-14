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

- **T011** — `dreamteam-cli` v1.0.0 опубликован на PyPI 2026-05-14.
  Имя `dreamteam` оказалось занято squatter-аккаунтом с 2019 — PyPI
  package переименован в `dreamteam-cli`, command остался `dreamteam`.
  Скрипт публикации `scripts/publish.sh` + `.secrets` (git-ignored).
  Два ADR в `DECISIONS.md` (naming + publish flow). В CHANGELOG.md
  → [Unreleased].

- **T010** — Добавлен MIT License (`LICENSE` файл, classifier,
  README, ADR). Снимает блокер T011 (PyPI publish). В CHANGELOG.md
  → [Unreleased] → Added.
- **T012** — Создан `CLAUDE.md` в корне репо для разработки `dreamteam`-
  пакета (отдельный документ от `src/dreamteam/template/CLAUDE.md`,
  который попадает в derived проекты через `dreamteam init`).
  В CHANGELOG.md → [Unreleased] → Added.

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. -->
