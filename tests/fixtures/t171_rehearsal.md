# T171 — безопасная репетиция (процедура, ещё НЕ результат)

Запускать только лидом после интеграции backend/test checkpoint. Предпочтительный
источник — calque как богатый случай BOTH rules/skills. Оригинал read-only,
приложение/гейты исходного проекта не запускать; runtime probe только локальный
offline OpenCode --version. Никаких личных credentials или реальных secret files.

1. Записать known source path, `git rev-parse HEAD`, status без содержимого и
   fingerprints только согласованных tracked rules/skills. Проверить перечень
   `git ls-tree -r --name-only HEAD`: архивировать только explicit allowlist
   AGENTS.md, CLAUDE.md, .copier-answers.yml, .claude/{agents,commands,skills},
   .opencode/{agents,commands,skills}. Не архивировать settings*, .git,
   worktrees, окружения, ссылки, credentials и не делать whole-tree copy.
2. Проверить tracked allowlist на credentials. Если их отсутствие не доказано,
   вместо копирования подготовить обезличенный synthetic fixture соответствующей
   структуры; честно отметить ограничение. Применить `git archive HEAD -- <paths>`
   в новый пустой isolated root. Архивные symlink исключить до extraction;
   не запускать код/хуки из архива. Секретные ситуации только synthetic marker.
3. Проверить resolved root вне source; отсутствие symlinks, .git и worktrees,
   отсутствие реальных settings*. Отдельный HOME/XDG_STATE_HOME и private store.
   Инициализировать новый независимый git repo без hooks/remotes/alternates;
   проверить `git rev-parse --git-dir`, HEAD и metadata не связаны с оригиналом.
4. На isolated supported fixture: snapshot, dry-run, сверка полного snapshot
   (нет изменений/recovery); migration; verified retained useful rules обеих
   сторон и skills/roles + valid OpenCode config; повтор/no-op. Если исходный
   case unsupported — записать честный BLOCK+unchanged, затем отдельную копию
   с явной поддержанной адаптацией; не нормализовать оригинал и не скрывать BLOCK.
5. Из нового независимого исходного snapshot: synthetic settings.local marker
   => BLOCK без изменений/leak; затем отдельный child abrupt SIGKILL на
   target_applied и legacy_removed до journal ack. Публичный recovery/replay,
   drift после crash => BLOCK без уничтожения новой правки; rollback, если safe.
6. Source status/SHA/fingerprints совпадают с исходными. Не публиковать body
   правил, diff личной конфигурации или credentials. Этот шаблон не заменяет AC.

## Шаблон фактического отчёта

- Integration SHA / test checkpoint SHA:
- Source SHA; allowlisted tracked paths (имена, не содержимое):
- Изоляция root/git-dir/HOME/store; подтверждение отсутствия ссылок/секретов:
- Адаптации только копии и initial unsupported outcome:
- Exact commands; OpenCode version; exit codes; безопасный log path:
- Dry-run unchanged; verified transfer/BOTH; повтор/no-op:
- Injected event; SIGKILL evidence; recovery/rollback/drift outcomes:
- Source unchanged evidence:
- Непроверенные пункты и границы доказательств:
