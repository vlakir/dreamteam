---
translated_from: i18n/ru/BOARD.md
source_hash: a34bdadb4bacaae4c37715eff6d323c0c0552189b61a1c1d266c8c75927febb0
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Board

Une alternative Kanban légère dans un seul fichier markdown : trois
colonnes (To Do / Doing / Done) sous git, sans services ni outils
externes.

## Rapport avec les autres fichiers

- `BACKLOG.md` — longue file d'attente d'idées et de trouvailles
  latérales. C'est là que tombent « on y pensera plus tard », « pas
  maintenant ». Parking de scope.
- `BOARD.md` (ce fichier) — flux de travail actif. Les tâches que
  nous avons prises ou que nous prévoyons de prendre prochainement.
- `specs/T<NNN>-*/spec.md` — là où une grosse tâche du BOARD
  grandit, si elle se révèle être une feature de plus d'un jour
  de travail.

Cycle de vie d'une tâche : idée dans `BACKLOG.md` → mûre →
déménage dans `To Do` ici → prise en travail (`Doing`) → fermée
(`Done`) → après release passe dans `CHANGELOG.md` (l'entrée doit
contenir le T-ID), supprimée d'ici. **`CHANGELOG.md` est l'unique
stockage persistant des T-IDs des tâches terminées**, sans lui la
règle « l'ID n'est pas réutilisé » casse.

## Format d'une tâche

Chaque tâche — `- **T<NNN>** — <description courte>`. L'ID est
attribué à la création : le nouveau =
`max(T-IDs existants dans BOARD.md, BACKLOG.md et CHANGELOG.md) + 1`.
L'ID n'est jamais réutilisé. L'ID est partagé entre `BOARD.md` et
`BACKLOG.md` — il est préservé lors du passage entre eux ; après
une release, la tâche tombe dans `CHANGELOG.md` avec le même T-ID,
ce qui garantit l'unicité des numéros entre releases.

Nom de la branche : `T<NNN>-<slug>` (sans namespace de type
`fixes/` / `feature/` — l'ID donne déjà l'identification). Nom de
la PR : `T<NNN>: <title>`. Spécification d'une grosse fonctionnalité
: `specs/T<NNN>-<slug>/spec.md`.

Au goût, on peut ajouter :

- une étiquette de date de prise,
- un lien vers la spec,
- le nom de la branche.

Exemple :

```
- **T<NNN>** — Aperçu des posts dans Telegram
  (`specs/T<NNN>-telegram-preview/`, branche `T<NNN>-telegram-preview`).
```

---

## To Do

<!-- Prêt à être pris. File FIFO par défaut, on peut remonter les
     priorités. -->

<!-- Entrées de tâches au format `- **T<NNN>** — description`. Voir
     la section « Format d'une tâche » ci-dessus. -->

## Doing

<!-- En cours maintenant. À garder court : au maximum 1-2 tâches
     par développeur, sinon on perd le focus (règle classique
     du WIP-limit en Kanban). -->

- ...

## Done

<!-- Tâches fermées en attente de passage dans CHANGELOG.md à la
     prochaine release ou point significatif. Après le passage —
     on nettoie. -->

- ...
