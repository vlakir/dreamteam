# Spec: T009 — Full `dreamteam update` (diff/merge)

**Статус:** Draft
**Дата создания:** 2026-05-15
**Связанные документы:**
- `BACKLOG.md` (entry T009, оригинальная формулировка от 2026-05-14)
- `DECISIONS.md` → «Миграция на Copier + PyPI-distributed CLI (T006)»
  (известное ограничение MVP update, документировано)

---

## 1. Overview

`dreamteam update` в текущем MVP делает `copier.run_copy(...,
overwrite=True)` — это re-renders template-файлы поверх derived
проекта и **затирает** локальные правки пользователя в template-
managed файлах (`CLAUDE.md`, `README.md`, `CONCEPT.md`,
`BACKLOG.md`, `BOARD.md`, `CHANGELOG.md`, `DECISIONS.md` —
narrative-набор T013, плюс `pyproject.toml`, `hooks/pre-push`).
Это known limitation, документировано в command docstring и в
ADR T006.

Полноценный `update` должен делать three-way merge:
- **base** — template state на момент `dreamteam init` (или
  последнего update).
- **theirs** — текущий template state (новый, из
  installed `dreamteam-cli` package).
- **ours** — текущий state derived проекта (user edits + результат
  предыдущего update).

Не-конфликтные правки пользователя должны сохраняться; новые
правила из template должны подтягиваться; конфликты — fail
безопасно с понятной сигнализацией.

## 2. User Stories

- **Как владелец derived проекта, я хочу** `dreamteam update`
  забирал новые правила методики из обновлённого шаблона **без
  потери** моих локальных правок в `BACKLOG.md`, `BOARD.md`,
  `CHANGELOG.md`, `CLAUDE.md`, **чтобы** не мерджить вручную
  после каждого `pip install -U dreamteam-cli`.
- **Как владелец derived проекта, я хочу** одну команду
  (`dreamteam update`), **чтобы** не знать про copier internals,
  three-way merge или git plumbing.
- **Как владелец derived проекта, я хочу** видеть понятное
  сообщение в случае конфликта (git-style markers или явный
  reject-файл), **чтобы** разрешать вручную и не терять
  изменения.
- **Как maintainer dreamteam, я хочу** реализацию, которая
  работает с PyPI-distributed package (template как package-data),
  **чтобы** не требовать от пользователей клонировать репо.

## 3. Functional Requirements

- **ДОЛЖНА**: `dreamteam update <path>` производить three-way
  merge между *base / theirs / ours* для каждого template-
  managed файла.
- **ДОЛЖНА**: сохранять unchanged-by-user файлы — заменяются на
  новый template version.
- **ДОЛЖНА**: сохранять user-edited файлы без конфликтов —
  оставлять как есть, не клобберить.
- **ДОЛЖНА**: для конфликтных случаев — записывать конфликт-блоки
  в файл (формат — Clarify Q1).
- **ДОЛЖНА**: работать с PyPI-distributed package (template
  поставляется как package-data в wheel, без git history).
- **ДОЛЖНА**: сохранять идентичное поведение для multilang (T013)
  — три состояния (base/theirs/ours) рендерятся на сохранённом
  языке из `.copier-answers.yml`, before merge.
- **МОЖЕТ**: предоставлять `--dry-run` для preview без записи.
- **МОЖЕТ**: предоставлять `--force` flag — alias текущего
  MVP-поведения (overwrite without merge), на случай когда
  пользователь хочет «throw away local edits».
- **МОЖЕТ**: возвращать non-zero exit code при наличии
  конфликтов (для CI integration в derived проектах).
- **НЕ ДОЛЖНА**: rewriting git history derived проекта (никаких
  rebase / commit).
- **НЕ ДОЛЖНА**: требовать сетевого доступа в runtime (template
  в wheel, не из remote git).
- **НЕ ДОЛЖНА**: трогать файлы за пределами template-managed
  множества (user code в `src/`, тесты в `tests/`, и т.д., если
  не были template-rendered).

## 4. Success Criteria

- **Scenario A — clean update** (derived проект без user edits в
  template-managed файлах): `dreamteam update` → все файлы
  обновлены до новой версии, 0 конфликтов, exit 0.
- **Scenario B — user-edited non-conflict**: пользователь
  добавил bullet в `BACKLOG.md`, template добавил bullet в
  `CHANGELOG.md` → `dreamteam update` → оба изменения
  сохранены, exit 0.
- **Scenario C — conflict**: пользователь и template оба
  изменили один и тот же раздел в `CLAUDE.md` → `dreamteam
  update` → файл содержит конфликт-маркеры, exit ≠ 0,
  понятное сообщение со списком конфликтных файлов и hint
  о разрешении.
- **Scenario D — language preserved**: derived проект на ru
  (T013), template обновился → `dreamteam update` подтягивает
  ru-version новых файлов, не переключает на default `en`.
- **Integration test suite** на каждый scenario.
- 4 pre-push проверки (ruff / format / mypy / pytest) проходят
  с 0 ошибок на самом dreamteam-cli.

## 5. Key Entities

### Template state at init time (base)

Чтобы three-way merge работал, нужен snapshot template **на
момент init**. Текущий `.copier-answers.yml` содержит `_commit:
dreamteam-1.2.0` — это referenced commit/version, но не сами
файлы.

Опции хранения base — см. Clarify Q2:
- (a) bundle bare git repo внутри `dreamteam` wheel,
- (b) temp-extract from versioned package on update,
- (c) hash-based check + on-demand pip-download предыдущей
  версии,
- (d) другое.

### Three-way merge engine

Опции:
- `copier.run_update` (требует git-tracked template,
  необходимо обеспечить условие через одну из стратегий из
  Key Entities выше).
- `git merge-file` subprocess (POSIX-стандарт, требует git
  installed).
- Pure Python merge (e.g. `diff_match_patch`, `merge3` PyPI) —
  без git dependency, но менее обкатано.

### `.copier-answers.yml` extensions

Возможные новые поля:
- `_template_hash` — sha256 от template directory tree (для
  быстрой проверки «нужен ли update»).
- `_base_state_pointer` — путь / hash к base snapshot для
  three-way merge.

## 6. Assumptions & Constraints

- `dreamteam-cli` поставляется как PyPI package (wheel), template
  — package-data. Не меняем эту архитектуру.
- T013 multilang state в derived (`.copier-answers.yml →
  language: <lang>`) сохраняется при update. Все три состояния
  base/theirs/ours для merge рендерятся на сохранённом языке.
- User has standard dev environment (`python`, `pip`/`uv`,
  возможно `git`).
- Целевой случай — derived проекты с разумным количеством user
  edits (<100 правок per update); production-scale merge не
  целевая аудитория.

## 7. Out of Scope

- **Interactive merge UI** — никакого TUI / step-through prompt
  per conflict. File-level конфликт-маркеры (или reject-файлы) —
  достаточно.
- **Selective update** — `dreamteam update --only CLAUDE.md` или
  файл-by-файл выбор не делаем. Update — all-or-nothing.
- **History rewriting** в derived проекте (`dreamteam update
  --rebase`) — не трогаем git history.
- **Auto-resolve `.copier-answers.yml`** — этот файл всегда
  template-managed и обновляется самим dreamteam при update.
  Не считаем его «user-editable» для merge целей.
- **Migration helpers для breaking changes** — если новая версия
  template сломала совместимость (например, удалила файл, который
  user активно использовал), это — задача отдельной spec / ADR
  (`MAJOR` bump dreamteam-cli). Текущий T009 покрывает только
  backward-compatible updates.
- **Downgrade** — `dreamteam update --to-version 1.2.0` (откат на
  прошлую версию) — не делаем.
- **`dreamteam diff`** — отдельная команда для preview изменений
  без apply. `--dry-run` flag покрывает базовый use-case.

---

## Clarify (заполняется Разработчиком, потом Claude → Analyze)

### Open questions

- **Q1 (формат конфликт-маркеров)** — что предпочтительнее в
  случае непримиримого diff?
  - (a) **Git-style in-file**: `<<<<<<< theirs ... ======= ... >>>>>>> ours`
    прямо в `BACKLOG.md` / `CLAUDE.md`. Привычно для разработчиков,
    стандартный merge tooling (IDE, vimdiff) понимает. Минус:
    файл временно «сломан» как markdown — `<<<<<<<` будет
    отображаться буквально, пока конфликт не разрешён.
  - (b) **`.rej` files**: при конфликте оригинал остаётся как был
    (theirs или ours — на выбор), рядом создаётся `<file>.rej`
    с unified diff неприменённых hunks. Стандарт `patch -R`,
    `git apply --reject`. Чистый markdown в основном файле.
  - (c) **Дублирующие `.theirs.<lang>` файлы**: оригинал ours
    остаётся, рядом создаётся `<file>.theirs` с template-
    версией; user сам делает 3-way merge через IDE. Менее
    интрузивно, но больше работы.
  - (d) другое.

- **Q2 (хранение base state — template snapshot на момент last
  init/update)** — где?
  - (a) **Bundle bare git repo** в `src/dreamteam/template/.bundle/`
    при каждом build. Wheel становится ~150–300KB больше; update
    — `git clone --local .bundle /tmp/x && copier.run_update
    --vcs-ref=<commit>`. Все три состояния доступны.
  - (b) **Pip-download previous version**: `pip download
    dreamteam-cli==<base_version> -d /tmp/base; extract; use as
    template base`. Требует сетевого доступа и `pip`-availability
    на update.
  - (c) **Hash-based + bundled prior templates**: в wheel хранить
    отдельный `dreamteam/_history/` с каждой versioned template
    snapshot (1.0.0/, 1.1.0/, 1.2.0/, ...). Wheel разрастается
    линейно с числом releases (на 1.5x уже за 4 версии).
  - (d) **Не хранить base вообще** — делать **two-way merge** (theirs vs
    ours) без base. Менее точный, но проще: совпадающие куски
    — keep ours, расходящиеся — конфликт. Подходит если
    предположить, что user-edits локальны и не overlap-ят с
    template-changes.
  - (e) другое.

- **Q3 (git dependency)** — что делать, если `git` не установлен
  на user machine?
  - (a) **Fall back to current MVP** (`overwrite=True`) с явным
    warning «git not found, falling back to overwrite update;
    install git for full diff/merge support».
  - (b) **Hard error** + instruct install. Принудительно требуем
    git как dependency методики.
  - (c) **Pure-Python merge fallback** (e.g. `merge3` PyPI
    package). Зависимость +1 в `[dependencies]`, но без external
    binary.
  - (d) другое.

- **Q4 (`--force` flag)** — нужен ли явный flag для current
  MVP-behavior (overwrite without merge)?
  - (a) Да, `dreamteam update --force` = current MVP. Useful for
    «сбросить локальные правки шаблонной части».
  - (b) Нет — если user хочет overwrite, может вручную удалить
    template-managed файлы и запустить `dreamteam init` снова
    в ту же папку.
  - (c) другое.

- **Q5 (renamed / deleted в новой версии template)** — что
  делать с файлами, переименованными или удалёнными в новой
  версии?
  - (a) **Auto-follow**: rename ours, или delete если template
    delete-ит.
  - (b) **Preserve old + add new**: ours остаётся, дополнительно
    создаётся новый файл с новым именем. User мерджит вручную.
  - (c) **Conflict signal**: считается за «major change»,
    выводится в conflict report без auto-action.
  - (d) Не покрываем в этой spec — Out of Scope для MVP T009,
    отдельная задача.

- **Q6 (`.copier-answers.yml` upgrade при добавлении нового
  prompt)** — текущая ситуация: T013 добавил `language` prompt.
  Existing derived проекты на v1.2.0 не имеют `language` в
  answers file.
  - При `dreamteam update` сейчас (MVP overwrite) — copier добавит
    `language: en` (default).
  - При full update — что? (a) добавить default tихо, (b) prompt
    user даже в non-interactive update, (c) require explicit
    `--data language=...` при update если есть новые prompts,
    (d) другое.

- **Q7 (interaction с multilang T013)** — derived проект на ru.
  Template обновился в `i18n/ru/BACKLOG.md` (новый bullet) **и**
  user добавил свой bullet в derived `BACKLOG.md`. Three-way
  merge должен:
  - (a) merger ru → ru, both bullets present.
  - (b) merger всё в render-формате derived (after post-render
    task), на ru.
  - (c) что-то более сложное.

  Также: post-render task (`_tasks_post_render.py`) удаляет
  `i18n/` и strip frontmatter. Это means rendered tree в derived
  ≠ raw template tree в wheel. Нужно ли реверс-mapping для
  merge?

- **Q8 (`--dry-run` UX)** — что show при `--dry-run`?
  - (a) `git diff`-like unified diff на каждый файл.
  - (b) Сводка «N files would be updated, M unchanged, K
    conflicts».
  - (c) Both.

- **Q9 (Atomicity)** — что если update упал на третьем файле из
  10 (например, конфликт обнаружен в середине процесса)?
  - (a) **All-or-nothing** — atomic apply через tempdir + swap.
    Either все файлы обновлены, либо ничего.
  - (b) **Best-effort** — обновляем что можем, конфликтные
    оставляем с маркерами. User видит «3/10 success, 4
    conflicts, 3 untouched». Менее строго, проще.
  - (c) другое.

- **Q10 (Forward-compat с copier API)** — copier 9.x `run_update`
  явно требует git-tracked template. Если выберем Q2 → (a)
  bundle bare git repo — соответствуем. Если copier 10.x
  добавит native bundled-template support — нам мигрировать или
  держать свою реализацию? Это не блокер для spec, но влияет
  на implementation choice.

### Resolved (заполняется по мере ответов)

- ...

---

## Analyze (заполняется Claude после Clarify Resolved)

<!-- Issues с пометками 🔴 / 🟡 / 🟢. После прохождения Analyze
     спека переводится в статус Analyzed и идёт в implementation
     phases. -->

- ...

---

## Implementation Plan (черновой — финализируется после Analyze)

**Phase 1** — выбор и обкатка merge backend (`copier.run_update`
+ bundled git repo / `merge3` PyPI / `git merge-file`). На простом
2-файловом test case без T013 multilang.

**Phase 2** — full integration с multilang T013 (rendered-tree
mapping, language preservation, frontmatter handling).

**Phase 3** — conflict UX (формат маркеров из Q1, exit codes,
сообщения), `--dry-run`, `--force` (опционально из Q4).

**Phase 4** — docs / CHANGELOG / DECISIONS / version bump
(1.3.0 → 1.4.0 если backward-compatible, 1.3.0 → 2.0.0 если
breaking change в `update` semantics).
