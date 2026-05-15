---
translated_from: i18n/ru/specs/spec-template.md
source_hash: 0f45d2d1435c67a85ab50b0aa1d9f10e3c089615ee91c53712e6b80a55e4513c
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Spec: <Feature name>

**Status:** Draft | Clarified | Analyzed | In Progress | Done
**Creation date:** <YYYY-MM-DD>
**Related documents:** <links to DECISIONS, other specs, if any>

---

## 1. Overview

<!-- 2-4 sentences about the feature. What it is and why it is
     needed. No technical details — write as a product manager,
     not as an engineer. -->

## 2. User Stories

<!-- Scenarios in the format:
     "As a <role>, I want <action>, so that <goal>."

     For projects without explicit users (scripts, infrastructure,
     hardware) — replace with "Use cases" describing the situations
     in which the feature applies.
-->

- ...

## 3. Functional Requirements

<!-- What the system MUST be able to do. Use the wording
     "must / may / must not" — to keep it unambiguous. -->

- MUST: …
- MAY: …
- MUST NOT: …

## 4. Success Criteria

<!-- Measurable success conditions. Concrete numbers, timings,
     behaviour.
     Bad: "works fast".
     Good: "response < 200 ms on a typical request". -->

- ...

## 5. Key Entities

<!-- Entities and data the feature operates on. No DB schemas and
     no API — only conceptually: what kinds of objects, what their
     key fields are, how they relate.
-->

- ...

## 6. Assumptions & Constraints

<!-- What we take as given / what constrains the solution.
     Examples:
     - Target platform — Raspberry Pi Zero W (ARMv6).
     - The user is always one; no concurrent access.
     - The external API has a 60-requests-per-minute limit.
-->

- ...

## 7. Out of Scope

<!-- What is deliberately NOT included in this feature. Scope-creep
     guard. -->

- ...

---

## Clarify (filled in by Claude)

<!-- Claude re-reads the spec and asks counter-questions about
     blind spots. Categories: auth, validation, errors, edge cases,
     performance, security, integrations. The Developer's answers
     are sewn back into the corresponding sections above. -->

### Open questions

- ...

### Resolved (with answers)

- ...

---

## Analyze (filled in by Claude)

<!-- Claude reads the spec (and the plan, if any) and looks for
     contradictions, mismatches, omissions, technical impossibilities.

     A list of Issues with markers:
     - 🔴 Critical — fix before starting implementation.
     - 🟡 Warning — discuss, possibly fix.
     - 🟢 Note — for awareness.
-->

- ...
