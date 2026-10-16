# T171 — Analyze

Дата: 2026-10-16. Анализ базы `e32fbe14179588eaa8c8c75d8b61d69809baf758`.
Это анализ пробелов, не акт приёмки реализации T170 или T171.

## Подтверждённые пробелы

- `cli.py::_plan_merge` сопоставляет `.claude/` → `.opencode/` и CLAUDE.md →
  AGENTS.md, но при наличии destination выбирает его: BOTH теряет legacy input.
  Изменённые удалённые template-файлы сохраняются как legacy без завершения
  переноса. Custom вне old/new managed sets не мигрируются.
- `_apply_plan` сначала валидирует пути, затем последовательно пишет/удаляет;
  I/O-сбой посередине оставляет partial tree, rollback отсутствует.
- `_three_way_update` применяет conflict output и пишет answers до возврата
  conflict count. Это существующая обычная update-семантика, но не безопасное
  завершение миграции: новый migration path не должен продвигать base так.
- `update` считает migrating только legacy rules без AGENTS.md и только без
  force требует доступной базы; BOTH/force могут обходить сохранность.
- `apply` создаёт отсутствующий root и пишет answers после обычных решений;
  legacy-содержимое не является специальным источником. Нужен migration
  preflight до его любых записей/ответов, не после существующего mkdir.
- Dry-run T170 уже ограничен managed scope вместо копирования всего дерева.
  Это преимущество сохранить; recovery не должен вернуть whole-tree copy.
- T170 закрепляет OpenCode 1.19.0 / Ensemble 0.18.0. Нет доказательств для
  безграничного диапазона совместимости; точный pin — минимальный честный контракт.

## Риски → меры

| Риск | Требуемая мера и проверка |
| --- | --- |
| CLI найден, но не запускается | Реальный bounded --version, negative tests, no writes |
| CLI запускает project init | Безопасный cwd, только offline version invocation |
| BOTH/force затирает правило | Учитывать оба входа, validate content, force safety tests |
| Непереносимый hook отключён | Allowlist, unknown blocker до mutation, исходник цел |
| Секрет в diff/backup git | Redaction по значениям в тестах, приватный recovery вне git |
| Ошибка после частичной записи | Durable journal + staged originals + fault injection |
| Journal отстаёт от файла | Сверка факта/fingerprint перед повтором и rollback |
| User edits после прерывания | Stop без затирки, сохранить все версии, ручной recovery |
| История удалена как legacy | Разделить runtime artifacts и historical bundle/tags/ADR |
| Обход symlink/worktrees | Проверять компоненты путей, не рекурсировать exclusions |
| Тестовая копия связана с оригиналом | Независимый root/git-dir, исключить секреты/ссылки заранее |

## Рекомендованный минимальный дизайн

Один локальный migration planner/executor, общий для update/apply, с явными
записями path/action/source fingerprint/expected result/reason. Не вводить DSL,
плагины миграции и отдельный универсальный transaction engine. Обычная update
семантика остаётся вне этого пути. Транзакция scoped на затрагиваемые файлы,
включая answers, а не на весь каталог; перезапуск reconciles состояние.
Обещать exactly-once при произвольном падении нельзя.

Архитектор передал read-only рекомендации: preflight в безопасном cwd,
journal до mutation, verified transfer до delete, completion last, reconcile
фактического дерева при recovery. Эти рекомендации отражены в контракте;
проверка runtime-кода и финальное независимое review ещё предстоят.
