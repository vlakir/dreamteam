---
translated_from: i18n/ru/CLAUDE.md
source_hash: 53c67c8b3661fb18323fb23cd83584365dd00e0349ae1eec7e76a52d1291c3a2
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
# Règles projet pour Claude

Ce fichier contient les règles projet pour Claude (Claude Code). Les
règles globales (`~/.claude/CLAUDE.md`) s'appliquent toujours ; ici
— uniquement ce qui est spécifique à ce projet.

## Que lire au début d'une session

1. `CONCEPT.md` (s'il existe) — vision initiale du projet, document
   immuable. Utile comme point d'ancrage des mois plus tard.
2. `README.md` — description courante / quick start / statut du
   projet.
3. `DECISIONS.md` — décisions architecturales déjà prises.
4. `BACKLOG.md` — ce qui est en file d'attente.
5. Lors du travail sur une grosse fonctionnalité — le
   `specs/T<NNN>-*/spec.md` correspondant.

## Rituel de rédaction de `CONCEPT.md` (pour un nouveau projet)

Au début d'un nouveau projet, Claude aide le Développeur à rédiger
`CONCEPT.md` — document immuable de la vision initiale. C'est un
rituel de questions croisées, analogue au `clarify` pour une spec
de grosse fonctionnalité :

1. Le Développeur écrit une première ébauche (ou formule simplement
   l'idée).
2. Claude pose des questions croisées sur les angles morts :
   - **Objectif :** quelle douleur / quel problème le projet
     résout-il ?
   - **Utilisateur :** qui, dans quel contexte ?
   - **Fonctionnalité clé :** MVP minimum vs nice-to-have ?
   - **Out of scope :** ce que l'on ne fait DÉLIBÉRÉMENT pas
     (section principale — protection contre le scope creep dès
     le premier jour).
   - **Contraintes et hypothèses :** plateforme, stack, charge,
     hypothèses sur l'environnement / les utilisateurs.
3. Les réponses sont cousues dans `CONCEPT.md`, et la date de
   création est apposée.
4. **Une fois rempli, `CONCEPT.md` n'est plus édité.** L'état
   courant vit dans `README.md`. Si le concept change radicalement
   (rare, pivot) — on ajoute une nouvelle version :
   `concepts/v2-...md`, `v3-...md` (ADR-pattern, mais pour les
   concepts).

`CONCEPT.md` est rempli soit lors de la création du projet via
`dreamteam init` (Claude pose les questions croisées), soit
manuellement plus tard.

## Description du projet

{{ project_description }}

## Stack

**Stack de base du modèle (pour projets Python) :**
- Python 3.14+ (`requires-python` dans `pyproject.toml`).
- Gestionnaire de dépendances et d'environnements : **`{{ pm_name }}`**
  (choisi lors de `dreamteam init` via le prompt
  `package_manager` ; alternatives : `uv` / `poetry` / `pdm` /
  `hatch` / `pip`).
- Linter : `ruff` (règle `select = ["ALL"]` avec un `ignore` fixe).
- Type-checker : `mypy` avec `mypy_path = "src"`.
- Stack de tests : `pytest` + `pytest-cov` + `pytest-asyncio`. Seuil
  de coverage ≥ 80 % line coverage sur `src/`
  (`--cov-fail-under=80` dans `[tool.pytest.ini_options]`).
- **Racine des sources — `src/`** (toujours, dans tous les projets).
- Tests — dans `tests/` à la racine (`ruff` l'exclut, mais `pytest`
  les trouve via `testpaths = ["tests"]`).

**Commandes typiques (pour le `{{ pm_name }}` choisi) :**
{%- if package_manager == 'uv' %}
- `uv sync` — installer les dépendances (crée `.venv` au premier
  lancement).
- `uv add <pkg>` / `uv add --dev <pkg>` — ajouter une dépendance
  runtime / dev.
- `uv run python ...` — exécuter sous `.venv` sans l'activer.
- `uvx <tool>` — exécuter un outil CLI sans installation locale.
{%- elif package_manager == 'poetry' %}
- `poetry install` — installer les dépendances (crée le venv au
  premier lancement).
- `poetry add <pkg>` / `poetry add --group dev <pkg>` — ajouter
  une dépendance runtime / dev.
- `poetry run python ...` — exécuter sous le venv poetry sans
  l'activer.
- `poetry env activate` — ouvrir un sous-shell avec le venv actif.
{%- elif package_manager == 'pdm' %}
- `pdm install` — installer les dépendances (crée `.venv` au
  premier lancement).
- `pdm add <pkg>` / `pdm add -dG dev <pkg>` — ajouter une
  dépendance runtime / dev.
- `pdm run python ...` — exécuter sous `.venv` sans l'activer.
{%- elif package_manager == 'hatch' %}
- `hatch env create` — créer l'environnement `default` avec les
  dev-deps.
- Les dépendances sont éditées dans
  `[tool.hatch.envs.default.dependencies]` dans `pyproject.toml`.
- `hatch run <cmd>` — exécuter une commande dans l'env `default`
  sans activation.
- Les scripts sont définis dans
  `[tool.hatch.envs.default.scripts]` et appelés via
  `hatch run <script>`.
{%- else %}
- `python -m venv .venv && .venv/bin/pip install -e .[dev]` —
  créer un venv et installer les dépendances dev.
- `.venv/bin/pip install <pkg>` — installer un paquet (puis
  ajoute-le à `pyproject.toml` toi-même ; pip ne met pas à jour
  le manifeste automatiquement).
- `.venv/bin/python ...` ou activer le venv
  (`source .venv/bin/activate`) et lancer `python ...`.
{%- endif %}

Avant chaque `git push`, **quatre** vérifications obligatoires
avec 0 erreur :
1. `{{ pm_run }}ruff check .`
2. `{{ pm_run }}ruff format --check .`
3. `{{ pm_run }}mypy <code>`
4. `{{ pm_run }}pytest` (inclut le seuil de coverage ≥ 80 %).

**À lancer en une chaîne unique**, pour qu'un échec à n'importe
quelle étape interrompe le commit :

```bash
{{ pm_run }}ruff check . && \
{{ pm_run }}ruff format --check . && \
{{ pm_run }}mypy <code> && \
{{ pm_run }}pytest && \
git add -A && git commit -m "..." && git push
```

**Catch-it-at-the-output :** si dans la sortie de la commande
précédente tu vois `FAILED`, `Error`, `1 failed` ou des marqueurs
similaires — **n'avance pas**, vérifie la cause. Et n'étouffe pas
le code de sortie : `pytest | tail -5` renvoie le code de sortie
de `tail`, pas de `pytest` — un échec passe silencieusement dans
`git commit`.

Pas de `# noqa` / `# type: ignore` / extensions de la section
`ignore` sans discussion explicite avec le Développeur. Détails —
dans `~/.claude/CLAUDE.md` global, sections « Linters » et
« Tests ».

## Workflow git

Règles de base du processus (s'appliquent toujours dans ce projet) :

- **Les tâches sont numérotées.** Chaque entrée dans `BOARD.md` /
  `BACKLOG.md` a un ID `T<NNN>` ; la branche est `T<NNN>-<slug>` ;
  la PR est `T<NNN>: <title>`. Exception — les PR
  méthodologiques qui changent les règles elles-mêmes (sans
  `T`-ID).
- **Push direct sur `main` / `master` est interdit.** Tout
  changement — via une branche feature et une PR/MR.
- **Une PR — un commit.** Sur une branche feature on commit comme
  on veut pour le travail ; squash avant le merge.
- **Chaque PR passe par une code review** avant le merge. Par
  défaut — Claude (self-review avec checklist : scope / architecture
  / code / linters / docs / conventions / sécurité). Parfois — le
  Développeur.
- **Ne pas ignorer les reviews tierces.** Les bots comme
  `qodo-code-review` doivent être lus, analysés, discutés avec le
  Développeur ; la décision est consignée (accepter / écarter /
  reporter).

## Discipline de planification

Sans cérémonies Scrum (sprints, story points, velocity, burndown).
On ne garde que les éléments utiles :

- **Versioning par milestone.** `[Unreleased]` dans `CHANGELOG.md`
  accumule les changements. Le passage à une nouvelle version
  `[N.M.0]` se fait quand c'est **achevé de façon significative**
  (critère souple) : changements significatifs introduits, OU un
  ensemble logique de tâches clos, OU on a accumulé « assez » pour
  un point de sauvegarde. Le Développeur tranche en dernier ; il
  n'y a pas de métrique formelle — ce serait contraire au principe
  « pas de Scrum-cargo ». Format des versions — Keep a Changelog
  (`## [N.M.0]`, sans préfixe `v`).
- **Rétrospective comme rituel** après la fermeture d'un milestone.
  Un court débriefing en trois points :
  - ce qui a marché (work-as-expected, ou une surprise agréable),
  - ce qui n'a pas marché (bundling, slips, overhead inutile),
  - ajustements méthodologiques (que changer dans
    `~/.claude/CLAUDE.md` / `CLAUDE.md` projet / le modèle).
  Placement : **section `### Retrospective`** à l'intérieur de
  l'entrée de la version correspondante dans `CHANGELOG.md`. Pas
  un fichier séparé — la rétro est étroitement liée au milestone
  et il est pratique de la lire à côté.
- **Critères d'acceptation** obligatoires pour les tâches plus
  grandes qu'une édition d'une ligne — consignés directement dans
  `BOARD.md` / `BACKLOG.md` sous forme de bloc court
  (`Acceptance: <ce qui doit être atteint pour que la tâche soit
  considérée close>`) ou dans `specs/T<NNN>-*/spec.md` pour les
  grosses fonctionnalités. Sans critères d'acceptation explicites,
  la tâche n'est pas considérée comme mûre pour passer
  `BACKLOG → BOARD → Doing`.
- **WIP-limit** dans `BOARD.md → Doing` : au maximum 1-2 tâches.
  Plus — et l'on perd le focus (règle kanban classique).

Si le Développeur a un `~/.claude/CLAUDE.md` global configuré —
ce fichier contient la version étendue de ces règles (sections
« Ne jamais pusher directement sur main », « Une PR — un commit »,
« Code review sur chaque PR »). La version courte ci-dessus suffit
comme source autonome.

## Règles spécifiques au projet

## Ce qui dans ce projet va habituellement dans BACKLOG.md, pas dans l'édition courante

