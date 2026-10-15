---
translated_from: i18n/ru/.opencode/team-roles.md
source_hash: 313acfd4f704304f9d838f7cd2ca1b2a82eb9e6e0c8f1fef11aab5702f103e54
translation_engine: agent-assisted-migration
translation_date: 2026-10-15
---
# Rôles de l’équipe dans OpenCode

Le responsable coordonne développement, architecture, design et revue. Les
connaissances durables restent dans AGENTS.md, CONCEPT.md, DECISIONS.md, specs,
BOARD.md et BACKLOG.md. La mémoire externe est facultative.

Avec Ensemble, créer une équipe, répartir les tâches et leurs dépendances avec
les identifiants retournés. Chaque développeur dispose de son worktree et de
critères de validation précis. Commencer avec deux ou trois agents. Utiliser
team_message entre collègues et team_broadcast pour les informations communes.
Vérifier les tests et la revue avant intégration. Le statut done ne permet pas
la fusion dans main. mergeOnCleanup est désactivé : intégrer explicitement les
branches. BOARD.md et BACKLOG.md restent le registre du projet ; Ensemble suit
l’exécution. Des worktrees distincts ne suppriment pas les conflits de fusion.

@architect est un sous-agent en lecture seule. Son modèle est hérité, sauf
configuration provider/model-id. Le designer est facultatif : modèle avec vision
ou service MCP configuré séparément, sans abonnement obligatoire. Redémarrer
OpenCode après une mise à jour des agents. Configurer modèles et fournisseurs
au niveau utilisateur, sans publier de secrets. Le tableau de bord expose les
tâches et messages ; la communication entre équipes indépendantes n’est pas acquise.

L’équipe standard comprend neuf rôles : tech-lead, architect (analyse des besoins et architecture), designer (UX/UI), frontend, mobile, backend, tester, reviewer et devops. Tous sont disponibles dans .opencode/agents ; le responsable choisit les spécialistes selon la tâche.
