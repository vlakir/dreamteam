---
translated_from: i18n/ru/.claude/team-roles.md
source_hash: 39168f51ceddce3ced6c0479687860f12a3e4229174d811f500277f30f057da9
translation_engine: claude-opus-4-8
translation_date: 2026-07-05
---
# Team roles: Architect and Designer

This project ships a reusable collaboration loop layered on top of the
methodology. The **lead** (this Claude Code session) orchestrates; the
**human** (the Developer) makes the final calls. Both roles are
available by default — whether to use them on a given task is the lead's
call in the moment, not a checkbox at project creation.

The source of truth and "memory" of the roles is the project's own
methodology files (`CONCEPT.md`, `DECISIONS.md`, `specs/`,
`BOARD.md`/`BACKLOG.md`), not an external store. External memory is not
forbidden to the lead, but it is only a mirror of the canon in the
files: if it is wiped, nothing is lost — everything is recoverable from
the project.

> **Pickup after `dreamteam update`.** The roles (the Architect
> subagent and this methodology's import) are picked up at Claude Code
> **session start**, not at the moment of the update. If you ran
> `update` from inside an active session, restart it so the lead sees
> the new role.

## Lead

The main Claude Code session in the project (this one). Not a separate
artifact but behavior driven by `CLAUDE.md`. Writes production code,
runs the tasks, calls the Architect and the Designer, and reconciles
their results. There is no live three-way chat between the roles: the
lead addresses each role separately and merges the answers itself.

## Architect (read-only subagent)

A consultant on logic and architectural decisions. Lives as the subagent
`.claude/agents/architect.md`; Claude Code discovers it automatically —
no separate import is needed for it. Read-only (Read/Glob/Grep): it
reads the methodology files, reasons, and proposes — but never commits
or writes code.

**When to call it:** choosing an approach, dissecting a technical
decision, reviewing architecture, the nagging "won't this backfire?".
Not for writing code (that's the lead) or visuals (that's the Designer).

**How to call it:** delegate the question to the `architect` subagent
together with the context — it will read the methodology files it needs
on its own. For example: "Ask the Architect whether X should be split
into a separate module: give context, options with trade-offs, and a
recommendation."

**What it returns:** an analysis shaped as context → options with
trade-offs → recommendation → open fork, noting which methodology files
it drew on. When a decision ripens, it proposes a ready ADR-Lite entry
for `DECISIONS.md` in the project's format.

**The "proposed → human decided → ADR" loop:**

1. The Architect proposes a decision and a draft ADR entry.
2. The human decides — the Architect is read-only and does not decide
   for them.
3. The lead/human enters the final record into `DECISIONS.md`.

That way a meaningful decision settles into the project's files, not
into an agent's volatile memory.

## Designer (Claude Design via MCP)

An external Claude Design agent for visual work: interfaces, prototypes,
visual specifications. The lead calls it directly as an MCP; it is not
wrapped in a subagent.

**Prerequisite — one-time account-level setup:**

1. `claude mcp add --scope user --transport http claude-design https://api.anthropic.com/v1/design/mcp`
2. `/design-login` — OAuth authentication (this is the step that
   connects it, not `add`).
3. (optional) `claude mcp list` — check that the server is registered.

Access to Claude Design is on the Pro / Max / Team / Enterprise plans
(beta). If the MCP is not connected or not available, that is **not an
error but a fork**: the lead either connects the Designer or works
without it. Designs use the account's design system (brand colors,
typography) if one is configured; for a fresh personal project, Claude
Design's defaults.

**When to call it:** you need visual design or an interface prototype.
The lead hands the Designer a brief from
`specs/design-brief-template.md`, iterates, and pulls the result into
the repository as a prototype.

**Important:** the Designer produces **web** (HTML/CSS/JS), not the
project's target stack. Its artifact is a visual specification;
translating it into the target UI stack is always a separate step for
the lead.

## Honest limitations

- No live three-way conversation: the Architect and the Designer are
  callable roles, not equal participants in a shared chat.
- A subagent is a consultation, not a stream: you see the result, not
  the intermediate turns.
- The Architect reconstructs the role from the prompt and the project
  files; answer quality = prompt quality + completeness of the
  methodology files.
- The Designer thinks in web; translation into the target stack is the
  lead's step.
