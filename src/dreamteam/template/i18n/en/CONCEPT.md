---
translated_from: i18n/ru/CONCEPT.md
source_hash: eca6f2951dddf2c7658035c0812d8ce15bed724414f720f5e3b5cf66bb378603
translation_engine: claude-opus-4-8
translation_date: 2026-07-30
---
# Concept: {{ project_name }}

> **This is an immutable document** — it captures the initial vision
> of the project at the moment of its creation. Once filled, **it is
> not edited**. Current state of the project lives in `README.md`;
> if the concept changes drastically (rare case, pivot) — a new
> version is created in `concepts/v1-...md`, `concepts/v2-...md`
> (ADR-pattern, but for concepts).
>
> **Creation date:** `<YYYY-MM-DD>`
>
> When the project is created via `dreamteam init` this file is
> already in place; go through the counter-question ritual with
> Claude (see below), fill in the sections and lock them as
> immutable.

<!-- The structure below is a QUESTIONNAIRE (leading questions) for an
     empty concept, not a mandatory form. If you already have a
     substantive concept / spec / vision — replace this file's content
     wholesale with your own, without recasting anything into these
     headings. What matters is that an "Out of scope" section is
     present in some form (protection against scope creep) and that the
     document stays immutable once locked. The clarify ritual (Claude's
     counter-questions about blind spots) runs against the actual
     content. -->

## Goal

<!-- 1-2 sentences. What the project does and why it is needed. No
     technical details and no implementation promises — only the
     meaning. -->

## User

<!-- For whom. The use case in one or two phrases. If the user is
     the Developer themselves, write so; if it is a future "third
     party", briefly describe their context. -->

## Key functionality

<!-- 3-7 bullets at the "capability" level, not implementation. Each
     bullet answers "what must the system be able to do?", not
     "how". -->

- ...

## Out of scope

<!-- What this project deliberately does NOT do. This section is the
     main defence against scope creep from day one. Write plainly:
     "X — we do not do" / "Y — we leave to people / external systems". -->

- ...

## Constraints and assumptions

<!-- Platform, stack (if already known), non-functional requirements
     (performance, reliability, security), assumptions about the
     environment / users / load. Assumptions go here too — they may
     later turn out to be wrong, and it is important to record what
     exactly we assumed at the moment of starting. -->

- ...

---

## Filling-in ritual (helper text, delete after filling in)

At the start of a new project `CONCEPT.md` is filled in through a
**counter-question ritual**, analogous to `clarify` for a big-feature
spec:

1. The Developer writes a first draft of the sections (or simply
   states the idea).
2. Claude asks counter-questions about blind spots:
   - **Goal:** what pain / task does the project solve?
   - **User:** who exactly is the user, in what context?
   - **Key functionality:** what is the minimum set for MVP? What
     is potentially-useful but not now?
   - **Out of scope:** what we definitely do NOT do? (Special focus
     — this is the most valuable section for defence against scope
     creep.)
   - **Constraints:** platform, stack, target load, assumptions?
3. The Developer's answers are sewn into the corresponding sections.
4. Once filled, this helper section ("Filling-in ritual") is
   removed. `CONCEPT.md` is stamped with a date and considered
   immutable.
