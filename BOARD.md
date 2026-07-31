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
- **T036** — Размещение и жизненный цикл worktree: `dt worktree
  root/path/list/prune`; путь вычисляется (`$DT_HOME/worktrees/<branch>`),
  факт — из `git worktree list --porcelain`; `prune` консервативен
  (managed-only, слитую ветку удаляет, squash не детектит → пропуск).
  `[closed 2026-07-30, PR T036-worktrees]`
- **T037** — Текстовое представление доски `dt board`: модель
  (`board_model`/`board_columns`, git-free, переиспользуется E10) отделена
  от рендера; секции столбиком `todo→doing→review→done`, `dropped` отсеян,
  сортировка `updated` убыв.; `--json` = columns.
  `[closed 2026-07-30, PR T037-board]`
- **T038** — Поиск задачи по фразе `dt task find`: токены (casefold, Unicode),
  веса `title>tags/branch>body`, статус active>done, морфология через общий
  префикс ≥4 (`курсор`~`курсора`); ранжирование score→updated→id; `--json`
  со score; без эмбеддингов. `[closed 2026-07-30, PR #84]`
- **T058** — `dt task check` предупреждает о дрейфе frontmatter `id` ↔ имя
  файла (follow-up ревью T038): сравнивает сырой `load_task(path).id` с именем
  файла → WARNING (не ERROR — стор самоисцеляется). Acceptance: запись с
  `id`≠stem даёт warning, `check` не падает. `[closed 2026-08-01, PR #85]`
- **T039** — Композитный старт задачи `dt task start`: статус → `doing`,
  генерация ветки `T<NNN>-<slug>` (транслит ru→lat), создание/переиспользование
  worktree, привязка нового worktree (`current-task`/`context.line`), tmux
  rename внутри CLI (тихо вне tmux), `--json` со спекой и Handover. Чистые
  ядра `dt/slug.py` + `dt/starts.py` + `dt/tmux.py`, git-хелперы в `paths.py`.
  `[closed 2026-08-01, PR #86]`
- **T040** — Синхронизация BACKLOG.md `dt backlog sync`: статус-независимая
  проекция store в управляемый блок между маркерами (ручная проза сохранена,
  self-bootstrap), отказ вне основной ветки без `--force`; чистая функция
  расхождения `backlog_divergence` для будущего `dt context` (T051). Ядро
  `dt/backlog.py` (typer-/git-free), обёртка `backlog_cli.py`.
  `[closed 2026-08-01, PR #87]`
