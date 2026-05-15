---
translated_from: i18n/ru/DECISIONS.md
source_hash: ecf297efe8b7b96e7620a8533b03d12e0c7764ae4384d909ee35bd39c56d160c
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Décisions d'architecture

ADR-Lite : un journal compact des décisions d'architecture avec
justifications. L'objectif — dans six mois on peut répondre à la
question « pourquoi avons-nous fait comme ça à l'époque ? », sans
reconstruire le contexte à partir des commits.

## Format

Chaque décision — un bloc court :

- **Date** — quand elle a été prise.
- **Décision** — ce qui a été décidé (1 ligne).
- **Contexte** — quelle tâche / contrainte y a mené.
- **Alternatives** — ce qui a été envisagé et pourquoi rejeté.
- **Conséquences** — ce que cela nous donne maintenant et ce que
  cela nous coûte.

Les décisions ne sont pas éditées après fixation. Si une décision
est revisitée — on ajoute un nouveau bloc avec un lien vers
l'ancienne, et l'ancienne est marquée « Remplacée par la décision
du <date> ».

---

## Exemple (à supprimer lors du remplissage du modèle)

### 2026-05-13 — SQLite à la place de PostgreSQL pour le MVP

- **Contexte :** projet pour un seul utilisateur, < 10 Mo de
  données, démarrage rapide requis sans service séparé.
- **Alternatives :**
  - PostgreSQL — rejeté, pas de raison de garder un processus
    séparé pour un utilisateur unique ; la migration on a toujours
    le temps de la faire.
  - Fichier JSON — rejeté, on perd la transactionnalité et les
    index.
- **Conséquences :** déploiement = un binaire, backup = une copie
  du fichier. À la croissance > 100 Mo ou à l'apparition d'accès
  concurrent — revisiter.

---

## Décisions du projet

<!-- Les vraies décisions sont ajoutées ici, les nouvelles en
     haut. -->

