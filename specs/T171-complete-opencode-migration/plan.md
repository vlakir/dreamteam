# T171 — План исполнения и контракты

Дата: 2026-10-16. Единственная продуктовая задача — BOARD.md T171; Ensemble
задачи отражают её этапы, не создают параллельный backlog. База docs-раунда:
`e32fbe14179588eaa8c8c75d8b61d69809baf758`. Следующий раунд начинается от
интегрированного локального checkpoint, **точный SHA записывает лид перед
выдачей задач**; не использовать main/HEAD как плавающий заменитель.

## Ownership и порядок

| Этап / исполнитель | Исключительное право записи | Критерий передачи |
| --- | --- | --- |
| Docs/spec (migration-spec) | BOARD только T171; specs/T171-complete-opencode-migration/*; новый ADR DECISIONS | Контракт, матрица AC, risks; docs checkpoint, не acceptance |
| Backend | src/dreamteam/cli.py; новый узкий migration-модуль в src/dreamteam/ при необходимости | Общие planner/executor update/apply, preflight/recovery, описанный allowlist; SHA + clean status |
| Tester | tests/test_* migration/update/apply regressions; новые обезличенные fixtures только под tests/ | Независимая матрица AC, fault injection, повтор/rehearsal report без секретов; SHA + clean status |
| Docs/release | README.md, CHANGELOG.md, активные docs/шаблоны и их переводы; version metadata/lock/bundle только при release cut | Публичный safety/recovery контракт, clean init 5 языков, проверка истории; SHA + clean status |
| Architect/reviewer | Нет (worktree:false) | Анализ интерфейса/рисков и независимое review с точными ссылками |
| Лид | Интеграционная ветка; T171 acceptance/BOARD после передачи ownership | Гейты, review, результаты, release/PR по правилам проекта |

Каждый writer — новый отдельный worktree. До edits проверить hostname devbox,
clean state и точный согласованный base SHA. Не reset чужой/грязный checkout.
Backend и tester напрямую согласуют точки fault injection, категории blockers,
exit codes и privacy contract до параллельной работы. Префиксы новых тестовых
файлов согласовать, не поручать один файл двум авторам. Перед shutdown получить
SHA, проверить scope/dirty; затем shutdown и team_merge. Новая итерация — новый
уникальный worker от checkpoint; unfinished work сохранить. Done != acceptance.

## Последовательность реализации

1. **Backend contract/preflight.** Зафиксировать allowlist переносимых файлов,
   settings/hooks и способ верификации. Выделить migration detection для BOTH
   и custom. Локальный --version prerequisite до side effects/prompts; pin
   1.19.0, timeout 5 с; exit 1 без записи при отказе. Не менять init policy.
2. **План и безопасность.** Read-only inventory selected root, merge обоих
   источников, known base для managed update, без ложной базы unmanaged apply.
   Выявить все unsupported/conflicts/unsafe paths до backup или mutation.
   Dry-run показывает действия и безопасные diff только несекретных файлов.
3. **Узкая recovery операция.** Приватные originals + durable journal вне git
   и legacy. Plan/revalidate/stage/apply/verify/delete verified sources/
   finalize answers+completion. Не добавлять generic migration framework.
   Подготовить поддержанную операторскую процедуру восстановления (путь,
   команда либо конкретные безопасные шаги) до передачи tester/docs.
4. **Независимые тесты.** Tester строит AC fixtures без личной конфигурации,
   подменяет executable версии в unit tests, проверяет crash windows и повтор.
   Backend не ослабляет ожидаемые проверки ради текущей реализации.
5. **Публичная документация/active cleanup.** Docs writer удаляет только
   действующие зависимости/ложные hints Claude CLI/Max. Исторические ADR,
   bundle tags и provenance сохраняются; Anthropic API остаётся. Описать
   prerequisite, blockers, recovery, force и no repo-scan при package install.
6. **Репетиция.** На независимой копии реального проекта согласно acceptance;
   сначала доказать изоляцию/редакцию. Оригинал не менять. Проверить успешный
   перенос, второй запуск, injected failure recovery, unsupported intact.
7. **Интеграция/review/gates.** Лид проверяет все diff и сообщения reviewer,
   фиксирует разрешение каждого замечания. Только после зелёного полного
   результата финального коммита stable 2.0.0 / PR / release по политике.

## Контракт backend → tester → docs

- **Вход:** explicit root, команда update/apply, legacy/destination bytes,
  проверенная base metadata где доступна; никаких repo-scans.
- **План:** список относительных безопасных путей, тип операции, происхождение,
  fingerprint, ожидаемый результат, blockers/conflicts без secret values.
- **Выход:** 0 = весь перенос verified + completion; 1 = error/unsupported;
  2 = migration content conflict. Dry-run даёт соответствующий прогноз без
  backup/journal/answers/deletes. Неуспех до apply оставляет весь root неизменным.
- **State:** immutable originals и journal стадий planned/staged/applied/
  verified/completed (названия могут отличаться, семантика обязательна).
  Interrupted != completed. Сверять filesystem перед повтором; unknown state
  блокирует, а не «успешно пропускает». Recovery не уничтожает новые user edits.
- **Privacy:** stdout/stderr/diff и git не содержат secret fixture marker;
  recovery вне git, owner-only; `.git`, worktrees и внешние ссылки untouched.
- **Handoff:** backend сообщает фактический allowlist, path recovery, процедуру
  reconcile/rollback, fault injection seams и safe error categories. Docs не
  обещает ещё неподдерживаемые преобразования и future-version compatibility.

## Гейты (в этом docs-раунде не запускались)

Обязательны `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy src`, `uv run pytest` с порогом покрытия проекта, точечные
integration update/apply/init и все 5 языков, translation source_hash check,
`uv build` и twine check wheel/sdist. Проверить installed wheel, историческую
base 1.7.0 и свежий tag текущей версии в bundle, без duplicate package entries.
Тяжёлые прогоны — под действующим мьютексом/правилами окружения. Если применим
проектный srv pipeline, полный зелёный прогон итогового коммита обязателен
перед merge; не подменять его локальным checkpoint. URL/логи, точные команды,
коммит и отдельный rehearsal report вне секретов фиксируются в acceptance.
