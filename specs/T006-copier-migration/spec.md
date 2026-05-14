# Spec: T006 — Copier migration (PyPI-distributed CLI package)

**Статус:** Analyzed (revised 2026-05-14 после уточнения scope:
PyPI publication поднята из Out of Scope в Functional Requirements)
**Дата создания:** 2026-05-14
**Связанные документы:**
- `TEMPLATE-BACKLOG.md → T006` (краткое описание задачи)
- `TEMPLATE-DECISIONS.md → 2026-05-14 — Префикс TEMPLATE-* для мета-файлов шаблона (T005)`
  (текущая структура, которую частично переосмысливаем)

---

## 1. Overview

Шаблон `vlakir/dreamteam` сейчас распространяется как GitHub Template
Repository — пользователь жмёт «Use this template», и репо копируется
**целиком**, со всеми `TEMPLATE-*` мета-файлами, примерами в
`DECISIONS.md`, плейсхолдерами в `pyproject.toml`. Дальше — 9 ручных
шагов очистки из инструкции «Как использовать» в `README.md`.

Это трение бьёт по самому ценному моменту — старту нового проекта.
И с ростом методики оно растёт: чем больше правил, тем больше шагов
очистки.

Миграция превращает шаблон в **PyPI-distributed CLI-инструмент**
(в духе `django-admin startproject`). Пользователь:

```bash
pip install dreamteam        # или uvx dreamteam (zero-install)
dreamteam init my-project    # одна команда → чистый проект
dreamteam update             # обновить существующий проект
```

Внутри CLI вызывает [Copier](https://copier.readthedocs.io/) через
Python API — Copier инкапсулирует jinja-render, interactive prompts,
diff-based update. Сам же `dreamteam`-package содержит copier-template
как package-data resource.

**Архитектурный выигрыш:** методика **отвязана от конкретного хостинга**
(`gh:`-reference больше не нужен). Сегодня GitHub, завтра GitFlic /
GitLab / Forgejo — `pip install dreamteam` работает одинаково.

## 2. User Stories

- **Как разработчик**, я хочу установить инструмент **одной командой**
  (`pip install dreamteam` или `uvx dreamteam`) — без необходимости
  знать про copier, gh-references и т.п.
- **Как разработчик**, я хочу создать новый проект из шаблона одной
  командой (`dreamteam init my-project`) с интерактивными prompts,
  без последующей ручной чистки — старт занимает минуты, а не четверть
  часа.
- **Как разработчик**, я хочу обновить существующий проект до новой
  версии методики (`dreamteam update`), чтобы накопленные улучшения
  шаблона подтягивались без копирования вручную.
- **Как поддерживающий шаблон**, я хочу простую структуру
  (`src/dreamteam/template/` + `copier.yml`), чтобы изменения в
  методике вносились естественно и тестировались автоматически.
- **Как разработчик в команде, использующей GitFlic / GitLab / любой
  хостинг**, я не должен зависеть от GitHub — установка через PyPI
  работает на любой машине с pip.

## 3. Functional Requirements

### Distribution

- **ДОЛЖНА:** инструмент устанавливается как Python-package с PyPI:
  `pip install dreamteam` или `uvx dreamteam`. Сам package содержит
  copier-template как data resource — пользователю не нужно знать
  про copier или хостинг шаблона.
- **ДОЛЖНА:** package работает на любом OS, любом хостинге репо.
  Привязки к `gh:` / `gl:` / `bb:` ссылкам **нет**.

### CLI

- **ДОЛЖНА:** команда `dreamteam init <path>` создаёт работающий
  derived проект **без любых `TEMPLATE-*` файлов** и без
  примеров-для-удаления.
- **ДОЛЖНА:** команда `dreamteam update` подтягивает изменения
  шаблона в существующий проект (через `copier.run_update`).
- **ДОЛЖНА:** интерактивные prompts при `init`, с разумными
  defaults. Минимум — `project_name`, `project_description`,
  `author_name`, `author_email`.
- **ДОЛЖНА:** все 4 pre-push проверки (ruff / format / mypy / pytest)
  проходят на сгенерированном проекте **immediately** после
  `dreamteam init` (без дополнительных правок).
- **МОЖЕТ:** `--no-input` режим для CI / автоматических тестов
  (использовать defaults).

### Internals

- **ДОЛЖНА:** template-файлы попадают в package как `package-data`
  (через `[tool.hatch.build.targets.wheel]` / `package_data` /
  `importlib.resources`).
- **ДОЛЖНА:** подстановка переменных в файлы (`pyproject.toml`,
  `CONCEPT.template.md` → `CONCEPT.md`, `PROJECT.md`, и т.п.).
- **МОЖЕТ:** post-generation hooks для удобства (например, `git init`
  в новом проекте) — не как обязательное требование MVP.

### Compatibility

- **НЕ ДОЛЖНА:** ломать совместимость с пока не мигрированными
  старыми проектами Разработчика. Они продолжают жить как есть.
- **НЕ ДОЛЖНА:** требовать gh-CLI / GitHub Auth для использования.

## 4. Success Criteria

- **Установка:** `pip install dreamteam` (или `uvx dreamteam`)
  успешно отрабатывает на свежей машине с Python 3.10+; команда
  `dreamteam --help` доступна.
- **Скорость:** `dreamteam init ./project` < 30 секунд от запуска
  до готового проекта (включая интерактивные ответы).
- **Чистота:** в новом проекте 0 `TEMPLATE-*` файлов, 0 строк-примеров
  «удалить при заполнении», 0 плейсхолдеров `Your Name` / `you@`.
- **Готовность к работе:** `cd project && uv sync && uv run pytest`
  проходит зелёным без правок.
- **Update flow:** `dreamteam update` в derived проекте подтягивает
  изменения шаблона; merge conflicts отображаются стандартным
  copier-способом для ручного resolve.
- **Tests:** ≥ 80% coverage на сам `dreamteam` package (CLI + helpers),
  плюс end-to-end test через `dreamteam init` во временной директории
  с прогоном проверок на результате.
- **PyPI:** package публикуется на TestPyPI (`pip install --index-url
  https://test.pypi.org/simple/ dreamteam` работает) перед публикацией
  на основной PyPI. После основной публикации — `pip install dreamteam`
  ставит ту же версию.

## 5. Key Entities

- **`src/dreamteam/`** — Python-package, который публикуется на PyPI.
  Содержит:
  - `__init__.py` (version, public API);
  - `cli.py` (Typer-based CLI: `init`, `update`, `--version`);
  - `__main__.py` (поддержка `python -m dreamteam`);
  - `template/` (data resource — copier-template).
- **`src/dreamteam/template/`** — папка с copier-шаблоном. Содержит
  `copier.yml` и template-файлы с jinja-переменными (`{{project_name}}`
  и т.п.). Эта папка упаковывается как package-data.
- **`src/dreamteam/template/copier.yml`** — конфигурация copier:
  переменные, prompts, validators, `_min_copier_version`, exclude rules.
- **`pyproject.toml`** в корне репо — package metadata для PyPI
  (`name = "dreamteam"`, `version`, `dependencies = ["copier",
  "typer"]`, `[project.scripts] dreamteam = "dreamteam.cli:app"`,
  `[tool.hatch.build.targets.wheel] packages = ["src/dreamteam"]`,
  и т.п.).
- **Мета-документы шаблона** — `TEMPLATE-BACKLOG.md`,
  `TEMPLATE-BOARD.md`, `TEMPLATE-DECISIONS.md`, `TEMPLATE-CHANGELOG.md`,
  `specs/` — остаются в корне репо как maintainer-документы, **не**
  попадают в `src/dreamteam/template/`.
- **Тесты `tests/test_cli.py` + `tests/test_template.py`** —
  проверяют CLI (вызов `dreamteam init` через `typer.testing.CliRunner`)
  и end-to-end (создание во временной директории, прогон
  ruff/mypy/pytest на результате).
- **`.copier-answers.yml`** — артефакт в derived проекте, copier
  создаёт автоматически. Содержит ответы на prompts, version,
  используется для `dreamteam update`.

## 6. Assumptions & Constraints

- Python ≥ 3.10 на машине пользователя (требование copier).
- `git` установлен на пользовательской машине (copier использует git
  для diff-based update; при `init` тоже создаёт `.copier-answers.yml`,
  но git не строго обязателен).
- `uv` установлен — для использования сгенерированного проекта.
- Сценарий: один разработчик, один проект за раз. Multi-tenancy не
  рассматривается.
- Hosting репо самого `dreamteam`-package: GitHub. После публикации
  на PyPI хостинг становится **деталью** реализации, не частью
  пользовательского контракта.
- PyPI account и публикация — Разработчик (как maintainer) отвечает
  за credentials и `uv publish` команды. Документировать.

## 7. Out of Scope

- **Не-Python шаблоны.** Сейчас только Python-проекты; универсальный
  multi-language скаффолдер — отдельная задача (T8XX).
- **Миграция старых Разработчиковых проектов.** Они остаются как
  есть; будут мигрироваться отдельной задачей по мере необходимости.
- **CI/CD пайплайн** для самого шаблона (тестирование через GitHub
  Actions на каждый PR) — желательно, но не блокер MVP. Пересекается
  с **T007** (замена qodo / автоматический code review).
- **Сложные post-generation hooks** (git init, initial commit,
  pre-commit setup и т.п.). MVP: вручную после `dreamteam init`.
- **Опциональность стека.** На MVP — фиксированный стек (uv + ruff
  + mypy + pytest + hooks/pre-push). Опциональные prompts типа
  «нужен ли mypy?» — отдельная задача в будущем.
- **Поддержка пакетных менеджеров кроме pip/uv.** Conda / pdm /
  poetry — пользователь сам адаптирует, если нужно.

---

## Clarify (заполняется Claude в autonomous mode)

В autonomous overnight mode Claude задаёт сам себе встречные вопросы
и отвечает на основе принципов методики и здравого смысла. Если
Разработчик не согласен с ответом — поправит при обзоре spec.

### Open questions

(нет — все вопросы переведены в Resolved ниже)

### Resolved

**Auth / Authorization:**
- Q: Нужен ли `copier` доступ к private-репозиториям?
- A: Нет на MVP. `vlakir/dreamteam` public, copier работает без auth.

**Data validation & limits:**
- Q: Какие prompts обязательны?
- A: Минимум: `project_name` (regex `^[a-z][a-z0-9_-]*$`),
  `project_description` (≥ 5 chars), `author_name`, `author_email`.
  Дефолты — пустые, валидация через `copier.yml`.

**Error handling:**
- Q: Что если `copier copy` упирается в существующую non-empty
  директорию?
- A: Copier по умолчанию запрашивает confirmation; с `--force`
  перезаписывает. Default поведение нас устроит, документировать
  не требуется.
- Q: Что если `copier update` сталкивается с merge conflicts на
  файлах, изменённых пользователем?
- A: Это **стандартный copier-flow** — `*.rej` файлы создаются,
  пользователь resolves manually. Документируем кратко в README
  шаблона.

**Edge cases:**
- Q: Что если пользователь хочет сгенерировать проект, **не**
  использующий стандартный стек (например, без mypy)?
- A: MVP — fixed стек (uv + ruff + mypy + pytest). Опциональность
  стека (через prompts типа «нужен ли mypy?») — следующая итерация,
  T8XX.
- Q: Что если пользователь не хочет `hooks/pre-push`?
- A: По умолчанию включаем. Removal — после `copier copy` руками.
  Опциональность через prompts — следующая итерация.

**Performance & scale:**
- Q: Сколько занимает `copier copy` сейчас на похожих шаблонах?
- A: Обычно секунды (clone + jinja-render). Цель < 30 секунд
  включая интерактив — достижимо.

**Security & privacy:**
- Q: Какие секреты могут попасть в шаблон при миграции?
- A: На MVP — нет (шаблон не содержит секретов в `vlakir/dreamteam`,
  только плейсхолдеры). Будущие fixtures для интеграционных тестов
  могут потребовать — обсудим тогда.

**API integration:**
- Q: Copier поддерживает GitHub-template reference (`gh:owner/repo`)?
- A: Да, через стандартный `gh:` префикс.

---

## Analyze (заполняется Claude в autonomous mode)

### 🟡 Warnings (обсудить / возможно учесть в реализации)

- **`TEMPLATE-*` переосмысление.** После миграции на copier у нас
  будет **нативное** разделение: исходник шаблона = `src/dreamteam/
  template/`, результат = derived проект. **`TEMPLATE-*` мета-файлы
  (BACKLOG / BOARD / DECISIONS / CHANGELOG) остаются в корне репо
  шаблона** — но **не** в `template/`. То есть они продолжают
  существовать как «документы разработки самого шаблона», но
  физически уезжают **выше** по дереву. Это переосмысление T005 —
  не отмена, а уточнение в новом контексте.

- **PyPI namespace.** Имя `dreamteam` на PyPI — может быть занято.
  Проверить через `pip search` (deprecated) или прямой PyPI lookup
  до Phase 8. Если занято — `dreamteam-template` / `dreamteam-cli`
  как fallback. Решение отложено до Phase 8 (есть простор
  переименовать `[project.name]` без переписывания CLI).

- **`uv publish` vs `flit` / `twine`.** `uv publish` — современный
  путь, но **требует PyPI API token**. Конфигурация — через
  `UV_PUBLISH_TOKEN` env var или `~/.pypirc`. Документировать
  в Phase 8.

- **Двойной jinja.** Документация шаблона (`CLAUDE.md`,
  `README.template.md`, `CONCEPT.template.md`) сама содержит примеры
  с jinja-syntax (например, `{{ project_name }}` как пример из
  copier). Чтобы избежать «двойной обработки» при render — нужны
  jinja-escape (`{% raw %}...{% endraw %}`) в нужных местах.
  Учесть при реализации.

- **Тесты copier требуют доп. инфраструктуры.** Pytest должен
  уметь запускать `copier copy` во временной директории, прогонять
  ruff/mypy/pytest на результате, проверять отсутствие
  `TEMPLATE-*` файлов. Это нетривиальный setup, требует
  `pytest-copier` или ручного через `subprocess`. Учесть в фазе
  тестирования.

- **Версионирование template.** Copier поддерживает версионирование
  через git tags (`_min_copier_version` и `_envops` в `copier.yml`).
  Решение по версии — выпускать `1.0.0` как первую copier-версию
  (semver major — архитектурная переориентация). Это согласуется с
  обсуждённым ранее.

### 🟢 Notes (информационно)

- **`README.md` репо шаблона** — после миграции описывает не «как
  скопировать и почистить руками», а «как использовать через
  `copier copy`». Это сильно сокращает README.
- **`README.template.md`** — попадает в `template/README.md` (с
  jinja-переменными). Default-name `README.md` репо шаблона —
  отдельный документ (про сам шаблон, не для derived).
- **`hooks/pre-push`** — попадает в `template/hooks/pre-push` как
  есть. Install command остаётся «`cp hooks/pre-push
  .git/hooks/pre-push && chmod +x`» — это user-side post-generation.

### 🔴 Critical issues (требуют решения до начала реализации)

(нет)

---

## Implementation phases (план реализации)

Намечено как ориентир. Каждая фаза = отдельный PR с `T006`-prefix и
осмысленным slug:

- **Phase 1 — `T006-package-skeleton`.** Создать `src/dreamteam/`
  с минимальным CLI (Typer-based) и `pyproject.toml` для PyPI
  publication (`name="dreamteam"`, `[project.scripts]`,
  `[build-system]`). CLI имеет только `dreamteam --version` и
  `dreamteam init <path>` — последний выводит stub-сообщение.
  Acceptance: `pip install -e .` ставит package; `dreamteam --version`
  и `dreamteam init /tmp/test` отрабатывают.
- **Phase 2 — `T006-copier-integration`.** Добавить copier как
  dependency. `dreamteam init` вызывает `copier.run_copy` через
  Python API. Минимальный `src/dreamteam/template/copier.yml` +
  `template/` с одним placeholder-файлом для проверки render.
  Acceptance: `dreamteam init /tmp/test` создаёт файл с
  подставленными переменными.
- **Phase 3 — `T006-template-content`.** Перенос всех методических
  файлов (`CLAUDE.md`, `PROJECT.md`, `DECISIONS.md`, `CHANGELOG.md`,
  `BACKLOG.md`, `BOARD.md`, `CONCEPT.template.md → CONCEPT.md`,
  `specs/spec-template.md`, `hooks/pre-push`, `src/main.py` стартер,
  `tests/test_main.py`, `pyproject.toml` derived, `.gitignore`,
  `README.template.md → README.md`) в `src/dreamteam/template/`
  с jinja-переменными. Acceptance: `dreamteam init` создаёт
  полностью функциональный derived проект.
- **Phase 4 — `T006-cli-update`.** Добавить `dreamteam update`
  команду (вызывает `copier.run_update`). Документировать
  merge-conflict resolution flow.
- **Phase 5 — `T006-tests`.** `tests/test_cli.py` (через
  `typer.testing.CliRunner`) + `tests/test_template.py` (e2e:
  `dreamteam init` в tmp dir → прогон ruff/mypy/pytest на результате).
  Coverage ≥ 80% на `src/dreamteam/`.
- **Phase 6 — `T006-docs`.** Переписать `README.md` репо шаблона
  под PyPI/CLI flow (`pip install dreamteam`, `dreamteam init`,
  `dreamteam update`). Удалить устаревшую инструкцию из 9 шагов.
  Обновить `TEMPLATE-CHANGELOG.md → [Unreleased]` (или сразу
  финализировать `[1.0.0]`).
- **Phase 7 — `T006-cleanup`.** Удалить дубликаты из корня репо
  шаблона: default-name `*.md` (`BACKLOG.md`, `BOARD.md`,
  `DECISIONS.md`, `CHANGELOG.md`, `CLAUDE.md`, `PROJECT.md`),
  `README.template.md`, `CONCEPT.template.md`, `hooks/`,
  `src/main.py`, `tests/test_main.py` — они теперь живут только в
  `src/dreamteam/template/`. Репо шаблона остаётся с: `src/dreamteam/`
  (package), `tests/` (тесты package), `pyproject.toml` (package),
  `TEMPLATE-*.md` (maintainer-документы), `specs/`, `.gitignore`,
  `README.md` (пользовательский — про установку и использование
  CLI), `uv.lock`.
- **Phase 8 — `T006-publish`.** TestPyPI publication (sanity check
  через `uv publish --publish-url https://test.pypi.org/legacy/`).
  Затем — основной PyPI (`uv publish`). Документировать процесс
  release в `TEMPLATE-DECISIONS.md`. Финализация `v1.0.0` в
  `TEMPLATE-CHANGELOG.md` с retrospective.

После Phase 8 — закрываем как **`v1.0.0`** в `TEMPLATE-CHANGELOG.md`
с retrospective. PR-ов больше — но каждый меньше; проще обзор и
откат при необходимости.
