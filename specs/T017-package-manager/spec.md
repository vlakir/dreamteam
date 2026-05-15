# Spec: T017 — Package-manager parametrization для derived projects

**Статус:** Analyzed (Q1–Q10 resolved 2026-05-15)
**Дата создания:** 2026-05-15
**Связанные документы:**
- `DECISIONS.md` → «`uv` как менеджер зависимостей и окружений»
  (current default, T002-era ADR в template-эпохе).
- T016 (PR #50) — `dt` alias, latest in-tree change.

---

## 1. Overview

Шаблон derived-проектов сейчас жёстко вшит на **`uv`**: команды
вроде `uv sync`, `uv run pytest`, `uv add --dev`, `uv build`
встречаются в каждом из 5 языковых вариантов
`src/dreamteam/template/i18n/<lang>/CLAUDE.md` (~11 occurrences
per file) и `README.md` (~7), плюс ссылки в `hooks/pre-push` и
комментариях `pyproject.toml`. Если пользователь работает на
`poetry` / `pip` / `pdm` / `hatch` / `pixi`, эти инструкции не
подходят, и Claude в derived-проекте получает противоречивые
сигналы: «uv» из шаблона vs реальный tooling в репо
(`poetry.lock`, `requirements.txt`, и т. п.).

T017 параметризует выбор менеджера через **новый `package_manager`
prompt в `copier.yml`** и заменяет hardcoded `uv` команды на
условный rendering из per-manager шаблонных fragments. Default
остаётся `uv` (existing derived projects не затронуты при
`dreamteam update`; new init без явного `--data` тоже получает
`uv`).

## 2. User Stories

- **Как новый user, работающий на poetry, я хочу** `dreamteam init`
  предложить мне выбрать `package_manager: poetry`, и получить
  derived project с инструкциями `poetry install` / `poetry run
  pytest` вместо uv-only, **чтобы** Claude в проекте говорил на
  языке моего tooling и не путал команды.
- **Как существующий uv-user, я хочу** `dreamteam init` по умолчанию
  выбрать `uv` (Enter → default), **чтобы** ничего не менять в моём
  привычном workflow.
- **Как user смешанного tooling (uv для venv, pip для install в
  prod)**, я хочу указать `package_manager: pip` для базовой совместимости
  + добавить uv-команды в проектные правила вручную, **чтобы** не
  навязывать команды коллегам, которым uv недоступен.
- **Как maintainer dreamteam-cli, я хочу** один источник правды
  per language (как сейчас с multilang) + условные fragments per
  manager, **чтобы** не множить 5 lang × N managers независимых
  файлов с риском drift-а.

## 3. Functional Requirements

- **ДОЛЖНА:** `copier.yml` содержать prompt `package_manager`
  типа `str` с `choices: [uv, poetry, pdm, hatch, pip]` (MVP
  set по Q1 resolved) + display-имена в help-тексте, default `uv`.
- **ДОЛЖНА:** narrative-файлы (`CLAUDE.md`, `README.md`,
  `hooks/pre-push`, любые другие с командами) рендериться с
  правильными командами для выбранного менеджера через Jinja-
  conditional (`{% if package_manager == 'uv' %}` … `{% endif %}`)
  ИЛИ через single substitution variable (`{{ pm_run_pytest }}`)
  — выбор архитектуры в Q3.
- **ДОЛЖНА:** `pyproject.toml` рендериться с минимальным
  manager-specific блоком (Q4 / Q5 resolved):
  - **uv**: pure PEP 621 + `[build-system] hatchling` (как сейчас).
  - **poetry**: PEP 621 + `[tool.poetry] package-mode = false` +
    `[build-system] poetry-core`.
  - **pdm**: PEP 621 + optional `[tool.pdm]` + `[build-system]
    pdm-backend`.
  - **hatch**: PEP 621 + `[tool.hatch.*]` (env + envs.default
    минимально) + `[build-system] hatchling` (build-backend
    совпадает с uv, но добавляются hatch-specific env-секции).
  - **pip**: pure PEP 621 + `[build-system] hatchling`,
    идентично uv minus `[tool.uv]` (которого у нас и не было).
- **ДОЛЖНА:** `pre-push` chain команд адаптироваться к выбранному
  менеджеру:
  - **uv:** `uv run ruff check . && uv run ruff format --check .
    && uv run mypy . && uv run pytest`.
  - **poetry:** `poetry run ruff check . && poetry run ruff format
    --check . && poetry run mypy . && poetry run pytest`.
  - **pdm:** `pdm run ruff check . && pdm run ruff format --check
    . && pdm run mypy . && pdm run pytest`.
  - **hatch:** `hatch run ruff:check . && hatch run ruff:format-
    check . && hatch run mypy . && hatch run test` (через
    `[tool.hatch.envs.default.scripts]`).
  - **pip:** `ruff check . && ruff format --check . && mypy . &&
    pytest` (предполагается активированный venv).
- **ДОЛЖНА:** `dt update` / `dreamteam update` без явного
  `--data package_manager=` сохраняет ранее выбранный manager из
  `.copier-answers.yml` (стандартный copier behavior). При
  отсутствии answer (existing projects on v1.x, очень малое
  количество) — silent default `uv` (Q9 resolved). Без
  warning, без prompt, без миграционной логики — проект молодой
  и накопленных derived-проектов мало; specialized handling не
  оправдано (минимизация surface).
- **ДОЛЖНА:** ru-source (`i18n/ru/`) — single source of truth с
  conditional Jinja-блоками; en/fr/de/zh — AI-regenerate как
  обычно через Claude Code session, обновлённый `source_hash` в
  каждом frontmatter. Manager-specific fragments переводятся раз и
  кэшируются как обычный narrative content.
- **ДОЛЖНА:** integration test для каждой комбинации
  `package_manager` × `language` (sanity matrix, не полная — см.
  Analyze про test matrix).
- **МОЖЕТ:** в будущем расширять `choices` до `pdm`, `hatch`,
  `pixi` (Q1 stretch — отвергнуто в MVP, но архитектура должна
  это позволять).
- **НЕ ДОЛЖНА:** автомиграция existing v1.x derived projects с
  hardcoded uv-commands в их CLAUDE.md/README.md (= manual user
  action; `dreamteam update --force` поверх с явным
  `--data package_manager=<choice>` ИЛИ оставить как есть).
- **НЕ ДОЛЖНА:** генерировать lock-files на стороне dreamteam-cli
  (`uv sync` / `poetry install` производят их при первом запуске
  user-ом). См. Q6.

## 4. Success Criteria

- `dreamteam init /tmp/foo --defaults` → `package_manager: uv` в
  `.copier-answers.yml`, derived контент идентичен текущему (no
  behavior change for the default user).
- `dreamteam init /tmp/foo --data package_manager=poetry` →
  `pyproject.toml` содержит `[tool.poetry]` секцию + `poetry-core`
  build-backend; `CLAUDE.md` использует `poetry run` команды;
  `dt init` → `cd derived && poetry install && poetry run pytest`
  проходит на freshly generated project (smoke).
- `dreamteam init /tmp/foo --data package_manager=pip` →
  `pyproject.toml` — pure PEP 621 + hatchling, без manager-
  specific секций; `CLAUDE.md` использует bare commands (без
  prefix); `python -m venv .venv && .venv/bin/pip install -e .[dev]
  && .venv/bin/pytest` smoke passes.
- 4 pre-push проверки (ruff / format / mypy / pytest) проходят
  на сгенерированном derived **для каждого** `package_manager` ×
  `language` combination в integration suite.
- `dreamteam update` сохраняет manager choice из answers; не
  навязывает миграцию.
- `translate_check.py` остаётся зелёным после param-edits ru-
  source (re-translated и `source_hash` обновлён).

## 5. Key Entities

### `copier.yml`: новый prompt

```yaml
package_manager:
  type: str
  help: "Package manager for the generated project (uv = fast, opinionated default; poetry = traditional, pyproject-only; pip = bare, no extra tooling)"
  choices:
    "uv (Astral)": uv
    "poetry": poetry
    "pip (vanilla)": pip
  default: "uv"
```

### Conditional rendering — два кандидата (Q3)

**Option A — Single-variable substitution.** Define в `copier.yml`
extra vars (или в `_macros`) typed на `package_manager`:

```jinja
{# in CLAUDE.md template #}
{% if package_manager == 'uv' %}{% set pm_run = 'uv run' %}{% set pm_install = 'uv sync' %}
{% elif package_manager == 'poetry' %}{% set pm_run = 'poetry run' %}{% set pm_install = 'poetry install' %}
{% else %}{% set pm_run = '' %}{% set pm_install = 'pip install -e .[dev]' %}{% endif %}

To run tests: `{{ pm_run }} pytest` (or just `pytest` если venv активирован).
```

**Option B — Inline conditional blocks per command.** Каждое
вхождение `uv run pytest` оборачивается в `{% if ... %}` ladder.
Verbose, но без macro overhead.

**Option C — Separate per-manager file fragments.** `template/
i18n/<lang>/pre-push.uv.sh`, `pre-push.poetry.sh`, `pre-push.pip.sh`
и `copier.yml _tasks` выбирает нужный + rename. Только для
полу-self-contained файлов; для CLAUDE.md/README c многими
inline-командами не подходит.

### `pyproject.toml` template — два кандидата (Q4)

**Option A — Single Jinja file** с conditional sections:

```toml
[project]
name = "{{ project_name }}"
...

{% if package_manager == 'poetry' %}
[tool.poetry]
package-mode = false  # for app, not library

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
{% else %}
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
{% endif %}
```

**Option B — Three files** (`pyproject.uv.toml`, `pyproject.poetry.toml`,
`pyproject.pip.toml`) + `_tasks` post-render rename. Cleaner
templates, но три копии в репо.

### Lock file generation — Q6

После `dreamteam init`, derived project не содержит lock file.
Стандартно — user сам выполняет `uv sync` / `poetry install` /
`pip install -e .[dev]`. Опционально (out of MVP):
post-render `_tasks` step выполняет lock command автоматически.
Минусы автогенерации: требует manager installed в user's PATH в
момент `dreamteam init`, замедляет init, может failure для
edge cases. Рекомендация: не делать в MVP, документировать в
README.

### Test matrix — Q10

Полная матрица: 5 managers × 5 languages = **25** integration
cases (after Q1 expansion). На каждый — install dependencies
через выбранный manager + 4 pre-push checks. ~3-5 sec per case
× 25 = **~100s** в integration suite. Acceptable (current
multilang integration already ~30s; combined budget ~130s
still under 5-minute CI timeout). Plus fast-suite tests на
conditional render output verify.

## 6. Assumptions & Constraints

- Python 3.14+ доступен пользователю (current requirement).
- User имеет выбранный package manager installed (`uv`, `poetry`,
  или `pip`); `dreamteam init` не verify presence (Q6 stretch).
- Conditional Jinja в `copier.yml`-rendered files works
  cross-platform.
- T013 multilang flow остаётся неизменным: ru-source + 4
  AI-translations. Manager-conditional fragments переводятся как
  обычный текст (английские команды типа `uv run` остаются
  английскими во всех языках — это identifiers).

## 7. Out of Scope

- **Поддержка `pipenv`, `pixi`, `conda`, `rye`** — отвергнуты в
  MVP T017 (Q1 resolved):
  - **`pipenv`** — declining (Pipfile-based, не PEP-621-native;
    users migrate на poetry/uv).
  - **`pixi`** — niche (conda-compatible, новый).
  - **`conda` / `mamba`** — другая парадигма (env + pkg
    объединены), требует отдельного ADR и, вероятно,
    отдельного `env_manager` prompt-а.
  - **`rye`** — superseded by `uv` (Astral acquired, merged).
  Архитектура (conditional Jinja через macros) позволяет
  расширение в будущем без переписывания файлов.
- **Lock-file авто-генерация** при `dreamteam init` (Q6 out of
  scope).
- **Auto-migration of v1.x derived projects** к параметризованной
  template-эпохе.
- **`dreamteam init --to <manager>` для existing projects** — не
  делаем; это `dreamteam update --data package_manager=...` work,
  и derived user должен сам обновлять pyproject.toml.
- **Detection of installed managers на user machine** — копир не
  enforced.
- **CI sample workflows per manager** — `.github/workflows/ci.yml`
  в derived (если будет; сейчас нет) — отдельная следующая T-ID.

---

## Clarify

### Resolved (2026-05-15)

- **Q1 (supported managers в MVP) → `uv` + `poetry` + `pdm` +
  `hatch` + `pip` (5 managers).** Расширили базовый набор из
  3-х до 5 на основе текущего landscape Python tooling: `pdm`
  и `hatch` — оба PEP-621-native, активные, заметная user
  база; `hatch` особенно естественен — наш build-backend
  `hatchling` уже от тех же maintainer-ов. Покрывает весь
  spectrum от opinionated-fast (`uv`) до bare (`pip`).
  Отвергнуты: `pipenv` (declining), `pixi` (niche, conda
  compat), `conda`/`mamba` (другая парадигма, требует отдельного
  `env_manager` prompt), `rye` (superseded by `uv`).

- **Q2 (default) → `uv`.** Current behavior, no surprises для
  existing uv-first users. Также matches T002-era ADR в template.

- **Q3 (conditional rendering architecture) → (a) single-variable
  substitution через Jinja macros.** Define в `_macros` (или
  inline в template files) переменные `pm_run`, `pm_install`,
  `pm_add`, `pm_add_dev`, `pm_build`, etc. — заполняются один
  раз на основе `package_manager`, используются в narrative
  файлах как `{{ pm_run }} pytest`. DRY, scales до 5+ managers
  без quadratic growth текста.

- **Q4 (`pyproject.toml` template strategy) → (a) single Jinja
  file с conditional sections.** Matches Q3 (single Jinja
  source). Per-manager блоки внутри `{% if package_manager ==
  '...' %}` ladder. Альтернатива (5 отдельных файлов) была бы
  cleaner per-file но создавала бы 5 копий с риском drift-а.

- **Q5 (build-system per manager):**
  - **uv:** `hatchling`.
  - **poetry:** `poetry-core`.
  - **pdm:** `pdm-backend`.
  - **hatch:** `hatchling` (own ecosystem).
  - **pip:** `hatchling` (modern PyPA-supported choice).
  Везде, где не nativny build-backend manager-а — используется
  `hatchling` как modern default. `setuptools` не выбран — менее
  modern для new projects.

- **Q6 (lock file generation в init) → (a) не генерировать в
  MVP.** User сам делает `uv sync` / `poetry install` / `pdm
  install` / `hatch env create` / `pip install -e .[dev]`
  после `dreamteam init`. README в derived содержит manager-
  specific quick-start.
  Trade-off: один extra step при init, но zero failure surface
  (manager может быть не установлен в момент init).

- **Q7 / Q9 (legacy projects + backward compat при `dreamteam
  update`) → ничего специального не делаем (Q9 resolved).**
  Проект молодой; derived-projects на v1.x — единичные
  (Vladimir's own). При `dreamteam update` без
  `package_manager` answer (existing v1.x) — copier silent
  default `uv` через стандартный copier mechanism (matches T013
  multilang pattern для missing `language` answer). Никаких
  warning-ов, prompt-ов или миграционных команд. Минимизация
  surface > backward-compat hygiene для current project age.

- **Q8 (translation overhead для manager-specific fragments)
  → standard multilang flow.** Edit ru-source с conditional
  Jinja блоками → AI-regenerate `i18n/{en,fr,de,zh}/*.md`
  через Claude Code session → refresh `source_hash`. Manager
  commands (`uv run`, `poetry run`, etc.) — English
  identifiers, не переводятся, остаются inside Jinja blocks
  одинаково во всех 5 lang.

- **Q10 (integration test scope) → полная матрица 5 × 5 = 25
  cases.** Per-case ~3-5s × 25 = ~100s в integration suite.
  Защита от drift между managers и languages. Currently
  multilang integration suite ~30s; combined ~130s ещё под
  5-min CI timeout (с запасом).

---

## Analyze (2026-05-15)

### Issues

- 🟡 **Warning — Test matrix 25 integration cases (~100s)**.
  Удваивает наш integration suite (current ~30s). Combined
  ~130s under 5-min CI timeout, но рост заметный. **Mitigation**:
  если CI начнёт thrash-ить, можно cut к 5 × 1 (en only) + 1 ×
  4 (uv × other langs) sanity = 9 cases (~36s). Полную матрицу
  гонять nightly cron job или manual smoke before release.

- 🟡 **Warning — Conditional Jinja с 5 ветками = readability
  hit**. `{% if pm == 'uv' %}…{% elif pm == 'poetry' %}…{% elif
  pm == 'pdm' %}…{% elif pm == 'hatch' %}…{% else %}…{% endif %}`
  ladder появляется в CLAUDE.md / README в нескольких местах.
  **Mitigation**: Q3 winner (single-variable macros) — define
  переменные `pm_run`, `pm_install` один раз в начале файла или
  в `_macros.jinja`, и тогда тело file использует `{{ pm_run }}
  pytest` без conditional repetition. Сложность — concentrated
  в макро-секции, не разлита по тексту.

- 🟡 **Warning — `hatch` ambiguity** (manager AND build-backend).
  Наш build-backend `hatchling` is PyPA-supported; `hatch` manager
  — built on top. В pyproject.toml comments и README легко
  запутать readers. **Mitigation**: явно в `copier.yml` help-
  тексте и в derived README disambiguate: «`hatch` manager
  (project + env management, отдельно от build-backend
  `hatchling` который используется в этой config независимо от
  выбора manager-а)». Plus возможно отдельный note в ADR.

- 🟡 **Warning — Multilang re-bootstrap workload**. 8 narrative
  files × 4 non-ru languages = 32 AI re-translations нужно
  после Phase 1 (ru-source updated с conditional blocks). Standard
  T013 flow, но не trivial по времени Claude Code session.
  **Mitigation**: Phase 2 dedicated к этому в Implementation Plan;
  бюджет ~1 session.

- 🟢 **Note — `pip` без manager-specific build-config**. Для
  pip-derived проектов pyproject не должен содержать `[tool.uv]`
  / `[tool.poetry]` / `[tool.pdm]` / `[tool.hatch.envs]` — только
  PEP 621 `[project]` + `[build-system] hatchling`. Identical
  к uv-pyproject minus any `[tool.uv]` (которого у нас и так
  не было). Эффективно uv и pip share rendered pyproject; они
  различаются только в pre-push командах и quick-start
  инструкциях.

- 🟢 **Note — PEP 735 / `[dependency-groups]`** (стандартизация
  2025). Может в будущем заменить часть manager-specific
  dependency-groups секций (`[tool.uv.sources]`, `[tool.poetry.
  group]`, etc.) на universal `[dependency-groups]`. Spec
  должна быть flexible enough для future migration без
  переписывания. Conditional Jinja-структура это позволяет —
  можно поменять content внутри `{% if %}` без перекомпоновки.

- 🟢 **Note — Test fixture для install verification на CI**.
  CI runner может не иметь `pdm`/`hatch` pre-installed. Если
  тест нужен реальный `pdm install`/`hatch env create`, это
  требует setup step в `.github/workflows/ci.yml`
  (`pdm-project/setup-pdm`, `pypa/hatch`). **Mitigation
  approach**: integration tests verify лишь *rendered output*
  (correctness of generated pyproject.toml + CLAUDE.md +
  pre-push hook) — не выполняют actual install. Это hint —
  finalize в Phase 2 testing.

### Verdict

Все 10 Clarify questions resolved (Q1 expanded к 5 managers
после consultation с Vladimir). 0 🔴 critical блокеров, 4 🟡
warnings c mitigation, 2 🟢 notes к памяти. Spec **moves to
Analyzed**, готов к Phase 1 implementation.

---

## Implementation Plan

**Phase 0** — этот PR (spec drafting, Clarify resolved, Analyze).
Завершается с merge этого PR.

**Phase 1** — `copier.yml` prompt + Jinja macros architecture.
Update **только `i18n/ru/`** narrative files в Phase 1 (ru
source); re-render `i18n/{en,fr,de,zh}/` отложено в Phase 2.
Implement `pyproject.toml` conditional sections (5 managers).
Conditional `hooks/pre-push` шаблон. Fast unit tests для
conditional render output verify (один тест на manager × один
файл = ~5 cases без full integration overhead).

**Phase 2** — Multilang re-bootstrap: AI-regenerate
`i18n/{en,fr,de,zh}/*.md` через Claude Code session с updated
ru content (8 файлов × 4 lang = 32 files); refresh `source_hash`
в frontmatter-ах через `hashlib.sha256(ru_bytes)`. Integration
matrix test (5 managers × 5 langs = 25 cases) — verify rendered
output, не actual install (см. Analyze 🟢 note про test
fixture).

**Phase 3** — Docs / ADR / CHANGELOG / version bump 1.4.0 →
1.5.0 (MINOR — `package_manager` prompt опционален; default
`uv` сохраняет current behavior). ADR в `DECISIONS.md` фиксирует
все 10 Q-resolutions, rejected alternatives (`pipenv` /
`conda` / `pixi` / `rye`), `hatch` ambiguity disambiguation.
README обновляется с manager-prompt описанием. Bundle re-tag
через `scripts/update_bundle.py`.
