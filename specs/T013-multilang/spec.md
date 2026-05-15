# Spec: T013 — Multilang support для derived projects

**Статус:** Analyzed (Q1–Q9 resolved 2026-05-15)
**Дата создания:** 2026-05-15
**Связанные документы:**
- `BACKLOG.md` (entry T013, оригинальная формулировка)
- `DECISIONS.md` (после implementation — ADR о выборе Variant A
  и ADR о source-of-truth = ru + AI-translation flow)

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

**Source of truth — `ru`** (решение Разработчика 2026-05-15 в Clarify Q7).
Vladimir редактирует `i18n/ru/` вручную; для `en`/`fr`/`de`/`zh`
заготавливается AI-перевод. У Vladimir нет Anthropic API key (Claude
Max subscription, не API), поэтому перевод делает Claude в обычной
Claude Code session по запросу — не scripted CLI, а human-in-the-loop
maintainer flow (Q8 resolution). Это переворачивает industry-default
«English source», но логично для Vladimir-monolingual maintainer и
поднимает quality bar — английская версия теперь равна по качеству
другим AI-переводам, а не source-language privilege.
**Default для users остаётся `en`** (стандарт UX expectation для CLI
tools); ru = source — внутренний maintenance detail. CI guard
(`scripts/translate_check.py`, pure stdlib hashlib) блокирует PR,
если `i18n/ru/` изменился без synced изменений в остальных 4 языках
(hash mismatch в frontmatter).

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
- **Как maintainer (Vladimir), я хочу** редактировать методику
  только на одном языке (русский) и автоматически получать
  AI-переводы для остальных 4 языков, **чтобы** не тратить время
  на ручной multilingual maintenance.
- **Как maintainer (Vladimir), я хочу** safety net в CI — PR
  не сможет смержиться, если изменения в `i18n/ru/` не сопровождаются
  изменениями в `i18n/{en,fr,de,zh}/` — **чтобы** drift между языками
  был структурно невозможен (как T015 для quality gate).

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
- **МОЖЕТ**: для языков без полного перевода — placeholder с
  warning banner + duplicate ru→en fallback content (Q1 = Option B).
- **ДОЛЖНА**: `i18n/ru/` — source of truth, редактируется вручную
  Vladimir-ом (Q7).
- **ДОЛЖНА**: `i18n/{en,fr,de,zh}/` — AI-сгенерированные переводы из
  ru source. Flow: Vladimir правит ru-source → запрашивает у
  Claude в Claude Code session («переведи на все 4 языка, обнови
  frontmatter») → Claude reads ru-source, generates translations
  с frontmatter, writes files → Vladimir reviews + commits.
- **ДОЛЖНА**: каждый файл в `i18n/{en,fr,de,zh}/<file>.md` иметь
  YAML frontmatter с полями: `translated_from`, `source_hash`,
  `translation_engine` (имя модели), `translation_date`.
- **ДОЛЖНА**: CI guard (`scripts/translate_check.py`, pure stdlib
  через `hashlib` + YAML parse) запускается как step в
  `.github/workflows/ci.yml`. Для каждого файла в `i18n/{en,fr,de,zh}/`
  с frontmatter — пересчитывает hash актуального `i18n/ru/<same>.md`,
  сравнивает с `source_hash`. Mismatch → exit 1 с error message,
  указывающим конкретный file и hint о regenerate flow.
- **ДОЛЖНА**: `scripts/translate_check.py` — отдельный standalone
  Python script (`uv run python scripts/translate_check.py`), 0
  внешних dependencies (только stdlib + PyYAML, который уже в
  `dependencies` для copier).
- **НЕ ДОЛЖНА**: переводить technical termы — `ruff`, `mypy`,
  `kanban`, `ADR`, `WIP-limit`, `scope`, names of CLI flags / commands.
- **НЕ ДОЛЖНА**: переводить code blocks внутри `.md` файлов.
- **НЕ ДОЛЖНА**: иметь runtime translation (`anthropic SDK` /
  Google Translate / etc.) при `dreamteam init` — Variant B
  отвергнут. AI-translation выполняется через Claude Code session
  (Q8 Option 2), не runtime в package.
- **НЕ ДОЛЖНА**: зависеть от Anthropic API / `anthropic` PyPI
  package как build- или runtime-dependency. У maintainer-а Claude
  Max subscription, не API access. Перевод — manual flow через
  Claude Code session.

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

### Структура (Q2 = Layout A)

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
│   ├── ru/                    # ✱ SOURCE OF TRUTH (manually edited by Vladimir)
│   │   ├── CLAUDE.md
│   │   ├── README.md
│   │   ├── CONCEPT.md
│   │   ├── BACKLOG.md
│   │   ├── BOARD.md
│   │   ├── CHANGELOG.md
│   │   ├── DECISIONS.md
│   │   └── specs/spec-template.md
│   ├── en/                    # AI-translated из ru
│   ├── fr/                    # AI-translated из ru
│   ├── de/                    # AI-translated из ru
│   └── zh/                    # AI-translated из ru
└── _tasks_post_render.py     # post-generation: move i18n/<lang>/* → root, rm i18n/
```

В корне репо (НЕ template) — translation tooling:

```
scripts/
└── translate_check.py         # CI guard: hash-based sync verification.
                               # Pure stdlib (hashlib + PyYAML). Запускается
                               # как step в CI workflow на каждом PR.
```

**Translation flow для maintainer-а (no API):**

1. Vladimir правит `i18n/ru/<file>.md` локально.
2. Vladimir в Claude Code session пишет: «переведи изменения в
   i18n/ru/<file>.md на остальные 4 языка, обнови frontmatter с
   actual source_hash».
3. Claude (я) reads ru-source, generates translations с frontmatter
   через стандартные Read/Write tools, computes source_hash через
   `hashlib.sha256(ru_bytes).hexdigest()`.
4. Vladimir reviews diff, smoke-check (опционально — Google Translate
   roundtrip для en на 1-2 ключевых правила), commits.
5. CI guard verifies hash sync — если несовпадение, PR fail-ит.

### Файлы AI-переведённых языков

Frontmatter в каждом `i18n/{en,fr,de,zh}/<file>.md`:

```yaml
---
translated_from: i18n/ru/<file>.md
source_hash: <sha256 of ru source at translation time>
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
```

CI guard (`scripts/translate_check.py`):
для каждого file в `i18n/{en,fr,de,zh}/` с frontmatter →
пересчитать hash актуального `i18n/ru/<same>.md` → сравнить с
`source_hash`. Mismatch → fail с message: «русский в
i18n/ru/<file>.md изменился (current hash <X>) с момента последнего
перевода в i18n/<lang>/<file>.md (recorded hash <Y>). Перегенерируй
переводы через Claude Code session». Файлы без frontmatter
пропускаются с warning (Q9 = Option A).

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
- Maintainer (Vladimir) редактирует только `i18n/ru/` (source of truth).
  Остальные 4 языка — AI-translated через Claude Code session по
  запросу maintainer-а (Q7 + Q8).
- Translation flow — manual (human-in-the-loop через Claude Code
  session), не scripted CLI. У maintainer-а Claude Max subscription,
  не API access (Q8).
- Copier поддерживает `_tasks` для post-generation cleanup (есть
  в API copier 9.x).
- Целевая аудитория derived projects — solo developers / small
  teams, использующие AI-assist (главный consumer narrative-
  контента — Claude, у которого мультиязычность встроена).
- `scripts/translate_check.py` использует только stdlib (`hashlib`,
  `pathlib`) + PyYAML (уже dependency для copier) — нет дополнительных
  внешних пакетов.

## 7. Out of Scope

- **AI-translation at runtime** (Variant B) — нет дополнительной
  dependency на anthropic SDK / OpenAI / Google в `dreamteam init`.
  AI-translation существует только как maintainer-tool offline.
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

## Clarify

### Resolved (2026-05-15)

- **Q1 (fallback при missing translation) → Option B**. Placeholder-
  файл с warning banner + duplicate ru→en fallback content (для
  языков, где AI-translation не запущен или провалился).

- **Q2 (layout) → Layout A**. `src/dreamteam/template/i18n/<lang>/`
  с narrative + `_tasks` post-rename. Технические файлы на root
  template уровне, не дублируются.

- **Q3 (post-generation rename) → `_tasks` с Python script**.
  Cross-platform (Windows-compatible).

- **Q4 (качество fr/de/zh) → Option B**. AI-generated initial draft
  через Claude. Дополнительно усилено в Q7: AI flow — core process,
  не one-time MVP. Disclaimer banner в README остаётся.

- **Q5 (SemVer) → MINOR (v1.3.0)**. Default `en` для users сохраняет
  behavior. Existing derived проекты после update получат `language: en`.

- **Q6 (kanban headings) → Option A**. International keywords
  (`## To Do` / `## Doing` / `## Done`) на всех языках.

- **Q7 (drift mitigation) → KEY CHANGE: ru = source of truth +
  AI-translation на остальные + CI guard.**

  Решение Разработчика 2026-05-15:
  «Первичен русский вариант. Из него генерируется AI-перевод для
  остальных языков. Желательно предохранительный механизм в CI:
  "русский изменился, остальные тоже должны измениться".»

  **Реализация:**
  1. `i18n/ru/` — single source of truth, manually edited.
  2. `scripts/translate.py` (NEW, maintainer-tool) — читает
     `i18n/ru/*.md`, генерирует переводы в `i18n/{en,fr,de,zh}/*.md`
     через Anthropic SDK с system prompt о dont-translate-list
     (ruff/mypy/ADR/`To Do`/etc.) и кодовых блоках.
  3. **Frontmatter в каждом переведённом файле** содержит
     `source_hash` (sha256 of ru source at translation time) +
     `translation_engine`, `translation_date`.
  4. **CI guard step** в `.github/workflows/ci.yml`: после 4
     standard проверок добавляется `scripts/translate_check.py`
     — пересчитывает hash актуального `i18n/ru/<file>.md`,
     сравнивает с `source_hash` в каждом `i18n/{en,fr,de,zh}/<file>.md`.
     Mismatch → fail PR.
  5. Maintainer flow при правке методики:
     - Edit `i18n/ru/<file>.md`.
     - Run `python scripts/translate.py` локально (требует
       `ANTHROPIC_API_KEY` env / `.secrets`).
     - Commit `i18n/ru/` + regenerated `i18n/{en,fr,de,zh}/`.
     - CI guard verify hash sync на PR.

  Альтернативы рассмотрены:
  - **Diff-based check** (просто проверять, что other-language
    files изменены): cheap, но не verify валидность — PR может
    cheat'ить просто touch'ом файла.
  - **AI translation as CI step** (auto-regenerate на CI с
    Anthropic key в secrets): дешевле workflow для maintainer,
    но требует API key в GitHub secrets, дополнительные costs
    на каждый CI run, race-conditions при concurrent PR-ах.

  Выбран **hash-based check** + **manual `scripts/translate.py`** —
  баланс между robustness и простотой.

### Resolved (продолжение, 2026-05-15)

- **Q8 (AI engine) → Option 2 (Manual через Claude Code session)**.

  Решение Разработчика: «У меня не API-версия, у меня подписка Max.
  Соответственно, перевод — твоя головная боль».

  **Реализация:**
  - Никакого `scripts/translate.py` с Anthropic SDK. Никакого
    `anthropic` package в dependencies (ни build, ни runtime, ни dev).
  - Maintainer flow: Vladimir правит `i18n/ru/<file>.md` → пишет в
    Claude Code session «переведи на en/fr/de/zh, обнови frontmatter»
    → Claude (я) использует стандартные Read/Write tools, computes
    `source_hash = sha256(ru_bytes)` через `hashlib`, формирует
    frontmatter, пишет в `i18n/<lang>/<file>.md` → Vladimir reviews
    и commits.
  - Trade-off vs scripted flow: каждое изменение требует session
    interaction (не one-line CLI command), но zero API cost, covered
    by Max subscription, no key management.
  - `translation_engine` в frontmatter записывает текущую модель
    Claude в session (e.g., `claude-opus-4-7`) — traceability сохранена.

- **Q9 (frontmatter parse failure) → Option A (soft-fail с warning)**.

  CI guard принимает отсутствие frontmatter в `i18n/<lang>/<file>.md`
  как «не-AI-translated» (community manual edit, or bootstrap
  partial state). Skip hash-check для этого файла, log warning в
  stdout. Это:
  - Не блокирует community contributions (кто-то правит fr напрямую,
    без regeneration через Claude).
  - Не блокирует bootstrap (initial commit может содержать частично
    frontmatter-ы пока я регенерирую все языки).
  - Soft-fail. Mismatching hash (frontmatter есть, но hash не
    совпадает) — fail. Missing frontmatter — warning.

---

## Analyze (заполняется Claude — мой пас по spec)

### Issues

- 🟡 **Warning — Translation quality risk (fr/de/zh AND en)**.
  После Q7 (ru = source) **все 4 не-русских языка** — AI-generated.
  Это поднимает risk surface: английская версия теперь равна по
  trust-level другим AI-переводам, а не source-language privilege.
  Худший сценарий: правило в `CLAUDE.md` на en/zh/fr/de означает
  противоположное ru-источнику. **Mitigation**: (1) AI-translation
  system prompt включает явный «do-not-translate list» (ruff/mypy/
  ADR/имена файлов/code blocks/kanban keywords); (2) frontmatter
  с `source_hash` + `translation_engine` для traceability;
  (3) disclaimer banner в README («Source of truth — Russian;
  other languages are AI-translations, PRs welcome»). Главный
  smoke-check для Vladimir — Google Translate roundtrip на 1-2
  ключевых правила в en (back-translate в ru, compare semantics).
  Long-term — bilingual community reviewers per язык.

- 🟡 **Warning — Maintenance burden = Claude Code session-time**.
  После Q8 (no API) каждое изменение `i18n/ru/<file>.md` triggers
  retranslate через Claude Code session — Vladimir пишет prompt,
  ждёт response, проверяет diff. **API cost = $0** (covered Max
  subscription), но time-cost per change возрастает vs scripted
  flow. **Mitigation**: (1) Claude может batch-обрабатывать multiple
  files за один request («переведи всё изменённое в i18n/ru/ за
  один проход»); (2) для cosmetic ru-changes (typo, whitespace) —
  Claude использует hashlib для recompute source_hash без full
  retranslate (frontmatter-only update mode); (3) session взаимодействие
  все равно happens когда Vladimir работает над методикой — adding
  «и переведи» к запросу — incremental cost.

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

- 🟡 **Warning — CI guard false positives при non-narrative diff**.
  CI guard срабатывает на любой diff в `i18n/ru/<file>.md`. Но:
  изменение whitespace, typo fix, реструктуризация parag-разделителей
  меняют hash, требуя regenerate. **Mitigation**: для cosmetic
  ru-edits Vladimir в Claude Code session говорит «обнови только
  source_hash во всех 4 языках, перевод не трогай — изменения
  cosmetic». Claude применяет `hashlib.sha256(ru_bytes)` и обновляет
  frontmatter без regeneration content. Это manual judgment — нет
  машинного способа отличить «cosmetic» от «semantic» diff,
  Vladimir принимает решение per change. CI error message
  включает hint про этот flow.

- 🟢 **Note — Никаких новых dependencies для T013**.
  После Q8 (no API): `scripts/translate_check.py` использует stdlib
  + PyYAML (уже в `dependencies` для copier). Никакого `anthropic`
  package — ни как build/runtime/dev dependency. End-users не
  получают extra dep, dreamteam-cli package остаётся lean.

- 🟢 **Note — Bootstrap flow для T013 Phase 1**.
  Vladimir создаёт `i18n/ru/<file>.md` для каждого narrative file
  → одна Claude Code session по запросу «переведи все ru-файлы
  на en/fr/de/zh с frontmatter» делает initial bootstrap всех 4
  языков. Все frontmatter записываются с правильным source_hash от
  начального ru-state. CI guard `scripts/translate_check.py`
  работает с первого PR Phase 1.

### Verdict

Все Clarify questions Q1-Q9 resolved. Spec **переведён в Analyzed**
статус — готов к implementation phases. Critical блокеров не
найдено. Warning'ов — четыре (quality risk шире из-за en тоже AI;
maintenance burden как session-time; CI guard false positives;
cross-platform `_tasks`). Все имеют mitigation или принятый trade-off.

---

## Implementation Plan (phases — будут отдельными PR-ами после approve spec)

**Phase 1 — Skeleton + ru source + bootstrap всех 5 языков.**
- `copier.yml` prompt + `_tasks` post-render script (Python) для
  rename `i18n/<lang>/*` → root + cleanup `i18n/`.
- `i18n/ru/` — Vladimir переводит текущие English narrative-файлы
  на ru. Это становится source of truth.
- **Bootstrap translations**: одной Claude Code session — Vladimir
  просит «переведи весь i18n/ru/ на en/fr/de/zh с frontmatter».
  Claude (я) generates все 4 языка с правильным `source_hash`,
  `translation_engine`, `translation_date`. Commits в одном PR.
- `scripts/translate_check.py` (NEW, ~80 lines Python, stdlib +
  PyYAML): iterate `i18n/{en,fr,de,zh}/*.md`, parse frontmatter,
  compute `sha256(i18n/ru/<same>.md bytes)`, compare с
  `source_hash`. Mismatch → exit 1 с indication file + hint.
  Missing frontmatter → skip + warning (Q9).
- `tests/test_translate_check.py` (unit): valid/mismatch/missing
  frontmatter cases.
- `tests/test_multilang.py` (integration) для всех 5 языков:
  rendering + 4 pre-push checks на derived проекте.

**Phase 2 — CI guard integration.**
- Расширить `.github/workflows/ci.yml`: добавить step
  `python scripts/translate_check.py` после 4 standard проверок,
  внутри того же `ruff + format + mypy + pytest` job (для simplicity
  и single required status check; visibility — через step name в
  workflow output).
- Smoke PR на отдельной ветке: edit `i18n/ru/<file>.md` без
  regeneration переводов → CI должна fail с понятным сообщением.

**Phase 3 — Documentation & version bump.**
- `CHANGELOG.md` → [Unreleased] → Added (language prompt, multilang
  support, manual AI-translation flow через Claude Code session,
  hash-based CI guard).
- `DECISIONS.md` → ADR T013 (выбор Variant A; ru = source of truth;
  manual translation flow через Claude Code session vs scripted
  API approach; hash-based CI guard; rejected alternatives B/C/D
  и alternatives внутри Q7/Q8).
- Version bump v1.2.0 → v1.3.0 (MINOR — language default `en`
  preserves behavior для existing derived projects).
- Final integration suite green для всех 5 языков.
- README update (template + dreamteam itself): language prompt
  описание, disclaimer о AI-translation, instruction для
  contributors как edit ru source + flow для regeneration.
