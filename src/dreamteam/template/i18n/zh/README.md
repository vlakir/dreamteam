---
translated_from: i18n/ru/README.md
source_hash: 6cbcb2749f1ac3d91c54f37a9d58d667a6b46afb505129c142e310d7e61b76b1
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# {{ project_name }}

{{ project_description }}

<!-- 上面 1-3 句由 `dreamteam init` 的回答填充。可按需扩展。
     架构决策记录在 DECISIONS.md，历史记录在 CHANGELOG.md。 -->

## Quick start

```bash
uv sync                       # 创建 .venv 并安装依赖
uv run python src/main.py     # 运行
```

## 依赖

```bash
uv add <pkg>                  # runtime
uv add --dev <pkg>            # dev
```

## Push 前检查

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy <代码路径>
```

三项都必须以 0 错误通过。绕过手段（`# noqa`、`# type: ignore`、
扩展 `ignore` 段）—— 仅在事先同意的情况下使用。

## 项目结构

- `src/` —— 源码根目录。
- `CONCEPT.md` —— 项目的初始愿景（不可变）。
- `DECISIONS.md` —— 带理由的架构决策（ADR-Lite）。
- `BOARD.md` —— 工作 Kanban 看板（To Do / Doing / Done）。
- `BACKLOG.md` —— 想法与旁支发现的停车场。
- `CHANGELOG.md` —— 显著变更的日志。
- `specs/` —— 大型功能的规格说明。
- `CLAUDE.md` —— Claude（Claude Code）的项目规则。

## 方法论

项目由模板 [vlakir/dreamteam](https://github.com/vlakir/dreamteam)
创建。方法论的详细描述（scope discipline、针对大型功能的
spec/clarify/analyze 仪式、pre-push 把关）—— 见模板仓库。

<!-- 下方添加项目特定章节：API、部署、数据库 schema、模块文档、
     联系方式等。 -->
