# Project rules for OpenCode — `dreamteam` package

Проектные правила для OpenCode при работе **над пакетом dreamteam** (этим
репо). Глобальные правила (`~/.config/opencode/AGENTS.md`) применяются всегда;
здесь — специфика репозитория.

**Важно:** этот файл — правила для работы над **самим пакетом**. Файл
`src/dreamteam/template/AGENTS.md` — отдельный документ; он попадает в
**derived projects** через `dreamteam init`. Не путать.

## Что прочитать в начале сессии

1. `BACKLOG.md` — актуальный бэклог пакета.
2. `BOARD.md` — что прямо сейчас в работе (To Do / Doing / Done).
3. `DECISIONS.md` — ADR-Lite, ключевые архитектурные решения
   (`uv`, `src/`-layout, logging-split, Copier+PyPI, …).
4. При работе над крупной задачей — соответствующий
   `specs/T<NNN>-*/spec.md`.
5. При желании контекста эволюции — `CHANGELOG.md` (последняя версия
   + retrospective).

## Описание проекта

**`dreamteam`** — project scaffolding CLI с встроенной методологией.
Пользователь делает `pip install dreamteam-cli && dreamteam init my-project`
и получает готовый Python-проект с pytest, mypy, ruff, kanban в
markdown-файлах, ADR-log и полным набором правил для AI-assisted
разработки.

Внутри — тонкий Typer-based CLI поверх Copier. Template для derived
проектов лежит как package-data в `src/dreamteam/template/`.

## Стек

- **Python 3.14+** (`requires-python` в `pyproject.toml`).
- **Менеджер зависимостей и окружения:** `uv` (см. ADR в `DECISIONS.md`).
- **Build system:** `hatchling`.
- **CLI:** `typer` (Annotated-style для параметров).
- **Templating:** `copier` 9.x.
- **Linter:** `ruff` (`select = ["ALL"]` с фиксированным `ignore`).
- **Type checker:** `mypy` с `mypy_path = "src"`,
  `exclude = ["src/dreamteam/template/"]`.
- **Testing:** `pytest` + `pytest-cov` + `pytest-asyncio`.

## Команды разработки

```bash
uv sync                                  # установить deps, package в editable
uv run pytest                            # fast tests (CLI, без integration)
uv run pytest -m integration --no-cov    # slow e2e (init + uv sync + 4 проверки на результате)
uv run dreamteam init /tmp/x --defaults  # smoke-test после правки template/
uv run dreamteam update /tmp/x           # smoke-test update flow
uv build                                 # wheel + sdist в dist/
```

## Pre-push контракт

Перед каждым `git push` четыре обязательные проверки с 0 ошибок:

1. `uv run ruff check .`
2. `uv run ruff format --check .`
3. `uv run mypy src`
4. `uv run pytest` (fast suite; integration tests запускаются точечно).

Никаких `# noqa` / `# type: ignore` / расширений `ignore`-секций без
явного обсуждения с Разработчиком — даже когда ruff выдаёт ложно-
положительные срабатывания (типичные false positives и обходы без
noqa собраны в `DECISIONS.md` и в `src/dreamteam/cli.py`-комментариях).

## Специфика репо

- **Two AGENTS.md в одном репо**: этот файл — для работы над `dreamteam`;
  `src/dreamteam/template/AGENTS.md` — для derived проектов
  (попадает в `dreamteam init` результат). При изменении методики
  обычно нужно править **оба**.
- **Template живёт в `src/dreamteam/template/`** как package-data
  (`[tool.hatch.build.targets.wheel] packages = ["src/dreamteam"]`).
  При rename / restructure template файлов проверять, что
  `uv build` не выдаёт duplicate-name warnings и что
  `dreamteam init` на сгенерированном проекте проходит свои pre-push
  проверки.
- **Jinja syntax в template/**: ruff / mypy / coverage явно
  `exclude` для `src/dreamteam/template/` (там не валидный Python /
  не валидный markdown с jinja-vars).
- **`copier.Worker`** используется в `init()` для capture user
  answers (run_copy возвращает None). Worker помечен как internal
  API в copier (deprecation warning) — accept до public alternative.
- **`dreamteam update`** использует three-way merge по bundled base,
  сохраняя пользовательские правила. `--force` явно перезаписывает только
  файлы шаблона после проверки путей; dry-run не копирует дерево проекта.
  Миграция без проверяемой базовой версии останавливается без записи.

## Task numbering

Каждая задача из `BACKLOG.md` / `BOARD.md` получает ID `T<NNN>`
(три цифры). Scope `max()` — по этим двум плюс `CHANGELOG.md`.
Новый ID = `max(существующих) + 1`. ID не переиспользуется.

Имя ветки: `T<NNN>-<slug>`. Имя PR: `T<NNN>: <title>`. Папка спеки
крупной фичи: `specs/T<NNN>-<slug>/spec.md`. Методические PR
(правки самих правил) — без `T`-ID, имена `meta/<slug>` или
`rules/<slug>`.

## Git workflow

Полная версия — в глобальном `~/.config/opencode/AGENTS.md`. Ключевые правила:

- **Никогда не пушить напрямую в `main`.** Branch Protection
  включена на `vlakir/dreamteam` (см. ADR T001), сервер блокирует.
- **Один PR — один коммит** (squash при merge).
- **Закрытие задачи — в её же PR.** Перенос `BOARD.md → Doing` в
  `Done` делается в том же squash-коммите задачного PR, не отдельным
  chore-PR. Границы PR — по логической связности задачи; дробить
  связное ради «PR покороче» — anti-pattern. Fallback chore-PR — если
  перенос забыли и обнаружили после merge.
- **Code review каждого PR.** На `vlakir/dreamteam` подключён
  CodeRabbit — он baseline, отдельный self-review OpenCode'а на код-PR
  по умолчанию не нужен. Self-review (`gh pr review --comment`,
  чеклист scope / архитектура / код / линтеры / документация /
  соглашения / безопасность) остаётся дефолтом для **docs / методика**
  PR (боты слабо ревьюят прозу), а также как targeted deep-review
  нетривиального кода и как fallback при недоступности бота. Сторонние
  ревью (CodeRabbit / qodo и т.п.) не игнорировать.
- **Импорты только в шапке модуля.** Никаких lazy / conditional
  imports в runtime коде. Исключение — `TYPE_CHECKING`-блоки для
  type hints.
- **Scope discipline** — не «заодно». Побочные находки — в
  `BACKLOG.md` через новый T-ID.
- **Catch-it-at-the-text** — порядок упоминания мест в правилах
  имеет значение; durable источники первыми (`AGENTS.md` / global
  `~/.config/opencode/AGENTS.md`), README — расширенная версия для людей.

## Собственная команда dreamteam

Репозиторий библиотеки использует собственный OpenCode шаблон: opencode.json,
девять ролей в .opencode/agents и .opencode/team-roles.md. Сначала запустить
`dt serve .`, затем подключаться через `dt run .`; дополнительные клиенты
подключаются к этому же серверу. Правила разработки пакета в этом AGENTS.md
имеют приоритет над общими примерами шаблона.
