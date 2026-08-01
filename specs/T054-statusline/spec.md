# Spec: T054 — Statusline (shell-reader для `context.line`)

**Статус:** Analyzed
**Дата создания:** 2026-08-01
**Связанные документы:**
- Дизайн-документ E9: `specs/roadmap-v0.3-v1.0/design.md` (§421–423 E9.6
  «Statusline», §432 критерий «две сессии — каждая свою задачу», §1090+
  карточка T022 = репозиторный T054, §101–110 layout `by-worktree/<slug>/`).
- Фундамент: `specs/T033-store-core/spec.md` (`worktree_slug`, резолв
  `$DT_HOME` от git-common-dir, `by-worktree/`), `specs/T039-task-start/spec.md`
  (`context_line`, `write_binding`), `specs/T052-session-registry/spec.md`
  (SessionStart-хук пишет `context.line`), `specs/T051-context/spec.md`
  (`dt context` пишет `context.line`).
- Контракт `statusLine` Claude Code сверен по докам
  `https://code.claude.com/docs/en/statusline.md` (2026-08-01).
- ADR этой задачи: `DECISIONS.md` (2026-08-01 — «T054: statusline как
  git-only shell-reader, паритет slug с Python без запуска интерпретатора»).

---

## 1. Overview

Постоянный ответ на вопрос «над чем эта сессия». В `.claude/settings.json`
шаблона появляется `statusLine` типа `command` — короткий shell-скрипт,
который на каждом обновлении сообщений показывает в статусной строке
Claude Code задачу текущего worktree (`T054 [doing] Заголовок`) рядом с
именем рабочего каталога. Строку **уже пишут** SessionStart-хук (T052),
`dt task start` (T039) и `dt context` (T051) в `by-worktree/<slug>/context.line`;
T054 добавляет **только читателя** — скрипт вычисляет `<slug>` от рабочего
каталога и печатает содержимое файла. Скрипт не запускает Python, укладывается
в 50 мс и никогда не роняет статусную строку.

## 2. Сценарии использования

- **Постоянная ориентация.** Сессия привязана к задаче; в статусной строке
  всегда видно `dreamteam · T054 [doing] Заголовок` — не нужно спрашивать
  «над чем работаем».
- **Мгновенное отражение статуса.** `dt task move T054 review` из worktree,
  работающего над T054, сразу обновляет `context.line` этого worktree, и на
  следующем апдейте статуслайн показывает `[review]` — не дожидаясь
  SessionStart/`dt context`.
- **Две параллельные сессии (§432).** Два worktree одного репозитория, две
  сессии Claude Code. Каждая показывает **свою** задачу, потому что
  `context.line` разложен по `<slug>` рабочего каталога.
- **Непривязанная сессия.** В каталоге нет `context.line` для этого slug →
  статусная строка пуста, без ошибок и без блокировки работы.
- **Проект без оперативного слоя.** Каталог — git-репозиторий, но `$DT_HOME`
  ещё не создан (нет `.dt`) → файла нет → пустая строка, код 0.
- **Не git / нет git в PATH.** Скрипт не может определить worktree → пустая
  строка, код 0. Работе в проекте это не мешает (критерий приёмки §9).

## 3. Functional Requirements

Скрипт-читатель (`template/.claude/statusline.sh`):

- ДОЛЖЕН вычислять `<slug>` = `sha1(<resolved-abs-path worktree>)[:8]`
  **побитово идентично** `dreamteam.dt.paths.worktree_slug` (иначе прочитает
  не тот файл). Резолв symlink'ов через `cd "$top" && pwd -P` — эквивалент
  `Path(...).resolve()`.
- ДОЛЖЕН резолвить `$DT_HOME` идентично `dreamteam.dt.paths.dt_home`:
  переменная `$DT_HOME` — verbatim override; иначе от git-common-dir
  (`--path-format=absolute --git-common-dir`): common с именем `.git` →
  main = его родитель; иначе (bare) → main = сам common; итог —
  каталог-сосед `<main>.dt`.
- ДОЛЖЕН читать `<DT_HOME>/store/by-worktree/<slug>/context.line` и печатать
  одну строку: `<basename рабочего каталога> · <содержимое context.line>`.
- ДОЛЖЕН при **любом** сбое (нет git, не репозиторий, нет файла, пустой файл,
  нет `sha1sum`/`shasum`) выводить пустую строку и завершаться **кодом 0**
  (non-zero гасит статусную строку — контракт Claude Code).
- НЕ ДОЛЖЕН запускать интерпретатор Python и НЕ ДОЛЖЕН зависеть от `dt`
  в `PATH`.
- НЕ ДОЛЖЕН парсить stdin-JSON: команда исполняется с рабочим каталогом =
  cwd сессии (контракт), поэтому worktree берётся `git rev-parse` от `.`.
- МОЖЕТ иметь fallback `sha1sum` → `shasum` для переносимости (Linux/macOS).

`.claude/settings.json` шаблона:

- ДОЛЖЕН получить ключ `statusLine` типа `command`, где `command` —
  bootstrap, локализующий скрипт по git-toplevel (относительный путь
  ненадёжен: cwd сессии может быть подкаталогом) и терпимый к «не git»
  (`|| true`).
- НЕ ДОЛЖЕН ломать уже присутствующий блок `hooks.SessionStart` (T052).

`dt task move` (writer, design §778):

- ДОЛЖЕН после смены статуса перезаписывать `context.line` **текущего
  worktree** новой строкой — но ТОЛЬКО если перемещаемая задача и есть задача
  этого worktree. **Привязка авторитетна:** если worktree привязан
  (`current-task` есть) — обновляем строку лишь когда привязка называет именно
  эту задачу. Совпадение `HEAD` с `task.branch` — **fallback только для
  непривязанного** worktree (иначе общая ветка вроде `main` позволила бы
  `move` чужой задачи затереть строку привязанной). Иначе `context.line` не
  трогаем.
- НЕ ДОЛЖЕН менять `current-task`-привязку (перезапись только строки статуса)
  и НЕ ДОЛЖЕН падать вне git (git-контекст недоступен → тихий пропуск, `move`
  всё равно успешен). Ядро `move_task` остаётся git-free — git-эффект живёт в
  обёртке `task_cli.py`, как у `dt task start` (T039).

## 4. Success Criteria

- В worktree с привязанной задачей `statusline.sh` печатает
  `<каталог> · T054 [doing] Заголовок` для той же задачи, что показывает
  `dt context`.
- Отсутствие файла / не git / нет sha1-утилиты → пустой stdout, exit 0.
- Slug из скрипта совпадает с `worktree_slug()` для того же пути (тест
  паритета: скрипт читает файл, записанный `write_binding` по Python-slug).
- Полный проход скрипта < 50 мс на типичном репозитории (замер `time`;
  ≤ 2 вызова `git rev-parse` + 1 `sha1sum`).
- Две сессии в разных worktree дают разные строки (разные slug).
- `dreamteam init` на сгенерированном проекте проходит все 4 pre-push
  проверки; `.claude/settings.json` остаётся валидным JSON.

## 5. Key Entities

- **`context.line`** — файл `by-worktree/<slug>/context.line`, одна строка
  `T<NNN> [status] Title` (формат из `context_line`, T039). Источник истины
  для статусной строки; T054 его только читает.
- **`<slug>`** — 8 hex-символов sha1 от абсолютного resolved-пути worktree.
- **`$DT_HOME`** — `<main-worktree>.dt` (или override), корень оперативного
  слоя; `store/by-worktree/` внутри.
- **bootstrap-команда** в `settings.json` — локатор скрипта по git-toplevel.

## 6. Assumptions & Constraints

- Целевой harness — Claude Code; `statusLine` (`type: command`) исполняется
  с рабочим каталогом = cwd сессии, stdin = JSON (не используется), первый/
  единственный вывод в stdout = статусная строка, non-zero exit гасит её,
  debounce 300 мс, in-flight-запуск отменяется при новом апдейте.
- `git` в git-проекте по определению есть; sha1 в shell — `sha1sum`
  (coreutils, Linux) с fallback `shasum` (macOS). Python недопустим.
- `_templates_suffix: ""` → copier рендерит скрипт как Jinja: в тексте не
  должно быть литералов `{{`, `{%`, `{#` (shell `${}`/`$()` безопасны).
- Строка не обрезается по ширине (перенос — забота терминала); `COLUMNS`
  доступен, но в scope не используется.

## 7. Out of Scope

- **Догфудинг statusline на самом репо `dreamteam`**: у репо нет корневого
  `.claude/settings.json`, а store пуст до `dt migrate tasks` (T042) →
  строка всё равно была бы пустой. Отложить до T042.
- **Handover / устаревание** — T055. **Секция методики `sessions`** — T047.
- **Цвет ANSI, модель, ветка, PR, rate-limits** в статусной строке —
  минимализм; при потребности — отдельной задачей.

---

## Clarify (заполняется Claude)

### Open questions

1. **Формат строки.** Карточка T022 требует «базовое имя рабочего каталога
   рядом с ID задачи». Предлагаю `<каталог> · <context.line>`, напр.
   `dreamteam · T054 [doing] Statusline`. Устраивает разделитель `·` и
   порядок (каталог слева)? Альтернативы: только `context.line`;
   `[dreamteam] T054 …`; каталог справа.
2. **Разделение читатель/дизайн §778.** Подтвердить, что «`move` обновляет
   `context.line`» выносим в backlog отдельной задачей, а не тащим в T054.

### Resolved (с ответами)

1. **Формат строки** → `<каталог> · <context.line>` (каталог слева,
   разделитель `·`): `dreamteam · T054 [doing] Statusline`.
2. **§778 `move` → `context.line`** → включаем в T054 (осознанное решение
   Владимира при поднятом флаге scope). Реализуем с guard'ом (см. FR).

---

## Analyze (заполняется Claude)

- 🔴 **C1 — паритет slug (иначе фича не работает).** Скрипт обязан вычислять
  slug **побитово** как `worktree_slug`: `hashlib.sha1(str(Path(top).resolve())
  .encode())[:8]`. Три места рассинхрона: (a) symlink'и — git-toplevel может
  не быть полностью резолвнут, а Python делает `.resolve()` → в shell
  `resolved=$(cd "$top" && pwd -P)`; (b) кодировка — `printf '%s' "$path" |
  sha1sum` хеширует UTF-8-байты без перевода строки, как `.encode()`; (c)
  формат вывода `sha1sum` = `<hex>  -` → `cut -c1-8`. Тест-паритет обязателен:
  Python пишет `write_binding` по своему slug, скрипт должен прочитать тот же
  файл.
- 🔴 **C2 — non-zero гасит статуслайн.** Контракт Claude Code: любой ненулевой
  код или пустой stdout → статусная строка гаснет. Значит все ветки отказа
  (нет git / не репозиторий / нет файла / пустой файл / нет sha1-утилиты) →
  `exit 0` с пустым stdout. Это совпадает с желаемым «нет привязки → пусто».
- 🟡 **W1 — локализация скрипта.** cwd сессии может быть подкаталогом →
  относительный `.claude/statusline.sh` ненадёжен, а `~`/абсолют шаблон не
  знает. Решение: `command` = bootstrap через `git rev-parse --show-toplevel`
  + `|| true`. Цена — 2 вызова `git rev-parse` (bootstrap + скрипт), оба
  тривиальные, суммарно << 50 мс.
- 🟡 **W2 — Jinja-рендер скрипта.** `_templates_suffix: ""` рендерит
  `statusline.sh` как Jinja. Запрещены литералы `{{` `{%` `{#`; shell
  `${var}`, `$(...)`, `case … in *)` их не содержат — безопасно. Проверить
  `dreamteam init --defaults` на отсутствие артефактов рендера.
- 🟡 **W3 — footgun `move` чужой задачи.** Без guard'а `dt task move B …` из
  worktree, занятого задачей A, затёр бы `context.line` = B. Guard (перемещаем
  именно задачу этого worktree) закрывает это; тест на «move чужой задачи не
  трогает строку». **Уточнение (ревью qodo #1):** guard `bound==id OR
  branch==task.branch` дырявый — при общей ветке (`main`) второе условие
  срабатывает даже когда worktree привязан к другой задаче. Исправлено:
  привязка приоритетна (`bound==id`), branch-fallback только при `bound is
  None`; регресс-тест на «bound=A, B с той же веткой → строка A цела».
- 🟡 **W4 — многострочный вывод (ревью qodo #2).** `context.line` строится из
  `Task.title` без санитизации; `cat` печатал бы весь файл — при `\n` в
  заголовке статуслайн получил бы лишние строки. Reader читает только первую
  строку (`IFS= read -r line <file`), гарантируя один ряд; тест на файл с
  встроенным `\n`.
- 🟢 **N1 — двойная утилита sha1.** `sha1sum` (Linux/coreutils) с fallback
  `shasum` (macOS). Обе дают одинаковый хекс для одного stdin.
- 🟢 **N2 — общий file-I/O.** Хелперы `read_current_task`/`write_context_line`
  кладём в `dt/starts.py` (рядом с `write_binding`), чтобы знание о раскладке
  `by-worktree/<slug>/` не размножалось; `context_cli` может делегировать.
- 🟢 **N3 — длина строки.** `context.line` c длинным заголовком не обрезаем —
  перенос на терминале; `COLUMNS` доступен для будущего, в scope не входит.
