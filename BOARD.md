# Board (dreamteam package)

Kanban-доска разработки `dreamteam`-пакета (To Do / Doing / Done),
один-два WIP в Doing, FIFO в To Do (можно поднимать приоритетное).

**Scope правила нумерации:** `max()` для T-ID считается по
`BACKLOG.md`, `BOARD.md` и `CHANGELOG.md` этого репо.

В derived projects — свой `BOARD.md` (из `src/dreamteam/template/`).

---

## To Do

<!-- Задачи готовые к взятию. Текущий backlog — в `BACKLOG.md`. -->

## Doing

- **T011** — Опубликовать `dreamteam` v1.0.0 на PyPI (hybrid:
  `twine check` для validation + `uv publish` для upload).

  **Готово к публикации:** wheel и sdist собраны
  (`dist/dreamteam-1.0.0-py3-none-any.whl` + `.tar.gz`),
  `uv run twine check dist/*` → **PASSED** на оба artefacts,
  smoke-test через `uvx --from <wheel>` пройден.

  **Требуется от Разработчика** (PyPI credentials):
  ```bash
  # 1. TestPyPI (sanity check)
  UV_PUBLISH_TOKEN=<test-token> \
    uv publish --publish-url https://test.pypi.org/legacy/

  # 2. Verify install из TestPyPI
  uvx --index https://test.pypi.org/simple/ \
      --extra-index https://pypi.org/simple/ \
      --from dreamteam==1.0.0 dreamteam --version

  # 3. Real PyPI
  UV_PUBLISH_TOKEN=<prod-token> uv publish
  ```

## Done

- **T010** — Добавлен MIT License (`LICENSE` файл, classifier,
  README, ADR). Снимает блокер T011 (PyPI publish). В CHANGELOG.md
  → [Unreleased] → Added.
- **T012** — Создан `CLAUDE.md` в корне репо для разработки `dreamteam`-
  пакета (отдельный документ от `src/dreamteam/template/CLAUDE.md`,
  который попадает в derived проекты через `dreamteam init`).
  В CHANGELOG.md → [Unreleased] → Added.

<!-- Закрытые задачи, ждущие переноса в CHANGELOG.md при следующем
     релизе. После переноса — очищаем. -->
