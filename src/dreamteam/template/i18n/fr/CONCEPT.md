---
translated_from: i18n/ru/CONCEPT.md
source_hash: eca6f2951dddf2c7658035c0812d8ce15bed724414f720f5e3b5cf66bb378603
translation_engine: claude-opus-4-8
translation_date: 2026-07-30
---
# Concept : {{ project_name }}

> **C'est un document immuable** — il fixe la vision initiale du
> projet au moment de sa création. Une fois rempli, **il n'est plus
> édité**. L'état courant du projet est maintenu dans `README.md` ;
> si le concept change radicalement (cas rare, pivot) — on crée
> une nouvelle version dans `concepts/v1-...md`,
> `concepts/v2-...md` (ADR-pattern, mais pour les concepts).
>
> **Date de création :** `<YYYY-MM-DD>`
>
> Lors de la création du projet via `dreamteam init`, ce fichier
> est déjà en place ; passe le rituel de questions croisées avec
> Claude (voir ci-dessous), remplis les sections et fige-les comme
> immuables.

<!-- La structure ci-dessous est un QUESTIONNAIRE (leading questions)
     pour un concept vide, pas une forme obligatoire. Si tu as déjà un
     concept / cahier des charges / vision substantiel — remplace
     entièrement le contenu de ce fichier par le tien, sans rien
     transposer dans ces rubriques. L'essentiel : qu'une section « Out
     of scope » soit présente sous une forme quelconque (protection
     contre le scope creep) et que le document reste immuable une fois
     figé. Le rituel de clarify (questions croisées de Claude sur les
     angles morts) se fait sur le contenu réel. -->

## Objectif

<!-- 1-2 phrases. Ce que fait le projet et pourquoi il est
     nécessaire. Pas de détails techniques ni de promesses
     d'implémentation — seulement le sens. -->

## Utilisateur

<!-- Pour qui. Use case en une ou deux phrases. Si l'utilisateur est
     le Développeur lui-même, on l'écrit ; si c'est une future
     « tierce partie » — on décrit brièvement son contexte. -->

## Fonctionnalité clé

<!-- 3-7 points au niveau « capacités », pas implémentation. Chaque
     point répond à la question « que doit savoir faire le système ?
     », pas « comment ». -->

- ...

## Out of scope

<!-- Ce que ce projet ne fait DÉLIBÉRÉMENT PAS. Cette section est
     la protection principale contre l'extension du scope dès le
     premier jour. Écris franchement : « X — on ne fait pas » /
     « Y — on laisse aux gens / aux systèmes externes ». -->

- ...

## Contraintes et hypothèses

<!-- Plateforme, stack (si déjà connu), exigences non
     fonctionnelles (performance, fiabilité, sécurité), hypothèses
     sur l'environnement / les utilisateurs / la charge. Les
     hypothèses aussi vont ici — elles peuvent se révéler fausses
     plus tard, et il est important de fixer ce que l'on supposait
     exactement au moment du démarrage. -->

- ...

---

## Rituel de rédaction (texte d'aide, à supprimer après remplissage)

Au début d'un nouveau projet, `CONCEPT.md` se remplit via le
**rituel de questions croisées**, analogue au `clarify` pour la
spec d'une grosse fonctionnalité :

1. Le Développeur écrit une première ébauche des sections (ou
   formule simplement l'idée).
2. Claude pose des questions croisées sur les angles morts :
   - **Objectif :** quelle douleur / quel problème le projet
     résout-il ?
   - **Utilisateur :** qui exactement est l'utilisateur, dans quel
     contexte ?
   - **Fonctionnalité clé :** quel est l'ensemble minimal pour le
     MVP ? Qu'est-ce qui est potentiellement utile, mais pas
     maintenant ?
   - **Out of scope :** ce que l'on ne fait définitivement PAS
     ? (Attention particulière — c'est la section la plus précieuse
     pour la protection contre le scope creep.)
   - **Contraintes :** plateforme, stack, charge cible, hypothèses ?
3. Les réponses du Développeur sont cousues dans les sections
   correspondantes.
4. Une fois rempli, cette section d'aide (« Rituel de rédaction »)
   est supprimée. `CONCEPT.md` est marqué d'une date et considéré
   comme immuable.
