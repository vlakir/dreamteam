---
translated_from: i18n/ru/README.md
source_hash: 6cbcb2749f1ac3d91c54f37a9d58d667a6b46afb505129c142e310d7e61b76b1
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# {{ project_name }}

{{ project_description }}

<!-- Les 1-3 phrases ci-dessus ont été remplies à partir des réponses
     à `dreamteam init`. Étends si nécessaire. Les décisions
     architecturales — dans DECISIONS.md, l'historique — dans
     CHANGELOG.md. -->

## Quick start

```bash
uv sync                       # créer .venv et installer les dépendances
uv run python src/main.py     # lancer
```

## Dépendances

```bash
uv add <pkg>                  # runtime
uv add --dev <pkg>            # dev
```

## Vérifications avant push

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy <chemin du code>
```

Les trois doivent passer avec 0 erreur. Les contournements
(`# noqa`, `# type: ignore`, extension de la section `ignore`) —
uniquement sur accord préalable.

## Structure du projet

- `src/` — racine des sources.
- `CONCEPT.md` — vision initiale du projet (immuable).
- `DECISIONS.md` — décisions architecturales avec justifications
  (ADR-Lite).
- `BOARD.md` — tableau Kanban de travail (To Do / Doing / Done).
- `BACKLOG.md` — parking d'idées et de trouvailles latérales.
- `CHANGELOG.md` — journal des changements notables.
- `specs/` — spécifications des grosses fonctionnalités.
- `CLAUDE.md` — règles projet pour Claude (Claude Code).

## Méthodologie

Le projet est créé depuis le modèle
[vlakir/dreamteam](https://github.com/vlakir/dreamteam). La
description détaillée de la méthodologie (scope discipline, rituel
spec/clarify/analyze pour les grosses fonctionnalités, contrôle
pre-push) — voir le repo du modèle.

<!-- Ci-dessous on ajoute des sections spécifiques au projet : API,
     déploiement, schémas de BD, doc des modules, contacts, etc. -->
