# Backlog (dreamteam package)

Парковка идей и задач **разработки самого `dreamteam`-пакета**
(scaffolding CLI на Copier). В derived projects (создаваемых через
`dreamteam init`) — свой собственный `BACKLOG.md` с другим
содержимым; они не пересекаются, потому что репо `dreamteam`
содержит template как **package data** в `src/dreamteam/template/`,
не как файлы в корне.

Структура и правила: порядок имеет значение (сверху — что
планируется ближайшим), формат —
`- **T<NNN>** — [<дата>] <описание>`. Когда задача берётся в работу
— переезжает в `BOARD.md → To Do`.

**Scope правила нумерации:** `max()` для T-ID считается по
`BACKLOG.md`, `BOARD.md` и `CHANGELOG.md` этого репо. Раньше
(до v1.0.0) файлы имели префикс `TEMPLATE-`; ADR об обратном
ренейме — в `DECISIONS.md`.

## Items

<!-- Историческая справка: завершённые задачи T002–T005 ушли в
     CHANGELOG → [0.2.0], T001/T006 — в CHANGELOG → [1.0.0]. Все
     завершённые задачи лежат в CHANGELOG.md. Records ниже —
     актуальный backlog. -->

<!--
- **T006** — [2026-05-14] Миграция шаблона на **Copier** для
  устранения «мусора в корне» derived projects.

  **Контекст.** Сейчас инструкция «Как использовать» содержит 9
  ручных шагов (rm TEMPLATE-*.md, очистка BACKLOG/BOARD/DECISIONS/
  CHANGELOG до заготовок, копирование README.template.md, замена
  плейсхолдеров в pyproject.toml, и т.д.). Copier инкапсулирует
  это в `copier copy gh:vlakir/dreamteam ./my-project`. Главная
  фишка copier vs cookiecutter — `copier update`: можно
  подтягивать новые правила методики в уже созданные проекты.

  **Состав:**
  - Перевод репозитория шаблона в Copier-template формат
    (`copier.yml`, папка `template/` с jinja-переменными).
  - Перенос текущих `TEMPLATE-*` и default-name файлов в
    copier-структуру; default-name становятся результатом
    скаффолдинга, а не отдельно лежащими заготовками.
  - Интерактивные prompts: имя проекта, цель (для `CONCEPT.md`),
    стек (Python только / другое), нужен ли pytest / mypy / hooks.
  - Поддержка `copier update` flow.
  - Тесты через pytest: `copier copy` создаёт ожидаемую структуру,
    `copier update` подтягивает изменения.
  - Решить про PyPI публикацию (опционально, на этапе clarify).

  **Требует:** spec в `specs/T006-copier-migration/spec.md` с
  ритуалами clarify + analyze (крупная фича > 1 дня работы).

  **Acceptance:**
  - `copier copy gh:vlakir/dreamteam ./new-project` создаёт чистый
    derived-проект **без TEMPLATE-* мусора**, со всеми методическими
    файлами на месте.
  - `copier update` подтягивает изменения шаблона в существующий
    проект (с возможностью merge user changes).
  - Все 4 pre-push проверки (ruff/format/mypy/pytest) проходят
    на сгенерированном проекте по умолчанию.
  - Сама миграция версионируется как `v1.0.0` (semver major —
    архитектурная переориентация).

  **Приоритет:** после T001 (Branch Protection).
-->

<!-- T013 (multilang) уехала в CHANGELOG → [1.3.0] 2026-05-15.
     T009 (full update diff/merge) переехала в BOARD.md → Doing
     2026-05-15. Spec phase активен:
     specs/T009-full-update/spec.md.
     T007 (qodo replacement) закрыта 2026-05-15: выбран CodeRabbit
     + manual Claude Code hybrid. Запись в CHANGELOG → [Unreleased]
     → Notes. -->

- **T021** — [2026-05-15] `template/hooks/pre-push` должен
  пропускать initial push.

  **Контекст.** Хук в `src/dreamteam/template/hooks/pre-push`
  отклоняет любой push, где `remote_ref` совпадает с
  `refs/heads/main` или `refs/heads/master`. Это корректно
  для **обычной работы** (всё через feature-ветку и PR), но
  ломает **bootstrap-сценарий нового проекта**: после
  `git init && git commit -m "initial commit"` единственный
  способ опубликовать репозиторий — `git push -u origin main`,
  и этот push хук блокирует, заставляя использовать
  `--no-verify` (как пришлось в `efactory`, см. recent session
  log 2026-05-15 19:41).

  **Корень.** Initial push отличается от регулярного push в
  `main` тем, что на remote такой ветки ещё **нет** —
  `_remote_sha` в stdin-формате хука равен 40 нулям
  (`0000000000000000000000000000000000000000`). Это
  безопасный, легко детектируемый bootstrap-маркер.

  **Состав правки:**
  - В цикле `while read` добавить проверку:
    если `_remote_sha == "0000000000000000000000000000000000000000"` —
    разрешить (`continue` / no exit), параллельно вывести
    краткое info-сообщение «detected initial push, allowing
    bootstrap».
  - Обновить header-комментарий хука: объяснить, что initial
    push разрешён.
  - Unit-тест: smoke-проверка скрипта через подачу
    stdin-stub-а в `bash hooks/pre-push` (одна строка с
    `_remote_sha = 40 zeros` → exit 0; обычная строка с
    `_remote_sha != zeros` → exit 1). Тестировать в
    fast-suite через `subprocess` (как уже сделано для
    других CLI-вещей).

  **Acceptance:**
  - `bash hooks/pre-push <<< "refs/heads/main <sha> refs/heads/main 0000000000000000000000000000000000000000"`
    → exit 0 (initial push разрешён).
  - `bash hooks/pre-push <<< "refs/heads/feat <sha> refs/heads/main <existing_sha>"`
    → exit 1 (обычный push в main по-прежнему запрещён).
  - В derived-проекте после `dt init && cd <project> && git
    init && git add . && git commit -m initial` команда
    `git push -u origin main` (если remote свежий) не
    требует `--no-verify`.
  - Тест добавлен в fast-suite (`tests/test_*.py`),
    coverage не снижается ниже 80%.

  **Тип:** правка template-файла + новый тест. Через PR в
  dreamteam-репо, version bump PATCH (1.5.1 → 1.5.2),
  bundle re-tag нужен (`scripts/update_bundle.py 1.5.2`).

- **T022** — [2026-05-15] `template/.gitignore` пропускает
  `.secrets` без расширения.

  **Контекст.** В `src/dreamteam/template/.gitignore` секция
  «Secrets / config» покрывает `.env`, `.secrets.*`,
  `.secrets.toml`, `secrets.env` — но не **`.secrets`**
  плоского имени (без расширения, source-able shell-файл с
  токенами). Это ровно тот формат, который шаблон сам же
  использует в `scripts/publish.sh` для PyPI-токенов (см.
  CHANGELOG [1.3.0] → «scripts/publish.sh + .secrets»).
  Обнаружено при bootstrap-е `efactory` 2026-05-15: пришлось
  доруками править `.gitignore`, прежде чем класть туда
  токены, иначе риск утечки в первый коммит.

  **Состав правки:**
  - В template `.gitignore` секция «Secrets / config»: три
    строки `.secrets.*` / `.secrets.toml` / `secrets.env`
    консолидировать в `.secrets*` (покрывает `.secrets`,
    `.secrets.toml`, `.secrets.env`, `.secrets.local` и т.п.).
    `.env` оставить отдельно (логически другой класс файла).
  - Можно дополнительно добавить `*.secret` / `*.secrets` для
    устойчивости — обсудимо.

  **Acceptance:**
  - В свежесозданном `dt init`-проекте файл с именем `.secrets`
    (без расширения) попадает в `git status` как ignored.
  - Существующие шаблоны имён (`.secrets.toml`, `.secrets.env`,
    `secrets.env`, `.env`) продолжают игнорироваться.
  - Unit-тест в fast-suite: после `dt init` в tempdir создать
    `.secrets`, `git status --ignored` показывает его в
    `Ignored files`. Coverage не падает.

  **Тип:** правка template-файла + тест. Через PR в dreamteam-
  репо, version bump PATCH. Логично совместить с T021 в одном
  release cut (1.5.2) — оба касаются «bootstrap нового проекта»
  и обнаружены в одной обкатке.

- **T023** — [2026-05-15] Смягчить требование к структуре
  `CONCEPT.md` — это leading questions, не формальный
  contract.

  **Контекст.** В `efactory` (первый derived-проект по методике)
  Разработчик пришёл с заранее написанным детальным ТЗ (~2600
  строк, версия 5.1). Claude сделал замечание про несоблюдение
  заданной структуры (Цель / Пользователь / Ключевая
  функциональность / Out of scope / Ограничения и догадки) —
  и это абсурд: зрелое ТЗ облегчает работу, а не нарушает её.
  Claude должен был принять concept как valid и провести clarify
  по слепым зонам, а не требовать перекладки в шаблонные
  заголовки.

  **Корень.** В глобальном `~/.claude/CLAUDE.md` (раздел
  «Ритуал составления `CONCEPT.md`», строки 161+) структура
  подана как **обязательный список разделов** — без оговорки,
  что это **leading questions для пустого concept**, не жёсткий
  contract. Шаблон `CONCEPT.md` в `template/i18n/<lang>/`
  закрепляет это визуально (готовые заголовки).

  **Состав правки:**
  - В `~/.claude/CLAUDE.md` раздел «Ритуал составления
    `CONCEPT.md` в новом проекте» переписать так:
    - Структура шаблона — **рекомендация / опросник**, не
      требование к финальной форме.
    - Если в репозитории уже есть содержательный
      `CONCEPT.md` / `ТЗ.md` / любой эквивалент — Claude
      **принимает его как есть** и проводит clarify по
      слепым зонам по его содержимому, не требуя
      перекладки в шаблонные заголовки.
    - Единственный обязательный пункт ритуала — **clarify**
      (встречные вопросы по слепым зонам). Out of scope
      остаётся «главным разделом» как защита от scope creep,
      но может быть выражен в любой форме внутри уже
      существующего документа.
    - Immutable-инвариант (concept не редактируется после
      фиксации) сохраняется.
  - В `src/dreamteam/template/i18n/ru/CONCEPT.md` (source of
    truth) добавить leading comment-блок: «эта структура —
    подсказка для пустого concept; если у вас уже есть
    детальное ТЗ, замените содержимое целиком, главное —
    раздел Out of scope в любой форме». Сохранить
    immutable-маркер.
  - Re-bootstrap `en/fr/de/zh` версий `CONCEPT.md` через
    Claude Code session (паттерн T013 multilang),
    `source_hash` обновить, прогнать `translate_check.py`.
  - В `src/dreamteam/template/i18n/<lang>/CLAUDE.md` (×5)
    проверить раздел про CONCEPT-ритуал, привести в
    consistency с новой формулировкой; обновить
    `source_hash` где нужно.

  **Acceptance:**
  - В свежем derived-проекте свежая Claude-сессия, видя
    содержательный `CONCEPT.md` нестандартной формы, **не
    делает замечание про структуру** и предлагает clarify по
    содержимому.
  - В глобальном `~/.claude/CLAUDE.md` явно указано: структура —
    leading questions, не requirement.
  - `translate_check.py` проходит чисто после регенерации
    переводов.
  - 4 pre-push проверки зелёные.

  **Тип:** методическая правка (глобальный CLAUDE.md) +
  правка template-файлов + multilang re-bootstrap. Через PR
  в dreamteam-репо, version bump MINOR (1.5.x → 1.6.0) —
  это правка контракта между Claude и Разработчиком в начале
  нового проекта, не bugfix. Координировать с T020 (тоже
  правит глобальный CLAUDE.md): можно сделать T020 → T023
  последовательно одной сессией, либо параллельно в разных
  PR, если diff-ы не пересекаются.

- **T024** — [2026-05-15] Self-review Claude'а опционален при
  наличии рабочего внешнего ревью-бота.

  **Контекст.** Текущая методика требует self-review Claude'а
  на **каждый** PR по 7-пунктовому чеклисту (scope /
  архитектура / код / линтеры / документация / соглашения /
  безопасность), а сторонние ревью (CodeRabbit) — «не
  игнорировать, обсуждать». На практике с CodeRabbit (T007,
  v1.5.0) бот покрывает ровно тот же круг вопросов
  (catches scope drift, security, style, конкретные баги),
  и self-review Claude'а — дублирование с confirmation bias
  (Claude ревьюит свои же изменения). Hybrid-стратегия из
  CHANGELOG `[1.5.0]` (CodeRabbit baseline + manual Claude
  для нетривиальных PR) уже эту проблему фиксировала
  поведенчески, но формальное правило в `CLAUDE.md` не
  обновлялось.

  **Новое правило (предлагаемая формулировка):**

  - **Дефолт при подключённом боте.** Если в проекте
    подключён рабочий автоматический ревью-сервис
    (CodeRabbit, qodo-code-review, или аналог), который
    ревьюит каждый PR — self-review Claude'а **не
    требуется** по умолчанию. Бот = baseline review.
  - **Targeted Claude-review** — опционально, по запросу
    Разработчика или собственной инициативе Claude, если
    PR нетривиален (архитектурное изменение, security-
    sensitive code, сложный scope). Не формальный 7-
    пунктовый pass, а deep review по конкретной зоне риска.
  - **Исключение — methodology / docs PR.** Бот заточен
    под код; PR с правками только markdown / методики
    (`*.md`, `specs/**`, `docs/**`, ветки `meta/*` /
    `rules/*`) бот ревьюит слабо. Здесь self-review
    Claude'а остаётся **дефолтом** (по тому же 7-пунктовому
    чеклисту, адаптированному под доку: scope / коherence /
    cross-refs / typos / methodology consistency).
  - **Fallback при недоступности бота** (rate-limit,
    monthly quota исчерпана, сервис лёг). Если бот не
    прошёл по PR (например, CodeRabbit не отчитался в
    течение разумного окна) — Claude делает self-review,
    чтобы не оставлять PR без review. Memory
    `feedback_coderabbit_retrigger.md` про
    `@coderabbitai review` retrigger продолжает действовать.

  **Состав правки:**

  - `~/.claude/CLAUDE.md` — раздел «Code review каждого
    PR» (строки 240+) переписать: убрать «по умолчанию
    ревьюер — Claude», поставить условный flow с тремя
    ветками выше.
  - `~/.claude/projects/-home-vlakir-programming-dreamteam/memory/feedback_review_each_pr.md`
    — обновить под новое правило либо deprecate
    (заменить более точным feedback-memory про conditional
    self-review). MEMORY.md index обновить.
  - `/home/vlakir/programming/dreamteam/CLAUDE.md` —
    строка 109+, упомянуть conditional flow с ссылкой на
    глобальный CLAUDE.md для деталей.
  - `src/dreamteam/template/i18n/ru/CLAUDE.md` — строки
    131+, 171+ обновить под новую формулировку (source
    of truth).
  - Re-bootstrap `i18n/{en,fr,de,zh}/CLAUDE.md` через
    Claude Code session, `source_hash` обновить,
    `translate_check.py` прогнать.

  **Acceptance:**

  - В новом проекте с подключённым CodeRabbit Claude
    **не делает** формальный 7-пунктовый self-review на
    каждый code-PR; ограничивается submit PR + ожидание
    бота.
  - В PR на правки markdown / методики Claude
    **продолжает** делать self-review.
  - При rate-limit / недоступности бота на code-PR Claude
    делает self-review как fallback.
  - 4 pre-push проверки зелёные; `translate_check.py`
    проходит.

  **Тип:** методическая правка (глобальный CLAUDE.md,
  memory) + правка template-файлов + multilang re-bootstrap.
  Через PR в dreamteam-репо. Версионирование — **MINOR
  (1.6.0)**, логично объединить с T023 в один release cut
  «правки методики после первой обкатки». T020 (PROJECT.md
  cleanup) и T024 пересекаются по файлу `~/.claude/CLAUDE.md`
  — координировать.

