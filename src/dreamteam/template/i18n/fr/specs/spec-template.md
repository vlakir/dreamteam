---
translated_from: i18n/ru/specs/spec-template.md
source_hash: 0f45d2d1435c67a85ab50b0aa1d9f10e3c089615ee91c53712e6b80a55e4513c
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Spec : <Nom de la fonctionnalité>

**Statut :** Draft | Clarified | Analyzed | In Progress | Done
**Date de création :** <YYYY-MM-DD>
**Documents liés :** <liens vers DECISIONS, autres specs, le cas échéant>

---

## 1. Overview

<!-- 2-4 phrases sur la feature. Ce que c'est et pourquoi c'est
     nécessaire. Pas de détails techniques — on écrit comme un
     product manager, pas comme un ingénieur. -->

## 2. User Stories

<!-- Scénarios au format :
     « En tant que <rôle>, je veux <action>, afin de <but>. »

     Pour les projets sans utilisateurs explicites (scripts,
     infrastructure, matériel) — remplacer par « Scénarios
     d'usage » décrivant les situations dans lesquelles la
     feature s'applique.
-->

- ...

## 3. Functional Requirements

<!-- Ce que le système DOIT savoir faire. On utilise les
     formulations « doit / peut / ne doit pas » — pour que ce
     soit sans ambiguïté. -->

- DOIT : …
- PEUT : …
- NE DOIT PAS : …

## 4. Success Criteria

<!-- Conditions de succès mesurables. Nombres concrets, timings,
     comportement.
     Mauvais : « fonctionne vite ».
     Bien : « réponse < 200 ms sur une requête typique ». -->

- ...

## 5. Key Entities

<!-- Entités et données sur lesquelles opère la feature. Sans
     schémas de BD ni d'API — seulement conceptuellement : quels
     sont les objets, quels sont leurs champs clés, comment ils
     sont liés.
-->

- ...

## 6. Assumptions & Constraints

<!-- Ce que l'on considère comme acquis / ce qui contraint la
     solution.
     Exemples :
     - Plateforme cible — Raspberry Pi Zero W (ARMv6).
     - L'utilisateur est toujours un seul, pas d'accès
       concurrent.
     - L'API externe a une limite de 60 requêtes par minute.
-->

- ...

## 7. Out of Scope

<!-- Ce qui n'entre PAS DÉLIBÉRÉMENT dans cette feature.
     Protection contre l'extension du scope. -->

- ...

---

## Clarify (rempli par Claude)

<!-- Claude relit la spec et pose des questions croisées sur les
     angles morts. Catégories : auth, validation, errors, edge
     cases, performance, sécurité, intégrations. Les réponses du
     Développeur sont recousues dans les sections correspondantes
     ci-dessus. -->

### Open questions

- ...

### Resolved (avec réponses)

- ...

---

## Analyze (rempli par Claude)

<!-- Claude lit la spec (et le plan, s'il existe) et cherche les
     contradictions, divergences, omissions, impossibilités
     techniques.

     Liste d'Issues avec marqueurs :
     - 🔴 Critical — à fixer avant le début de l'implémentation.
     - 🟡 Warning — à discuter, possiblement fixer.
     - 🟢 Note — pour information.
-->

- ...
