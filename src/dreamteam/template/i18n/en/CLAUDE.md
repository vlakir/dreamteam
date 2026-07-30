---
translated_from: i18n/ru/CLAUDE.md
source_hash: 7eaae69f3591aa6e08d3aaa12ef0b3f0ac2158db49be286799b7c18e5848c934
translation_engine: claude-opus-4-8
translation_date: 2026-07-30
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
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

**The structure is a questionnaire, not a contract.** The sections
above (Goal / User / Key functionality / Out of scope / Constraints)
are **leading questions for an empty `CONCEPT.md`**, not a mandatory
form for the final document. If the project already has a substantive
`CONCEPT.md` / spec / vision in any form — Claude **accepts it as is**
and runs `clarify` on the blind spots of its content, **without
demanding** a recast into the template headings. The only mandatory
element of the ritual is **clarify** (counter-questions). `Out of
scope` remains the most valuable section (protection against scope
creep), but may be expressed in any form inside the existing document.
The immutable invariant (not edited once locked) holds in every case.

`CONCEPT.md` is filled either at project creation via
`dreamteam init` (Claude asks the counter-questions) or later, by
hand.

## Project description

{{ project_description }}

## Stack

**Baseline template stack (for Python projects):**
- Python 3.14+ (`requires-python` in `pyproject.toml`).
- Dependency and environment manager: **`{{ pm_name }}`** (chosen
  during `dreamteam init` via the `package_manager` prompt;
  alternatives: `uv` / `poetry` / `pdm` / `hatch` / `pip`).
- Linter: `ruff` (rule `select = ["ALL"]` with a fixed `ignore`).
- Type checker: `mypy` with `mypy_path = "src"`.
- Test stack: `pytest` + `pytest-cov` + `pytest-asyncio`. Coverage
  threshold ≥ 80% line coverage on `src/` (`--cov-fail-under=80`). The
  threshold is enforced by an **explicit command** in the pre-push gate
  and CI, not by the default `addopts` — the default `pytest` is kept
  deliberately light (see "Heavy test runs — through the mutex wrapper"
  below).
- **Source root — `src/`** (always, in every project).
- Tests — in `tests/` at the root (`ruff` excludes it, but `pytest`
  finds them via `testpaths = ["tests"]`).

**Typical commands (for the chosen `{{ pm_name }}`):**
{%- if package_manager == 'uv' %}
- `uv sync` — install dependencies (creates `.venv` on first run).
- `uv add <pkg>` / `uv add --dev <pkg>` — add runtime / dev dependency.
- `uv run python ...` — run inside `.venv` without activating it.
- `uvx <tool>` — run a CLI tool without local install.
{%- elif package_manager == 'poetry' %}
- `poetry install` — install dependencies (creates venv on first run).
- `poetry add <pkg>` / `poetry add --group dev <pkg>` — add runtime / dev dependency.
- `poetry run python ...` — run inside the poetry venv without activating it.
- `poetry env activate` — open a subshell with the venv activated.
{%- elif package_manager == 'pdm' %}
- `pdm install` — install dependencies (creates `.venv` on first run).
- `pdm add <pkg>` / `pdm add -dG dev <pkg>` — add runtime / dev dependency.
- `pdm run python ...` — run inside `.venv` without activating it.
{%- elif package_manager == 'hatch' %}
- `hatch env create` — create the `default` environment with dev deps.
- Dependencies are edited in `[tool.hatch.envs.default.dependencies]` in `pyproject.toml`.
- `hatch run <cmd>` — run a command inside the `default` env without activation.
- Scripts are defined in `[tool.hatch.envs.default.scripts]` and called as `hatch run <script>`.
{%- else %}
- `python -m venv .venv && .venv/bin/pip install -e .[dev]` — create a venv and install dev dependencies.
- `.venv/bin/pip install <pkg>` — install a package (then add it to `pyproject.toml` yourself; pip does not auto-update the manifest).
- `.venv/bin/python ...` or activate the venv (`source .venv/bin/activate`) and run `python ...`.
{%- endif %}

Before every `git push` run **four** checks, each with 0 errors:
1. `{{ pm_run }}ruff check .`
2. `{{ pm_run }}ruff format --check .`
3. `{{ pm_run }}mypy <code>`
4. `scripts/pytest-guard.sh --cov=src --cov-report=term-missing --cov-fail-under=80`
   — the full run with the ≥ 80% coverage threshold **through the mutex
   wrapper** (see "Heavy test runs — through the mutex wrapper" below).

**Run them as a single chain**, so a failure at any step aborts the
commit:

```bash
{{ pm_run }}ruff check . && \
{{ pm_run }}ruff format --check . && \
{{ pm_run }}mypy <code> && \
scripts/pytest-guard.sh --cov=src --cov-report=term-missing --cov-fail-under=80 && \
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

## Heavy test runs — through the mutex wrapper

When several `git worktree`s share one machine (see "Parallel work in
multiple git worktrees" below), the shared resource is **RAM**. A full /
coverage run holds a noticeable RSS; two or three at once (next to a
heavy IDE) stack into **OOM or a freeze**. The wrapper
`scripts/pytest-guard.sh` serialises heavy runs across ALL worktrees
through a shared per-user lock (concurrency 1, blocking wait: the second
run waits its turn and starts by itself). Only the **launch** is
serialised — code and uncommitted session state are never touched.

**Rule — what goes through the wrapper, what goes direct:**

- **Full / coverage run and the pre-push test gate — through the
  wrapper** (`scripts/pytest-guard.sh …`), not the bare runner;
  especially with live parallel sessions.
- **A single-file run** (light, one-off) — may go direct
  (`{{ pm_run }}pytest tests/test_x.py`); the mutex is optional.
- **CI — direct** (isolated runner, nothing to share).

**Light default run.** Coverage is kept out of the default `addopts`
(the coverage tracer inflates RSS/CPU): the default `{{ pm_run }}pytest`
stays light for repeated local iteration. The ≥ 80% threshold is still
enforced — just by an **explicit command** (gate 4 above and CI), not by
the default.

**Optional per-run memory cap.** The variable `PYTEST_GUARD_MEM_MAX`
(e.g. `4G`; `0` or unset — off): on Linux with a systemd session the run
is launched in a transient cgroup with an RSS limit, so a runaway test
is killed by the OOM-killer **inside its own cgroup** (the run fails,
but the machine and the IDE survive) instead of taking down the system.
Outside Linux/systemd (macOS, Windows, containers) it is a no-op — the
run still goes through the mutex.

**Cross-platform.** `flock` is util-linux (Linux / macOS-like). Where it
is absent (Windows) the wrapper **degrades gracefully**: it prints one
notice line and runs the tests directly (no serialisation), never
failing.

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
- **Closing a task — in its own PR.** Moving the entry from
  `BOARD.md → Doing` to `Done` is done **in the same squash commit** of
  the task PR, not in a separate chore-PR (after merge the task is Done
  anyway — `BOARD.md` just reflects reality). PR boundaries follow the
  task's logical cohesion; splitting related changes just to make "a
  shorter PR" is an anti-pattern (extra review overhead, review-bot
  quota burn).
- **Every PR goes through code review** before merge. If the project
  has a working automated review bot connected (CodeRabbit,
  qodo-code-review or similar, reviewing every PR) — it is the
  baseline, and **a separate self-review by Claude is not required by
  default**. Claude's self-review is needed in three cases: (1) **docs
  / methodology** — a PR changing only markdown / rules / specs (bots
  review prose poorly) → self-review stays the default; (2)
  **non-trivial code** — a targeted deep-review of the risk area
  (architecture, security, complex scope), at the Developer's request
  or Claude's initiative; (3) **fallback** — the bot is unavailable
  (rate-limit, down, no report within a reasonable window). Self-review
  checklist: scope / architecture / code / linters / docs / conventions
  / security.
- **Do not ignore third-party reviews.** Bots like CodeRabbit /
  qodo-code-review must be read, analysed, discussed with the
  Developer; the decision is recorded (accept / drop / defer).

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

## Where project knowledge lives (memory-agnostic)

**Core principle: all durable project knowledge lives INSIDE the
project** — in its repository (`CLAUDE.md`, `DECISIONS.md`, `docs/`,
`specs/`, `BOARD.md` / `BACKLOG.md`). Any **external** persistent
assistant-memory layer (if the Developer has one at all — they may not)
is **only an optional duplicate / backup**; the methodology must work
even WITHOUT it.

The reason is twofold:

1. External assistant memory is often tied to a path / machine and does
   not travel or get shared between working copies (worktrees) and
   platforms.
2. Knowledge about the project should travel with the repository to
   anyone who clones it.

**The rule:** first record the fact in the project's files, and only
then (if such a mechanism exists) optionally mirror it outside. "Mirror
it if you like, but everything about the project is inside the project."

## Working in parallel across several git worktrees

Several tasks can run **at the same time**, each in its own
`git worktree` (a separate working copy of the repository, shared
`.git`), so you don't switch branches inside a single checkout. At such
a moment **several Claude sessions** may be working in parallel in
different folders — one per worktree. They must know about each other
and not collide.

**The registry is the built-in `git worktree list`.** All worktrees
share one `.git`, so from any clone folder `git worktree list` shows ALL
sibling worktrees (path + branch + HEAD). No homemade registry file is
needed.

**Start ritual.** At the start of a session — `git worktree list` +
`git branch --show-current`. If there is more than one worktree,
**another session may be working** nearby on a different branch; its
path and branch are **someone else's territory**.

**Isolation (hard):**

- One worktree = one task = one branch. Do not check out, commit,
  rebase or push into someone else's branch; do not edit files under
  someone else's worktree path.
- Run gates and tests from **your own** environment. An inherited
  virtual-environment variable may point at **another** folder's
  environment — activate / point to your own, otherwise you run the
  checks in the wrong environment.
- **Shared "append-at-the-top" journals** (`DECISIONS.md`,
  `CHANGELOG.md`, `BOARD.md`, `BACKLOG.md`) almost always conflict when
  two parallel tasks merge. Touch **only your own task's entry**; before
  the PR always `git fetch` + `git rebase` onto fresh `main` and resolve
  conflicts (usually — keep the others' entries, add yours). Code of
  different tasks usually merges cleanly — it is the journal text that
  conflicts.

**Worktree lifecycle:**

- Create: `git worktree add ../<repo>-T<NNN> -b T<NNN>-<slug>` (or onto
  an existing branch).
- Before the PR: `git fetch` → rebase onto fresh `main` → squash into
  one commit (the "one PR — one commit" rule) → push → PR → review.
- After merge: `git worktree prune` + delete the local branch.

**Clean up after yourself — asking permission.** Once a task or a
related group of tasks is done, **propose removing the clone folder**
(worktree). But the clone may hold something needed (uncommitted work,
local notes, artifacts), so `git worktree remove` — **only after an
explicit "yes"** from the Developer. Do not remove it silently. The main
checkout and other people's worktrees are left untouched.

**Shared dev services — one instance per user.** If launching the app
brings up shared resources (a database, containers, a local config, a
busy port), two parallel copies **share** them — diverging
migrations / state, a fight over the port. Warn, and show how to isolate
(a separate DB / config / port per worktree).

**Memory is NOT shared between folders.** The assistant's file-based
auto-memory, if it has one, is usually tied to the cwd path: a session
started **inside** a clone folder gets a SEPARATE (empty) memory and
does NOT see the main folder's memory. So keep durable knowledge in the
repository's files (they are present in every worktree) — see "Where
project knowledge lives (memory-agnostic)" above. By default prefer
starting the session from the main folder and working on the worktree
via absolute paths.

## Project-specific rules

## What in this project usually goes to BACKLOG.md, not the current edit


## Team roles (Architect + Designer)

This project ships a reusable collaboration loop: the lead (this
session), a read-only Architect subagent, and an external Designer
(Claude Design). How to call them, the consultation ritual, and the
"proposed → human decided → ADR" loop live in a separate file:

@.claude/team-roles.md
