# Architecture decisions (dreamteam package)

Архитектурные решения `dreamteam`-пакета (scaffolding CLI на Copier),
ADR-Lite. В derived projects — свой `DECISIONS.md` (из
`src/dreamteam/template/`), они не пересекаются.

Формат и принципы: решения фиксируются и не редактируются после
принятия; новый блок при пересмотре. Исторические упоминания
`TEMPLATE-*.md` в старых ADR ниже **не правлены** — immutable history.

---

## Решения

<!-- Новые решения добавляются сюда, новые сверху. -->

### 2026-05-15 — Full `dreamteam update` с three-way merge (T009)

- **Контекст:** MVP-вариант `dreamteam update` (T006) выполнял
  `copier.run_copy(..., overwrite=True)` — re-rendered template
  поверх derived проекта, **затирал** локальные правки пользователя
  в template-managed файлах (`CLAUDE.md`, `BACKLOG.md`,
  `CHANGELOG.md`, `pyproject.toml`, `hooks/pre-push`). Известное
  ограничение, документировано в command docstring и в ADR T006.
  T009 — follow-up, заменяющий MVP-overwrite на полноценный
  three-way merge с сохранением правок и git-style conflict
  markers.
- **Альтернативы (layout — Q2, `i18n/<lang>/` interaction):**
  - **Runtime AI-merge через `anthropic` SDK** — отвергли. У
    Разработчика Claude Max subscription (не API), и runtime
    зависимость от LLM делает поведение update-а
    недетерминированным.
  - **Pure-Python merge (`merge3` PyPI)** — отвергли как fallback
    для git-absent сценария (Q3). Дополнительная dependency для
    редкого случая, менее обкатано чем `git merge-file`. Вместо
    этого — fall back to MVP overwrite + WARNING.
  - **Diff-based check** (просто проверять что other-language
    файлы тоже изменены) — отвергли. PR может cheat-нуть
    `touch`-ом.
- **Альтернативы (хранение base state — Q2):**
  - **Pip-download предыдущей версии** на update — отвергли.
    Сетевой доступ при runtime противоречит **MUST NOT:
    требовать сетевого доступа в runtime** из spec.md
    (caught CodeRabbit-ом в spec PR #44 ranee как противоречие).
  - **Hash-based + versioned history в wheel** (separate
    `dreamteam/_history/` с each snapshot) — отвергли.
    Линейный рост wheel-а с каждой версией; ~150% уже при 4
    версиях.
  - **Two-way merge без base** (только theirs vs ours) —
    отвергли как слишком неточный для overlapping kanban-edits;
    user правки и template changes часто пересекаются в
    BACKLOG/BOARD/CHANGELOG.
  - **Выбран bundled bare git repo** в
    `src/dreamteam/template/.bundle/` (Q2 → option a). Каждый
    release добавляет один annotated tag (`1.3.0`, `1.4.0`, …)
    через `scripts/update_bundle.py`. Wheel вырастает ~50 KB →
    ~165 KB (acceptable; rough ~3× против оценки в Analyze
    Warning ~5×).
- **Альтернативы (формат тегов — обнаружено в Phase 1):**
  - **`v`-prefixed теги** (`v1.3.0`, `v1.4.0`) — естественный
    git-style, но **dunamai** внутри copier-а использует
    `Pattern.DefaultUnprefixed` для определения версии. Отвергли
    в пользу PEP-440 unprefixed (`1.3.0`, `1.4.0`).
  - **Выбран PEP 440 без prefix-а**. `scripts/update_bundle.py`
    отклоняет `v`-prefixed input с понятной ошибкой.
- **Альтернативы (`Subproject.template` source — обнаружено в Phase 1):**
  - **Bundle как `_src_path` в answers напрямую** — отвергли.
    Bare repo не имеет working tree, copier-овский Template
    class на нём ломается («Updating is only supported in
    git-tracked templates»).
  - **Переписать `_src_path` в answers перед update** — отвергли.
    Запись на диск делает derived dirty, copier отказывается
    обновлять dirty subproject.
  - **Выбрано: pre-populate `worker.subproject.__dict__['last_answers']`
    с указанием temp clone path** до вызова `run_update`. Это
    bypass-ит cached_property без записи на диск. Documented
    как hack-зависимый от copier internals; работает на 9.x.
- **Альтернативы (conflict resolution UX — Q1):**
  - **`.rej` файлы** (`patch -R` стиль) — отвергли. Чище в
    основном файле, но нестандартный для git-developers; IDE
    merge tools не подхватывают.
  - **Дублирующие `.theirs.<lang>` файлы** — отвергли. Менее
    интрузивно, но user сам делает 3-way merge через IDE.
    Дополнительная нагрузка.
  - **Выбрано: git-style in-file markers**
    (`<<<<<<< before updating` / `=======` / `>>>>>>> after updating`).
    Стандарт, vimdiff/VSCode/IDE merge tools понимают.
- **Альтернативы (`git` absent — Q3):**
  - **Hard error** + «install git first» — отвергли. Min friction
    при dev-environments без git (редкий случай).
  - **Pure-Python merge fallback** (`merge3` PyPI) — отвергли,
    см. выше.
  - **Выбрано: fall back to MVP `run_copy(..., overwrite=True)`
    с явным WARNING** в stderr.
- **Альтернативы (atomicity — Q9):**
  - **All-or-nothing** через tempdir + swap — отвергли.
    Откат успешных мержей из-за одного конфликта — плохой UX;
    user должен сам решать сохранять ли progress частично.
  - **Выбрано: best-effort**. Per-file успех/конфликт/error;
    итоговый exit code mirrors самый серьёзный исход (0 / 1 / 2).
- **Альтернативы (`--dry-run` UX — Q8):**
  - **Только summary line** — отвергли. Без diff пользователь не
    знает что именно изменится.
  - **Только per-file unified diff** — отвергли. Без summary
    сложно быстро оценить scope.
  - **Выбрано: both** — top-line summary с 5 bucket-ами + per-file
    unified diff через `difflib.unified_diff`. Target никогда не
    модифицируется.
- **Последствия:**
  - **`dreamteam update`** теперь по умолчанию делает three-way
    merge через `copier.Worker.run_update`. Старое поведение
    доступно через `--force`.
  - **`--dry-run`** даёт preview без записи.
  - **Bundle** упакован в wheel, реrender при release через
    `scripts/update_bundle.py`. Maintainer запускает скрипт на
    каждый release cut.
  - **Exit codes**: `0` clean / `1` error / `2` conflicts.
    CI-friendly: PR в derived проекте может условно блокировать
    merge при unresolved conflicts.
  - **`_commit` в `.copier-answers.yml`** теперь PEP-440 без
    prefix-а (`1.4.0`, не `dreamteam-1.4.0`). Legacy
    `dreamteam-<X.Y.Z>` mapped в `_resolve_base_version_tag` для
    backward-compat (пре-1.3.0 проекты падают в overwrite
    fallback т.к. bundle не имеет таких тегов).
  - **`__version__`** теперь из `importlib.metadata.version()`
    — single source of truth, синхронизирован с pyproject.toml.
  - **Открытые упстрим quirks** (документированы в test
    comments, не блокеры):
    - Copier diff-ит Jinja-source против rendered subproject
      content; conflict markers могут попасть на Jinja-only
      line (`{{ project_name }}`) вместо semantically
      затронутой line.
    - Conflict resolution внутри `i18n/<lang>/` файлов трипает
      copier `git checkout -- <path>` staging step (rendered
      path ≠ template path после `_tasks_post_render.py`
      rename). Workaround в Phase 2 test — использовать
      root-level файл для conflict scenario. Multilang merge
      без overlap-а работает корректно.
  - **Version bump:** `1.3.0 → 1.4.0` (MINOR; backward-compatible
    — default flow изменился, но `--force` сохраняет MVP-поведение
    для тех кто на него полагался).
  - **Phase split** в Implementation: Phase 0 (spec, PR #44),
    Phase 1 (skeleton + merge backend, PR #46), Phase 2
    (synthetic-bundle integration tests, PR #47), Phase 3
    (`--dry-run`, PR #48), Phase 4 (docs + version + bundle
    re-tag, этот PR).

### 2026-05-15 — Multilang: Variant A + ru = source of truth + manual translation (T013)

- **Контекст:** narrative-файлы методики (`CLAUDE.md`, `README.md`,
  `CONCEPT.md`, kanban-файлы, `specs/spec-template.md`)
  поставлялись только на английском. Это работает для англоязычных
  пользователей, но создаёт барьер для non-English разработчиков
  — особенно когда суть документов — narrative описание методики,
  а не код. Решаем расширить шаблон на 5 языков (`en`/`ru`/`fr`/
  `de`/`zh`).
- **Альтернативы (layout — Variant A vs B vs C, см. spec.md Q1–Q2):**
  - **Variant B (runtime AI-translation в `dreamteam init`)** —
    отвергли. Требует `anthropic` SDK как build- или runtime-
    зависимость, у Разработчика Claude Max subscription (не API
    access), generation на каждый `dreamteam init` нестабилен и
    дорог.
  - **Variant C (hybrid mixed-language файлы — narrative на ru,
    headings на en в одном файле)** — отвергли. Нечитаемая каша,
    contributor confusion.
  - **`_subdirectory` copier-механизм с дублированием технических
    файлов в каждой `i18n/<lang>/`** — отвергли. Duplication
    burden: одно изменение в `pyproject.toml` → 5 файлов.
  - **Выбран Variant A:** `src/dreamteam/template/i18n/<lang>/`
    с narrative; технические файлы — на root template уровне;
    post-render task (`_tasks_post_render.py`) переносит
    `i18n/<выбранный>/*` → root и удаляет `i18n/`.
- **Альтернативы (source of truth — ru vs en, см. spec.md Q7):**
  - **English source + ru/fr/de/zh AI-перевод** (industry default)
    — отвергли. Разработчик monolingual maintainer (русскоязычный),
    редактировать методику на en и затем переводить на ru через
    AI — лишний этап с потерей качества именно в ru (родном языке
    Разработчика).
  - **Выбран ru = source of truth** + AI-перевод на остальные 4
    языка. Trade-off: en теряет «source language privilege» —
    теперь это AI-перевод равного trust-level с zh/fr/de. UX
    expectation `default: en` сохранён (стандарт для CLI tools);
    ru = source — внутренний maintenance detail.
- **Альтернативы (AI engine — scripted API vs manual session, см.
  spec.md Q8):**
  - **`scripts/translate.py` с Anthropic SDK** (scripted CLI:
    `python scripts/translate.py` → API call → переводы) —
    отвергли. Требует `ANTHROPIC_API_KEY` env var, расходы на API
    при каждом regen, `anthropic` package в `[dependency-groups]
    .dev` — у Разработчика API не подключен.
  - **AI translation as CI step** (auto-regenerate на CI с API key
    в GitHub secrets) — отвергли. Race conditions при concurrent
    PR, API costs на каждый CI run, secret management.
  - **Выбран manual flow через Claude Code session.** Разработчик
    правит `i18n/ru/<file>.md`, в Claude Code session просит
    «переведи на en/fr/de/zh, обнови frontmatter». Claude
    (`claude-opus-4-7`) использует стандартные Read/Write tools,
    computes `sha256(ru_bytes)` через stdlib `hashlib`, пишет
    переводы с frontmatter. Trade-off: каждое изменение требует
    session interaction (не one-line CLI), но zero API cost
    (covered Max subscription), нет key management, нет новых
    dependencies.
- **Альтернативы (drift mitigation — diff vs hash, см. spec.md Q7):**
  - **Diff-based check** (CI проверяет, что other-language файлы
    тоже изменились) — отвергли. Cheap, но PR может «cheat»-нуть
    `touch`-ом файла без реального перевода.
  - **AI translation как CI auto-regen** — см. выше, отвергли.
  - **Выбран hash-based check** (`scripts/translate_check.py`,
    pure stdlib + PyYAML). Каждый не-русский файл несёт
    frontmatter с `source_hash` (sha256 of ru source at translation
    time); CI step после pytest пересчитывает hash актуального
    `i18n/ru/<same>.md` и сравнивает. Mismatch → PR fail с
    указанием конкретного файла + hint regenerate. Отсутствие
    frontmatter → warning + skip (Q9 — soft-fail, чтобы не
    блокировать community manual edits / bootstrap partial state).
- **Последствия:**
  - **Структура `src/dreamteam/template/`:** narrative-файлы
    переехали в `i18n/{ru,en,fr,de,zh}/`. ru остаётся
    единственным редактируемым вручную набором. Технические файлы
    (pyproject.toml, src/, tests/, hooks/, .gitignore, copier.yml)
    не дублируются.
  - **`copier.yml`:** новый prompt `language` (первый, до
    `project_name`), choices `[en, ru, fr, de, zh]`, default `en`,
    display names с native variants (`en (English)` / `ru
    (Русский)` / …). `_tasks` step запускает
    `_tasks_post_render.py {{ language }}` после рендера.
  - **`_tasks_post_render.py`** в template root: перемещает
    `i18n/<lang>/*` в корень derived-проекта, strip-ит translation
    frontmatter (derived users получают clean markdown), удаляет
    `i18n/` и сам себя.
  - **`cli.py`:** `unsafe=True` в `Worker` / `run_copy` (template —
    package-data, доверяем `_tasks`); новый `--data key=value`
    (repeatable) на `dreamteam init` для прокидывания answers в
    copier (нужен для `--data language=ru`).
  - **`scripts/translate_check.py`** (stdlib `hashlib` + PyYAML,
    который уже в copier dependencies). Запускается локально и
    как step в `.github/workflows/ci.yml` после pytest. 32 ok при
    зелёном состоянии (4 языка × 8 файлов).
  - **`tests/test_translate_check.py`** — 8 unit-кейсов
    (valid / mismatch / missing-fm / partial-fm / missing-source
    / round-trip / dir-skip / live-repo-state).
  - **`tests/test_multilang.py`** — fast render-per-language тесты
    + `@pytest.mark.integration` e2e (uv sync + 4 pre-push на
    каждом из 5 derived проектов, ~16 секунд suite total).
  - **Frontmatter format** в каждом `i18n/{en,fr,de,zh}/<file>.md`:
    ```yaml
    ---
    translated_from: i18n/ru/<file>.md
    source_hash: <sha256 of ru at translation time>
    translation_engine: claude-opus-4-7
    translation_date: 2026-05-15
    ---
    ```
  - **Maintainer flow при правке методики:**
    1. Vladimir правит `i18n/ru/<file>.md`.
    2. В Claude Code session: «переведи изменения в `i18n/ru/<file>.md`
       на en/fr/de/zh, обнови `source_hash`».
    3. Claude reads ru-source, computes `hashlib.sha256(ru_bytes)
       .hexdigest()`, пишет переводы с обновлённым frontmatter.
    4. Vladimir commits ru + регенерированные переводы.
    5. CI guard verify hash sync.
  - **Cosmetic ru-edits** (typo, whitespace, реструктуризация
    переносов) меняют hash и формально требуют regenerate. Workflow
    на этот случай: «обнови только `source_hash` во всех 4 языках,
    перевод не трогай — изменения cosmetic». Claude применяет
    `hashlib.sha256` и обновляет frontmatter без regeneration
    content. Manual judgment per change.
  - **Версия пакета:** `dreamteam-cli` 1.2.0 → 1.3.0 (MINOR).
    Default `en` сохраняет поведение для existing derived
    проектов; после `dreamteam update` те получат `language: en`
    в `.copier-answers.yml` и rendered narrative на en — то же,
    что у них и так было.
  - **Quality risk** (warning из Analyze): все 4 не-русских языка
    — AI-generated, теоретически возможно правило в `CLAUDE.md`
    на en/zh означает противоположное ru. Mitigation:
    (1) do-not-translate list в practice (ruff/mypy/ADR/имена
    файлов/code blocks/kanban keywords оставляются как есть);
    (2) frontmatter traceability; (3) Google Translate roundtrip
    smoke на ключевые правила по желанию; (4) long-term —
    bilingual community reviewers.
- **Phase split (исторический):**
  - **Phase 1** — skeleton + ru source + bootstrap всех 5 языков
    + unit/integration tests (PR #38).
  - **Phase 2** — CI guard step в workflow (PR #39, stacked).
  - **Phase 3** — этот ADR + CHANGELOG + README + version bump
    (этот PR, stacked на Phase 2).
  - Опциональный **smoke PR** (after Phase 2 merged into main) —
    edit `i18n/ru/<file>.md` без regen на отдельной ветке,
    показать CI fail на live runner; не merge-ить.

### 2026-05-15 — Удаление `PROJECT.md` из шаблона (T014)

- **Контекст:** `PROJECT.md` в template был задуман как «паспорт
  проекта» (цель / статус / стек / артефакты / открытые вопросы /
  история). Каждый из этих блоков **дублируется** более
  специализированным документом: цель и статус — в `README.md`,
  открытые вопросы — в `BACKLOG.md`, история — в `CHANGELOG.md`,
  стек и зависимости — в `pyproject.toml` / `[project.urls]`,
  архитектурные решения — в `DECISIONS.md`. Catch-all-документ без
  чёткой роли — гарантированный drift.
- **Альтернативы:**
  - **Оставить как есть** — отвергли. Drift между `PROJECT.md` и
    `README.md` / `BACKLOG.md` / `CHANGELOG.md` неизбежен; дополнительная
    дисциплина без выгоды.
  - **Расширить роль `PROJECT.md`** (например, заменить ARCHITECTURE.md)
    — отвергли. Для текущего масштаба проектов лишняя сущность.
  - **Merge в `README.md`** (один большой README) — отвергли.
    README превратится в state-dump, что портит quick-start
    природу. Стандартное ожидание Python community — README
    компактный, для onboarding.
- **Последствия:**
  - `src/dreamteam/template/PROJECT.md` удалён.
  - `src/dreamteam/template/CLAUDE.md` — в «Что прочитать в начале
    сессии» `PROJECT.md` заменён на `README.md` (current state
    теперь там); в разделе про CONCEPT — упоминание `PROJECT.md`
    заменено на `README.md`.
  - `src/dreamteam/template/README.md` — `PROJECT.md` убран из
    «Структуры проекта»; вместо него добавлен `CONCEPT.md`
    (immutable initial vision — раньше отсутствовал в списке).
  - `src/dreamteam/template/CONCEPT.md` — ссылка «Текущее
    состояние ведётся в `PROJECT.md`» заменена на `README.md`.
  - Версия `dreamteam-cli`: `1.0.0 → 1.1.0` (MINOR — template
    change; existing проекты на v1.0.0 с PROJECT.md остаются как
    есть, `dreamteam update` не удаляет файл).
  - Итоговая методическая картина: **6 специализированных файлов
    без catch-all**: CONCEPT (immutable vision), README (public +
    current state), CLAUDE (правила для Claude), BACKLOG (идеи),
    BOARD (текущая работа), CHANGELOG (история), DECISIONS (ADR).

### 2026-05-14 — PyPI naming: `dreamteam-cli` вместо `dreamteam` (T011)

- **Контекст:** При первой попытке publish (T011) обнаружено, что
  имя `dreamteam` на PyPI занято с 2019 года: squatter-аккаунт с
  single-version 0.0.1, заброшен (last upload 2019-09-12, владелец
  не отвечает на запросы по аналогичным случаям). Имя нужно сейчас.
- **Альтернативы:**
  - **PEP 541 reclamation** (запрос реклемации заброшенного package
    у PyPI admins) — отвергли: процесс на недели, требует emails
    к admins + период ожидания response от original maintainer.
    Несовместимо с темпом релиза.
  - **`dreamteam-scaffold`, `dreamteamkit`, `dreamteamx`, прочие** —
    отвергли в пользу `dreamteam-cli`: последний более self-
    descriptive (CLI tool) и следует распространённой Python
    конвенции (`django-cli`, `kubernetes-cli` и т.п.).
- **Последствия:**
  - **PyPI name:** `dreamteam-cli`. `pip install dreamteam-cli`,
    `uvx --from dreamteam-cli dreamteam ...`.
  - **Command name** остаётся `dreamteam` (через `[project.scripts]
    dreamteam = "dreamteam.cli:app"`). Brand сохраняется в
    повседневной работе.
  - **Import name** остаётся `dreamteam` (папка `src/dreamteam/`).
    Python permits PyPI name ≠ import name; common pattern.
  - **Repo name** остаётся `vlakir/dreamteam` (GitHub).
  - В `README.md` явно прописан note про PyPI name vs command name
    distinction.
  - Известный артефакт: бесполезный squatter package `dreamteam`
    0.0.1 продолжает существовать на PyPI; наш `dreamteam-cli` —
    отдельная запись, никаких коллизий.

### 2026-05-14 — Publish flow: `scripts/publish.sh` + `.secrets` (hybrid: twine check + uv publish) (T011)

- **Контекст:** Для регулярных публикаций dreamteam-cli на PyPI
  нужен скрипт. Передавать токен в командной строке каждый раз —
  опасно (попадает в shell history); хранить токен в коде —
  нельзя. Validation артефактов перед upload желательна (PyPI
  не позволяет re-upload одной версии, ошибка в metadata = bump
  version).
- **Альтернативы:**
  - **Чистый `uv publish` без validation step** — отвергли. `uv
    publish` не имеет аналога `twine check`; ошибка в metadata
    обнаружится после irrevocable upload. Bump-and-republish —
    плохой UX для первой публикации.
  - **Чистый `twine upload`** — отвергли. Заменять `uv publish`
    на twine в пользу одного дополнительного шага не нужно.
    Hybrid берёт лучшее из обоих.
  - **Inline команды без скрипта** (как было сначала) — отвергли.
    Токен в командной строке + shell history + повторение при
    каждом релизе.
  - **`.env` вместо `.secrets`** — отвергли. У Разработчика уже
    устоявшаяся конвенция `.secrets` family (от dynaconf-эпохи
    старых проектов).
- **Последствия:**
  - **`scripts/publish.sh`** (bash, `set -euo pipefail`):
    1. Source `.secrets` (export PYPI_TOKEN / PYPI_TEST_TOKEN).
    2. `rm -rf dist/ && uv build`.
    3. `uv run twine check dist/*` (validation).
    4. `UV_PUBLISH_TOKEN=$TOKEN uv publish` (или с
       `--publish-url https://test.pypi.org/legacy/` при `--test`).
    5. Print verify-команду.
  - **`.secrets`** в `.gitignore` (явно, поскольку `.secrets.*`
    pattern не покрывает bare `.secrets`).
  - **`.secrets.example`** в git (через negation
    `!.secrets.example` в `.gitignore`) — template для onboarding.
  - **`twine`** добавлен в `[dependency-groups].dev`.
  - Usage: `cp .secrets.example .secrets`, paste tokens, run
    `scripts/publish.sh` (или `--test` для TestPyPI).

### 2026-05-14 — MIT License для `dreamteam` package (T010)

- **Контекст:** `dreamteam` — scaffolding CLI, ориентирован на широкую
  adoption и использование в любых проектах (включая proprietary).
  Перед публикацией на PyPI (T011) требуется явная license; до сих
  пор её не было.
- **Альтернативы:**
  - **Apache 2.0** — permissive + explicit patent grant. Отвергли:
    для small CLI tool patent grant overkill; больше boilerplate.
    Может быть пересмотрено при росте проекта / контрибьюторов.
  - **GPL-3.0** — copyleft, viral. Отвергли: для scaffolding tool
    блокирует использование в proprietary derived projects, что
    противоречит главной цели (широкая adoption).
  - **BSD-3-Clause** — like MIT + non-endorsement clause. Отвергли:
    extra clause без значимой выгоды для small Python tool.
- **Последствия:**
  - `LICENSE` file в корне репо со standard MIT text (Copyright (c)
    2026 vlakir).
  - В `pyproject.toml`: `license = "MIT"` + `license-files = ["LICENSE"]`
    (PEP 639 syntax). License classifier из `[project.classifiers]`
    **не дублируется** — PEP 639 запрещает.
  - Wheel автоматически включает LICENSE через hatchling +
    `license-files` directive.
  - Снимает блокер T011 (PyPI publish).
  - **Discrete от derived projects:** template/ не содержит LICENSE.
    Пользователь `dreamteam init` сам решает что добавить (или
    оставить unlicensed). Если в будущем хотим предложить license
    choice в `dreamteam init` — отдельная задача.

### 2026-05-14 — `TEMPLATE-*.md` → default names в корне репо

- **Контекст:** Префикс `TEMPLATE-` для мета-документов (BACKLOG,
  BOARD, CHANGELOG, DECISIONS) был введён в T005 для разделения
  «мета шаблона» vs «заготовки для derived» в одном репо. После
  T006 заготовки уехали в `src/dreamteam/template/` как package
  data; в корне репо остались только мета-документы — коллизия
  исчезла, префикс стал избыточным.
- **Альтернативы:**
  - **Оставить префикс** — отвергли. Избыточен после T006, делает
    файлы менее обычными для нового читателя репо.
  - **Перенести мета-документы в `meta/` подпапку** — отвергли.
    Default позиция меты — корень репо (как везде в Python проектах).
- **Последствия:**
  - `TEMPLATE-BACKLOG.md → BACKLOG.md`,
    `TEMPLATE-BOARD.md → BOARD.md`,
    `TEMPLATE-CHANGELOG.md → CHANGELOG.md`,
    `TEMPLATE-DECISIONS.md → DECISIONS.md` (через `git mv`).
  - Live references (в README, pyproject `[project.urls] Changelog`,
    intro секциях самих файлов) обновлены на default-names.
  - Historical entries в CHANGELOG (внутри версий) и в этом
    DECISIONS (внутри старых ADR), а также `specs/T006-.../spec.md`
    — **не правлены**. Это immutable history.
  - Глобальный `~/.claude/CLAUDE.md` обновлён: scope правила
    нумерации T-ID для репо шаблона теперь по `BACKLOG.md`/`BOARD.md`/
    `CHANGELOG.md` (без `TEMPLATE-`-префикса).
  - Файлы в `src/dreamteam/template/` (внутри template для derived)
    не затронуты — там и были без префикса.

### 2026-05-14 — Миграция на Copier + PyPI-distributed CLI (T006)

- **Контекст:** Шаблон распространялся как GitHub Template Repository.
  Каждый новый проект требовал 9 ручных шагов очистки (`rm TEMPLATE-*`,
  очистка примеров, копирование `README.template.md`, замена
  плейсхолдеров). Это трение в самый ценный момент — старт проекта.
- **Альтернативы:**
  - **Остаться на gh-template** — отвергли. Трение растёт с
    методикой.
  - **Cookiecutter** — отвергли. Нет нативного `update`, экосистема
    стагнирует на фоне `copier`.
  - **Свой CLI с нуля** — отвергли. 1-2 недели работы vs 1 день с
    `copier`-инфраструктурой. Reinventing the wheel.
  - **Чистый `copier copy gh:vlakir/dreamteam`** (без своего CLI и
    PyPI) — отвергли. Привязка к `gh:`-reference нарушает правило
    «методика универсальная, не привязанная к платформе».
- **Последствия:**
  - `dreamteam` — Python-package на PyPI, тонкий Typer CLI поверх
    `copier`. Команды: `dreamteam init <path>`, `dreamteam update`.
  - Template живёт в `src/dreamteam/template/` (package-data),
    `copier` вызывается через Python API.
  - **`dreamteam update` ограничен на MVP** — re-applies template
    с stored answers (`overwrite=True`), не делает diff/merge. Full
    diff/merge через `copier.run_update` требует git-tracked
    template, что нетривиально для PyPI-distributed package.
    Планируется отдельной задачей.
  - **`Worker` from copier** используется для capture user answers
    (run_copy возвращает None). Worker помечен как internal API,
    deprecation warning принимается до публичного API.
  - Файлы методики в корне репо удалены (Phase 7) — они теперь
    только в `src/dreamteam/template/`. Корень репо: package +
    tests + `TEMPLATE-*.md` meta-docs + specs + README + .gitignore +
    pyproject + uv.lock.
- **Process для release на PyPI** (для maintainer):
  ```bash
  # 1. Локально проверить build
  uv build
  unzip -l dist/dreamteam-1.0.0-py3-none-any.whl   # sanity check

  # 2. TestPyPI (sanity check)
  # Требует API token на test.pypi.org, переменная UV_PUBLISH_TOKEN
  uv publish --publish-url https://test.pypi.org/legacy/

  # 3. Verify install из TestPyPI работает
  pip install --index-url https://test.pypi.org/simple/ \
              --extra-index-url https://pypi.org/simple/ \
              dreamteam

  # 4. Основной PyPI (после OK на TestPyPI)
  # Требует API token на pypi.org
  uv publish
  ```
- **Versioning policy** для `dreamteam` package:
  - Semver. `1.0.0` — первый release с Copier/CLI архитектурой.
  - `MAJOR` bump при breaking changes методики (изменения, которые
    `dreamteam update` не может применить безопасно).
  - `MINOR` — новые правила / features в шаблоне (backward-compatible
    через `update`).
  - `PATCH` — fix-ы / documentation / tooling без изменения шаблона.

### 2026-05-14 — Branch Protection на `main` через GitHub-side enforcement (T001)

- **Контекст:** правило «не пушить напрямую в `main`» было
  поведенческим + локальный `hooks/pre-push` как опциональная
  защита. Сервер пропускал прямой push, если поведенческое правило
  было нарушено. Это «дыра» в дисциплине: один неосторожный
  `git push origin main` — и история запачкана.
- **Альтернативы:**
  - **Только поведенческое правило + локальный hook** — отвергли.
    Локальный hook нужно установить вручную (`cp hooks/pre-push
    .git/hooks/pre-push`), а если разработчик забыл — защиты нет.
    Сервер всё разрешит.
  - **GitHub Actions check** (workflow проверяет каждый push на
    main) — отвергли. Это reactive (фиксирует факт), а не
    preventive (не позволяет случиться).
  - **Branch Protection без `enforce_admins`** — отвергли по
    результатам smoke-теста: admin (владелец репо) bypass'ит
    защиту с warning «Bypassed rule violations», push проходит.
    Acceptance не достигается.
- **Последствия:**
  - На `vlakir/dreamteam` через `gh api .../branches/main/
    protection -X PUT` включена защита со следующими настройками:
    - `required_pull_request_reviews: { required_approving_review_count: 0 }`
      — push в `main` запрещён, мерджить можно через PR без
      обязательных approvals (Разработчик один, не имеет смысла
      требовать approval себя самого).
    - `enforce_admins: true` — защита применяется и к владельцу
      репо. **Autonomous decision** после первого smoke-теста,
      когда `enforce_admins=false` оказался дырявым.
    - `required_status_checks: null` — checks не требуются пока
      не настроим CI (`T007` после миграции на copier).
    - `restrictions: null` — нет ограничений по push users.
    - `allow_force_pushes: false`, `allow_deletions: false` —
      от автомата.
  - Через `gh repo edit --enable-merge-commit=false
    --enable-rebase-merge=false` оставлен только Squash-merge.
    Это enforces правило «один PR — один коммит» через GitHub UI.
  - Acceptance verified: `git push origin main` напрямую
    отклоняется сервером с `GH006: Protected branch update
    failed for refs/heads/main. Changes must be made through a
    pull request.`
- **Known artifact** в истории `main`: коммит `49bbebe` «T001
  smoke-test: this should be rejected by branch protection» —
  пустой коммит, попавший в main во время первого smoke-теста с
  `enforce_admins=false`. Не revert-ил, чтобы не нарушать своё же
  правило «не force-push в main». Остаётся как историческое
  свидетельство bootstrap процесса.
- **Платформо-специфично:** настройка через `gh` — для GitHub.
  Для других хостингов (GitLab, GitFlic, Forgejo) — аналоги
  через UI или API соответствующей платформы. Behavioral правило
  «не пушить напрямую в main» остаётся универсальным.

### 2026-05-14 — Префикс `TEMPLATE-*` для мета-файлов шаблона (T005)

- **Контекст:** Файлы шаблона несли двойную нагрузку: заготовка для
  derived users **И** место для нашей реальной работы над шаблоном.
  В `BACKLOG.md` лежали как пример для пользователя, так и наши
  задачи (T001-T005); в `DECISIONS.md` — пример SQLite и наши
  реальные ADR (uv, src/, logging); в `BOARD.md` — пример и T001.
  Именование непоследовательное: `META-CHANGELOG.md` (для шаблона)
  и `README.template.md` (для derived) — разные суффиксы для
  концептуально одинаковых ролей.
- **Альтернативы:**
  - **Двойной набор файлов в одном каталоге без явного префикса** —
    отвергли. Невозможно с одним именем хранить два смысла; путаница
    остаётся.
  - **Отдельная директория `.template-meta/`** — отвергли. При
    template-create копируется наравне с прочим; требует явного
    удаления; всё равно нужен маркер.
  - **Два репозитория** (`vlakir/dreamteam` для шаблона +
    `vlakir/dreamteam-meta` для разработки) — отвергли. Один
    разработчик, два репо — overhead координации.
  - **GitHub Issues / Projects для меты** — отвергли, нарушает
    принцип «методика универсальная, не привязанная к платформе»
    (см. правило `feedback_tasks_in_markdown_not_platform.md`).
- **Последствия:**
  - Введён префикс **`TEMPLATE-*`** для всех мета-файлов разработки
    шаблона. Default-имена (без префикса) — заготовки для derived.
  - Файлы созданы / переименованы:
    `META-CHANGELOG.md → TEMPLATE-CHANGELOG.md`;
    новые `TEMPLATE-BACKLOG.md`, `TEMPLATE-BOARD.md`,
    `TEMPLATE-DECISIONS.md`.
  - Накопленные данные шаблона перенесены в `TEMPLATE-*`;
    default-name файлы очищены до заготовок.
  - `README.md` — единственное исключение от schema (github
    отображает его на странице репо). В derived перезаписывается
    через `README.template.md`.
  - В инструкции «Как использовать» шаблона добавлен шаг
    `rm TEMPLATE-*.md` — стоит **перед** финальной перезаписью
    `README.md` через `README.template.md`, чтобы оставшиеся шаги
    setup не исчезли при overwrite.
  - В проектном `CLAUDE.md` добавлен раздел «Специфика репозитория
    `vlakir/dreamteam`» с явной пометкой «НЕ применяется в derived».
  - Scope правила `max()` для T-ID контекстен: в шаблоне —
    по `TEMPLATE-*`, в derived — по default-names.

### 2026-05-13 — CLI-style logging: DEBUG/INFO → stdout, WARNING+ → stderr

- **Контекст:** `logging.basicConfig(level=...)` без явного `stream=`
  пишет все логи (включая INFO/DEBUG) в `sys.stderr`. PyCharm и
  большинство терминалов красят stderr красным независимо от уровня —
  обычные информационные сообщения выглядят как ошибки. Кроме того,
  стандартный pipe `2>/dev/null` глушит и реальные ошибки, и
  безобидные INFO-логи — разделить их без перенастройки нельзя.
- **Альтернативы:**
  - **Оставить дефолт `basicConfig`** (всё в stderr) — отвергли.
    Визуальный шум в IDE, никакого pipe-контроля.
  - **Всё в stdout** (`stream=sys.stdout` в basicConfig) — отвергли.
    Ошибки уходят туда же, куда обычный вывод; пайплайны смешивают
    значимое и неважное.
- **Последствия:**
  - В `src/main.py` корневой logger конфигурируется двумя
    `StreamHandler`-ами: stdout (DEBUG/INFO, отсечено фильтром
    `_stdout_filter` по `record.levelno < WARNING`) и stderr
    (WARNING и выше).
  - `python src/main.py 2>/dev/null` — только информационные логи.
  - `python src/main.py >/dev/null` — только ошибки и предупреждения.
  - В PyCharm красным окрашивается только то, что реально требует
    внимания.
  - Конвенция распространяется на все новые проекты из шаблона.
    Сложные логгеры (структурные, ротация файлов и т.п.) — отдельный
    выбор по месту, но базовая разводка stdout/stderr сохраняется.

### 2026-05-13 — `src/` как корень исходников

- **Контекст:** Стартовый `main.py` лежал в корне проекта рядом с
  `pyproject.toml`, `README.md`, документами методики. По мере роста
  проекта корень захламляется, исходники смешиваются с инфраструктурой.
- **Альтернативы:**
  - **Flat layout** (исходники в корне) — отвергли. Корень
    превращается в свалку, нужно вручную исключать всё лишнее в
    `ruff exclude` / `mypy`.
  - **Пакет в корне** (`<project_name>/main.py` в корне) — отвергли.
    Имя пакета лезет в имя репозитория, при ренейме надо двигать
    директорию; коллизии с типичными именами модулей.
- **Последствия:**
  - Все исходники приложения живут в `src/` — это конвенция для
    всех новых проектов.
  - Запуск: `uv run python src/main.py`.
  - В `pyproject.toml` указан `mypy_path = "src"` — тип-чекинг
    находит модули из `src/` без `from src.* import`.
  - Имя проекта (`name` в `pyproject.toml`) можно менять без
    перестановки директорий.
  - Тесты, документация и инфраструктура остаются в корне или в
    собственных папках (`tests/`, `docs/`, `.github/` и т.п.).

### 2026-05-13 — `uv` как менеджер зависимостей и окружений

- **Контекст:** Шаблон стартовал на `poetry` (привычка Разработчика,
  все старые проекты на poetry). На первой же настройке линтеров
  всплыла проблема: poetry-стиль `^3.14` в `[project].requires-python`
  невалиден по PEP 621, ruff упал на парсинге. Дополнительно: `poetry
  install` в 10–100× медленнее, чем `uv sync` — для AI-workflow
  с частыми пересборками окружений это ощутимо.
- **Альтернативы:**
  - **Остаться на `poetry`** — отвергли. Замедляет работу с AI,
    несовместимости с PEP 621 будут всплывать снова, экосистема
    уверенно мигрирует на uv.
  - **Гибрид** — отвергли. Два стандарта в одном репо = путаница
    и двойная поддержка.
- **Последствия:**
  - Новые проекты из этого шаблона стартуют на `uv`.
    - В `pyproject.toml` используется чистый PEP 621 `[project]` без
    poetry-секций. Build-system намеренно не задан (применимо к
    приложениям; для библиотек — добавить отдельно).
  - При работе с PyCharm: интерпретатор указывается на `./.venv/bin/python`
    (PyCharm автоматически распознаёт `.venv` в корне проекта).
