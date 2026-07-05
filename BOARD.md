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
     1.3.0 — 2026-05-15. -->

- **T029** — [closed 2026-07-06, текущий PR] `dreamteam update` через
  `git merge-file` вместо copier `run_update`. Чинит два оставшихся
  после T028 дефекта (крэш на read-only `.git/commit-graph` +
  разрушение рабочего дерева без отката): merge теперь в temp,
  `.git` не трогается вовсе. Удалена деструктивная run_update-машинерия.
  ADR в `DECISIONS.md` (ревизирует T028/T009), регресс-тест, CHANGELOG
  `[Unreleased]`. Релиз — PATCH.

- **T026** — [closed 2026-07-05, текущий PR] Роли команды: Архитектор
  (read-only субагент) + Дизайнер (Claude Design MCP) в шаблоне. Все 9
  фаз §8 + ADR §9 закрыты. Рендер шапка+тело (partials под `_exclude`
  + Jinja-сборщик в `src/dreamteam/_jinja_ext/`), методика ролей + бриф
  Дизайнера через i18n, авто-пикап на `dreamteam update` (новые файлы +
  пост-апдейт-хук `@import`). Спека: `specs/T026-team-roles/spec.md`;
  ADR — `DECISIONS.md`; CHANGELOG `[Unreleased]`. 7 fast + 2 integration
  новых теста; сьют 51 integration зелёный. Версионирование — MINOR
  (следующий release cut).
