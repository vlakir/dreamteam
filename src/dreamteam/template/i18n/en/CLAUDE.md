---
translated_from: i18n/ru/CLAUDE.md
source_hash: 5b86cdd58929d29c1432f734d68d9afec73e4b4c17937907c769d6453624ed1d
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Project rules for Claude

This file holds project-specific rules for Claude (Claude Code). The
global rules (`~/.claude/CLAUDE.md`) always apply; this file adds
only what is specific to this project.

## What to read at the start of a session

1. `CONCEPT.md` (if present) — initial project vision, an immutable
   document. Useful as an anchor months later.
2. `README.md` — current description / quick start / project status.
3. `DECISIONS.md` — architectural decisions already taken.
4. `BACKLOG.md` — what is queued up.
5. When working on a large feature — the corresponding
   `specs/T<NNN>-*/spec.md`.

## Ritual for filling in `CONCEPT.md` (for a new project)

At the start of a new project, Claude helps the Developer fill in
`CONCEPT.md` — an immutable document of the initial vision. The
ritual is a counter-questioning pass, analogous to `clarify` for a
large-feature spec:

1. The Developer writes a first sketch (or simply states the idea).
2. Claude asks counter-questions about blind spots:
   - **Goal:** what pain / task does the project solve?
   - **User:** who, in what context?
   - **Key functionality:** MVP minimum vs nice-to-have?
   - **Out of scope:** what we deliberately do NOT build (the main
     section — defence against scope creep from day one).
   - **Constraints and assumptions:** platform, stack, load,
     assumptions about environment / users.
3. The answers are sewn into `CONCEPT.md`, and the creation date is
   stamped.
4. **Once filled, `CONCEPT.md` is not edited.** Current state lives
   in `README.md`. If the concept changes drastically (rare, pivot) —
   a new version is added: `concepts/v2-...md`, `v3-...md`
   (ADR-pattern, but for concepts).

`CONCEPT.md` is filled either at project creation via
`dreamteam init` (Claude asks the counter-questions) or later, by
hand.

## Project description

{{ project_description }}

## Stack

**Baseline template stack (for Python projects):**
- Python 3.14+ (`requires-python` in `pyproject.toml`).
- Dependency and environment manager: `uv` (fast, from Astral).
- Linter: `ruff` (rule `select = ["ALL"]` with a fixed `ignore`).
- Type checker: `mypy` with `mypy_path = "src"`.
- Test stack: `pytest` + `pytest-cov` + `pytest-asyncio`. Coverage
  threshold ≥ 80% line coverage on `src/` (`--cov-fail-under=80`
  in `[tool.pytest.ini_options]`).
- **Source root — `src/`** (always, in every project).
- Tests — in `tests/` at the root (`ruff` excludes it, but `pytest`
  finds them via `testpaths = ["tests"]`).

**Typical commands:**
- `uv sync` — install dependencies (creates `.venv` on first run).
- `uv add <pkg>` / `uv add --dev <pkg>` — add runtime / dev dependency.
- `uv run python ...` — run inside `.venv` without activating it.
- `uvx <tool>` — run a CLI tool without local install.

Before every `git push` run **four** checks, each with 0 errors:
1. `uv run ruff check .`
2. `uv run ruff format --check .`
3. `uv run mypy <code>`
4. `uv run pytest` (includes coverage threshold ≥ 80%).

**Run them as a single chain**, so a failure at any step aborts the
commit:

```bash
uv run ruff check . && \
uv run ruff format --check . && \
uv run mypy <code> && \
uv run pytest && \
git add -A && git commit -m "..." && git push
```

**Catch-it-at-the-output:** if the previous command's output shows
`FAILED`, `Error`, `1 failed` or similar markers — **stop and check
the cause**. And do not mask exit codes: `pytest | tail -5` returns
`tail`'s exit code, not `pytest`'s — a failure silently slips into
`git commit`.

No `# noqa` / `# type: ignore` / `ignore`-section extensions without
explicit discussion with the Developer. Details — in the global
`~/.claude/CLAUDE.md`, sections "Linters" and "Testing".

## Git workflow

Baseline process rules (apply in this project always):

- **Tasks are numbered.** Each entry in `BOARD.md` / `BACKLOG.md`
  has an ID `T<NNN>`; the branch is `T<NNN>-<slug>`; the PR is
  `T<NNN>: <title>`. Exception — methodology PRs that change the
  rules themselves (no `T`-ID).
- **Direct push to `main` / `master` is forbidden.** Any change —
  through a feature branch and a PR/MR.
- **One PR — one commit.** On a feature branch commit however you
  like for the workflow; squash before merging.
- **Every PR goes through code review** before merge. By default —
  Claude (self-review with a checklist: scope / architecture / code /
  linters / docs / conventions / security). Sometimes — the Developer.
- **Do not ignore third-party reviews.** Bots like `qodo-code-review`
  must be read, analysed, discussed with the Developer; the decision
  is recorded (accept / drop / defer).

## Planning discipline

No Scrum ceremonies (sprints, story points, velocity, burndown). We
keep only the useful elements:

- **Milestone-based versioning.** `[Unreleased]` in `CHANGELOG.md`
  accumulates changes. The cut to a new version `[N.M.0]` happens
  when **meaningfully complete** (soft criterion): significant
  changes introduced, OR a logically related set of tasks closed,
  OR enough has accumulated for a save-point. The Developer makes
  the final call; there is no formal metric — that would contradict
  the "no Scrum-cargo" principle. Version format — Keep a Changelog
  (`## [N.M.0]`, no `v`-prefix).
- **Retrospective as a ritual** after closing a milestone. A short
  debrief in three points:
  - what worked (as expected, or a pleasant surprise),
  - what did not (bundling, slips, extra overhead),
  - methodology adjustments (what to change in
    `~/.claude/CLAUDE.md` / project `CLAUDE.md` / the template).
  Placement: **a `### Retrospective` section** inside the
  corresponding version entry in `CHANGELOG.md`. Not a separate file
  — the retro is tightly coupled to the milestone and is convenient
  to read next to it.
- **Acceptance criteria** are mandatory for tasks larger than a
  one-line edit — recorded directly in `BOARD.md` / `BACKLOG.md` as
  a short block (`Acceptance: <what must be achieved for the task
  to be considered closed>`) or in `specs/T<NNN>-*/spec.md` for big
  features. Without explicit acceptance criteria the task is not
  considered ready to move `BACKLOG → BOARD → Doing`.
- **WIP-limit** in `BOARD.md → Doing`: at most 1-2 tasks. More — and
  focus is lost (classic kanban rule).

If the Developer has a global `~/.claude/CLAUDE.md` configured —
that file holds the extended version of these rules (sections
"Never push directly to main", "One PR — one commit", "Code review
on every PR"). The short version above is a self-contained source.

## Project-specific rules

## What in this project usually goes to BACKLOG.md, not the current edit

