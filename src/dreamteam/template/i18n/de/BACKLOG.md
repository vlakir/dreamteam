---
translated_from: i18n/ru/BACKLOG.md
source_hash: 2e77b47e3292371b7529bc9a2d494a48383d41053bf845384b2b16bb6f81e065
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Backlog

Parking für Ideen, Seitenfunde und „müsste man noch reparieren".

**Regel:** wenn OpenCode oder der Entwickler während der Arbeit an
der aktuellen Aufgabe etwas Außenstehendes bemerken — geht es
hierher, nicht in den aktuellen Commit. Das ist der Schutz vor
scope creep.

Das ist **kein formaler Task-Tracker** mit Deadlines und Metriken
— es ist ein Ideen-Parking. Aber **die Reihenfolge zählt**: oben —
was als Nächstes geplant ist, unten — weniger dringend (FIFO als
Default, Prioritäres kann nach oben gezogen werden). Wenn aus dem
Backlog etwas in Arbeit geht — wird daraus eine Aufgabe oder eine
Spec (`specs/T<NNN>-…`) und wird von hier entfernt.

## Format

`- **T<NNN>** — [<Funddatum>] <Kurzbeschreibung> — <optional: Kontext / wo es aufgetaucht ist>`

Die ID wird bei der Erstellung vergeben; die neue =
`max(bestehende T-IDs in BACKLOG.md, BOARD.md und CHANGELOG.md) + 1`.
Die ID wird nicht wiederverwendet und bleibt beim Übergang
zwischen BACKLOG und BOARD erhalten; nach einem Release wandert
die Aufgabe in `CHANGELOG.md` (mit derselben T-ID), was die
Eindeutigkeit zwischen Releases garantiert.

## Items

<!-- Beispiel (beim Ausfüllen der Vorlage löschen):

- **T<NNN>** — [<Datum>] Logs sind in stdout und Datei dupliziert — Logging-Config prüfen.
- **T<NNN+1>** — [<Datum>] Funktion `parse_post` ist auf 80 Zeilen angewachsen, bittet um Aufteilung.
- **T<NNN+2>** — [<Datum>] Rate Limiting auf /publish nachdenken (kam beim Clarify des Telegram-Publishing-Features auf).

-->
