---
translated_from: i18n/ru/.claude/team-roles.md
source_hash: 39168f51ceddce3ced6c0479687860f12a3e4229174d811f500277f30f057da9
translation_engine: claude-opus-4-8
translation_date: 2026-07-05
---
# Team-Rollen: Architekt und Designer

Dieses Projekt bringt einen wiederverwendbaren Kollaborationskreis auf
der Methodik mit. Der **Lead** (diese Claude-Code-Session) orchestriert;
der **Mensch** (der Entwickler) trifft die finalen Entscheidungen. Beide
Rollen sind standardmäßig verfügbar — ob man sie in einer konkreten
Aufgabe nutzt, entscheidet der Lead situativ, nicht ein Häkchen bei der
Projekterstellung.

Quelle der Wahrheit und „Gedächtnis" der Rollen sind die eigenen
Methodik-Dateien des Projekts (`CONCEPT.md`, `DECISIONS.md`, `specs/`,
`BOARD.md`/`BACKLOG.md`), kein externer Speicher. Externer Speicher ist
dem Lead nicht verboten, aber er ist nur ein Spiegel des Kanons in den
Dateien: wird er gelöscht, geht nichts verloren — alles ist aus dem
Projekt wiederherstellbar.

> **Übernahme nach `dreamteam update`.** Die Rollen (der
> Architekt-Subagent und der Import dieser Methodik) werden beim
> **Sessionstart** von Claude Code übernommen, nicht im Moment des
> Updates. Hast du `update` aus einer aktiven Session gestartet, starte
> sie neu, damit der Lead die neue Rolle sieht.

## Lead

Die Haupt-Claude-Code-Session im Projekt (diese). Kein eigenes Artefakt,
sondern Verhalten gemäß `CLAUDE.md`. Schreibt Produktionscode, führt die
Aufgaben, ruft Architekt und Designer und führt ihre Ergebnisse zusammen.
Ein Live-Dreiergespräch zwischen den Rollen gibt es nicht: der Lead
wendet sich an jede Rolle einzeln und fügt die Antworten selbst zusammen.

## Architekt (schreibgeschützter Subagent)

Ein Berater für Logik und Architekturentscheidungen. Existiert als
Subagent `.claude/agents/architect.md`; Claude Code entdeckt ihn
automatisch — ein separater Import ist für ihn nicht nötig.
Schreibgeschützt (Read/Glob/Grep): er liest die Methodik-Dateien,
überlegt und schlägt vor — committet aber nie und schreibt keinen Code.

**Wann rufen:** eine Herangehensweise wählen, eine technische
Entscheidung sezieren, Architektur reviewen, der Zweifel „geht das nicht
nach hinten los?". Nicht zum Schreiben von Code (das ist der Lead) oder
für Visuelles (das ist der Designer).

**Wie rufen:** delegiere die Frage an den Subagenten `architect`
zusammen mit dem Kontext — er liest die nötigen Methodik-Dateien selbst
nach. Zum Beispiel: „Frag den Architekten, ob X in ein eigenes Modul
ausgelagert werden sollte: gib Kontext, Optionen mit Kompromissen und
eine Empfehlung."

**Was er zurückgibt:** eine Analyse in der Form Kontext → Optionen mit
Kompromissen → Empfehlung → offene Weggabelung, mit dem Hinweis, welche
Methodik-Dateien einflossen. Wenn eine Entscheidung reif ist, schlägt er
einen fertigen ADR-Lite-Eintrag für `DECISIONS.md` im Format des
Projekts vor.

**Die Schleife „vorgeschlagen → Mensch entschied → ADR":**

1. Der Architekt schlägt eine Entscheidung und einen ADR-Entwurf vor.
2. Der Mensch entscheidet — der Architekt ist schreibgeschützt und
   entscheidet nicht an seiner Stelle.
3. Der Lead/Mensch trägt den finalen Eintrag in `DECISIONS.md` ein.

So setzt sich eine bedeutsame Entscheidung in den Projektdateien ab und
nicht im flüchtigen Gedächtnis eines Agenten.

## Designer (Claude Design über MCP)

Ein externer Claude-Design-Agent für visuelle Arbeit: Oberflächen,
Prototypen, visuelle Spezifikationen. Der Lead ruft ihn direkt als MCP;
er wird nicht in einen Subagenten verpackt.

**Voraussetzung — einmalige Einrichtung auf Kontoebene:**

1. `claude mcp add --scope user --transport http claude-design https://api.anthropic.com/v1/design/mcp`
2. `/design-login` — OAuth-Authentifizierung (dieser Schritt verbindet,
   nicht `add`).
3. (opt.) `claude mcp list` — prüfen, dass der Server registriert ist.

Der Zugang zu Claude Design besteht auf den Plänen Pro / Max / Team /
Enterprise (beta). Ist der MCP nicht verbunden oder nicht verfügbar, ist
das **kein Fehler, sondern eine Weggabelung**: der Lead verbindet
entweder den Designer oder arbeitet ohne ihn. Designs nutzen das
Design-System des Kontos (Markenfarben, Typografie), falls eines
konfiguriert ist; für ein frisches persönliches Projekt die
Standardwerte von Claude Design.

**Wann rufen:** du brauchst visuelles Design oder einen
Oberflächen-Prototyp. Der Lead übergibt dem Designer ein Briefing aus
`specs/design-brief-template.md`, iteriert und zieht das Ergebnis als
Prototyp ins Repository.

**Wichtig:** der Designer produziert **Web** (HTML/CSS/JS), nicht den
Zielstack des Projekts. Sein Artefakt ist eine visuelle Spezifikation;
die Übersetzung in den Ziel-UI-Stack ist immer ein eigener Schritt des
Leads.

## Ehrliche Grenzen

- Kein Live-Dreiergespräch: Architekt und Designer sind aufrufbare
  Rollen, keine gleichberechtigten Gesprächspartner in einem
  gemeinsamen Chat.
- Ein Subagent ist eine Beratung, kein Stream: man sieht das Ergebnis,
  nicht die Zwischenschritte.
- Der Architekt rekonstruiert die Rolle aus dem Prompt und den
  Projektdateien; Antwortqualität = Prompt-Qualität + Vollständigkeit
  der Methodik-Dateien.
- Der Designer denkt in Web; die Übersetzung in den Zielstack ist der
  Schritt des Leads.
