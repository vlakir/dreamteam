# Spec: T013 — Multilang support для derived projects

**Статус:** Draft
**Дата создания:** 2026-05-15
**Связанные документы:**
- `BACKLOG.md` (entry T013, оригинальная формулировка)
- `DECISIONS.md` (после implementation — ADR о выборе Variant A)

---

## 1. Overview

`dreamteam init` сегодня создаёт derived проект с методическими
файлами (`CLAUDE.md`, `README.md`, `CONCEPT.md`, kanban-файлы) только
на английском (исходник в `src/dreamteam/template/`). Это снижает
порог входа для англоязычных разработчиков, но создаёт барьер для
non-English пользователей, особенно когда суть документов —
narrative-описание методологии, а не код.

Добавляем prompt `language` в `copier.yml` (choices `[en, ru, fr,
de, zh]`, default `en`) и поставляем переведённый narrative-content
для каждого из 5 языков. Технические части (`pyproject.toml`, `src/`,
hooks, kanban-keyword'ы `To Do`/`Doing`/`Done`) остаются одинаковыми
на любом языке.

## 2. User Stories

- **Как русскоязычный разработчик, я хочу** получить derived проект
  с `CLAUDE.md` / `README.md` / прочей методикой на русском, **чтобы**
  понимать правила без необходимости перевода в голове.
- **Как пользователь любого из 5 целевых языков, я хочу** видеть
  language prompt на старте `dreamteam init`, **чтобы** явно выбрать
  свой язык (а не получить дефолтный en).
- **Как Claude, работающий в derived проекте, я хочу** знать, какой
  язык выбрал пользователь, **чтобы** отвечать на нём (язык записан
  в `.copier-answers.yml` после init).
- **Как maintainer (Vladimir), я хочу** простую structurally clean
  организацию переводов (`i18n/<lang>/`), **чтобы** добавление нового
  языка / правка существующего занимали O(1) места — один файл на
  язык, без сложных merge-стратегий.

## 3. Functional Requirements

- **ДОЛЖНА**: `copier.yml` содержать prompt `language` типа `str`
  с `choices: [en, ru, fr, de, zh]`, default `en`, help-текст на
  английском с inline-нативными названиями (`en (English) / ru
  (Русский) / fr (Français) / de (Deutsch) / zh (中文)`).
- **ДОЛЖНА**: после рендера в derived проекте присутствовать только
  одна копия каждого narrative-файла (не 5 копий), на выбранном
  языке. Не выбранные языки не попадают в derived проект.
- **ДОЛЖНА**: технические файлы (`pyproject.toml`, `src/main.py`,
  `tests/`, `.github/workflows/ci.yml`, `.git/hooks/pre-push`)
  идентичны для любого выбранного языка.
- **ДОЛЖНА**: kanban-секции в `BOARD.md` иметь заголовки `To Do` /
  `Doing` / `Done` на любом языке (international keywords —
  поведенческое решение Разработчика).
- **ДОЛЖНА**: derived `.copier-answers.yml` содержать поле
  `language: <выбранный>`, чтобы `dreamteam update` (и любой
  будущий tooling) знали, какой язык use.
- **ДОЛЖНА**: integration test для каждого из 5 языков
  (`pytest -m integration`): рендер → 4 pre-push проверки на
  результате проходят с 0 ошибок.
- **МОЖЕТ**: для языков без полного перевода — fallback к `en` на
  уровне отдельного файла (если `i18n/fr/CLAUDE.md` отсутствует, в
  derived попадает `i18n/en/CLAUDE.md`). См. clarify Q1.
- **НЕ ДОЛЖНА**: переводить technical termы — `ruff`, `mypy`,
  `kanban`, `ADR`, `WIP-limit`, `scope`, names of CLI flags / commands.
- **НЕ ДОЛЖНА**: переводить code blocks внутри `.md` файлов.
- **НЕ ДОЛЖНА**: иметь runtime translation (`anthropic SDK` /
  Google Translate / etc.) — Variant B отвергнут.

## 4. Success Criteria

- `dreamteam init /tmp/foo --defaults` (без явного `language`) →
  `language: en` в `.copier-answers.yml`, derived проект идентичен
  тому, что сейчас рендерится (no behavior change for default).
- `dreamteam init /tmp/foo` (interactive) → язык запрашивается
  как 1-й prompt (до `project_name`), choices видны
  `[en (English), ru (Русский), ...]`, default = `en` (просто Enter
  → English).
- `dreamteam init /tmp/foo --data language=ru` → narrative файлы
  в `/tmp/foo` на русском.
- 4 pre-push проверки (`ruff` / `format` / `mypy` / `pytest`)
  проходят с 0 ошибок **на любом из 5 derived проектов** (=
  выбран любой из 5 языков).
- `tests/test_cli.py` (или новый `tests/test_multilang.py`)
  содержит integration test для каждого языка.
- `dreamteam --version` / `dreamteam init --help` не упоминают
  language логику (она запрашивается через copier prompts, не CLI
  flags) — кроме standard copier `--data` mechanism.

## 5. Key Entities

### Структура (предложение, см. Clarify Q2)

В `src/dreamteam/template/`:

```
src/dreamteam/template/
├── copier.yml                 # обновлён prompt'ом language + _tasks
├── pyproject.toml             # технический файл, без перевода
├── .gitignore                 # технический
├── src/                       # технический
├── tests/                     # технический
├── hooks/                     # технический
├── .github/                   # технический
├── i18n/                      # NEW — переводы narrative content
│   ├── en/
│   │   ├── CLAUDE.md
│   │   ├── README.md
│   │   ├── CONCEPT.md
│   │   ├── BACKLOG.md
│   │   ├── BOARD.md
│   │   ├── CHANGELOG.md
│   │   ├── DECISIONS.md
│   │   └── specs/spec-template.md
│   ├── ru/                    # аналогично en
│   ├── fr/
│   ├── de/
│   └── zh/
└── _tasks_post_render.py     # post-generation: move i18n/<lang>/* → root, rm i18n/
```

После copier render:

```
derived-project/
├── pyproject.toml
├── CLAUDE.md         ← из i18n/<выбранный>/
├── README.md         ← из i18n/<выбранный>/
├── ... (остальные narrative)
└── (i18n/ удалена)
```

### Языковые коды (ISO 639-1)

| Code | Language    | Native name |
| ---- | ----------- | ----------- |
| `en` | English     | English     |
| `ru` | Russian     | Русский     |
| `fr` | French      | Français    |
| `de` | German      | Deutsch     |
| `zh` | Chinese     | 中文         |

Использование 2-letter ISO 639-1 (не BCP-47 типа `en-US` / `zh-CN`)
— упрощение для MVP, расширение возможно через choices update.

### Copier mechanism

- `copier.yml` → новый `language` prompt.
- `_tasks`: post-generation Python script (или shell), который
  переносит `i18n/<выбранный>/*` в корень проекта и удаляет `i18n/`.
- Альтернатива (см. Clarify Q2): `_subdirectory: "i18n/{{ language
  }}"` + duplicate всех технических файлов в каждой `i18n/<lang>/`
  директории. Отвергнуто из-за duplication burden.

## 6. Assumptions & Constraints

- Только narrative-файлы переводятся (см. Functional Requirements).
- Maintainer (Vladimir) лично контролирует переводы `en` + `ru`
  (свободный bilingual). Для `fr` / `de` / `zh` — community
  contribution или AI-assisted draft с human review.
- В MVP допустимо иметь только en + ru полностью; fr / de / zh —
  placeholder файлы с предупреждением (см. Clarify Q1 и Phase 3
  implementation plan).
- Copier поддерживает `_tasks` для post-generation cleanup (есть
  в API copier 9.x).
- Целевая аудитория derived projects — solo developers / small
  teams, использующие AI-assist (главный consumer narrative-
  контента — Claude, у которого мультиязычность встроена).

## 7. Out of Scope

- **AI-translation at runtime** (Variant B) — нет дополнительной
  dependency на anthropic SDK / OpenAI / Google.
- **Hybrid mixed-language файлы** (Variant C) — не делаем
  «narrative на ru + headings на en» в одном файле.
- **Поддержка >5 языков** — добавление нового языка возможно
  через новый PR, но не в этой задаче.
- **BCP-47 region codes** (`en-US`, `zh-CN`, `zh-TW`) — оставляем
  ISO 639-1.
- **Auto-detection** языка по `LANG` env var — пользователь явно
  выбирает через copier prompt.
- **Translation memory tooling** (gettext / Crowdin / Weblate) —
  для 5 narrative файлов overkill.
- **i18n CLI strings самого `dreamteam`** — команды `dreamteam
  init` / `update` остаются English-only (CLI tool для developers
  → ожидание English UX).
- **Драйв-кейс «сменить язык в derived проекте после init»** —
  T009 (full update) даст это как side effect; в MVP T013 не
  поддерживаем.

---

## Clarify (заполняется Claude — мой первый pass; ответы Разработчика вшиваются в соответствующие разделы выше)

### Open questions

**Q1. Fallback при missing translation.**
Если `i18n/fr/CLAUDE.md` отсутствует (язык не полностью переведён),
что попадает в derived проект?

- **Option A**: `i18n/en/CLAUDE.md` (silent fallback).
- **Option B**: `i18n/fr/CLAUDE.md` с placeholder-предупреждением
  («This file is not yet translated to French — using English version
  below»).
- **Option C**: error на этапе init — заставить maintainer закрыть
  pre-MVP полностью все языки.

Моё мнение: **Option B**. Прозрачно для пользователя, не блокирует
init, мотивирует contribute переводы. Реализация: для fr/de/zh
держать placeholder-файл в i18n/<lang>/ с include-директивой
к en-версии (или просто duplicate en content с warning банером
сверху).

**Q2. Layout: `i18n/<lang>/` + `_tasks` vs `_subdirectory`.**
Два candidate layout'а:

- **Layout A**: `i18n/<lang>/` с narrative + `_tasks` post-rename.
  Технические файлы (pyproject.toml, src/) — на root template
  уровне, не дублируются. ✅ DRY.
- **Layout B**: `_subdirectory: "{{ language }}"` (copier feature)
  + полная duplicate template tree в `en/`, `ru/`, `fr/`, `de/`,
  `zh/`. ❌ 5x duplication технических файлов; правка одного
  bug в src/main.py требует 5 edits.

Моё мнение: **Layout A**. Минимизирует duplication, упрощает
maintenance.

**Q3. Чем именно делается post-generation rename?**
Copier предлагает несколько механизмов:

- **`_tasks`** (copier.yml top-level): список shell commands /
  Python scripts, запускаемых после render.
- **`_jinja_extensions`**: кастомный Jinja-плагин (overkill для
  rename).
- **External post-processing**: hook в `dreamteam.cli` сам после
  copier.run_copy переносит файлы.

Моё мнение: **`_tasks`** с Python skript для cross-platform
совместимости (shell `mv` отличается на Windows). Скрипт читает
`{{ language }}` из copier context, копирует / переносит файлы,
удаляет `i18n/`.

**Q4. Качество переводов fr/de/zh.**
Vladimir не bilingual для этих языков. Варианты:

- **Option A**: MVP с en + ru full, fr/de/zh — placeholder-файлы
  fallback (см. Q1). Реальные переводы — community PR-ы.
- **Option B**: AI-generated initial draft (Claude через web UI),
  Vladimir вычитывает базовый язык, оставляет как «AI-draft, PRs
  welcome» в README.
- **Option C**: не релизим v2 без всех 5 — отложить на N месяцев.

Моё мнение: **Option B**. Снижает trust-barrier (pluggable system,
а не «coming soon»), при этом честно maркирует quality level в
README. Vladimir может «smoke check» через Google Translate roundtrip.

**Q5. SemVer impact.**
Multi-lang adds new `language` prompt → existing v1.x derived
проекты не имеют этого answer. `dreamteam update` (когда будет
T009) спросит missing answer. Это:

- **MAJOR** (breaking update flow): bump к v2.0.0.
- **MINOR** (default `en` preserves behavior): bump к v1.3.0.

Моё мнение: **MINOR (v1.3.0)**. Default = `en` сохраняет text-
для-text идентичность с current behavior. Existing derived проекты
после update получат language: en автоматически (copier предложит
default).

**Q6. Заголовки kanban-секций.**
`BOARD.md` имеет секции `## To Do` / `## Doing` / `## Done`.
Перевод?

- **Option A**: international keywords — оставить English на всех
  языках. Pro: tooling / parsing проще, recognizable cross-team.
- **Option B**: native — `## Сделать` / `## В работе` / `## Готово`
  для ru.

Моё мнение: **Option A**. Это поведенческое решение из original
BACKLOG entry T013. Подтверждение нужно.

**Q7. Обновления методики после T013.**
После релиза multi-lang каждое изменение narrative-файла в template
требует 5 правок (по одной на язык). Risk: drift между языками.

- **Mitigation A**: процедура — изменение делается сначала в `en`,
  затем `ru` (Vladimir), затем placeholder-обновление для
  fr/de/zh («section X requires translation»).
- **Mitigation B**: автоматический drift-checker (CI step):
  diff-counter linecount между i18n/en/*.md и других — alert при
  расхождении > N%.

Моё мнение: **Mitigation A** для MVP (process discipline), **B**
— в отдельную follow-up задачу если drift станет реальной болью.

### Resolved (с ответами)

<!-- Заполняется после ответов Разработчика. -->

---

## Analyze (заполняется Claude — мой пас по spec)

### Issues

- 🟡 **Warning — Translation quality risk (fr/de/zh)**.
  Vladimir не bilingual для этих языков → переводы могут содержать
  скрытые ошибки. Худший сценарий: правило в `CLAUDE.md` на zh
  означает противоположное en-версии. **Mitigation**: explicit
  disclaimer banner в fr/de/zh версиях («AI-assisted translation,
  PRs welcome»), и hard-link на en-source в каждой translation
  для side-by-side reference. Тесно связано с Clarify Q4.

- 🟡 **Warning — Maintenance burden скейлится по N языков**.
  Каждое изменение методики = 5 edits (en/ru/fr/de/zh). Если
  Vladimir пушит много небольших правил-tweaks, это становится
  больно. **Mitigation**: разделить «hot» сегменты текста
  (часто меняющиеся правила) и «cold» (стабильное narrative).
  Hot — оставить только в en, «cold» — переводить. В MVP — не
  делаем, оставляем как accepted trade-off. Принято Vladimir-ом
  при выборе Variant A («вопрос дисциплины»).

- 🟡 **Warning — `_tasks` cross-platform**.
  `_tasks` в copier 9.x умеет shell commands и Python scripts.
  Python preferred (Windows compat). Но: copier `_tasks` runs
  **after** template files are written to disk, не in-memory. Это
  значит, что `i18n/` появится в derived project, потом cleanup.
  Acceptable, но видно в timeline. **Mitigation**: гарантировать
  что cleanup task crash-safe (если interrupt — `i18n/` остаётся,
  derived project всё равно функционален). Тесно связано с Q3.

- 🟢 **Note — Plural-aware translations не нужны**.
  Narrative files — статический text без plural-форм / number
  injection (типа «5 задач» vs «1 задача»). Не нужно gettext /
  ICU MessageFormat. Простой file-level swap достаточен.

- 🟢 **Note — Encoding consideration**.
  zh содержит non-ASCII. Все .md файлы UTF-8 — стандарт для copier
  + git + большинства tooling. Проверить, что hatch wheel build
  не corrupts non-ASCII при packaging. Простое smoke check
  (`uv build && unzip -l dist/*.whl | grep -i zh && uv pip install
  dist/*.whl && python -c "from importlib.resources import files;
  print(files('dreamteam').joinpath('template/i18n/zh/CLAUDE.md').
  read_text())"`).

- 🟢 **Note — `--defaults` в `dreamteam init`**.
  Сейчас `dreamteam init <path> --defaults` skip-аются все prompts
  → take default values. После T013 default `language: en` →
  поведение `--defaults` остаётся идентичным current. Но: integration
  test нужен именно с `--defaults` чтобы verify.

- 🟢 **Note — `.copier-answers.yml` уже сейчас включает все answers**.
  `dreamteam.cli.init` уже пишет answers manually (т.к. copier не
  auto-writes для unversioned local templates). После T013 просто
  один дополнительный ключ `language` — никаких изменений в
  cli.py логике не требуется (она generic dict-based).

### Verdict

После ответов на Clarify Q1-Q7 spec готов к Analyzed статусу.
Critical блокеров не найдено. Warning'ов — три (quality, maintenance,
cross-platform `_tasks`), все имеют mitigation или принятый
trade-off.

---

## Implementation Plan (phases — будут отдельными PR-ами после approve spec)

**Phase 1 — Skeleton & en/ru baseline.**
- `copier.yml` prompt + `_tasks` post-render script (Python).
- `i18n/en/` — перенос текущих narrative files (one-to-one rename).
- `i18n/ru/` — полные переводы (Vladimir).
- `tests/test_multilang.py` (integration) для `en` + `ru`.
- Smoke check `dreamteam init` для обоих.

**Phase 2 — fr/de/zh placeholders с fallback warning.**
- `i18n/fr/`, `i18n/de/`, `i18n/zh/` с placeholder files
  (warning banner + duplicate en content).
- Integration tests для 3 placeholder-языков.
- README update (template + dreamteam itself) — описание language
  prompt и translation status.

**Phase 3 — Documentation & version bump.**
- `CHANGELOG.md` → [Unreleased] → Added (язык prompt, переводы).
- `DECISIONS.md` → ADR T013 (выбор Variant A, rejected alternatives B/C/D).
- Version bump v1.2.0 → v1.3.0 (MINOR — language default preserves behavior).
- Final integration suite green для всех 5 языков.
