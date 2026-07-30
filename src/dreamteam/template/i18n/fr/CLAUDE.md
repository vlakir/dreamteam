---
translated_from: i18n/ru/CLAUDE.md
source_hash: 7eaae69f3591aa6e08d3aaa12ef0b3f0ac2158db49be286799b7c18e5848c934
translation_engine: claude-opus-4-8
translation_date: 2026-07-30
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

**La structure est un questionnaire, pas un contrat.** Les rubriques
ci-dessus (Objectif / Utilisateur / Fonctionnalité clé / Out of scope /
Contraintes) sont des **leading questions pour un `CONCEPT.md` vide**,
pas une forme obligatoire du document final. Si le projet possède déjà
un `CONCEPT.md` / cahier des charges / vision substantiel sous une
forme quelconque — Claude **l'accepte tel quel** et mène le `clarify`
sur les angles morts de son contenu, **sans exiger** une transposition
dans les rubriques du modèle. Le seul élément obligatoire du rituel est
le **clarify** (questions croisées). `Out of scope` reste la rubrique
la plus précieuse (protection contre le scope creep), mais peut
s'exprimer sous une forme quelconque au sein du document existant.
L'invariant d'immuabilité (plus édité une fois figé) tient dans tous
les cas.

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
  de coverage ≥ 80 % line coverage sur `src/` (`--cov-fail-under=80`).
  Le seuil est appliqué par une **commande explicite** dans le gate
  pre-push et la CI, non par le `addopts` par défaut — le `pytest` par
  défaut reste volontairement léger (voir « Prises de tests lourdes —
  via le wrapper mutex » ci-dessous).
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
4. `scripts/pytest-guard.sh --cov=src --cov-report=term-missing --cov-fail-under=80`
   — la prise complète avec le seuil de coverage ≥ 80 % **via le wrapper
   mutex** (voir « Prises de tests lourdes — via le wrapper mutex »
   ci-dessous).

**À lancer en une chaîne unique**, pour qu'un échec à n'importe
quelle étape interrompe le commit :

```bash
{{ pm_run }}ruff check . && \
{{ pm_run }}ruff format --check . && \
{{ pm_run }}mypy <code> && \
scripts/pytest-guard.sh --cov=src --cov-report=term-missing --cov-fail-under=80 && \
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

## Prises de tests lourdes — via le wrapper mutex

Quand plusieurs `git worktree` partagent une machine (voir « Travail
parallèle sur plusieurs git worktree » ci-dessous), la ressource
partagée est la **RAM**. Une prise complète / coverage retient un RSS
notable ; deux ou trois à la fois (à côté d'un IDE lourd) s'empilent en
**OOM ou blocage**. Le wrapper `scripts/pytest-guard.sh` sérialise les
prises lourdes entre TOUS les worktree via un verrou partagé par
utilisateur (concurrence 1, attente bloquante : la deuxième prise attend
son tour et démarre d'elle-même). Seul le **lancement** est sérialisé —
le code et l'état non commité des sessions ne sont jamais touchés.

**Règle — ce qui passe par le wrapper, ce qui va en direct :**

- **Prise complète / coverage et gate de tests pre-push — via le
  wrapper** (`scripts/pytest-guard.sh …`), pas le runner nu ; surtout
  avec des sessions parallèles vivantes.
- **Une prise sur un seul fichier** (légère, ponctuelle) — peut aller en
  direct (`{{ pm_run }}pytest tests/test_x.py`) ; le mutex est optionnel.
- **CI — en direct** (runner isolé, rien à partager).

**Prise par défaut légère.** Le coverage est tenu hors du `addopts` par
défaut (le traceur de coverage gonfle le RSS/CPU) : le `{{ pm_run }}pytest`
par défaut reste léger pour l'itération locale répétée. Le seuil ≥ 80 %
reste appliqué — juste par une **commande explicite** (gate 4 ci-dessus
et CI), non par le défaut.

**Plafond mémoire optionnel par prise.** La variable
`PYTEST_GUARD_MEM_MAX` (par ex. `4G` ; `0` ou non définie — désactivé) :
sous Linux avec une session systemd, la prise est lancée dans un cgroup
transitoire avec une limite RSS, pour qu'un test emballé soit tué par
l'OOM-killer **dans son propre cgroup** (la prise échoue, mais la
machine et l'IDE survivent) au lieu de faire tomber le système. Hors
Linux/systemd (macOS, Windows, conteneurs) c'est un no-op — la prise
passe quand même par le mutex.

**Multiplateforme.** `flock` est util-linux (Linux / assimilé macOS). Là
où il est absent (Windows), le wrapper **dégrade proprement** : il
imprime une ligne d'avertissement et lance les tests directement (sans
sérialisation), sans jamais échouer.

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
- **Clôturer une tâche — dans sa propre PR.** Le déplacement de
  l'entrée de `BOARD.md → Doing` vers `Done` se fait **dans le même
  commit squash** de la PR de la tâche, pas dans une chore-PR séparée
  (après le merge la tâche est de toute façon Done — `BOARD.md` ne fait
  que refléter la réalité). Les limites de la PR suivent la cohérence
  logique de la tâche ; fractionner des changements liés juste pour
  faire « une PR plus courte » est un anti-pattern (overhead de review
  en plus, consommation du quota des bots de review).
- **Chaque PR passe par une code review** avant le merge. Si le projet
  dispose d'un bot de review automatique fonctionnel (CodeRabbit,
  qodo-code-review ou similaire, qui review chaque PR) — c'est lui le
  baseline, et **une self-review séparée de Claude n'est pas requise
  par défaut**. La self-review de Claude est nécessaire dans trois cas :
  (1) **docs / méthodologie** — une PR ne changeant que du markdown /
  des règles / des specs (les bots reviewent mal la prose) → la
  self-review reste le défaut ; (2) **code non trivial** — une
  deep-review ciblée de la zone à risque (architecture, sécurité, scope
  complexe), à la demande du Développeur ou à l'initiative de Claude ;
  (3) **fallback** — le bot est indisponible (rate-limit, en panne,
  aucun rapport dans un délai raisonnable). Checklist de self-review :
  scope / architecture / code / linters / docs / conventions /
  sécurité.
- **Ne pas ignorer les reviews tierces.** Les bots comme CodeRabbit /
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

## Où vit la connaissance du projet (memory-agnostic)

**Principe central : toute connaissance durable du projet vit À
L'INTÉRIEUR du projet** — dans son dépôt (`CLAUDE.md`, `DECISIONS.md`,
`docs/`, `specs/`, `BOARD.md` / `BACKLOG.md`). Toute couche **externe**
de mémoire persistante de l'assistant (si le Développeur en a une —
peut-être pas) n'est **qu'un double / une sauvegarde optionnels** ; la
méthodologie doit fonctionner même SANS elle.

La raison est double :

1. La mémoire externe de l'assistant est souvent liée à un chemin / une
   machine et ne se transporte ni ne se partage entre les copies de
   travail (worktrees) et les plateformes.
2. La connaissance du projet doit voyager avec le dépôt vers quiconque
   le clone.

**La règle :** enregistre d'abord le fait dans les fichiers du projet,
et seulement ensuite (si un tel mécanisme existe) duplique-le
éventuellement à l'extérieur. « Duplique si tu veux, mais tout ce qui
concerne le projet est dans le projet. »

## Travail en parallèle sur plusieurs git worktrees

Plusieurs tâches peuvent être menées **en même temps**, chacune dans son
propre `git worktree` (une copie de travail distincte du dépôt, `.git`
partagé), pour ne pas changer de branche dans un seul checkout. À ce
moment-là, **plusieurs sessions Claude** peuvent travailler en parallèle
dans des dossiers différents — une par worktree. Elles doivent se
connaître mutuellement et ne pas se télescoper.

**Le registre, c'est le `git worktree list` intégré.** Tous les
worktrees partagent un seul `.git`, donc depuis n'importe quel dossier
cloné `git worktree list` montre TOUS les worktrees frères (chemin +
branche + HEAD). Aucun fichier-registre maison n'est nécessaire.

**Rituel de démarrage.** Au début d'une session — `git worktree list` +
`git branch --show-current`. S'il y a plus d'un worktree, **une autre
session travaille peut-être** à côté sur une autre branche ; son chemin
et sa branche sont **le territoire de quelqu'un d'autre**.

**Isolation (stricte) :**

- Un worktree = une tâche = une branche. Ne pas checkout, committer,
  rebaser ni pusher dans la branche d'autrui ; ne pas éditer de fichiers
  sous le chemin de worktree d'autrui.
- Lancer les gates et les tests depuis **ton propre** environnement. Une
  variable d'environnement virtuel héritée peut pointer vers
  l'environnement d'un **autre** dossier — active / pointe vers le tien,
  sinon tu lances les vérifications dans le mauvais environnement.
- **Les journaux « ajout par le haut »** (`DECISIONS.md`,
  `CHANGELOG.md`, `BOARD.md`, `BACKLOG.md`) entrent presque toujours en
  conflit lors du merge de deux tâches parallèles. Ne touche **qu'à
  l'entrée de ta propre tâche** ; avant la PR, toujours `git fetch` +
  `git rebase` sur un `main` frais et résous les conflits (en général —
  garder les entrées des autres, ajouter la tienne). Le code de
  différentes tâches se fusionne d'habitude proprement — c'est le texte
  des journaux qui entre en conflit.

**Cycle de vie d'un worktree :**

- Créer : `git worktree add ../<repo>-T<NNN> -b T<NNN>-<slug>` (ou sur
  une branche existante).
- Avant la PR : `git fetch` → rebase sur `main` frais → squash en un
  seul commit (règle « une PR — un commit ») → push → PR → review.
- Après le merge : `git worktree prune` + supprimer la branche locale.

**Nettoie derrière toi — en demandant la permission.** Une fois une
tâche ou un groupe de tâches liées terminé, **propose de retirer le
dossier cloné** (worktree). Mais le clone peut contenir quelque chose de
nécessaire (travail non committé, notes locales, artefacts), donc
`git worktree remove` — **seulement après un « oui » explicite** du
Développeur. Ne le supprime pas en silence. Le checkout principal et les
worktrees des autres restent intacts.

**Services de dev partagés — une instance par utilisateur.** Si le
lancement de l'app fait monter des ressources partagées (une base de
données, des conteneurs, une config locale, un port occupé), deux copies
parallèles les **partagent** — migrations / état divergents, bataille
pour le port. Préviens, et montre comment isoler (une BD / config / port
distincts par worktree).

**La mémoire n'est PAS partagée entre les dossiers.** L'auto-mémoire
fichier de l'assistant, s'il en a une, est d'habitude liée au chemin
cwd : une session démarrée **à l'intérieur** d'un dossier cloné obtient
une mémoire SÉPARÉE (vide) et ne voit PAS la mémoire du dossier
principal. Garde donc la connaissance durable dans les fichiers du dépôt
(ils sont présents dans chaque worktree) — voir « Où vit la connaissance
du projet (memory-agnostic) » ci-dessus. Par défaut, préfère démarrer la
session depuis le dossier principal et travailler sur le worktree via
des chemins absolus.

## Règles spécifiques au projet

## Ce qui dans ce projet va habituellement dans BACKLOG.md, pas dans l'édition courante


## Rôles de l'équipe (Architecte + Designer)

Ce projet embarque un dispositif de collaboration réutilisable : le
lead (cette session), un sous-agent Architecte en lecture seule et un
Designer externe (Claude Design). Comment les appeler, le rituel de
consultation et la boucle « proposé → l'humain a décidé → ADR »
sont dans un fichier séparé :

@.claude/team-roles.md
