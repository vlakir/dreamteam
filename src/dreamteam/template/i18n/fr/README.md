---
translated_from: i18n/ru/README.md
source_hash: 842f573b30c91a69865c2efc4561a61f4f41462b1ddffac2f729edf40afcd348
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
translation_updates:
  - date: 2026-10-16
    engine: openai/gpt-6.1-sol
    scope: OpenCode startup and recovery section; remove duplicated runtime name
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
# {{ project_name }}

{{ project_description }}

<!-- Les 1-3 phrases ci-dessus ont été remplies à partir des réponses
     à `dreamteam init`. Étends si nécessaire. Les décisions
     architecturales — dans DECISIONS.md, l'historique — dans
     CHANGELOG.md. -->

## Quick start

Gestionnaire de dépendances et d'environnement : **`{{ pm_name }}`**
(choisi lors de `dreamteam init`).

```bash
{{ pm_install }}                       # installer les dépendances
{{ pm_run }}python src/main.py     # lancer
```

## Travailler avec OpenCode

Utilise OpenCode 1.19.0 ; ce projet utilise Ensemble 0.18.0. Fournisseurs,
modèles et identifiants relèvent de la configuration personnelle, pas des rôles.
Démarre un seul serveur : `dt serve .` ; connecte un autre terminal avec
`dt run .`. Les clients supplémentaires rejoignent le même serveur. Après une
interruption, examine d'abord `dt recover .` sur l'hôte du serveur ; reprends
uniquement les member, lead-session et task conservés. Vérifie le résultat réel
d'une opération incertaine avant de réessayer : un délai dépassé ne prouve pas
qu'elle n'a pas été exécutée.

## Dépendances
{% if package_manager == 'uv' %}
```bash
uv add <pkg>                  # runtime
uv add --dev <pkg>            # dev
```
{%- elif package_manager == 'poetry' %}
```bash
poetry add <pkg>              # runtime
poetry add --group dev <pkg>  # dev
```
{%- elif package_manager == 'pdm' %}
```bash
pdm add <pkg>                 # runtime
pdm add -dG dev <pkg>         # dev
```
{%- elif package_manager == 'hatch' %}
Hatch gère les dépendances via `pyproject.toml`. Runtime — à
ajouter dans `[project.dependencies]`. Dev — à ajouter dans
`[tool.hatch.envs.default.dependencies]`. Après modifications :
`hatch env prune && hatch env create`.
{%- else %}
```bash
.venv/bin/pip install <pkg>   # puis ajoute le paquet à pyproject.toml [project.dependencies] toi-même
```
{%- endif %}

## Vérifications avant push

```bash
{{ pm_run }}ruff check .
{{ pm_run }}ruff format --check .
{{ pm_run }}mypy <chemin du code>
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
- `AGENTS.md` — règles projet pour OpenCode.

## Méthodologie

Le projet est créé depuis le modèle
[vlakir/dreamteam](https://github.com/vlakir/dreamteam). La
description détaillée de la méthodologie (scope discipline, rituel
spec/clarify/analyze pour les grosses fonctionnalités, contrôle
pre-push) — voir le repo du modèle.

<!-- Ci-dessous on ajoute des sections spécifiques au projet : API,
     déploiement, schémas de BD, doc des modules, contacts, etc. -->
