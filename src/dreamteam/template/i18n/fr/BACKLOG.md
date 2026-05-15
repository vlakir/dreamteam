---
translated_from: i18n/ru/BACKLOG.md
source_hash: 97561a99e58717c8b3c1493b0669d8e69849ccff9ed8694c913846ee8908efb1
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Backlog

Parking d'idées, de trouvailles latérales et de « à corriger plus
tard ».

**Règle :** si pendant le travail sur la tâche courante, Claude ou
le Développeur remarquent quelque chose d'extérieur — cela va ici,
pas dans le commit courant. C'est la protection contre l'extension
du scope.

Ce n'est **pas un task tracker formel** avec deadlines et métriques
— c'est un parking d'idées. Mais **l'ordre compte** : en haut — ce
qui est prévu pour le prochain pas, plus bas — moins urgent (FIFO
par défaut, on peut remonter les priorités). Quand quelque chose
est pris du backlog en travail — cela devient une tâche ou une
spec (`specs/T<NNN>-…`) et est supprimé d'ici.

## Format

`- **T<NNN>** — [<date de découverte>] <description courte> — <optionnel : contexte / d'où c'est sorti>`

L'ID est attribué à la création ; le nouveau =
`max(T-IDs existants dans BACKLOG.md, BOARD.md et CHANGELOG.md) + 1`.
L'ID n'est pas réutilisé et est préservé lorsque la tâche passe
entre BACKLOG et BOARD ; après une release, la tâche passe dans
`CHANGELOG.md` (avec le même T-ID), ce qui garantit l'unicité entre
releases.

## Items

<!-- Exemple (à supprimer lors du remplissage du modèle) :

- **T<NNN>** — [<date>] Les logs sont dupliqués en stdout et fichier — regarder la config logging.
- **T<NNN+1>** — [<date>] La fonction `parse_post` a grossi jusqu'à 80 lignes, demande une scission.
- **T<NNN+2>** — [<date>] Penser au rate limiting sur /publish (apparu lors du clarify de la feature de publication Telegram).

-->
