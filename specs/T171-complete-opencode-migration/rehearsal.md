# T171 — репетиция установленных артефактов

Дата: 2026-10-16. База: `33eaaaf877853b22946a39d04ee0bbdd322bcfbc`.
Платформа: Linux, Python 3.14, фактический локальный OpenCode `1.19.0`.
Исполнитель: независимый tester, свежий чистый worktree `T171-rehearsal`.

**Итог: репетиция НЕ принята.** Обнаружено воспроизводимое нарушение AC10:
второй успешный `dt update` меняет `AGENTS.md`. Прочие подтверждённые ниже
сценарии не заменяют исправления, повторной репетиции и финальных гейтов.

## Кандидат и изоляция

Проверены SHA256 исходных файлов до установки:

| Артефакт | SHA256 |
| --- | --- |
| `dreamteam_cli-2.0.0-py3-none-any.whl` | `b5204eb21d5d7e1a2ea18ac9848e3c07febb9b57c5f8044679f9a4b86ea34b4f` |
| `dreamteam_cli-2.0.0.tar.gz` | `0d179ae54c336c05e6f3371c3400f2cc599dac9c0d31476dff37e6f652953791` |

Каждый установлен отдельно, offline, в **новый** private env:

```sh
uv venv --python 3.14 <candidate-env>
uv pip install --offline --python <candidate-env>/bin/python <absolute-artifact>
```

Родитель и дочерние процессы без `PYTHONPATH`/`PYTHONHOME`,
`PYTHONNOUSERSITE=1`; запуск через явные executable, не `uv run`.
Для обоих env проверены `importlib.metadata.version('dreamteam-cli') == '2.0.0'`
и реальные `__file__` четырёх модулей `cli`, `migration`, `migration_store`,
`runtime`: все под соответствующим env в `site-packages`, не в checkout/src.
Изолирующие процессы использовали также `python -I`.

Scratch `dreamteam-T171-rehearsal-7mirg3f3` сохранён вне Git, parent `0700`,
umask `077`. В нём private evidence, CLI logs, новые env, копии и recovery.
В Git включён только этот обезличенный отчёт. Серверы, auth, API, модели,
глобальные установки и код исходного приложения не запускались.

## Происхождение реальной копии

Источник: calque, SHA `9602e6fe6b8eb63370eb4f69e2aee9eef23f8b92`.
Взята ранее подготовленная independent methodology-only копия, а не новый
whole-tree copy: ровно **39 tracked файлов** по explicit allowlist из
`git archive HEAD`, с manifest SHA256 каждого файла. Все 39 hashes совпали.
Это **не клон всего приложения** и не тест приложения.

В копию входят проектные методические документы, answers, `.gitignore`,
`CLAUDE.md`/`AGENTS.md`, роли/rules/skills обоих namespaces и OpenCode config.
Действующие settings/settings.local, MCP, credentials, env, исходники,
исходный `.git`, worktrees и ссылки не копировались. Проверены отсутствие
symlinks и запрещённых secret/settings-файлов; manifest private `0600`, его
parent `0700`. Подготовленная копия сохранена **неизменной**; каждый сценарий
делался в новой собственной копии.

Для managed update инициализирован новый независимый Git directory внутри
сценария; git-dir соответствует этому root, remotes отсутствуют, alternates
отсутствуют, ссылок к исходному Git нет. Оригиналу разрешены только HEAD/status
до/после. Они совпали, включая неизменённый единственный untracked MCP-файл;
его содержимое не читалось.

## Initial real-input outcome: ожидаемый BLOCK

На исходной методической копии с metadata `1.6.2` выполнены:

```sh
<wheel-env>/bin/dt update <initial-copy> --dry-run
<wheel-env>/bin/dt update <initial-copy>
<wheel-env>/bin/dt update <initial-copy> --force
```

Все три: **exit 1**, безопасная категория
`Unsupported active legacy instructions: CLAUDE.md`.
Полный snapshot project bytes/modes/directories неизменён; dreamteam recovery
не создавался. Прочие возможные unsupported inputs этим первым blocker не
исследованы; автоматический перенос всей реальной конфигурации не заявляется.

Реальный `opencode --version` при первом запуске в свежем private HOME создаёт
свои XDG-каталоги. Для строгого сравнения dry-run они заранее прогреты тем же
разрешённым version probe. Нулевые изменения относятся к project и dreamteam
recovery; не утверждается, что чужой executable вообще не делает собственных
служебных mkdir. Никакой server/login/model operation не выполнялось.

## Supported controlled subset — явная ручная адаптация

На **другой** копии исходных 39 файлов все активные legacy/destination inputs
и answers перемещены в отдельный private retained archive вне selected root.
Оригинальные control fields не отключались/не переписывались под видом
автомиграции. Затем на копии отрендерен известный bundled baseline **1.7.0**,
с контролируемыми answers и `architect_model=inherit`. Это намеренно другой
baseline, **не успешная автомиграция исходной metadata 1.6.2**.

Незатронутые реальные методические документы остаются в root. Добавлены два
точных нейтральных требования из реальной копии: правило корня исходников с
legacy-стороны и правило размера модуля с destination-стороны. Их содержимое
в публичные доказательства не включается. Добавлены synthetic architect body
invariant, custom command и excluded worktree sentinel. Это проверка
контролируемого полезного subset, не универсальная поддержка исходных
hooks/roles/settings и не доказательство сохранения всей конфигурации.

Проверки установленного wheel:

| Проверка | Результат |
| --- | --- |
| `dt update <supported-copy> --dry-run` | exit 0; полный project/home snapshot unchanged после version prewarm |
| Первый `dt update <supported-copy>` | exit 0; answers `_commit=2.0.0` |
| Реальные полезные требования обеих сторон | каждое ровно 1 раз в `AGENTS.md` |
| Synthetic architect body и custom command | каждый invariant ровно 1 раз в destination |
| Verified sources | `CLAUDE.md`, старый architect и command удалены после переноса |
| Исключения | независимый `.git` и `.claude/worktrees` sentinel byte/mode unchanged; parent сохранён |
| Private recovery | вне project; directories `0700`, files `0600` |
| Повтор `dt update` | **exit 0, но FAIL no-op: изменён `AGENTS.md`** |

### Воспроизведение AC10 failure

Из сохранённого `supported-input-template-16` создать новую independent копию,
применить installed-wheel `dt update` дважды. Private reproducer:
`repeat-reproducer`; snapshots до/после сохранены рядом в private scratch.
Остальные project files и recovery не меняются.

| Состояние `AGENTS.md` | Bytes | SHA256 |
| --- | --- | --- |
| После первого update | 170 | `a314724af117d3f5320ddc600dd27911bc01ce48917ff5adc92c3142587e911e` |
| После второго update | 224 | `2da29ac85d89ec3144efadd9d17ce1d1ed9d71f2c61d22ecf8edcf03d682f998` |

Второй update вставляет четыре строки: пустую, `## Team roles — dreamteam`,
пустую, `.opencode/team-roles.md`. Обе реальные rules остаются count `1 → 1`:
потеря этих правил **не** обнаружена. Это нарушение строгого no-op, а не
доказанная потеря данных. Реализация tester-ом не менялась.

## Negative и реальное восстановление

Все сценарии — в отдельных копиях controlled input с candidate wheel.

| Сценарий/команда | Факт |
| --- | --- |
| OpenCode отсутствует в controlled PATH; `update --dry-run`, `update --force` | exit 1; project/recovery 0 writes |
| Synthetic nonempty `settings.local.json`; те же dry-run/force | exit 1; project/recovery unchanged; marker отсутствует в stdout/stderr |
| BOTH custom command с overlapping edits; dry-run/force | exit 2; project/recovery unchanged |
| Реальный первый target `Path.replace` бросает controlled OSError | child exit 1; публичный `migration-recover --rollback` exit 0; исходные file hashes/modes exact |
| Child убит после фактического `CLAUDE.md` unlink до caller acknowledgement | marker fsync, child **-9 SIGKILL**; публичный `migration-recover` exit 0, verified rules/command; повтор recovery no-op |
| Child убит после фактической публикации answers atomic replace | marker fsync, child **-9 SIGKILL**; публичный `migration-recover --rollback` exit 0; исходные file hashes/modes exact |
| После source-unlink SIGKILL внесён новый user edit | resume и rollback оба exit 1; project/store snapshots неизменны, edit и recovery сохранены |

Crash driver — самостоятельный private script, не изменение production/test
framework. Он импортирует установленный candidate, вызывает public CLI `app`
как `dt update`, оборачивает реальные filesystem operations, отправляет себе
SIGKILL только **после** нужного syscall. Recovery вызван отдельным процессом
через установленный executable. Не заявляются directory-wide atomicity,
power-loss safety, exactly-once или автоматическое восстановление любого сбоя.

## Package/init smoke

Wheel: реальные команды `dt init <new-root> --defaults --data language=<lang>`
для **en, ru, fr, de, zh** — exit 0. Проверены валидный JSON `opencode.json`,
ровно 9 валидных YAML role frontmatter, отсутствие hardcoded model и active
legacy files. `tech-lead` — primary с `permission.question: allow`, specialists
не имеют question allow. Sdist: отдельно installed env, minimal init exit 0,
валидный OpenCode config. Это не UI-smoke native question.

Ошибки первоначального private harness (`--language` вместо `--data`, неверно
предположенные языки es/hi) исправлены до принятого smoke; это не ошибки CLI.
Сами отказы и их logs оставлены в private evidence, положительные результаты
относятся только к фактическим пяти поддерживаемым языкам.

## Evidence и границы

Private `evidence.json` фиксирует exact args, exit codes, package import paths,
hashes, before/after source metadata, результаты и имена отдельных logs.
Обезличенные ориентиры: initial logs `010–012`, controlled subset `016–018`,
также отдельные negative/fault/reproducer entries в evidence. Private journals,
конфиги, body исходных правил и абсолютные личные пути в Git не включены.

Финальная проверка: все manifest bytes/modes/directories подготовленной копии
совпадают с началом; source HEAD/status совпадают. Prepared copy и private
evidence не удалялись. Полный pytest/integration/coverage выполняет лид; здесь
heavy tests не запускались. Windows legacy migration не проверялась и не
заявляется поддержанной. Исторические tags/bundles не изменялись исполнителем.

**Следующий обязательный шаг:** исправление AC10 отдельным writer раундом,
новый final candidate hash, повтор необходимого installed-artifact rehearsal
и независимое принятие. Этот report checkpoint не означает release acceptance.
