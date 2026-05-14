# dreamteam

**Project scaffolding CLI with built-in methodology.** One command —
working project with linters, tests, kanban, ADR log, and a complete
set of rules for AI-assisted development baked in.

```bash
pip install dreamteam        # or: uvx dreamteam (zero-install)
dreamteam init my-project
cd my-project
uv sync
```

That's it. The generated project passes its own pre-push check suite
(ruff / ruff format / mypy / pytest with 80% coverage threshold)
immediately — verified by the integration test in this repo.

## What you get

Every project scaffolded by `dreamteam init` includes:

- **Python stack** — `uv` for deps, `ruff` (`select = ["ALL"]` with
  a curated `ignore`), `mypy` (`mypy_path = "src"`), `pytest +
  pytest-cov + pytest-asyncio` with a `--cov-fail-under=80` gate.
- **`src/`-layout** with a working `main.py` (CLI-style logging:
  DEBUG/INFO → stdout, WARNING+ → stderr) and a coverage-100%
  `tests/test_main.py`.
- **Methodology files** that are not just placeholders but
  ready-to-fill documents:
  - `CONCEPT.md` — immutable initial draft of the project vision.
  - `PROJECT.md` — passport (purpose, status, stack, links).
  - `DECISIONS.md` — ADR-Lite for architectural decisions.
  - `BACKLOG.md` / `BOARD.md` — markdown kanban with task numbering
    (`T<NNN>` IDs, branch naming, PR naming, spec folder naming).
  - `CHANGELOG.md` — Keep-a-Changelog style with retrospective
    sections at milestone boundaries.
  - `CLAUDE.md` — project rules for [Claude Code](https://claude.com/claude-code),
    including scope discipline, Git workflow, pre-push contract, and
    a structured code-review checklist.
- **`hooks/pre-push`** — optional local hook rejecting direct pushes
  to `main` / `master`.
- **`specs/spec-template.md`** — template for major-feature specs
  with `clarify` / `analyze` sections.

## Updating an existing project

When the methodology evolves, propagate changes:

```bash
cd my-project
dreamteam update
```

> **MVP limitation.** Current `dreamteam update` re-applies the
> template with stored answers (`overwrite=True`). Local edits to
> template-managed files will be overwritten. Full diff/merge update
> requires a git-tracked template, which is non-trivial for
> PyPI-distributed packages — planned as a follow-up task.

## How it works

`dreamteam` is a thin Typer-based CLI on top of
[Copier](https://copier.readthedocs.io/). The template lives at
`src/dreamteam/template/` inside the installed package; `dreamteam
init` calls `copier.run_copy` programmatically, then persists answers
to `.copier-answers.yml` so updates can replay them.

Methodology evolves in this repository:
- **`BACKLOG.md` / `BOARD.md`** — what's planned / in progress for
  the `dreamteam` package itself.
- **`DECISIONS.md`** — ADRs for the package (e.g., why `uv` over
  `poetry`, why `src/`-layout, why Copier, why TEMPLATE-prefix was
  introduced and then dropped).
- **`CHANGELOG.md`** — Keep-a-Changelog for the package, with
  retrospective sections at milestone boundaries.

In derived projects (created via `dreamteam init`) there is a
separate set of these files with the same names but different
content — they live in `src/dreamteam/template/` here and get
rendered into the user's project. The two sets never collide
because they're physically separated by the package boundary.

## Development

```bash
git clone https://github.com/vlakir/dreamteam.git
cd dreamteam
uv sync
uv run dreamteam init /tmp/sandbox --defaults   # try it
uv run pytest                                    # fast tests
uv run pytest -m integration                     # e2e (slow, runs uv sync inside generated project)
```

Pre-push checks (run all four with 0 errors before any push):

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Methodology rules — including scope discipline, never push to `main`,
one PR one commit, mandatory code review, task numbering `T<NNN>` —
are documented in `CLAUDE.md` (project-level) and `~/.claude/CLAUDE.md`
(developer-level, optional).

## Status

Currently `v0.x` (pre-1.0). Stable feature set since `v0.2.0`
methodology consolidation; `v1.0.0` will be the first release with
this Copier/CLI architecture (T006). Roadmap in `BACKLOG.md`.

## License

(to be added — see `BACKLOG.md`, task T010).
