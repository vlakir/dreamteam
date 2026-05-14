#!/usr/bin/env bash
#
# Sandbox helper for trying dreamteam-cli without polluting the dev repo.
#
# Sandbox root: /tmp/dreamteam-sandbox/  (ephemeral — wiped on reboot).
# Hardcoded — script refuses to write anywhere else.
#
# Usage:
#   scripts/sandbox.sh init [--local] [--name <name>]
#       Create a fresh sandbox project.
#         --local : install from latest dist/*.whl (builds if missing).
#                   Default: install from PyPI (dreamteam-cli).
#         --name  : project name. Default: test-<HHMMSS>.
#
#   scripts/sandbox.sh list
#       List existing sandbox projects.
#
#   scripts/sandbox.sh shell <name>
#       Open a sub-shell inside the given sandbox project (exit to leave).
#
#   scripts/sandbox.sh clean
#       Remove /tmp/dreamteam-sandbox/ entirely (asks for confirmation).

set -euo pipefail

readonly SANDBOX_ROOT="/tmp/dreamteam-sandbox"

# Safety: refuse to run from inside the sandbox itself (avoids surprises
# if user accidentally invoked the script after entering a sandbox shell).
case "$PWD" in
    "$SANDBOX_ROOT"|"$SANDBOX_ROOT"/*)
        echo "ERROR: refusing to run from inside $SANDBOX_ROOT" >&2
        echo "       cd back to the dreamteam repo and try again." >&2
        exit 1
        ;;
esac

cmd_init() {
    local use_local=false
    local name=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --local) use_local=true; shift ;;
            --name)
                if [[ -z "${2:-}" ]]; then
                    echo "ERROR: --name requires a value." >&2
                    exit 1
                fi
                name="$2"
                shift 2
                ;;
            *)
                echo "ERROR: unknown option: $1" >&2
                exit 1
                ;;
        esac
    done

    [[ -z "$name" ]] && name="test-$(date +%H%M%S)"

    # Disallow path-traversal in --name (we only ever write under SANDBOX_ROOT)
    if [[ "$name" == *"/"* || "$name" == "." || "$name" == ".." ]]; then
        echo "ERROR: --name must be a simple identifier (no slashes)." >&2
        exit 1
    fi

    local target="$SANDBOX_ROOT/$name"
    if [[ -e "$target" ]]; then
        echo "ERROR: $target already exists." >&2
        echo "       Pick another --name, or run 'sandbox.sh clean' first." >&2
        exit 1
    fi

    mkdir -p "$SANDBOX_ROOT"

    if "$use_local"; then
        # Locate latest local wheel; build if none.
        local wheel
        wheel=$(ls -t dist/dreamteam_cli-*.whl 2>/dev/null | head -1 || true)
        if [[ -z "$wheel" ]]; then
            echo "→ No local wheel in dist/. Running uv build..."
            uv build
            wheel=$(ls -t dist/dreamteam_cli-*.whl | head -1)
        fi
        echo "→ Source: local wheel ($wheel)"
        echo "→ Target: $target"
        uvx --from "$wheel" dreamteam init "$target" --defaults
    else
        echo "→ Source: PyPI (dreamteam-cli)"
        echo "→ Target: $target"
        uvx --from dreamteam-cli dreamteam init "$target" --defaults
    fi

    echo ""
    echo "✓ Sandbox project ready at $target"
    echo ""
    echo "Next steps:"
    echo "  scripts/sandbox.sh shell $name        # enter the sandbox shell"
    echo "  cd $target && uv sync && uv run pytest"
    echo "  scripts/sandbox.sh clean              # wipe all sandboxes"
}

cmd_list() {
    if [[ ! -d "$SANDBOX_ROOT" ]]; then
        echo "(no sandbox yet — root: $SANDBOX_ROOT)"
        return
    fi
    local found=false
    for entry in "$SANDBOX_ROOT"/*; do
        if [[ -d "$entry" ]]; then
            echo "$(basename "$entry")"
            found=true
        fi
    done
    "$found" || echo "(empty — root: $SANDBOX_ROOT)"
}

cmd_shell() {
    local name="${1:-}"
    if [[ -z "$name" ]]; then
        echo "ERROR: 'shell' requires a sandbox name." >&2
        echo "       Try: scripts/sandbox.sh list" >&2
        exit 1
    fi
    local target="$SANDBOX_ROOT/$name"
    if [[ ! -d "$target" ]]; then
        echo "ERROR: $target does not exist." >&2
        echo "       Run: scripts/sandbox.sh list" >&2
        exit 1
    fi
    echo "→ Entering $target (exit the shell to leave)"
    cd "$target" && exec "${SHELL:-/bin/bash}"
}

cmd_clean() {
    if [[ ! -d "$SANDBOX_ROOT" ]]; then
        echo "(nothing to clean — $SANDBOX_ROOT does not exist)"
        return
    fi
    echo "About to remove: $SANDBOX_ROOT"
    echo "Contents:"
    ls -la "$SANDBOX_ROOT" 2>/dev/null | sed 's/^/    /'
    echo ""
    read -rp "Proceed? [y/N] " confirm
    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        rm -rf "$SANDBOX_ROOT"
        echo "✓ Cleaned"
    else
        echo "Cancelled."
    fi
}

cmd_usage() {
    cat <<USAGE
Sandbox helper for trying dreamteam-cli without polluting the dev repo.

Sandbox root: $SANDBOX_ROOT (ephemeral — /tmp is wiped on reboot).

Usage:
  scripts/sandbox.sh init [--local] [--name <name>]
      Create a fresh sandbox project.
        --local : install from latest dist/*.whl (builds if missing).
                  Default: install from PyPI (dreamteam-cli).
        --name  : project name. Default: test-<HHMMSS>.

  scripts/sandbox.sh list
      List existing sandbox projects.

  scripts/sandbox.sh shell <name>
      Open a sub-shell inside the given sandbox project.

  scripts/sandbox.sh clean
      Remove $SANDBOX_ROOT entirely (asks for confirmation).
USAGE
}

case "${1:-}" in
    init)  shift; cmd_init "$@" ;;
    list)  cmd_list ;;
    shell) shift; cmd_shell "$@" ;;
    clean) cmd_clean ;;
    -h|--help) cmd_usage ;;
    "")    cmd_usage; exit 1 ;;
    *)     echo "ERROR: unknown command: $1" >&2; echo ""; cmd_usage; exit 1 ;;
esac
