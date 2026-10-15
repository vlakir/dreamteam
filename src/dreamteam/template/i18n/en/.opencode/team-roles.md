---
translated_from: i18n/ru/.opencode/team-roles.md
source_hash: 313acfd4f704304f9d838f7cd2ca1b2a82eb9e6e0c8f1fef11aab5702f103e54
translation_engine: agent-assisted-migration
translation_date: 2026-10-15
---
# Team roles in OpenCode

The lead coordinates implementation, architecture, design, and review. Durable
knowledge lives in CONCEPT.md, DECISIONS.md, specs, BOARD.md and BACKLOG.md.
Read these and AGENTS.md before working; external memory is optional.

Use Ensemble for parallel independent work: create a team, add tasks with real
returned dependency IDs, and give each builder an isolated worktree. Assign
explicit file ownership and acceptance criteria. Start with two or three workers.
Use team_message for direct peer coordination and team_broadcast for shared facts.
Review results and run the project's gates before integrating. A completed task
is not permission to merge into main. mergeOnCleanup is disabled: integrate
branches deliberately and preserve unmerged work. Avoid duplicate task boards;
BOARD.md and BACKLOG.md remain the project record, Ensemble tracks execution.

The architect at .opencode/agents/architect.md is read-only. Invoke @architect
for alternatives, tradeoffs, reviews and proposed ADRs. Its model inherits the
caller unless configured with provider/model-id. A designer is optional: use a
vision-capable model or a separately configured MCP service. No subscription,
provider or external design service is required by the methodology.

Restart OpenCode after updating agent files. Configure providers and models in
user settings; never commit credentials. Check the Ensemble dashboard for live
messages and tasks. Peer messaging operates inside a team; independent-team
messaging is not assumed. Worktree isolation does not eliminate merge conflicts.

The standard team contains nine roles: tech-lead, architect (requirements analysis and architecture), designer (UX/UI), frontend, mobile, backend, tester, reviewer, and devops. All ship in .opencode/agents; the lead activates the specialists needed for each task.
