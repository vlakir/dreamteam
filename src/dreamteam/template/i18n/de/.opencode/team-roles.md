---
translated_from: i18n/ru/.opencode/team-roles.md
source_hash: 313acfd4f704304f9d838f7cd2ca1b2a82eb9e6e0c8f1fef11aab5702f103e54
translation_engine: agent-assisted-migration
translation_date: 2026-10-15
---
# Teamrollen in OpenCode

Die Leitung koordiniert Implementierung, Architektur, Design und Review.
Dauerhaftes Wissen bleibt in AGENTS.md, CONCEPT.md, DECISIONS.md, specs,
BOARD.md und BACKLOG.md. Externer Speicher ist optional.

Mit Ensemble ein Team erstellen, Aufgaben und Abhängigkeiten mit den tatsächlich
zurückgegebenen IDs planen. Jeder Entwickler erhält einen eigenen Worktree,
Dateigrenzen und Abnahmekriterien. Mit zwei bis drei Beteiligten beginnen.
team_message dient direkten Nachrichten, team_broadcast gemeinsamen Informationen.
Vor Integration Tests und Review prüfen. done erlaubt keinen Merge nach main.
mergeOnCleanup ist deaktiviert: Zweige ausdrücklich integrieren. BOARD.md und
BACKLOG.md bleiben die Projektakte; Ensemble verfolgt die Ausführung.
Worktrees verhindern keine Merge-Konflikte.

@architect ist ein schreibgeschützter Unteragent. Ohne provider/model-id erbt er
das Modell des Aufrufers. Design ist optional über ein Bildmodell oder separat
konfiguriertes MCP möglich; kein bestimmter Anbieter und kein Abonnement ist nötig.
Nach Agentenupdates OpenCode neu starten. Anbieter und Modelle in den persönlichen
Einstellungen konfigurieren und keine Schlüssel einchecken. Das Dashboard zeigt
Aufgaben und Nachrichten. Kommunikation zwischen unabhängigen Teams wird nicht
vorausgesetzt.

Das Standardteam umfasst neun Rollen: tech-lead, architect (Anforderungsanalyse und Architektur), designer (UX/UI), frontend, mobile, backend, tester, reviewer und devops. Alle liegen unter .opencode/agents; die Leitung wählt je nach Aufgabe passende Fachrollen.
