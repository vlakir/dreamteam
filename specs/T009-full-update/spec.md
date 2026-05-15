# Spec: T009 — Full `dreamteam update` (diff/merge)

**Статус:** Analyzed (Clarify resolved 2026-05-15, Analyze pass 2026-05-15)
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
- **ДОЛЖНА**: для конфликтных случаев — записывать **git-style
  in-file конфликт-маркеры** (`<<<<<<<` / `=======` / `>>>>>>>`)
  внутри файла (Q1 resolved).
- **ДОЛЖНА**: bundled bare git repo внутри wheel
  (`src/dreamteam/template/.bundle/`) использоваться как base
  storage для `copier.run_update --vcs-ref=<base_version>`
  (Q2 resolved). Версии в bundle помечаются tag-ами
  `v<MAJOR.MINOR.PATCH>` соответствующих template-snapshot-ов.
- **ДОЛЖНА**: при отсутствии `git` бинарника в `PATH` — fall back
  к текущему MVP-поведению (`copier.run_copy(..., overwrite=True)`)
  с явным `WARNING` в stderr: «git not found in PATH, falling
  back to overwrite update; install git for full diff/merge
  support» (Q3 resolved).
- **ДОЛЖНА**: предоставлять `--force` flag — alias к
  MVP-поведению (`overwrite=True`), для случая «throw away local
  edits and re-apply template clean» (Q4 resolved).
- **ДОЛЖНА**: предоставлять `--dry-run` flag, который выводит
  (a) top-line summary («N updated, M unchanged, K conflicts»)
  и (b) per-file unified diff, без записи на диск
  (Q8 resolved).
- **ДОЛЖНА**: возвращать exit codes — `0` = clean update,
  `1` = hard errors (broken template, IO failures, etc.),
  `2` = conflicts present (mergeable with manual intervention)
  — для CI integration в derived проектах.
- **ДОЛЖНА**: работать с PyPI-distributed package (template
  поставляется как package-data в wheel, без runtime network
  access).
- **ДОЛЖНА**: сохранять идентичное поведение для multilang (T013)
  — three-way merge выполняется в **render-формате derived**:
  base/theirs рендерятся (Jinja + post-render task) на языке из
  `.copier-answers.yml`, потом mergeable с ours (Q7 resolved).
- **ДОЛЖНА**: best-effort применение результатов — успешно
  смерженные файлы записываются, конфликтные — оставляются с
  маркерами, hard-errored — оставляются нетронутыми. Итоговое
  сообщение: «N/M succeeded, K conflicts, L errors» (Q9
  resolved).
- **ДОЛЖНА**: при добавлении нового prompt в template (например,
  T013 `language`) и отсутствии соответствующего ответа в
  существующем `.copier-answers.yml` — silent default (без
  interactive prompt). User может override через `dreamteam
  update --data language=ru` (Q6 resolved).
- **НЕ ДОЛЖНА**: переименовать или удалять файлы в derived
  проекте, если они rename-нуты / delete-нуты в новой версии
  template — это **out of scope** для T009 MVP. Выдаём явный
  WARNING в стиле «file `X` was renamed/deleted in new template;
  not auto-handled in this update, see follow-up task» (Q5
  resolved).
- **НЕ ДОЛЖНА**: rewriting git history derived проекта (никаких
  rebase / commit).
- **НЕ ДОЛЖНА**: требовать сетевого доступа в runtime (всё
  локально в bundled wheel).
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

### Bundled bare git repo (Q2 resolved → option (a))

`src/dreamteam/template/.bundle/` содержит **bare git repo** со
всеми template-snapshot-ами в виде tags
(`v1.0.0`, `v1.1.0`, …, `v1.3.0`, …). Создаётся build-time:
после Phase 3 каждого нового релиза dreamteam-cli, hatchling
запускает hook, который:

1. Берёт current `src/dreamteam/template/` контент (исключая
   сам `.bundle/`).
2. `git init --bare` в `.bundle/` (если не существует) → клонирует
   рабочий tree, commit-ит контент как `v<version>` tag.
3. `uv build` упаковывает `.bundle/` в wheel (через
   `[tool.hatch.build.targets.wheel] artifacts` или explicit
   pattern).

Wheel size estimate: текущий ~50KB → ~250-350KB после bundle
(rough — зависит от компрессии git и количества версий, но
linear-ish с числом версий: каждая снапшот добавляет diff,
не полный recopy).

### Three-way merge engine (Q2 / Q3 resolved)

**Primary path** (если `git` installed): `copier.run_update(
src_path=tempdir/clone-from-bundle, dst_path=derived,
vcs_ref=<base_version_tag>, defaults=True, overwrite=False)`.
Сам copier использует `git merge-file` под капотом для конфликт-
маркеров.

**Fallback path** (если `git` not in PATH): warning + текущий MVP
`run_copy(..., overwrite=True)`. Без diff/merge.

### `.copier-answers.yml` extensions

Существующие поля сохраняются как есть. Новых полей **не
добавляем** в MVP:

- `_commit: dreamteam-<version>` уже есть в существующих
  answers files — это становится `vcs_ref` для `run_update`
  (`v<version>` tag в bundle).
- `_template_hash` / `_base_state_pointer` — **отвергнуто** в
  пользу `_commit` reuse. Меньше migration пайна для derived
  проектов на v1.3.0.

### CLI surface

```text
dreamteam update <path>                  # default — three-way merge
dreamteam update <path> --force          # MVP overwrite (no merge)
dreamteam update <path> --dry-run        # preview, no writes
dreamteam update <path> --data key=value # override answers (rare)
```

Exit codes:
- `0` — clean update (no conflicts).
- `1` — hard error (broken template, IO, missing answers file).
- `2` — conflicts present (merge attempted, manual fixup needed).

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
  per conflict. File-level git-style маркеры — достаточно.
- **Selective update** — `dreamteam update --only CLAUDE.md` или
  файл-by-файл выбор не делаем. Update — all-or-nothing на
  уровне entry point; внутри best-effort per-file (Q9).
- **Renames / deletions в новой версии template** (Q5 resolved):
  не auto-handled в T009 MVP. WARNING + manual fixup. Отдельная
  follow-up задача (новый T-ID при необходимости).
- **History rewriting** в derived проекте (`dreamteam update
  --rebase`) — не трогаем git history.
- **Auto-resolve `.copier-answers.yml`** — файл template-managed,
  обновляется самим dreamteam при update. Не считаем его
  «user-editable» для merge целей.
- **Migration helpers для breaking changes** — если новая версия
  template сломала совместимость, это — задача отдельной spec /
  ADR (`MAJOR` bump dreamteam-cli). Текущий T009 покрывает
  только backward-compatible updates (MINOR/PATCH bumps).
- **Downgrade** — `dreamteam update --to-version 1.2.0` (откат на
  прошлую версию) — не делаем.
- **`dreamteam diff`** — отдельная команда. `--dry-run` flag
  покрывает базовый use-case (Q8).
- **All-or-nothing atomicity** (Q9 resolved → best-effort):
  partial success разрешён; failure на одном файле не откатывает
  успешные мержи.
- **Interactive prompt при new template prompts** (Q6 resolved →
  silent default): не спрашиваем user-а при `dreamteam update`,
  если template добавил новый prompt с default-значением.

---

## Clarify

### Resolved (2026-05-15)

- **Q1 (формат конфликт-маркеров) → (a) Git-style in-file**
  (`<<<<<<<` / `=======` / `>>>>>>>`). Стандарт, IDE/vimdiff
  понимают, copier-default. Markdown временно «сломан» в
  конфликтной зоне — acceptable, конфликт виден сразу.

- **Q2 (хранение base state) → (a) Bundled bare git repo**
  в `src/dreamteam/template/.bundle/`. Wheel вырастет ~50KB →
  ~250KB, без runtime network. Альтернативы (pip-download /
  versioned history / two-way merge без base) отвергнуты:
  network dependency / линейный wheel growth / unacceptable
  accuracy loss на overlapping kanban-edits.

- **Q3 (git absent) → (a) Fall back to MVP `overwrite=True`**
  с явным WARNING в stderr. Min friction; dev environments без
  git — редкость; pure-Python merge (`merge3` PyPI) отвергнут —
  лишняя dependency для редкого fallback case.

- **Q4 (`--force` flag) → (a) Yes, alias к MVP-поведению**.
  Escape hatch «throw away local edits» полезен.

- **Q5 (renames / deletions) → (d) Out of scope для T009 MVP**.
  WARNING + manual fixup. Отдельная follow-up задача при
  возникновении реального случая.

- **Q6 (`.copier-answers.yml` upgrade с новыми prompts) → (a)
  silent default**. Update не должен быть interactive
  (cron-friendly, scripted-use-case). Override через
  `--data key=value`.

- **Q7 (multilang interaction) → (b) merge в render-формате
  derived** на сохранённом языке. Engine рендерит base/theirs
  через template machinery (Jinja + `_tasks_post_render.py`) до
  three-way merge с ours; ours остаётся as-is. Mapping
  template-tree ↔ derived-tree уже handled post-render task,
  не нужен reverse mapping — мы просто render new state и
  делаем merge на rendered files.

- **Q8 (`--dry-run` UX) → (c) both** — top-line summary
  («N updated, M unchanged, K conflicts») + per-file unified
  diff. Cheap to implement, polished UX.

- **Q9 (atomicity) → (b) best-effort**. Success per-file,
  conflicts оставляем с маркерами, hard errors остаются
  нетронутыми. Итоговый report: «N/M succeeded, K conflicts,
  L errors». All-or-nothing откатывает успешные мержи из-за
  одного конфликта — плохой UX.

- **Q10 (forward-compat copier 10.x) → не блокер**. Q2 (a) →
  bundled bare git repo совместим с copier 9.x `run_update`.
  Если copier 10 добавит native bundled-template — мигрируем
  отдельной задачей (новый T-ID), без breaking changes для
  derived проектов.

---

## Analyze (2026-05-15)

### Issues

- 🟡 **Warning — Wheel size growth.** Bundled bare git repo
  добавит ~200KB к wheel (rough estimate; depends on number of
  template snapshots и git compression). Это 4-5× от текущего
  размера. **Mitigation:** (1) shallow snapshots если git tooling
  позволяет; (2) `git gc --aggressive` в bundle при build;
  (3) принять как стоимость full-update feature и документировать
  в DECISIONS ADR.

- 🟡 **Warning — Bundle creation at build time.** Hatchling
  hook должен создавать `.bundle/` *детерминированно* (одинаковый
  hash при повторном build). Git timestamps могут вносить noise.
  **Mitigation:** использовать `git commit-tree` с fixed
  `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE` (e.g., release date в
  CHANGELOG) и `core.compression=0` для reproducible builds. См.
  reproducible-builds.org для precedent.

- 🟡 **Warning — `.copier-answers.yml` без `_commit` поля.**
  Derived проекты, созданные через `dreamteam init` на v1.0.0–
  v1.2.0, могут иметь `_commit: dreamteam-1.0.0` (текущий
  pattern), но **строка-формат**, не git ref. Bundle expects
  git tag (`v1.0.0`). **Mitigation:** mapping logic в update
  command — strip `dreamteam-` prefix, prepend `v`. Document
  как migration note.

- 🟡 **Warning — Multilang interaction subtlety.**
  При `dreamteam update` для derived с `language: ru`:
  base рендерится из `v<old>` tag (i18n/ru/), theirs — из
  current template (i18n/ru/). Both pass through
  `_tasks_post_render.py` to produce rendered tree. Но ru-source
  файлов в `i18n/ru/` мог измениться структурно (например,
  переставлены секции) — git merge на rendered output может
  показывать spurious conflicts там, где semantically всё OK.
  **Mitigation:** smoke test после Phase 2 на realistic scenario
  (user edits CLAUDE.md ru-перевод + template обновился);
  document типичные false positives.

- 🟢 **Note — Conflict markers visibility for non-Git users.**
  Derived проекты могут принадлежать пользователям без git
  background. `<<<<<<<` markers могут запутать. **Mitigation:**
  в exit message `dreamteam update` (exit code 2) включить
  пример «conflicts in files X, Y, Z; resolve markers
  `<<<<<<<` / `=======` / `>>>>>>>` — see <link to docs>».

- 🟢 **Note — Test matrix combinatorics.** 4 scenarios (A/B/C/D)
  × 5 languages = 20 integration cases. Слишком много. **Plan:**
  4 scenarios × en (full coverage) + 1 scenario × 4 other
  languages (sanity) = 8 cases total. Multilang correctness
  доказывается отдельно (от T013), здесь — sanity.

- 🟢 **Note — Bundle git binary at build time.** Hatchling
  build host должен иметь `git` installed для создания bundle.
  Это OK на dev-машинах и в CI (GitHub Actions runners имеют
  git pre-installed), но `pip install --no-build-isolation` на
  host без git может упасть. **Mitigation:** wheel поставляется
  с готовым bundle (no build на user side); sdist install
  documented как требующий git.

- 🟢 **Note — Per-file rendering cost.** Three-way merge для
  каждого файла = (render base) + (render theirs) + (read ours)
  + (git merge-file). Для 8 narrative files в template = ~8×
  rendering. Acceptable performance-wise для interactive
  command (~1-2 sec total), не для batch use.

### Verdict

Все Clarify questions Q1–Q10 resolved. Critical блокеров нет
(0 🔴). Четыре 🟡 warnings с mitigation в Implementation Plan.
Три 🟢 notes для memory. Spec → **Analyzed**, готов к
implementation phases.

---

## Implementation Plan

**Phase 0 — Spec drafting, Clarify, Analyze.** Завершена в PR #44:
этот документ. Включает Draft → Clarify (Q1–Q10 resolved) →
Analyze (0 🔴 / 4 🟡 / 3 🟢) → Analyzed.

**Phase 1 — Bundled bare git repo + merge backend.**
- Hatchling build hook создаёт `src/dreamteam/template/.bundle/`
  с tag-ом `v<current_version>` (reproducible через fixed dates).
- `cli.py update` flow:
  1. Read `.copier-answers.yml`, extract `_commit` → derive
     `base_version_tag` (strip `dreamteam-`, prepend `v`).
  2. `shutil.which('git')` — если absent, warn + fall back to
     MVP `run_copy(..., overwrite=True)`. Done.
  3. tempdir → `git clone --local .bundle/ /tmp/<unique>`.
  4. `copier.run_update(src=tempdir, dst=derived,
     vcs_ref=base_version_tag, defaults=True, overwrite=False)`.
  5. Cleanup tempdir.
- Unit tests на mapping `_commit` → tag, на git fallback path.
- Smoke test на artifical 2-file template без multilang.

**Phase 2 — Multilang integration + full file matrix.**
- Render-tree mapping: убедиться, что `_tasks_post_render.py`
  применяется при `run_update` на base/theirs. Render output
  должен быть консистентен между runs (тот же `language` из
  answers).
- 8 narrative-файлов в template × 5 languages — sanity matrix
  (см. Analyze Note).
- Scenario tests A-D (см. Success Criteria).

**Phase 3 — Conflict UX + flags + exit codes.**
- `dreamteam update --dry-run`: top-line summary + per-file
  unified diff (через `difflib.unified_diff` или git
  diff-tree).
- `dreamteam update --force`: alias к текущему MVP
  `run_copy(..., overwrite=True)`.
- Exit codes: 0 / 1 / 2 (clean / error / conflicts).
- Conflict message с hint про markers + link to docs.
- Renames/deletions WARNING (out of scope, just notify).

**Phase 4 — Docs / CHANGELOG / DECISIONS / version bump.**
- ADR T009 в `DECISIONS.md` (выбор bundled git vs alternatives,
  best-effort vs atomic, git fallback policy).
- CHANGELOG `[Unreleased]` → Added.
- Version bump: 1.3.0 → 1.4.0 (MINOR — backward-compatible;
  default `dreamteam update` теперь three-way merge, но old
  behavior доступен через `--force`).
- README update: new merge semantics, `--dry-run` / `--force`
  flags, behavior на git absent, expected conflict-marker format.
- Final integration suite green.
