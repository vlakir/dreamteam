---
translated_from: i18n/ru/BACKLOG.md
source_hash: 97561a99e58717c8b3c1493b0669d8e69849ccff9ed8694c913846ee8908efb1
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Backlog

A parking lot for ideas, side findings and "should be fixed later".

**Rule:** if during work on the current task Claude or the Developer
notices something off-topic — it goes here, not into the current
commit. This is the scope-creep guard.

This is **not a formal task tracker** with deadlines and metrics —
it is an idea parking lot. But **order matters**: at the top — what
is planned next; lower — less urgent (FIFO by default; high-priority
items can be lifted to the top). When something is taken from the
backlog into work — it grows into a task or a spec
(`specs/T<NNN>-…`) and is removed from here.

## Format

`- **T<NNN>** — [<discovery date>] <short description> — <optional: context / where it surfaced>`

The ID is assigned at creation; the new one =
`max(existing T-IDs in BACKLOG.md, BOARD.md and CHANGELOG.md) + 1`.
The ID is not reused and is preserved as the task moves between
BACKLOG and BOARD; after a release the task moves to `CHANGELOG.md`
(with the same T-ID), which guarantees uniqueness across releases.

## Items

<!-- Example (delete when filling in the template):

- **T<NNN>** — [<date>] Logs are duplicated in stdout and the file — look at the logging config.
- **T<NNN+1>** — [<date>] The `parse_post` function has grown to 80 lines, asks for a split.
- **T<NNN+2>** — [<date>] Think about rate limiting on /publish (surfaced during clarify of the Telegram publishing feature).

-->
