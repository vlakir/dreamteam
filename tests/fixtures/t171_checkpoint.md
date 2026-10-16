# T171 — checkpoint независимых тестов (до интеграции backend)

Это **НЕ приёмка** и не зелёный gate. Тесты написаны независимо от реализации,
writer base: `82583bb1ea3b0658182286405f6ce0314bf4708b` (spec checkpoint).
Ни backend src, ни версии, ни bundle/docs/BOARD в этот diff не включены.
Legacy-preservation assertions существующих тестов пока не изменены; решать
только после интеграции, сохраняя полезные проверки verified transfer.

## Команды и результаты на devbox

Своя `.venv`, `uv sync --frozen`. Root:
`/home/vlakir/programming/dreamteam/.worktrees/T171-tests`.
Ни оригинальный calque, ни другой real project не читались/не запускались.

```bash
VIRTUAL_ENV="$ROOT/.venv" uv run --project "$ROOT" --active ruff format \
  --check --no-respect-gitignore "$ROOT/tests/test_t171_migration.py" \
  "$ROOT/tests/fixtures/t171_crash_driver.py"
# PASS: 2 files already formatted

flock /tmp/dreamteam-T171-pytest.lock env VIRTUAL_ENV="$ROOT/.venv" \
  uv run --project "$ROOT" --active pytest -c "$ROOT/pyproject.toml" \
  "$ROOT/tests/test_t171_migration.py" --no-cov --tb=no -rN
# 84 failed, 7 passed, 2 copier deprecation warnings; 68.49s
```

Ни skip, ни xfail, ни suppression не добавлены. `--no-cov` только для targeted
pre-integration diagnostics; полный coverage/gates остаётся обязанностью лида.
Probe fake binary — настоящий executable subprocess в изолированном PATH;
дом/state/config/cache отдельные tmp dirs, платные API/ключи не нужны.
Timeout проверяется настоящим bounded subprocess; SIGKILL driver выполняется
в отдельном процессе. На этой базе `migration_store` ещё отсутствует, поэтому
реальный recovery/crash outcome НЕ проверен и не заявляется как успешный.

## Точный ожидаемый red inventory на этой базе

В актуальном `tests/test_t171_migration.py` собрано **91** case. Ожидаются красные
**ВСЕ 84 case, кроме следующих семи точных node IDs** (префикс
`tests/test_t171_migration.py::`):

1. `test_legacy_dryrun_does_not_create_recovery_or_advance_answers[apply]`
2. `test_required_symlinks_block_without_reading_or_modifying_outside[source-leaf-update]`
3. `test_required_symlinks_block_without_reading_or_modifying_outside[source-parent-update]`
4. `test_required_symlinks_block_without_reading_or_modifying_outside[destination-leaf-update]`
5. `test_required_symlinks_block_without_reading_or_modifying_outside[destination-parent-update]`
6. `test_worktrees_git_and_external_links_are_excluded_and_parent_retained`
7. `test_snapshot_fixture_records_bytes_modes_and_dangling_links_without_recursion`

Ожидаемый red = новые AC ещё не реализованы в spec-only базе: runtime gate,
verified source deletion, BOTH, unsupported blockers, migration conflict
completion, private recovery, fault/crash/replay и native absent dry-run mkdir.
Это классификация исходного checkpoint, не разрешение оставить red после
интеграции. Новый fail на integrated backend требует самостоятельного анализа:
тест не менять только ради зелёного.

## Контракт/оставшиеся проверки

- Согласованный seam: `dreamteam.migration_store.checkpoint(event, operation_id)`;
  `recovery_prepared`, `target_applied`, `target_verified`, `legacy_removed`,
  `before_completion`, `completed`; первые target/delete события до journal ack.
- Публичный recovery: `dt migration-recover ROOT [--rollback]`; private store
  `$XDG_STATE_HOME/dreamteam/migrations` (или `~/.local/state/...`). Тесты не
  фиксируют layout journal. Actual syscall fault unit tests адресуют временные
  replace/unlink отдельно от checkpoint exceptions.
- Historical fixture рендерит **реальный bundled tag 1.7.0**, с оригинальными
  architect_model answers inherit/opus/sonnet/haiku до normalization. Не строит
  legacy template из текущего OpenCode template.
- После интеграции: все 91 case, существующие native regressions и integration
  update/apply, full gates/coverage/review. AC17 five-language init и AC18 build/
  install/no-scan не выдаются за проверенные этим файлом.
- Репетиция пока только процедура/шаблон `t171_rehearsal.md`. Запуск на реальной
  изолированной копии и финальный фактический отчёт — после интеграции лидом.
