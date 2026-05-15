---
translated_from: i18n/ru/BOARD.md
source_hash: a34bdadb4bacaae4c37715eff6d323c0c0552189b61a1c1d266c8c75927febb0
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Board

A lightweight Kanban alternative in a single markdown file: three
columns (To Do / Doing / Done) under git, without external services
and tools.

## Relation to other files

- `BACKLOG.md` — a long queue of ideas and side findings. This is
  where "we'll think about it later", "not now" land. Scope parking.
- `BOARD.md` (this file) — the active work stream. Tasks we have
  taken on or are going to take on soon.
- `specs/T<NNN>-*/spec.md` — where a big task from BOARD grows when
  it turns out to be a >1-day feature.

Task life cycle: an idea in `BACKLOG.md` → matured → moves to `To Do`
here → taken into work (`Doing`) → closed (`Done`) → after a release
moves to `CHANGELOG.md` (the entry must contain the T-ID), and is
removed from here. **`CHANGELOG.md` is the only persistent store of
T-IDs of completed tasks**, without it the rule "ID is not reused"
breaks.

## Task format

Each task — `- **T<NNN>** — <short description>`. The ID is assigned
at creation: the new one =
`max(existing T-IDs in BOARD.md, BACKLOG.md and CHANGELOG.md) + 1`.
The ID is never reused. The ID is shared between `BOARD.md` and
`BACKLOG.md` — it is preserved when the task flows between them;
after a release the task lands in `CHANGELOG.md` with the same T-ID,
which guarantees number uniqueness across releases.

Branch name: `T<NNN>-<slug>` (no namespace like `fixes/` / `feature/`
— the ID already provides identification). PR name: `T<NNN>:
<title>`. Spec of a large feature: `specs/T<NNN>-<slug>/spec.md`.

Optional additions:

- a take-date label,
- a link to the spec,
- the branch name.

Example:

```
- **T<NNN>** — Post preview in Telegram
  (`specs/T<NNN>-telegram-preview/`, branch `T<NNN>-telegram-preview`).
```

---

## To Do

<!-- Ready to be taken. FIFO queue by default; high-priority items
     can be lifted to the top. -->

<!-- Task entries in the format `- **T<NNN>** — description`. See the
     "Task format" section above. -->

## Doing

<!-- In work right now. Keep short: at most 1-2 tasks per developer,
     otherwise focus is lost (the classic WIP-limit rule from
     Kanban). -->

- ...

## Done

<!-- Closed tasks waiting to be moved to CHANGELOG.md on the next
     release or significant point. After the move — clear it. -->

- ...
