---
translated_from: i18n/ru/.claude/team-roles.md
source_hash: 39168f51ceddce3ced6c0479687860f12a3e4229174d811f500277f30f057da9
translation_engine: claude-opus-4-8
translation_date: 2026-07-05
---
# Rôles de l'équipe : Architecte et Designer

Ce projet embarque un dispositif de collaboration réutilisable posé sur
la méthodologie. Le **lead** (cette session Claude Code) orchestre ;
l'**humain** (le Développeur) tranche. Les deux rôles sont disponibles
par défaut — les utiliser sur une tâche donnée relève du choix du lead
sur le moment, pas d'une case cochée à la création du projet.

La source de vérité et la « mémoire » des rôles, ce sont les propres
fichiers de méthodologie du projet (`CONCEPT.md`, `DECISIONS.md`,
`specs/`, `BOARD.md`/`BACKLOG.md`), pas un stockage externe. La mémoire
externe n'est pas interdite au lead, mais elle n'est qu'un miroir du
canon des fichiers : effacée, rien n'est perdu — tout est récupérable
depuis le projet.

> **Prise en compte après `dreamteam update`.** Les rôles (le sous-agent
> Architecte et l'import de cette méthodologie) sont pris en compte au
> **démarrage de la session** Claude Code, pas au moment de la mise à
> jour. Si tu as lancé `update` depuis une session active, redémarre-la
> pour que le lead voie le nouveau rôle.

## Lead

La session Claude Code principale du projet (celle-ci). Pas un artefact
séparé, mais un comportement dicté par `CLAUDE.md`. Écrit le code de
production, mène les tâches, appelle l'Architecte et le Designer et
réconcilie leurs résultats. Il n'y a pas de chat à trois en direct entre
les rôles : le lead s'adresse à chaque rôle séparément et fusionne
lui-même les réponses.

## Architecte (sous-agent en lecture seule)

Un consultant sur la logique et les décisions d'architecture. Existe
comme sous-agent `.claude/agents/architect.md` ; Claude Code le découvre
automatiquement — aucun import séparé n'est nécessaire. En lecture seule
(Read/Glob/Grep) : il lit les fichiers de méthodologie, raisonne et
propose — mais ne commit jamais et n'écrit pas de code.

**Quand l'appeler :** choisir une approche, décortiquer une décision
technique, passer en revue l'architecture, le doute « ça ne va pas se
retourner contre nous ? ». Pas pour écrire du code (c'est le lead) ni le
visuel (c'est le Designer).

**Comment l'appeler :** délègue la question au sous-agent `architect`
avec le contexte — il lira de lui-même les fichiers de méthodologie
nécessaires. Par exemple : « Demande à l'Architecte s'il faut extraire X
dans un module séparé : donne le contexte, des options avec compromis et
une recommandation. »

**Ce qu'il renvoie :** une analyse en forme de contexte → options avec
compromis → recommandation → alternative ouverte, en signalant quels
fichiers de méthodologie l'ont nourrie. Quand une décision est mûre, il
propose une entrée ADR-Lite prête pour `DECISIONS.md` au format du
projet.

**La boucle « proposé → l'humain a décidé → ADR » :**

1. L'Architecte propose une décision et un brouillon d'entrée ADR.
2. L'humain décide — l'Architecte est en lecture seule et ne décide pas
   à sa place.
3. Le lead/l'humain inscrit l'entrée finale dans `DECISIONS.md`.

Ainsi une décision importante se dépose dans les fichiers du projet, et
non dans la mémoire volatile d'un agent.

## Designer (Claude Design via MCP)

Un agent externe Claude Design pour le travail visuel : interfaces,
prototypes, spécifications visuelles. Le lead l'appelle directement comme
MCP ; il ne l'enveloppe pas dans un sous-agent.

**Prérequis — configuration unique au niveau du compte :**

1. `claude mcp add --scope user --transport http claude-design https://api.anthropic.com/v1/design/mcp`
2. `/design-login` — authentification OAuth (c'est cette étape qui
   connecte, pas `add`).
3. (opt.) `claude mcp list` — vérifier que le serveur est enregistré.

L'accès à Claude Design est offert sur les plans Pro / Max / Team /
Enterprise (beta). Si le MCP n'est pas connecté ou indisponible, ce
n'est **pas une erreur mais une alternative** : le lead soit connecte le
Designer, soit travaille sans lui. Les designs utilisent le design
system du compte (couleurs de marque, typographie) s'il est configuré ;
pour un nouveau projet personnel, les valeurs par défaut de Claude
Design.

**Quand l'appeler :** tu as besoin d'un design visuel ou d'un prototype
d'interface. Le lead transmet au Designer un brief tiré de
`specs/design-brief-template.md`, itère et tire le résultat dans le
dépôt comme prototype.

**Important :** le Designer produit du **web** (HTML/CSS/JS), pas le
stack cible du projet. Son artefact est une spécification visuelle ; sa
traduction dans le stack UI cible est toujours une étape distincte du
lead.

## Limites honnêtes

- Pas de conversation à trois en direct : l'Architecte et le Designer
  sont des rôles appelables, pas des interlocuteurs égaux dans un chat
  commun.
- Un sous-agent est une consultation, pas un flux : on voit le résultat,
  pas les tours intermédiaires.
- L'Architecte reconstruit le rôle à partir du prompt et des fichiers du
  projet ; la qualité de la réponse = qualité du prompt + complétude des
  fichiers de méthodologie.
- Le Designer pense en web ; la traduction vers le stack cible est
  l'étape du lead.
