# Template development board

Kanban-доска **разработки самого шаблона** `vlakir/dreamteam`. Этот
файл — мета-документ; в derived projects он **удаляется** (см.
`rm TEMPLATE-*.md` в `README.md`).

Структура и правила — те же, что и у пользовательского `BOARD.md`:
три колонки (To Do / Doing / Done), один-два WIP в Doing, FIFO в
To Do (можно поднимать приоритетное).

**Scope правила нумерации:** `max()` для T-ID считается по
`TEMPLATE-BACKLOG.md`, `TEMPLATE-BOARD.md` и
`TEMPLATE-CHANGELOG.md` (не по default-name файлам).

---

## To Do

- **T001** — Реализовать защиту `main` через Branch Protection Rules.
  Серверный «второй слой» в дополнение к локальному `hooks/pre-push`.
  Платформо-специфично; для GitHub:

  ```bash
  gh api repos/<owner>/<repo>/branches/main/protection -X PUT \
    -F required_pull_request_reviews.required_approving_review_count=0
  gh repo edit <owner>/<repo> \
    --allow-squash-merge \
    --allow-merge-commit=false \
    --allow-rebase-merge=false
  ```

  На других хостингах (GitLab, GitFlic, Forgejo) — аналоги через UI
  или API. Acceptance: прямой `git push origin main` отклоняется
  сервером, merge PR возможен только через Squash and merge.

## Doing

<!-- Максимум 1-2 задачи. -->

## Done

<!-- Закрытые задачи, ждущие переноса в TEMPLATE-CHANGELOG.md
     при следующем релизе. После переноса — очищаем. -->
