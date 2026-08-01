#!/bin/sh
# Claude Code statusLine reader for dreamteam's operational state layer.
#
# Prints "<workdir> · <task status line>" for the task bound to the current
# git worktree, read verbatim from
#   $DT_HOME/store/by-worktree/<slug>/context.line
# The line is written elsewhere (SessionStart hook, `dt task start`,
# `dt context`, `dt task move`); this script only *reads* it.
#
# Contract & guarantees:
#   * No Python interpreter is launched (statusLine runs on every message
#     update — a Python start-up would blow the budget). Only git + a sha1
#     utility are used; the whole pass stays well under 50 ms.
#   * The script never fails the status line: any glitch (not a git repo, no
#     store, no binding, empty file, no sha1 tool) yields *empty stdout* and
#     *exit 0*. A non-zero exit or empty output blanks the status line, which
#     is exactly the desired "no bound task → nothing shown" behaviour.
#   * stdin (the statusLine JSON payload) is ignored: Claude Code runs the
#     command with the working directory set to the session cwd, so the
#     worktree is found with `git rev-parse` from ".".
#
# `<slug>` and `$DT_HOME` are computed bit-for-bit like
# dreamteam.dt.paths.worktree_slug / dt_home — otherwise the wrong file (or no
# file) is read. See specs/T054-statusline/spec.md.

# The main worktree top-level. Passed as $1 by the settings.json bootstrap
# (which already ran `git rev-parse` to locate this script); falls back to a
# lookup so the script also works when run directly.
top=${1:-$(git rev-parse --show-toplevel 2>/dev/null)}
[ -n "$top" ] || exit 0

# The shared common dir keys $DT_HOME (same root from every linked worktree).
common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0

# Resolve $DT_HOME: an explicit override wins; otherwise the sibling
# "<main-worktree>.dt". A common dir named ".git" means its parent is the main
# worktree; anything else is a bare repo taken as the root directly.
if [ -n "${DT_HOME:-}" ]; then
    home=$DT_HOME
else
    case $common in
        */.git) main=${common%/.git} ;;
        *) main=$common ;;
    esac
    home="${main}.dt"
fi

# Resolve symlinks so the hashed path matches Python's Path(...).resolve().
resolved=$(cd "$top" 2>/dev/null && pwd -P) || exit 0

# sha1 over the path *bytes* (no trailing newline, mirroring str.encode()),
# first eight hex chars. Prefer coreutils sha1sum; fall back to shasum (macOS).
if command -v sha1sum >/dev/null 2>&1; then
    slug=$(printf '%s' "$resolved" | sha1sum | cut -c1-8)
elif command -v shasum >/dev/null 2>&1; then
    slug=$(printf '%s' "$resolved" | shasum | cut -c1-8)
else
    exit 0
fi
[ -n "$slug" ] || exit 0

line_file="${home}/store/by-worktree/${slug}/context.line"
[ -r "$line_file" ] || exit 0
# Read only the FIRST line: the status line must be a single row, but the file
# is derived from an unsanitised task title that could carry an embedded
# newline. This also drops a `cat` subprocess. `read` returns non-zero on a
# final line without a trailing newline, yet still fills $line — so gate on the
# content, not on read's exit status.
IFS= read -r line <"$line_file"
[ -n "$line" ] || exit 0

printf '%s · %s\n' "$(basename "$resolved")" "$line"
