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

## Повторная независимая репетиция r2 — AC10 исправлен, приёмка блокирована

Дата: 2026-10-16. Новый writer `T171-rehearsal-r2` начал с exact clean
`c089f9b5686d448727a3485e2e6b31a420918c54`, без reset. Проверяемый новый
integrated source: `9ca58222bb3aef1e5e7aa79837d4728c88e5439f`, включает
backend fix `00b52a0b675fde3f1b7bdb46760be078b2f57809`.

| Новый установленный артефакт | SHA256 |
| --- | --- |
| wheel 2.0.0 | `c77ca03b5128776fb670139d21ddc05c83ab556ebb56f00bf7462c60c90a7ada` |
| sdist 2.0.0 | `e169bbe073802edc486d6779581421c37a050a5df238d72a5b992e806a82222e` |

Старые файлы/окружения/evidence не перезаписывались. Каждый новый артефакт
установлен offline в отдельный fresh env через `uv venv --python 3.14` и
`uv pip install --offline --python <env>/bin/python <artifact>`. Каждый
подтвердил metadata `2.0.0` и пути `cli`, `migration`, `migration_store`,
`runtime` только в своём `site-packages`; запуск import proof через `python -I`,
без `PYTHONPATH`/`PYTHONHOME`, CLI через явный installed executable.

Новый private scratch: `dreamteam-T171-rehearsal-r2-747fvsnl`, parent `0700`,
evidence/logs `0600`. `evidence.json` содержит 74 exact commands/exits и
отдельные logs. Все сценарии — fresh собственные копии immutable prepared
**39-file partial methodology** copy либо ранее явно вручную подготовленного
supported 1.7 subset. Это по-прежнему НЕ миграция всей оригинальной конфигурации
и НЕ запуск приложения. Оригинальный HEAD/status до/после совпали; prepared
copy bytes/modes/directories неизменны. Секретные файлы не читались.

### Подтверждённые результаты нового candidate

- Wheel **и sdist**: `dt init --defaults --data language=<lang>` для всех
  `en/ru/fr/de/zh` — PASS; валидный config JSON, 9 YAML roles, нет hardcoded
  model, primary tech-lead с question allow, specialists без question allow.
- Исходная 39-file копия: normal/dry-run/force ожидаемо BLOCK exit 1,
  project snapshot unchanged. Это не новая поддержка исходной 1.6.2 metadata.
- Supported subset: dry-run exit 0 и project/home snapshot unchanged после
  обычного version prewarm **вне project**; normal update exit 0;
  оба полезных реальных rule deltas ровно по одному, custom architect invariant
  и command сохранены, verified legacy sources удалены, answers `2.0.0`.
- **AC10 теперь PASS**: canonical team-roles reference присутствует уже после
  первого update, второй normal update exit 0, полный snapshot project
  bytes/modes/directories/links и private home/recovery строго unchanged.
  Отдельный fresh supported force scenario также PASS.
- Missing prerequisite, synthetic unsupported settings.local, BOTH overlapping
  command conflict: dry-run и force ожидаемые exits 1/1/2; project/home
  unchanged, synthetic secret не попал в output.
- Реальный target replacement I/O fault → public rollback exact original file
  hashes/modes; SIGKILL после source unlink → public resume + повтор no-op;
  SIGKILL после answers publication → public rollback exact originals;
  post-crash user drift → resume/rollback BLOCK без изменения project/store.
  Все PASS. Driver отдельный private script, не production edits.

Первый запуск нового private harness (`dreamteam-T171-rehearsal-r2-mem9f39c`)
остановился на ошибке **моего harness**: он требовал сохранения всей старой
template инструкции вместо полезного нейтрального delta. Исправлена только
экстракция факта; fresh повтор выше прошёл эту строгую проверку. Старый запуск
сохранён, не засчитан как product failure или успешная полная репетиция.

### Новый реальный blocker: vendor probe делает project mkdir в dry-run

На **новом установленном wheel c77ca03** в отдельной supported копии:

```sh
HOME=<fresh-private-home> \
XDG_STATE_HOME=<selected-project>/vendor-state-never-prewarmed \
<new-wheel-env>/bin/dt update <selected-project> --dry-run
```

Остальные XDG paths — вне selected project. Реальный OpenCode `1.19.0`.
**Внутри project vendor никогда не прогревался.** Результат: exit **0**,
сообщение `Migration --dry-run: 24 writes, 4 verified removals; no files changed.`
Но созданы новые project directories:

```text
vendor-state-never-prewarmed/
vendor-state-never-prewarmed/opencode/
```

Exact command/output — private `log-073.txt`; root `xdg-inside-dry`.
Предварительно то же независимо воспроизведено на старом b520 wheel в
`dreamteam-T171-xdg-r2-df0r334t`, что не заменяет новое candidate proof выше.
Реальный normal-case extra probe этим harness не достигнут, поэтому для него
artifact PASS/FAIL не заявляется. Каталоги пустые; это доказанная запись в
project, **не доказанная потеря данных или утечка секрета**.

### Автоматизированные независимые regression tests

Новый owned файл: `tests/test_t171_rehearsal_regressions.py`.

1. Verified bundled 1.7 original answers + нейтрально переписанные BOTH rules,
   custom architect body/command, excluded sentinel/link: first result уже
   canonical; each useful fact once; second normal update exact project/home
   no-op. На old c089 **RED** (role reference count 0). На readonly fixed
   backend `00b52a0` **GREEN**, 4 import module paths подтверждены; own testenv,
   `PYTHONPATH=<fixed>/src` **и** `pytest -o pythonpath=<fixed>/src`.
2. Fresh inside-project XDG state с CI-like executable, моделирующим фактический
   vendor mkdir: strict zero-project-writes и controlled exit 1, для normal
   и dry-run. На integrated `9ca5822` оба **RED**: ровно два лишних каталога.

Последний командный прогон под общим serial lock:

```sh
PYTHONPATH=<integrated>/src flock /tmp/dreamteam-T171-pytest.lock \
  <own-venv>/bin/python -m pytest -o pythonpath=<integrated>/src \
  tests/test_t171_rehearsal_regressions.py --no-cov
# 2 failed, 1 passed; expected remaining zero-write regressions
```

Никаких skips/xfails/ignore и ослабления snapshot assertions. Этот checkpoint
содержит намеренно падающие safety tests для следующего source fix, **не**
проходит release gates и **не** означает acceptance/stable approval.
Нужны отдельный fix round, новый exact candidate hash, fresh artifact rerun
с XDG-inside-project проверкой, затем независимое review и финальные гейты.


## Независимая итерация r3 — runtime ENV и строгие regression proofs

Дата: 2026-10-16. Новый writer `T171-tests-r3`: перед правками подтверждены
devbox, exact clean base `ee7a4255e9c4d74bf97f28317b6c3e4156e5c216` и собственная
ветка; reset не выполнялся. Ownership — существующий regression testfile и
дополнение этого отчёта. Source, другие тесты, lock, bundle, версии, global
config и оригиналы не изменялись. Старые отчёты и evidence сохранены.

`tests/test_t171_rehearsal_regressions.py` теперь содержит **67** сценариев:

- 54 negative cases: `HOME`, четыре `XDG_*_HOME`, `TMPDIR`/`TEMP`/`TMP`, public
  cached `tempfile.tempdir`; inside selected root и относительные paths;
  normal/dry-run/force. Проверяется не только controlled exit 1 и snapshot
  directories/bytes/modes/links, но и **отсутствие вызова version probe** по
  отдельному marker вне project. Recovery/home также строго unchanged.
- 3 positive cases: HOME и cached temp — безопасный **ancestor** selected root,
  пустые XDG/TMP env означают unset. Никакого запрета ancestor как такового.
- 3 symlink runtime-storage cases: внешний lexical path разрешается внутрь
  selected project; controlled отказ без project/home writes.
- 4 HOME-derived default cases: XDG unset, но default `.cache`, `.config`,
  `.local/state` или `.local/share` совпадает с project root; probe не вызывается.
- 2 native fresh init, NOLEGACY/NOJOURNAL: update и unmanaged apply dry-run при
  неиспользуемом XDG state внутри project остаются успешными, без migration
  probe и без mutations.
- 1 AC10 canonical first result/second exact no-op, полезные rules/custom,
  answers и excluded worktree sentinel/link.

RED → GREEN доказан без xfail/skip/ослабления assertions:

1. На own source `ee7a425` absolute inside-root XDG state: normal/dry/force
   **3 RED**, probe marker реально создан.
2. На exact backend-r4 `83cb3f0`: первые 61 cases дали **58 PASS / 3 RED**.
   Остались именно positive empty XDG tests: runtime guard считал empty unset,
   но recovery location возвращал `Path('.')` и ошибку absolute path.
   Дополнительные native 2 и HOME-derived 4 отдельно PASS.
3. После narrow source correction `70f2595e1e029a5015cd5796d189f3f7310daec6`
   в fresh backend-r5: **67 PASS**, 69.97s. Проверены clean HEAD/status и
   реальные пути всех четырёх modules в backend-r5/src. Own testenv создан
   через `uv sync --frozen`; одновременно заданы `PYTHONPATH=<fixed>/src` и
   `pytest -o pythonpath=<fixed>/src`; shared serial flock соблюдён.
4. Дополнительно existing safety subset `test_t171_migration.py -k
   "symlink or native or secret or excluded"` на backend-r4: **37 PASS**,
   включая external no-read/privacy, excluded paths и unrelated native policy.
   Этот файл не редактировался.

Ошибки подготовки native harness (оставленный legacy team-roles и отсутствие
`--defaults` у unmanaged apply) исправлены до принятого native результата;
они не засчитываются как product failures. Root-level штатные ruff check и
format-check, `git diff --check` PASS. Полные release gates — зона лида;
этот source crossrun сам по себе ещё не artifact/release acceptance.


## Финальная installed-artifact репетиция r3 — PASS в проверенном Linux scope

Новый кандидат после runtime guard и EMPTY fallback, source checkpoint
`70f2595e1e029a5015cd5796d189f3f7310daec6`. Старый wheel `c77ca03` не использован
для приёмки нового исправления. SHA256 проверены **до установки**:

| Финальный локальный артефакт 2.0.0 | SHA256 |
| --- | --- |
| wheel | `d0bd120e3fb0bae86cdc73f9ab156c5f1634c81646fff9ab1d6132a3d27523e2` |
| sdist | `417fc7afd1ef76fde4a7368a1957288df2ba35bd5c79e244af0d142e4e23d38c` |

Оба установлены offline через `uv pip` в **собственные новые** private envs,
не editable и не `uv run`. У parent и child удалены `PYTHONPATH`/`PYTHONHOME`,
включён `PYTHONNOUSERSITE=1`. Каждый import proof выполнен через `python -I`:
metadata `2.0.0`, реальные пути всех четырёх modules `cli`, `migration`,
`migration_store`, `runtime` только в соответствующем env/site-packages.
Дополнительно bytes всех четырёх modules **одинаковы** между installed wheel,
installed sdist и source checkpoint `70f2595`.

Новый scratch `dreamteam-T171-rehearsal-r3-9dziv5hu` — `0700`; evidence,
138 command logs и сохранённые private reproduction drivers — `0600`.
Private `evidence.json` содержит **138 exact commands/exits**, package hashes,
import paths и before/after metadata. Старые scratch/evidence не изменены.

### Принятые результаты

| Сценарий | Фактический результат |
| --- | --- |
| Wheel **и sdist**, init `en/ru/fr/de/zh` | Все 10 init PASS; валидный config JSON, 9 YAML roles без hardcoded model; tech-lead primary/question allow, specialists без question allow |
| Исходная неизменная prepared **39-file methodology-only** копия, metadata 1.6.2 | normal/dry/force: ожидаемый exit 1, точная категория unsupported active legacy instructions/CLAUDE.md; project и home/recovery unchanged |
| Явно вручную подготовленный supported 1.7 subset, wheel | dry-run exact zero-project/store writes; normal transfer PASS; force на fresh copy PASS |
| Полезные реальные rules обеих сторон, synthetic architect invariant/command | Каждый факт ровно один раз; verified legacy sources удалены; answers 2.0.0; canonical roles reference уже в первом результате |
| AC10, wheel | Второй normal update exact no-op для bytes/modes/directories/links project и home/recovery |
| Supported subset, независимо installed sdist | dry-run unchanged, normal transfer с обеими полезными rules, второй normal update exact project/home no-op |
| Missing OpenCode, synthetic unsupported settings.local, BOTH conflicting custom command | dry-run/force exits 1/1/2; project/store unchanged; synthetic secret отсутствует в stdout/stderr |
| Реальный target replacement OSError | Controlled update exit 1, публичный rollback exit 0; original file hashes/modes exact |
| SIGKILL после фактического source unlink | Child -9, public resume PASS, полезные rules/custom verified; повтор recovery no-op |
| SIGKILL после фактической answers publication | Child -9, public rollback PASS; original file hashes/modes exact |
| Новый user edit после source-unlink crash | Resume и rollback оба exit 1, edit/project/recovery snapshots unchanged |
| Private recovery modes | Directories 0700, files 0600, вне selected project |

Использован тот же **явно ручной supported 1.7 subset**, описанный выше, с
реальными полезными нейтральными facts и custom role/command. Это не новая
поддержка metadata 1.6.2 и не перенос всей оригинальной конфигурации. Исходные
control files, сохранённые вне selected root, не засчитываются как успешно
перенесённая executable семантика. Приложение и реальные auth/API/server не
запускались; действующие secrets не читались/не копировались.

### Закрытие настоящего ENV zero-write blocker

Реальный OpenCode **1.19.0**, а не только CI-like fake executable. По новой
fresh supported копии для каждой пары переменная/флаг:

- `HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`,
  `XDG_CONFIG_HOME`, `TMPDIR`, `TEMP`, `TMP` направлены в новый, **не существующий
  и никогда не прогретый** путь внутри selected root;
- каждый из normal/dry-run/force: **24 controlled exit 1**, безопасная категория
  outside-project storage; полные project и внешний home/store snapshots
  unchanged, включая **ноль новых пустых каталогов**;
- logs `073/075/…/119` содержат эти 24 фактических отказа. Fake-probe regression
  tests выше независимо доказывают, что при такой ошибке executable не вызывается;
- installed sdist отдельно повторил XDG_STATE_HOME normal/dry/force: все 3
  controlled exit 1, project/store unchanged;
- real EMPTY XDG/TMP, HOME — безопасный ancestor project: отдельные fresh
  normal/dry/force **3 PASS**. В dry-run root unchanged, normal/force verified
  transfer. Пустые env не требуют workaround и не блокируют штатную миграцию.

Никакого prewarming внутри selected project не было. Разрешён обычный
version prewarm **только внешних** vendor defaults в private home; их пустые
служебные каталоги вне root не объявляются project writes. Контракт ограничен
известным поведением pinned OpenCode 1.19.0 и проверенными storage paths;
не заявляется sandbox для произвольного вредоносного executable/wrapper.

### Финальная сохранность и границы принятия

Оригинальный calque HEAD `9602e6fe6b8eb63370eb4f69e2aee9eef23f8b92` и status до
и после совпали, включая прежний untracked MCP-файл без чтения его содержимого.
Prepared 39-file copy bytes/modes/directories unchanged. Каждый сценарий
использовал свою independent private копию, без ссылок к исходному `.git`,
worktrees или secret/settings-файлам. Evidence и полезные private body в Git
не включены.

**Итог r3:** независимая artifact-репетиция описанного Linux scope PASS;
предыдущие AC10 и inside-root ENV blockers воспроизведены и закрыты строгими
повторами. Это **не публикация и не разрешение stable release само по себе**:
финальные полные Linux gates, integrated review/CI/PR policy выполняет лид.
Windows secure migration не заявляется проверенной. Native question UI-widget
не проверялся: config/render PASS не заменяет safe TUI-restart smoke. Exactly-once,
directory-wide atomicity и восстановление после любого power-loss не заявляются.
