---
translated_from: i18n/ru/DECISIONS.md
source_hash: ecf297efe8b7b96e7620a8533b03d12e0c7764ae4384d909ee35bd39c56d160c
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Architecture Decisions

ADR-Lite: a compact log of architectural decisions with rationale.
The point — in six months you can answer "why did we do it that way
back then?" without reconstructing context from commits.

## Format

Each decision — a short block:

- **Date** — when it was taken.
- **Decision** — what was decided (1 line).
- **Context** — what task / constraint led to it.
- **Alternatives** — what was considered and why it was rejected.
- **Consequences** — what it gives us now and what it costs us.

Decisions are not edited after fixation. If a decision is revisited
— a new block is added with a link to the old one, and the old one
is marked "Replaced by the decision of <date>".

---

## Example (delete when filling in the template)

### 2026-05-13 — SQLite instead of PostgreSQL for MVP

- **Context:** project for a single user, < 10 MB of data, fast
  startup required without a separate service.
- **Alternatives:**
  - PostgreSQL — rejected; no reason to keep a separate process for
    a single user; migration can be done later.
  - JSON file — rejected; loses transactionality and indexes.
- **Consequences:** deploy = one binary, backup = a copy of the
  file. When > 100 MB or concurrent access appears — revisit.

---

## Project decisions

<!-- Actual decisions are added here, newest at the top. -->

