---
translated_from: i18n/ru/BOARD.md
source_hash: a34bdadb4bacaae4c37715eff6d323c0c0552189b61a1c1d266c8c75927febb0
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Board

Eine leichtgewichtige Kanban-Alternative in einer einzigen
Markdown-Datei: drei Spalten (To Do / Doing / Done) unter git,
ohne externe Services und Tools.

## Verhältnis zu anderen Dateien

- `BACKLOG.md` — lange Warteschlange von Ideen und Seitenfunden.
  Hierhin fällt „darüber denken wir später nach", „nicht jetzt".
  Scope-Parking.
- `BOARD.md` (diese Datei) — aktiver Arbeitsstrom. Aufgaben, die
  wir schon übernommen haben oder die wir demnächst übernehmen
  wollen.
- `specs/T<NNN>-*/spec.md` — wohin eine große Aufgabe vom BOARD
  hineinwächst, wenn sie sich als Feature >1 Tag Arbeit entpuppt.

Lebenszyklus einer Aufgabe: Idee in `BACKLOG.md` → gereift →
zieht in `To Do` hier um → wird in Arbeit genommen (`Doing`) →
abgeschlossen (`Done`) → nach einem Release wandert in
`CHANGELOG.md` (der Eintrag enthält zwingend die T-ID), von hier
entfernt. **`CHANGELOG.md` ist der einzige persistente Speicher
der T-IDs abgeschlossener Aufgaben**, ohne ihn bricht die Regel
„ID wird nicht wiederverwendet".

## Aufgabenformat

Jede Aufgabe — `- **T<NNN>** — <Kurzbeschreibung>`. Die ID wird
bei der Erstellung vergeben: die neue =
`max(bestehende T-IDs in BOARD.md, BACKLOG.md und CHANGELOG.md) + 1`.
Die ID wird nie wiederverwendet. Die ID ist zwischen `BOARD.md`
und `BACKLOG.md` geteilt — sie bleibt beim Übergang zwischen
ihnen erhalten; nach einem Release landet die Aufgabe in
`CHANGELOG.md` mit derselben T-ID, was die Eindeutigkeit der
Nummern zwischen Releases garantiert.

Branch-Name: `T<NNN>-<slug>` (kein Namespace wie `fixes/` /
`feature/` — die ID identifiziert schon). PR-Name: `T<NNN>:
<title>`. Spec eines großen Features:
`specs/T<NNN>-<slug>/spec.md`.

Nach Belieben kann ergänzt werden:

- Label mit dem Aufnahmedatum,
- Link zur Spec,
- Branch-Name.

Beispiel:

```
- **T<NNN>** — Vorschau von Posts in Telegram
  (`specs/T<NNN>-telegram-preview/`, Branch `T<NNN>-telegram-preview`).
```

---

## To Do

<!-- Bereit zur Aufnahme. FIFO-Queue als Default, Prioritäres kann
     nach oben gezogen werden. -->

<!-- Aufgaben im Format `- **T<NNN>** — Beschreibung`. Siehe
     Abschnitt „Aufgabenformat" oben. -->

## Doing

<!-- Jetzt in Arbeit. Kurz halten: maximal 1-2 Aufgaben pro
     Entwickler, sonst geht der Fokus verloren (die klassische
     WIP-Limit-Regel aus Kanban). -->

- ...

## Done

<!-- Abgeschlossene Aufgaben, die auf den Übergang in CHANGELOG.md
     beim nächsten Release oder bedeutsamen Punkt warten. Nach
     dem Übergang — leeren. -->

- ...
