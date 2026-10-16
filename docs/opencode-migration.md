# Migrating a selected project to OpenCode

## Release boundary

This guide describes the project migration contract in **dreamteam 2.0.0**.
Successful package installation alone does not prove project migration safety.
The validation scenarios and release evidence are recorded in
`specs/T171-complete-opencode-migration/acceptance.md`; read the supported-input
and platform limits below before changing an existing project.

Historical bundle snapshots, version tags, ADRs and translation provenance are
retained deliberately. They provide the old base for safe merges, not active
Claude CLI dependencies. Anthropic API remains a legitimate OpenCode provider.
Provider/model choices and credentials belong in personal configuration;
neither Claude CLI, Codex CLI nor an Anthropic Pro/Max subscription is required.

## Package installation is not project migration

Installing or upgrading `dreamteam-cli` installs the package only. It does not
scan repositories or change projects. Install the intended accepted package
version first; then choose **one explicit root**:

```bash
# Already managed by dreamteam (.copier-answers.yml present):
dt update /path/to/project --dry-run
dt update /path/to/project

# Existing, unmanaged project:
dt apply /path/to/project --dry-run --on-conflict keep
dt apply /path/to/project --on-conflict keep
```

The apply examples explicitly select the ordinary template conflict policy so
they also work without an interactive terminal. `keep`, `overwrite` and
`save-as-new` do not override migration safety or silently discard legacy
content. Use `dt init` for a new project; it generates active OpenCode files in
all five methodology languages and does not need an old migration baseline.

Before modifying a valuable project, work on an independent copy. Exclude real
credentials, `settings.local`, `.git`, worktrees, environments and external
symlinks; use synthetic markers for secret tests. Verify that its Git directory
and paths are independent of the original. A successful rehearsal is evidence
for that scenario, not a claim that every arbitrary legacy project can migrate.

## Runtime prerequisite, before any migration writes

The current legacy migration and migration-recovery implementation requires
POSIX ownership/mode checks and directory fsync support. On platforms without
these capabilities it refuses with exit `1` before recovery or project writes;
it does not assume equivalent Windows ACL protection. This boundary is specific
to legacy migration/recovery, not an additional prerequisite for native
OpenCode projects without a pending migration. Secure Windows legacy
migration/recovery is neither implemented nor tested. The developer explicitly
accepted full **Linux release gates** as sufficient for T171 stable 2.0.0; this
does not claim Windows migration acceptance or waive any other release gate.
Ordinary native OpenCode CLI must remain usable.

Install **OpenCode 1.19.0** on the host executing migration and put `opencode`
on PATH. This exact release is supported; future releases are not assumed
compatible. Ensemble 0.18.0 is the team coordination version, but migration
preflight does not start Ensemble, a server, an agent, API calls or MCP.

Migration runs the local `opencode --version` executable from a safe existing
service directory, with a **5-second timeout**. It checks execution, exit status
and a strictly recognized supported version. Missing, non-executable, broken,
timed-out, malformed or unsupported runtimes cause exit `1` before project
writes, recovery snapshots, prompts, deletes or answers. No login, provider,
network access or automatic installation is required for this probe. Raw probe
stdout/stderr is not printed, since it may contain sensitive output.

If planning and applying are separated by a pause, the prerequisite must be
checked again before the first write. `--force` cannot bypass it. Dry-run is
also local and read-only: it creates no journal, snapshot, answers or directories.

## Supported content and safe blockers

`dt update` uses a verified historical bundled base; when that base or required
Git support is unavailable, legacy migration blocks instead of overwriting,
including with `--force`. Unmanaged `dt apply` does not invent a Copier base.

| Input | Supported migration contract |
| --- | --- |
| `CLAUDE.md` | Preserve useful neutral project rules in `AGENTS.md`; verified template plumbing uses the known-base merge, not blind text replacement. |
| `.claude/team-roles.md` | Verified-base template merge preserves useful project additions. Unknown custom semantics block. |
| `.claude/agents/*.md`, `.claude/commands/*.md`, `.claude/skills/<name>/SKILL.md` | Neutral Markdown moves to the corresponding `.opencode` path. Custom frontmatter may contain string `name` and `description` only, with a matching artifact name; active legacy CLI semantics are not supported merely because metadata is neutral. |
| Verified 1.7.0 architect baseline | The exact historical name/tools/model shape maps to the rendered read-only OpenCode architect. User description/body edits are preserved by three-way merge; unknown control-field edits block. |
| Legacy JSON settings, including `settings.local` | Only an empty JSON object is supported. Nonempty keys, malformed config, custom tools/model/permissions, hooks and unknown transformations block; they are not copied, dropped or silently disabled. |
| Both legacy and destination present (BOTH) | Equal results deduplicate; non-overlapping additions from both sides survive; ambiguous or overlapping edits conflict. Destination does not automatically win. |

The verified 1.7.0 recipe does not imply universal support for all historic
versions. Historical snapshots remain available; unrecognized shapes block.
Custom control fields are not treated as safe merely because an unmodified
bundled template once used a field with the same name. Inspect the safe path/
category report and resolve the unsupported configuration explicitly; do not
delete settings or disable hooks just to make a command report success.

Conflicting legacy/destination content returns `2` without project mutation or
answer advancement. Unsupported configuration, prerequisite, unsafe paths and
I/O errors return `1`. A verified completed migration returns `0`. These
migration conflict rules do not redesign ordinary native OpenCode update:
native three-way conflicts may still write conflict markers as documented in
the README. Apply conflict options and update `--force` do not bypass the
migration rules.

`.git`, `.claude/worktrees` and external symlinks are protected exclusions, not
migration inputs or cleanup targets. Required source/destination paths crossing
a symlink block. Do not recursively remove `.claude`: it may still contain
excluded worktrees or other untransferred data. OpenCode also discovers legacy
skills, so `.claude/skills` is not a safe archive location for unsupported skills.

## Completion, interruptions and protected recovery

Before project mutation, migration must stage only the affected originals and
a durable journal in a private location **outside the project Git tree and
outside active legacy configuration** (directories `0700`, files `0600`). It
does not copy the whole project. An unavailable or insecure recovery location
blocks before project writes. Never paste snapshot contents, secrets or raw
settings into logs, issues or Git. Private legacy settings remain git-ignored
while migration is incomplete or blocked; that guard is not a CLI dependency.

The executor revalidates inputs, applies and verifies target content, and only
then deletes the specific verified legacy sources. A backup alone is not proof
of transfer. Answers/base metadata and completion are finalized last. Partial
results and conflicts are not success; a completed migration repeats without
duplicate rules, roles or recovery churn.

After an error or interruption:

1. Preserve the project and the reported private recovery snapshot/journal.
   Do not clean either directory or use `--force` to bypass the state.
2. Inspect actual affected files and the reported state before retrying. A
   process/HTTP timeout does not prove an operation failed to execute; the
   journal may lag a write. Reconcile fingerprints rather than trusting the
   last printed message.
3. Recovery may restore original files only when doing so cannot overwrite
   later user edits. If files changed after interruption, stop and preserve all
   versions; resolve the difference explicitly instead of blindly copying a
   snapshot over the current tree.
4. Follow the executor's reported recovery path. If the error lacks an
   actionable recovery location/procedure, treat migration as incomplete,
   retain artifacts and report that gap rather than declaring success.
5. Re-run only after state is understood; verify target rules/roles/custom
   additions, both original sides, protected exclusions and answers. Directory-
   wide atomicity and exactly-once execution are not promised. Process-crash
   reconciliation is not a guarantee of recovery after power loss or storage
   failure; filesystem directory updates are not transactionally committed
   together with the journal.

### Recover an interrupted migration

Use the public recovery commands for the explicitly selected project:

```bash
dt migration-recover /path/to/project              # reconcile and resume
dt migration-recover /path/to/project --rollback   # restore known originals
```

These commands require the same working OpenCode version prerequisite. Normal
retry of the original update/apply command also reconciles an unfinished
operation, even if legacy sources were already removed before interruption.
Rollback is scoped to affected paths; it proceeds only when each current file
matches a recorded before/after state. Drift blocks without overwriting user
edits. Do not edit the private journal by hand or regard a completed rollback
as a completed migration.

The private store is
`${XDG_STATE_HOME:-~/.local/state}/dreamteam/migrations/<sha256-absolute-root>/operation.json`.
Use the location reported by the executor rather than calculating or guessing
the directory. That store must remain outside the selected project. Original
bytes belong only in protected recovery data, never in normal reports or Git.
Recovery retains sensitive material: keep owner-only permissions, do not upload
it as an attachment, and do not remove it while an operation is unresolved.
`dt recover` below serves a different purpose.

## Native interactive questions

The repository and generated `tech-lead` agent explicitly set
`permission.question: allow` in their YAML frontmatter. Custom agents in
OpenCode 1.19.0 otherwise inherit a deny rule, even with `mode: primary`.
Only this native tool permission is added; specialist permissions and personal
provider/model configuration are unchanged. No question MCP or plugin is needed.

Running sessions retain their loaded configuration. Apply agent changes only
with a safe, coordinated restart of the existing team server, then reattach
clients; do not start a second server. Static/render checks and CLI debug tool
availability do not prove that an interactive UI question has been accepted.

## Team sessions are a separate recovery layer

After migration, run one persistent server with `dt serve <project>` and attach
clients with `dt run <project>`. Do not start independent team servers for IDE
and terminal clients. After a server interruption, inspect `dt recover <project>`
on the server host and resume only the exact preserved `--member`,
`--lead-session` and `--task`. This recovers Ensemble coordination; it is **not**
a project migration snapshot restore command. See the README worker-recovery
section and [provider configuration](opencode-providers.md).
