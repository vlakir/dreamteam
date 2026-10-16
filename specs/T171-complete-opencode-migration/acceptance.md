# T171 — Приёмочная матрица

**Статус на 2026-10-16: локальная Linux-приёмка выполнена.** Реализация,
регрессии, installed-artifact rehearsal и независимое safety review приняты
в описанном ниже объёме. Внешние CI/PR-review и публикация являются
релизным гейтом: этот документ не утверждает, что пакет уже опубликован.
Матрица ниже остаётся контрактом; результаты — в разделе доказательств и
rehearsal.md. Настройки, секреты и private raw logs сюда не копируются.

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
| AC19 | Repository tech-lead и свежий init всех 5 языков | YAML frontmatter валиден, 9 ролей; primary tech-lead имеет только question: allow, specialist roles не получают question: allow; нет hardcoded model/provider |

### Согласованная платформа приёмки (дополнение 2026-10-16)

Разработчик явно подтвердил: полного набора release gates на **Linux достаточно**
для T171 stable 2.0.0. Secure legacy migration/recovery на Windows не реализована
и не протестирована; ожидается ранний controlled unsupported без project/recovery
writes. Обычный native OpenCode CLI без legacy/pending migration не блокируется.
Не выдавать Linux-тесты или simulated unsupported checks за Windows-приёмку.

AC19 проверяется static/render fixtures без установленного OpenCode, auth/API
или работающего сервера. Отдельный manual CLI debug smoke может подтвердить
`tools.question=true` на isolated generated project. Ни static tests, ни debug
не принимают фактический UI-опрос: его smoke выполняется отдельно после
безопасного перезапуска активной команды; до этого UI не считается принятым.

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

- [x] Все локальные AC и fault windows подтверждены на integration input
      `ce7cf74f915fe8e87b08e3cb00275f4583508900` и проверенных артефактах.
- [x] Release gates выполнены на Linux; Windows legacy migration не заявлена
      поддержанной/проверенной, native CLI не сломан.
- [x] Репетиция на изолированной копии мигрируемой конфигурации реального
      проекта принята; оригинал untouched. Это не whole-app acceptance.
- [x] Ruff/format/mypy/pytest с покрытием, integration, translation, build и
      twine check зелёные на указанном input. После документального закрытия
      обязательны повторный pre-push gate и CI итогового HEAD.
- [x] Независимое source/test/docs safety review: открытых P1/P2 нет;
      проверки не ослаблены. История находок сохранена в rehearsal.md.
- [x] Внешнее CodeRabbit review выполнено; все пять замечаний оценены и
      исправлены с независимыми регрессиями. Дополнительное замечание о
      повторной repository assertion тоже учтено; состояние тестов изолировано.
- [x] T171 закрывается в своём задачном PR; при release cut T170/T171 перенесены
      в CHANGELOG [2.0.0], а колонка Done очищена. Это техническая приёмка,
      а не утверждение о выполненной публикации.

**Live merge/publication gate:** CI именно последнего HEAD должен быть зелёным
перед merge, все новые внешние замечания должны быть разобраны. Изменяемые
статусы проверяются в [PR #96](https://github.com/vlakir/dreamteam/pull/96),
а не копируются в этот версионированный документ заранее. Публикация допускается
после TestPyPI sanity и установки точной версии; её результат и окончательные
hashes подтверждаются отдельно в
[release 2.0.0](https://github.com/vlakir/dreamteam/releases/tag/2.0.0).

## Доказательства локальной приёмки

- **Input:** `ce7cf74f915fe8e87b08e3cb00275f4583508900`, чистая интеграционная
  ветка, Python 3.14.5 / Linux; controller подтвердил неизменность HEAD за весь
  прогон. Использованы собственная `.venv`, общий pytest mutex и CI-подобный
  PATH без настоящего OpenCode; положительные prerequisites имеют явные fake
  executables, отрицательные проверки ими не обходятся.
- **Гейты:** `uv run ruff check --no-cache .`,
  `uv run ruff format --check --no-cache .`, `uv run mypy src` с новым cache,
  `uv run python scripts/translate_check.py` — PASS; переводы **44/0/0**.
  `uv run pytest` — **353 passed**, 53 integration deselected,
  branch-aware coverage **84.36%** при неизменном пороге **80%**.
  `uv run pytest -m integration --no-cov` — **53 passed**, 353 deselected.
  Логи и controller manifest хранятся приватно; исходный warning Copier Worker
  известен по методике и не подавлялся.
- **Артефакты:** `uv build` и Twine 7 PASS для wheel/sdist 2.0.0. В отдельных
  fresh noneditable окружениях проверены metadata version, site-packages всех
  четырёх runtime-модулей и их совпадение с source input. Wheel runtime SHA256:
  `d0bd120e3fb0bae86cdc73f9ab156c5f1634c81646fff9ab1d6132a3d27523e2`.
  Проверенный sdist до итоговых изменений только отчётов:
  `417fc7afd1ef76fde4a7368a1957288df2ba35bd5c79e244af0d142e4e23d38c`.
  Финальный sdist пересобирается и проверяется заново; опубликованные hashes
  записываются в release notes, без self-referential hash внутри sdist.
- **Историческая база:** producer добавил внутренний template tag 2.0.0;
  object IDs всех десяти прежних тегов, включая 1.7.0, не изменились. Это не
  публикация GitHub tag или PyPI и не удаление compatibility history.
- **Репетиция:** подробный независимый отчёт — [rehearsal.md](rehearsal.md).
  Исходные 39 methodology files конфигурации calque 1.6.2 дают честный
  unsupported BLOCK без изменений. Поддерживаемый сценарий — явно вручную
  подготовленный 1.7 subset с реальными полезными правилами обеих сторон,
  отдельной ролью/командой и сохранённым исходным материалом. Архивирование
  неподдерживаемых исходных controls не считается переносом их поведения.
  Все проверки init пяти языков из wheel/sdist, transfer/repeat и реальные
  I/O/SIGKILL/recovery/drift,
  24 настоящих unsafe ENV и три EMPTY-env positive случая — PASS.
- **Ограничения:** не обещаны universal semantic conversion, Windows secure
  migration, exactly-once или power-loss atomicity. AC19 принимает конфигурацию
  и render/debug evidence; настоящий UI вопрос проверяется отдельно после
  безопасного перезапуска текущего клиента, не объявлен выполненным.

## Внешнее review и повторная приёмка

- CodeRabbit: `4294814700` — исправлена H2-иерархия только нового T171 ADR;
  исторические записи не переписывались.
- `4294814724` — legacy `update` без answers сообщает, что проект unmanaged,
  и указывает `dt apply`; safe-path и pending recovery precede этот guard.
- `4294814735` — state0775 под owner-private HOME0700 проверяется существующей
  ancestor policy, а не безусловно запрещается. UID/symlink/full-chain и строгие
  recovery-leaf0700/journal0600 сохранены. Независимая пара positive/negative
  проверяет настоящий недоступный/доступный постороннему путь; shared pytest
  parents и пользовательские каталоги не chmod-ились.
- `4294814743` — найденный через относительный PATH executable становится
  абсолютным до cwd `/`; исходный symlink launcher сохраняется. `shell=False`
  и отдельный argv не заменены shell-строкой. Дополнительный generic CWE-78
  сигнал не доказывает injection для этого доверенного executable lookup.
- `4294814753` — fixture `legacy_runtime` имеет отдельные HOME и четыре XDG,
  поэтому тестовые originals не записываются в личный state разработчика.
- Low-value комментарий о пяти repository assertions: проверка вынесена в
  отдельный независимый тест, проверки fresh init пяти языков не удалены.
  Qodo сообщил только приостановленную подписку; это не code finding и не
  выполненное review. Billing/подписки автоматически не менялись.
- Независимое targeted review `e51cb98` подтвердило корректность трёх source
  fixes и paired security fixtures; открытых P1/P2 не найдено. Source dependency
  cross-run: **364 passed**, **84.91%** source coverage, **53 integration passed**.
  Cross-worktree instrumentation проверяла реальные module paths; неправильные
  промежуточные coverage/PATH запуски не выдавались за gate.
- Повторная installed-artifact QA после source fixes выполнена целиком в
  fresh noneditable окружениях. Принятый runtime wheel:
  `c0a8305a0e8f5254bf9f14658fb62cf93bc5d50ff193294bf4abb22945da0b15`;
  sdist input: `3aee1d7b08cbafa6a2520403f3754f875365e68267c0b0130b32f9338a657bd9`.
  Подтверждены вся предыдущая матрица и дополнительные actual artifact случаи
  relative PATH, missing answers, безопасный state775, действительно публичный
  unsafe state, foreign UID, leaf/journal/symlink guards. Подробности в последнем
  разделе rehearsal.md; **238 записей команд включают и setup-отказы**, это не
  «238 успешных тестов». Оригинал и immutable подготовленная копия не изменены.
- После изменений только отчётов финальный wheel должен сохранить эту byte
  identity; изменившийся sdist получает новый hash, manifest comparison и
  установочный smoke. Публикуемые hashes не включаются в сам sdist рекурсивно.
