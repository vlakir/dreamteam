# Spec: T006 — Copier migration

**Статус:** Analyzed
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

Миграция на **Copier** инкапсулирует всё это в одну команду:
`copier copy gh:vlakir/dreamteam ./my-project` создаёт **уже чистый**
проект, без TEMPLATE-* мусора, с подставленными именами и
плейсхолдерами. Бонусом — `copier update` для подтягивания изменений
методики в уже созданные проекты (главное преимущество copier vs
cookiecutter).

## 2. User Stories

- **Как разработчик**, я хочу создать новый проект из шаблона одной
  командой, без последующей ручной чистки, чтобы старт занимал минуты,
  а не четверть часа.
- **Как разработчик**, я хочу интерактивно ответить на вопросы (имя
  проекта, краткая цель, нужен ли pytest / pre-push hook), чтобы
  шаблон сразу адаптировался под мой случай.
- **Как разработчик**, я хочу обновить существующий проект, созданный
  ранее, до новой версии методики (`copier update`), чтобы накопленные
  улучшения шаблона подтягивались без копирования вручную.
- **Как поддерживающий шаблон**, я хочу простую структуру (`copier.yml`
  + папка `template/`), чтобы изменения в методике вносились
  естественно и тестировались автоматически.

## 3. Functional Requirements

- **ДОЛЖНА:** команда `copier copy gh:vlakir/dreamteam ./project`
  создаёт работающий derived проект **без любых TEMPLATE-* файлов**
  и без примеров-для-удаления.
- **ДОЛЖНА:** интерактивные prompts при создании, с разумными
  defaults. Минимум — имя проекта, краткое описание, email автора.
- **ДОЛЖНА:** подстановка переменных в нужные файлы (`pyproject.toml`,
  `CONCEPT.template.md`, `PROJECT.md`, `README.md`).
- **ДОЛЖНА:** поддержка `copier update` — повторное применение
  шаблона к существующему проекту с merge user-изменений.
- **ДОЛЖНА:** все 4 pre-push проверки (ruff / format / mypy / pytest)
  проходят на сгенерированном проекте **immediately после
  `copier copy`** (без дополнительных правок).
- **МОЖЕТ:** post-generation hooks для удобства (например, `git init`
  в новом проекте) — но не как обязательное требование MVP.
- **НЕ ДОЛЖНА:** требовать установки template-package на PyPI —
  на MVP достаточно `gh:vlakir/dreamteam` reference.
- **НЕ ДОЛЖНА:** ломать совместимость с пока не мигрированными
  старыми проектами Разработчика. Они продолжают жить как есть.

## 4. Success Criteria

- **Скорость:** `copier copy gh:vlakir/dreamteam ./project` <
  30 секунд от запуска до готового проекта (включая интерактивные
  ответы).
- **Чистота:** в новом проекте 0 `TEMPLATE-*` файлов, 0 строк-примеров
  «удалить при заполнении», 0 плейсхолдеров `Your Name` / `you@`.
- **Готовность к работе:** `cd project && uv sync && uv run pytest`
  проходит зелёным без правок.
- **Update flow:** `copier update` в derived проекте подтягивает
  изменения шаблона; merge conflicts отображаются стандартным copier
  способом для ручного resolve.
- **Tests:** ≥ 80% coverage на copier-конфигурацию (через pytest +
  `copier.run_copy` API).

## 5. Key Entities

- **`copier.yml`** в корне репо шаблона — конфигурация: переменные,
  prompts, validators, exclude rules, версия copier-engine.
- **`template/`** — папка-родитель для всех файлов, которые попадают
  в derived проект (с jinja-переменными `{{ project_name }}` etc.).
- **Мета-документы шаблона** — `TEMPLATE-BACKLOG.md`,
  `TEMPLATE-BOARD.md`, `TEMPLATE-DECISIONS.md`, `TEMPLATE-CHANGELOG.md`
  — остаются в корне репо шаблона как maintainer-документы, **не**
  попадают в `template/`.
- **Тесты `tests/test_template.py`** — проверяют `copier copy` end-
  to-end (создание во временной директории, прогон ruff/mypy/pytest
  на результате).
- **`.copier-answers.yml`** — артефакт в derived проекте, который
  copier создаёт автоматически. Содержит ответы на prompts, version,
  и используется для `copier update`.

## 6. Assumptions & Constraints

- Python ≥ 3.10 на машине пользователя (требование copier).
- `git` установлен (требование copier для GitHub-templates).
- `uv` установлен — для использования сгенерированного проекта.
- Сценарий: один разработчик, один проект за раз. Multi-tenancy не
  рассматривается.
- Хостинг: репо лежит на GitHub. Для других хостингов copier
  поддерживает `gl:` / `bb:` префиксы — потенциально универсально,
  но MVP только GitHub.

## 7. Out of Scope

- **Не-Python шаблоны.** Сейчас только Python-проекты; универсальный
  multi-language скаффолдер — отдельная задача (T8XX).
- **PyPI публикация template-package.** На MVP `gh:vlakir/dreamteam`
  как reference достаточно.
- **Миграция старых Разработчиковых проектов.** Они остаются как
  есть; будут мигрироваться отдельной задачей по мере необходимости.
- **CI/CD пайплайн** для самого шаблона (тестирование через GitHub
  Actions на каждый PR) — желательно, но не блокер MVP. Это пересекается
  с **T007** (замена qodo / автоматический code review).
- **Сложные post-generation hooks** (git init, initial commit,
  pre-commit setup и т.п.). MVP: вручную после `copier copy`.

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
  будет **нативное** разделение: исходник шаблона = папка `template/`,
  результат = derived проект. **`TEMPLATE-*` мета-файлы (BACKLOG /
  BOARD / DECISIONS / CHANGELOG) остаются в корне репо шаблона** —
  но **не** в `template/`. То есть они продолжают существовать как
  «документы разработки самого шаблона», но физически уезжают **выше**
  по дереву. Это переосмысление T005 — не отмена, а уточнение в
  новом контексте.

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

- **Phase 1 — `T006-copier-bootstrap`.** Минимальный `copier.yml` +
  `template/` структура. Перенос Python-стартера (src/, tests/,
  pyproject.toml, uv.lock) в template/ с jinja-переменными
  (`{{project_name}}`, `{{author_name}}`, `{{author_email}}`).
  Acceptance: `copier copy` создаёт минимальный работающий проект
  (без методических `.md`-документов).
- **Phase 2 — `T006-copier-method-files`.** Перенос методических
  файлов (`CLAUDE.md`, `PROJECT.md`, `DECISIONS.md`, `CHANGELOG.md`,
  `BACKLOG.md`, `BOARD.md`, `CONCEPT.template.md`,
  `specs/spec-template.md`, `hooks/pre-push`) в `template/`.
  Подстановка переменных там где уместно. Acceptance: новый проект
  полностью соответствует текущей методике без TEMPLATE-* мусора.
- **Phase 3 — `T006-copier-tests`.** `tests/test_template.py`
  через `pytest-copier` или subprocess: `copier copy` →
  `uv sync && uv run pytest && ruff check && mypy` на результате.
  Coverage ≥ 80% на copier-config (если применимо).
- **Phase 4 — `T006-copier-docs`.** Переписать `README.md` репо
  шаблона под copier-flow (install copier, `copier copy gh:vlakir/
  dreamteam ./my-project`, `copier update` для существующих проектов).
  Удалить устаревшую инструкцию из 9 шагов. Обновить
  `TEMPLATE-CHANGELOG.md → [Unreleased]` (или сразу финализировать
  как `[1.0.0]`).
- **Phase 5 — `T006-copier-cleanup`.** Удалить ставшие ненужными
  default-name файлы из корня репо (они теперь живут только в
  `template/`). Удалить `README.template.md` (теперь
  `template/README.md`). Удалить `CONCEPT.template.md` (теперь
  `template/CONCEPT.md`). Сделать репозиторий шаблона **чистым** в
  плане «что вижу в корне = либо инструмент шаблона, либо документы
  его разработки».

После Phase 5 — закрываем как **`v1.0.0`** в `TEMPLATE-CHANGELOG.md`
с retrospective.
