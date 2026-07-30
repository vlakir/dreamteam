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

- **T032** — [closed 2026-07-30, PR T032-derived-ruff-cpy001] Сгенерённые
  проекты падали на своём же pre-push `ruff check` (`CPY001` из свежего
  `ruff`, вышел из preview при `select = ["ALL"]`). Фикс: `CPY001` в
  `ignore`-лист шаблона (`src/dreamteam/template/pyproject.toml`). ADR +
  CHANGELOG `[Unreleased]` → Fixed. Проверено: `dreamteam init` → derived
  `ruff` зелёный; integration 52 passed; полный сьют 151 passed, cov 88%.
- **T023** — [closed 2026-07-30, PR T023-methodology-shakedown] CONCEPT.md —
  leading questions, не contract. Ритуал `CONCEPT.md` в шаблоне: структура =
  опросник для пустого concept; содержательный существующий concept/ТЗ
  принимается как есть, clarify по его содержимому; обязателен только clarify
  + Out of scope в любой форме; immutable сохранён. Правки в
  `template/i18n/ru/CLAUDE.md` + `CONCEPT.md` + re-bootstrap en/fr/de/zh.
- **T024** — [closed 2026-07-30, PR T023-methodology-shakedown] Self-review
  Claude'а опционален при рабочем ревью-боте. Условный flow (bot=baseline;
  self-review дефолт для docs/методика-PR, targeted для нетривиального кода,
  fallback при недоступности бота). Правки в `template/i18n/ru/CLAUDE.md` +
  проектный `CLAUDE.md` + re-bootstrap en/fr/de/zh.
- **T025** — [closed 2026-07-30, PR T023-methodology-shakedown] Closing-правка
  `BOARD.md` (`Doing → Done`) в задачном PR, не парным chore-PR; границы PR по
  логической связности. Правки в `template/i18n/ru/CLAUDE.md` + проектный
  `CLAUDE.md` + re-bootstrap en/fr/de/zh. (Применено к самому этому PR.)
- **T026** — [closed 2026-07-05, текущий PR] Роли команды: Архитектор
  (read-only субагент) + Дизайнер (Claude Design MCP) в шаблоне. Все 9
  фаз §8 + ADR §9 закрыты. Рендер шапка+тело (partials под `_exclude`
  + Jinja-сборщик в `src/dreamteam/_jinja_ext/`), методика ролей + бриф
  Дизайнера через i18n, авто-пикап на `dreamteam update` (новые файлы +
  пост-апдейт-хук `@import`). Спека: `specs/T026-team-roles/spec.md`;
  ADR — `DECISIONS.md`; CHANGELOG `[Unreleased]`. 7 fast + 2 integration
  новых теста; сьют 51 integration зелёный. Версионирование — MINOR
  (следующий release cut).
