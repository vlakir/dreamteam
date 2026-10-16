# T171 — Приёмочная матрица

**Статус на 2026-10-16: НЕ ВЫПОЛНЕНО.** Все пункты ниже — требования к
исполнению, не результаты. Документальный checkpoint не принимает реализацию.
Для каждого результата записать exact commit, команду/fixture, outcome и
безопасную ссылку на журнал. Не копировать настройки/секреты в доказательства.

## Автоматические AC

| ID | Сценарий | Проверяемый результат |
| --- | --- | --- |
| AC01 | PATH missing, executable broken/nonzero/nonexecutable, timeout, malformed version, версия ниже/выше 1.19.0 | Exit 1; ясная причина; ноль project/recovery writes, prompts/answers/deletes, включая force |
| AC02 | Реальный local opencode 1.19.0 --version | Запускается на хосте миграции, bounded/offline, безопасный cwd, без auth/API/MCP/server |
| AC03 | Managed update legacy-only из bundled 1.7.0 | Правила/роли/custom перенесены в валидный OpenCode result, source удалён только после verify, answers last |
| AC04 | Managed update BOTH, разные custom additions обеих сторон | Ни одна полезная правка не теряется; конфликт → 2 без mutation/продвижения base |
| AC05 | Unmanaged apply legacy-only и BOTH, без старой Copier-базы | Аналогичная сохранность; answers не создаётся до полного verify |
| AC06 | Custom roles/commands/rules, edited и unchanged managed | Поддержанные преобразования verified; unsupported не маскируется копированием |
| AC07 | Unknown settings/hooks, invalid config, secret settings.local marker | Exit 1 до записи, source intact, нет secret marker в stdout/stderr/diff/git |
| AC08 | Force update; apply keep/overwrite/save-as-new | Не обходят prerequisite, unsupported, BOTH preservation и verified-delete |
| AC09 | Dry-run update/apply legacy/BOTH/unsupported/force | Не меняет root, metadata, answers; не создаёт backup/journal; secret-safe report, только selected root |
| AC10 | Повтор успешной миграции | No-op относительно результата первого запуска, без duplicate rules/roles/backup churn |
| AC11 | Symlink source/destination/intermediate, .git, .claude/worktrees | Не следовать/не удалять/не изменять exclusions; unsafe required paths блокируют; родитель с exclusions сохранён |
| AC12 | Нет managed base/bundle/git при legacy update | Безопасный отказ без overwrite потери данных, также force |
| AC13 | Backup создать невозможно / permissions insecure | До mutation отказ; source и answers intact; recovery files 0600 / directory 0700 вне git/legacy |
| AC14 | Реальные faults на каждом этапе таблицы ниже | Без ложного success; rollback либо явно доступный recovery; повтор безопасен |
| AC15 | User edits между планом и apply / после interruption | Revalidate обнаруживает drift, не затирает новые правки; обе версии сохранены |
| AC16 | Обычный native OpenCode update/apply без legacy | Unrelated conflict semantics не расширены; текущие регрессии зелёные |
| AC17 | Чистый init, все 5 языков | Только OpenCode active artifacts, нет Claude CLI/Max hints; валидная методика/роли |
| AC18 | Package install/update, wheel/sdist | Не сканирует/не меняет репозитории; сохранены historical tags/base и Anthropic API support |

Negative prerequisite cases прогнать для обоих entrypoints и проверить не только
байты существующих файлов, но и отсутствие новых каталогов/answers/recovery.
Тесты используют локальные fake binaries без сети; AC02 отдельно проверяет
реальный бинарник. Ни один тест не требует личных ключей, login или провайдера.

## Fault-injection/recovery matrix

| Окно прерывания/ошибки | Ожидаемое доказательство |
| --- | --- |
| Staging originals/journal до root writes | Источник неизменён, незавершённый state не completed |
| После первой target write до journal update | Повтор сверяет факт по fingerprints, не повторяет разрушительно |
| Между несколькими target writes | Доступен безопасный rollback/recovery с исходными bytes |
| После verify target, до legacy delete | Старый источник не потерян, повтор проверяет фактический target |
| Во время legacy deletes | Originals доступны; partial state не completed, повтор восстанавливаем |
| Перед/во время answers + completion finalize | Base не считается продвинутой при незавершении; reconcile устраняет неоднозначность |
| Сбой самого rollback / последующие user edits | Recovery сохраняется; нет ложного success/потери новых правок; конкретные инструкции |

Для каждого окна проверить повторную команду и восстановление. Не заявлять
атомарность каталога или exactly-once на основании одного happy-path теста.

## Обязательная репетиция на копии реального проекта

1. Взять один реальный проект как источник **только чтения**, записать исходный
   SHA и безопасные fingerprints. В отдельном root сделать обезличенную копию:
   исключить действующие settings.local/credentials, .git/worktrees/окружения
   и внешние ссылки; секретные случаи заменить synthetic marker fixtures.
   Не запускать whole-tree copy с обходом ссылок и не писать в оригинал.
2. До миграции подтвердить независимый root/git-dir и отсутствие ссылок на
   оригинал/общие worktrees/секреты. Никаких package/runtime действий до этого.
3. На копии выполнить dry-run, миграцию, проверку сохранённых правил/ролей/BOTH
   и валидности OpenCode, повтор (no-op). CLI prerequisite — локальный offline.
4. Из независимого исходного fixture повторить injected interruption/recovery
   и unsupported-setting/hook отказ; источник не уничтожен, секретов в report нет.
   Допустим честный initial BLOCK unsupported без изменения копии, затем
   supported-сценарий после явно описанной адаптации только копии. Не обещать
   автоматический бесконфликтный перенос любого произвольного проекта.
5. Сверить, что оригинал не менялся. В отчёте: isolated fixture description,
   точные команды, версии, checkpoint, exit codes, recovery outcome и границы
   доказательств, **не содержимое личных файлов**.

## Финальный gate

- [ ] Все AC и fault windows подтверждены на итоговом integration commit.
- [ ] Репетиция на изолированной реальной копии принята; оригинал untouched.
- [ ] Ruff/format/mypy/pytest с покрытием, integration, translation, build и
      twine check зелёные; результаты привязаны к финальному SHA.
- [ ] Независимое review и все внешние замечания разобраны, safety не ослаблена.
- [ ] Только после этого stable 2.0.0, PR/release по политике; T171 Doing → Done
      в задачном PR. Этот spec checkpoint сам по себе ни один пункт не закрывает.
