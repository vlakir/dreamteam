---
translated_from: i18n/ru/CONCEPT.md
source_hash: eca6f2951dddf2c7658035c0812d8ce15bed724414f720f5e3b5cf66bb378603
translation_engine: claude-opus-4-8
translation_date: 2026-07-30
---
# Konzept: {{ project_name }}

> **Dies ist ein unveränderliches Dokument** — es hält die
> ursprüngliche Vision des Projekts zum Zeitpunkt seiner Erstellung
> fest. Nach dem Ausfüllen **wird es nicht mehr bearbeitet**. Der
> aktuelle Projektstand wird in `README.md` geführt; ändert sich
> das Konzept grundlegend (seltener Fall, Pivot) — wird eine neue
> Version in `concepts/v1-...md`, `concepts/v2-...md` angelegt
> (ADR-Pattern, aber für Konzepte).
>
> **Erstellungsdatum:** `<YYYY-MM-DD>`
>
> Bei der Projekterstellung über `dreamteam init` liegt diese
> Datei bereits vor; durchlaufe das Ritual der Gegenfragen mit
> Claude (siehe unten), fülle die Abschnitte und friere sie als
> unveränderlich ein.

<!-- Die Struktur unten ist ein FRAGEBOGEN (leading questions) für ein
     leeres Konzept, keine Pflichtform. Wenn du bereits ein
     inhaltliches Konzept / Lastenheft / eine Vision hast — ersetze den
     Inhalt dieser Datei vollständig durch deinen eigenen, ohne etwas
     in diese Überschriften umzugießen. Wichtig ist nur, dass ein
     Abschnitt „Out of scope" in irgendeiner Form vorhanden ist (Schutz
     vor scope creep) und dass das Dokument nach dem Festschreiben
     unveränderlich bleibt. Das clarify-Ritual (Claudes Gegenfragen zu
     blinden Flecken) läuft über den tatsächlichen Inhalt. -->

## Ziel

<!-- 1-2 Sätze. Was das Projekt tut und wozu es da ist. Ohne
     technische Details und ohne Implementierungsversprechen —
     nur der Sinn. -->

## Nutzer

<!-- Für wen. Use Case in einem oder zwei Sätzen. Ist der Nutzer
     der Entwickler selbst, so schreiben wir das; ist es eine
     zukünftige „dritte Partei" — kurz ihren Kontext beschreiben. -->

## Kernfunktionalität

<!-- 3-7 Punkte auf der Ebene „Fähigkeiten", nicht Implementierung.
     Jeder Punkt antwortet auf die Frage „was muss das System
     können?", nicht „wie". -->

- ...

## Out of scope

<!-- Was dieses Projekt BEWUSST NICHT tut. Dieser Abschnitt ist
     der Hauptschutz gegen scope creep vom ersten Tag an. Schreibe
     direkt: „X — machen wir nicht" / „Y — überlassen wir Menschen
     / externen Systemen". -->

- ...

## Einschränkungen und Annahmen

<!-- Plattform, Stack (falls schon bekannt), nicht-funktionale
     Anforderungen (Performance, Zuverlässigkeit, Sicherheit),
     Annahmen über Umgebung / Nutzer / Last. Annahmen kommen auch
     hier hin — sie können sich später als falsch erweisen, und
     es ist wichtig festzuhalten, was wir genau zum Startzeitpunkt
     angenommen haben. -->

- ...

---

## Ritual zum Ausfüllen (Hilfstext, nach dem Ausfüllen entfernen)

Zu Beginn eines neuen Projekts wird `CONCEPT.md` über das **Ritual
der Gegenfragen** ausgefüllt, analog zu `clarify` für die Spec
eines großen Features:

1. Der Entwickler schreibt einen ersten Entwurf der Abschnitte
   (oder formuliert einfach die Idee).
2. Claude stellt Gegenfragen zu blinden Flecken:
   - **Ziel:** welchen Schmerz / welche Aufgabe löst das Projekt?
   - **Nutzer:** wer ist der Nutzer genau, in welchem Kontext?
   - **Kernfunktionalität:** was ist das Minimum für MVP? Was
     wäre potenziell nützlich, aber nicht jetzt?
   - **Out of scope:** was machen wir definitiv NICHT? (Besondere
     Aufmerksamkeit — das ist der wertvollste Abschnitt für den
     Schutz vor scope creep.)
   - **Einschränkungen:** Plattform, Stack, Ziel-Last, Annahmen?
3. Die Antworten des Entwicklers werden in die entsprechenden
   Abschnitte eingenäht.
4. Nach dem Ausfüllen wird dieser Hilfsabschnitt („Ritual zum
   Ausfüllen") entfernt. `CONCEPT.md` wird mit einem Datum
   versehen und als unveränderlich angesehen.
