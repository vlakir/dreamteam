---
translated_from: i18n/ru/DECISIONS.md
source_hash: ecf297efe8b7b96e7620a8533b03d12e0c7764ae4384d909ee35bd39c56d160c
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Architekturentscheidungen

ADR-Lite: ein kompaktes Logbuch von Architekturentscheidungen mit
Begründungen. Ziel — in einem halben Jahr die Frage „warum haben
wir es damals so gemacht?" beantworten zu können, ohne den Kontext
aus Commits rekonstruieren zu müssen.

## Format

Jede Entscheidung — ein kurzer Block:

- **Datum** — wann getroffen.
- **Entscheidung** — was beschlossen wurde (1 Zeile).
- **Kontext** — welche Aufgabe / Einschränkung führte dazu.
- **Alternativen** — was wurde erwogen und warum verworfen.
- **Konsequenzen** — was es uns jetzt bringt und was es uns
  nimmt.

Entscheidungen werden nach der Fixierung nicht mehr bearbeitet.
Wird eine Entscheidung revidiert — ein neuer Block mit Verweis
auf den alten wird hinzugefügt, der alte wird als „Ersetzt durch
die Entscheidung vom <Datum>" markiert.

---

## Beispiel (beim Ausfüllen der Vorlage löschen)

### 2026-05-13 — SQLite statt PostgreSQL für MVP

- **Kontext:** Projekt für einen einzigen Nutzer, < 10 MB Daten,
  schneller Start ohne separaten Service erforderlich.
- **Alternativen:**
  - PostgreSQL — verworfen, kein Grund einen separaten Prozess
    für einen einzigen Nutzer laufen zu lassen; eine Migration
    kann man immer noch machen.
  - JSON-Datei — verworfen, wir verlieren Transaktionalität und
    Indizes.
- **Konsequenzen:** Deploy = eine Binary, Backup = Kopie der
  Datei. Bei Wachstum > 100 MB oder Auftauchen von konkurrierendem
  Zugriff — überdenken.

---

## Projektentscheidungen

<!-- Tatsächliche Entscheidungen kommen hierhin, neue oben. -->

