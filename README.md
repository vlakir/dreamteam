# dreamteam

**Project scaffolding CLI with built-in methodology.** One command —
working project with linters, tests, kanban, ADR log, and a complete
set of rules for AI-assisted development baked in.

```bash
pip install dreamteam-cli                              # then `dreamteam` (or `dt`) is available
# or zero-install via uvx:
uvx --from dreamteam-cli dreamteam init my-project
# short form:
dt init my-project

cd my-project
uv sync
```

> **Note:** the PyPI package name is `dreamteam-cli` (the bare `dreamteam` slot on PyPI is held by an unrelated 2019 package). The **command** stays `dreamteam` regardless — `pip install dreamteam-cli` exposes the `dreamteam` console script, and that's what you use in everyday work. The package also installs **`dt`** as a short alias pointing at the same callable, so `dt init my-project`, `dt update --dry-run`, `dt --version` all work equivalently.

That's it. The generated project passes its own pre-push check suite
(ruff / ruff format / mypy / pytest with 80% coverage threshold)
immediately — verified by the integration test in this repo.

## What you get

Every project scaffolded by `dreamteam init` includes:

- **Python stack with your chosen package manager** — `dreamteam
  init` asks for `package_manager` (`uv` default, or `poetry` /
  `pdm` / `hatch` / `pip`); the rendered `pyproject.toml`,
  `CLAUDE.md`, and `README.md` use the right build-backend and
  command prefix for the chosen manager. `ruff` (`select = ["ALL"]`
  with a curated `ignore`), `mypy` (`mypy_path = "src"`), `pytest +
  pytest-cov + pytest-asyncio` with a `--cov-fail-under=80` gate
  are universal regardless of manager.
- **`src/`-layout** with a working `main.py` (CLI-style logging:
  DEBUG/INFO → stdout, WARNING+ → stderr) and a coverage-100%
  `tests/test_main.py`.
- **Methodology files** that are not just placeholders but
  ready-to-fill documents:
  - `CONCEPT.md` — immutable initial draft of the project vision.
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

## Multilingual methodology

`dreamteam init` first asks for a methodology language (default `en`):

```
language  [en (English) / ru (Русский) / fr (Français) /
           de (Deutsch) / zh (中文)]
```

The chosen language renders into the derived project's narrative files
(`CLAUDE.md` / `README.md` / `CONCEPT.md` / `BACKLOG.md` / `BOARD.md` /
`CHANGELOG.md` / `DECISIONS.md` / `specs/spec-template.md`). Technical
files (`pyproject.toml`, `src/`, `tests/`, `hooks/`) and kanban
keywords (`To Do` / `Doing` / `Done`) are language-agnostic.

**Source of truth — Russian.** Files in
`src/dreamteam/template/i18n/ru/` are hand-edited by the maintainer;
`en` / `fr` / `de` / `zh` are AI-translations from the Russian
source, generated through Claude Code (no Anthropic API, no runtime
cost — covered by the maintainer's Claude Max subscription). Each
translated file carries a YAML frontmatter with `translated_from`,
`source_hash` (sha256 of the ru source at translation time),
`translation_engine`, and `translation_date`. The frontmatter is
stripped from the rendered derived project — users see clean
markdown.

**Contributing to the methodology:**

1. Edit only `src/dreamteam/template/i18n/ru/<file>.md` (the source).
2. In a Claude Code session ask: *"re-translate this change into
   en/fr/de/zh and refresh `source_hash` in the frontmatter."*
3. Commit the ru edit together with the four regenerated translations.
4. CI guard (`scripts/translate_check.py`, runs after pytest in
   `.github/workflows/ci.yml`) verifies that the recorded
   `source_hash` matches the actual sha256 of `i18n/ru/<file>.md`.
   A mismatch fails the PR with a clear hint about regeneration.

For cosmetic ru edits (typo, whitespace, paragraph re-flow) the
short-cut is to ask Claude to refresh only the `source_hash` in all
four translations without retranslating the content. There is no
machine-readable way to distinguish cosmetic from semantic diffs —
maintainer judgment per change.

> **AI translation disclaimer.** All four non-Russian variants are
> AI-generated. They are reviewed by the maintainer at translation
> time but have not gone through a bilingual human review. PRs
> correcting wording, nuance, or terminology in any of the four
> languages are welcome. If you find a passage where the meaning
> diverges from the ru source — please open an issue.

## Applying to an existing project

If you started a project with another tool — PyCharm's new-project
wizard, `poetry new`, `hatch new`, or just `mkdir + cd` — and now
want to layer dreamteam's methodology on top, use:

```bash
dt apply my-existing-project
```

`dt apply` renders the template into a temporary preview, walks
every file, and decides per file:

- **File absent in target** → create silently.
- **File matches template render exactly** → no-op.
- **File differs** → 4-way interactive prompt:
  - `[k]eep` your version (default if you just hit Enter);
  - `[o]verwrite` with the template version;
  - `[d]iff` to see a unified diff (loops back to the prompt);
  - `[s]ave-as-new` writes the template content next to your
    file as `<file>.dt-new` for manual merge later.

`.venv/`, `.git/`, your `src/` packages and any non-template-managed
files are left alone.

For non-interactive runs (CI, scripts) pass `--on-conflict
<keep|overwrite|save-as-new>`. `--dry-run` prints the per-bucket
plan without writing anything. `--data key=value` (repeatable)
seeds copier answers the same way as `dt init`.

> **Pre-flight checks.** If the target already contains
> `.copier-answers.yml` (i.e. it was created via `dt init`),
> `dt apply` exits with a hint to use `dt update` instead.
> If stdin is not a TTY and `--on-conflict` was not supplied,
> the command exits before any render work with an explicit
> error.

After a successful apply the target carries a valid
`.copier-answers.yml`, so subsequent `dt update` (three-way merge
against future template evolutions) works the same as for an
`dt init`-ed project.

## Updating an existing project

When the methodology evolves, propagate the changes into your derived
project with a three-way merge:

```bash
cd my-project
dreamteam update                   # default: three-way merge
dreamteam update --dry-run         # preview: per-file diff + summary, no writes
dreamteam update --force           # MVP overwrite: re-apply, lose local edits
```

`dreamteam update` merges three states:

- **base** — the template snapshot at the moment of `dreamteam init`
  (or the previous successful update), pulled from a bare git repo
  shipped inside the wheel (`src/dreamteam/template/.bundle/`).
- **theirs** — the current template state from the installed
  `dreamteam-cli` package.
- **ours** — the current state of your derived project on disk.

Files you have not edited are updated to **theirs**. Files where
only you changed something are kept as-is. Files where both you and
the template changed the same region produce git-style markers
(`<<<<<<<` / `=======` / `>>>>>>>`) and the command exits with code
`2`, listing the conflicted files in stderr. Clean merges exit `0`;
hard errors exit `1`.

> **Requirements.** Your derived project must be a git repository
> (`git init && git add -A && git commit -m 'initial'` once after
> `dreamteam init`). The git binary must be on `PATH`. If either is
> missing, `dreamteam update` falls back to MVP overwrite behavior
> with a warning. The `--force` flag explicitly opts into MVP
> overwrite (escape hatch for "throw away my local edits and start
> fresh").

> **Preview before applying.** `dreamteam update --dry-run` shows
> exactly what would change without touching the target: per-file
> unified diff to stdout plus a one-line summary
> (`N would change, M unchanged, K added, L removed, X conflicts`).
> Exit code matches what an actual update would emit.

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

### Sandbox (try the tool without touching the repo)

`scripts/sandbox.sh` creates throwaway `dreamteam`-projects inside
`/tmp/dreamteam-sandbox/` (ephemeral, wiped on reboot). The path is
hardcoded — script refuses to write anywhere else.

```bash
scripts/sandbox.sh init                         # install from PyPI
scripts/sandbox.sh init --local                 # install from local dist/*.whl (builds if missing)
scripts/sandbox.sh init --name my-experiment    # custom name (default: test-<HHMMSS>)

scripts/sandbox.sh list                         # list existing sandbox projects
scripts/sandbox.sh shell my-experiment          # open sub-shell inside that sandbox
scripts/sandbox.sh clean                        # remove /tmp/dreamteam-sandbox/ (asks confirm)
```

Use `--local` when testing changes before publishing to PyPI. The
script builds `dist/dreamteam_cli-*.whl` if missing and installs
into a uv-managed cache (does not touch the repo's `.venv/`).

### Releases — publishing to PyPI

`scripts/publish.sh` builds and uploads to PyPI. Token lives in
`.secrets` (git-ignored — copy `.secrets.example` and fill in):

```bash
cp .secrets.example .secrets
# edit .secrets, paste PYPI_TOKEN

scripts/publish.sh                              # publish to real PyPI
scripts/publish.sh --test                       # publish to TestPyPI
```

The script runs `twine check` on built artefacts before upload to
catch metadata / README rendering issues.

## Status

Currently `v0.x` (pre-1.0). Stable feature set since `v0.2.0`
methodology consolidation; `v1.0.0` will be the first release with
this Copier/CLI architecture (T006). Roadmap in `BACKLOG.md`.

## License

[MIT](LICENSE) — Copyright (c) 2026 vlakir.

This applies to `dreamteam` itself. Projects generated via
`dreamteam init` do not automatically inherit MIT — license choice
is left to the user (add your own `LICENSE` after `init`).
