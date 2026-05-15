---
translated_from: i18n/ru/README.md
source_hash: f96c2ff264d28425416521155c98b10324520cd825e9ded1c0cbe5f3a8289568
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
# {{ project_name }}

{{ project_description }}

<!-- 上面 1-3 句由 `dreamteam init` 的回答填充。可按需扩展。
     架构决策记录在 DECISIONS.md，历史记录在 CHANGELOG.md。 -->

## Quick start

依赖与环境管理器：**`{{ pm_name }}`**（在 `dreamteam init` 时选择）。

```bash
{{ pm_install }}                       # 安装依赖
{{ pm_run }}python src/main.py     # 运行
```

## 依赖
{% if package_manager == 'uv' %}
```bash
uv add <pkg>                  # runtime
uv add --dev <pkg>            # dev
```
{%- elif package_manager == 'poetry' %}
```bash
poetry add <pkg>              # runtime
poetry add --group dev <pkg>  # dev
```
{%- elif package_manager == 'pdm' %}
```bash
pdm add <pkg>                 # runtime
pdm add -dG dev <pkg>         # dev
```
{%- elif package_manager == 'hatch' %}
Hatch 通过 `pyproject.toml` 管理依赖。Runtime —— 添加到
`[project.dependencies]`。Dev —— 添加到
`[tool.hatch.envs.default.dependencies]`。修改后：
`hatch env prune && hatch env create`。
{%- else %}
```bash
.venv/bin/pip install <pkg>   # 之后将该包手动加入 pyproject.toml 的 [project.dependencies]
```
{%- endif %}

## Push 前检查

```bash
{{ pm_run }}ruff check .
{{ pm_run }}ruff format --check .
{{ pm_run }}mypy <代码路径>
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
