---
translated_from: i18n/ru/CLAUDE.md
source_hash: 5b86cdd58929d29c1432f734d68d9afec73e4b4c17937907c769d6453624ed1d
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Claude 的项目规则

本文件是 Claude（Claude Code）的项目规则。全局规则
（`~/.claude/CLAUDE.md`）始终生效；这里仅记录针对本项目的特定内容。

## 会话开始时需要阅读的内容

1. `CONCEPT.md`（如有）—— 项目的初始愿景，不可变文档。数月之后仍可
   作为锚点。
2. `README.md` —— 当前描述 / quick start / 项目状态。
3. `DECISIONS.md` —— 已经做出的架构决策。
4. `BACKLOG.md` —— 排队中的事项。
5. 在做大型功能时 —— 对应的 `specs/T<NNN>-*/spec.md`。

## 撰写 `CONCEPT.md` 的仪式（针对新项目）

新项目开始时，Claude 协助开发者撰写 `CONCEPT.md` —— 初始愿景的
不可变文档。这是反向提问的仪式，类似于针对大功能 spec 的 `clarify`：

1. 开发者写出第一稿（或仅仅提出想法）。
2. Claude 针对盲点提出反向问题：
   - **目标：** 项目解决什么痛点 / 任务？
   - **用户：** 是谁，在什么场景下？
   - **核心功能：** MVP 最小集 vs. nice-to-have？
   - **Out of scope：** 我们**有意**不做的事（核心章节 —— 从第一天
     就抵御 scope creep 的防线）。
   - **约束与假设：** 平台、技术栈、负载、对环境 / 用户的假设。
3. 答案被缝入 `CONCEPT.md`，标注创建日期。
4. **填写完成后 `CONCEPT.md` 不再修改。** 当前状态记录在
   `README.md`。如果概念发生根本变化（罕见，pivot）—— 新版本放入
   `concepts/v2-...md`、`v3-...md`（ADR-pattern，但用于概念）。

`CONCEPT.md` 的填写在通过 `dreamteam init` 创建项目时（Claude 进行
反向提问）或之后手动完成。

## 项目描述

{{ project_description }}

## 技术栈

**模板的基础栈（适用于 Python 项目）：**
- Python 3.14+（`pyproject.toml` 中的 `requires-python`）。
- 依赖与环境管理器：`uv`（Astral 出品，速度快）。
- Linter：`ruff`（规则 `select = ["ALL"]`，搭配固定的 `ignore`）。
- Type checker：`mypy`，`mypy_path = "src"`。
- 测试栈：`pytest` + `pytest-cov` + `pytest-asyncio`。Coverage
  阈值 ≥ 80% 行覆盖率（针对 `src/`，`--cov-fail-under=80`，在
  `[tool.pytest.ini_options]`）。
- **源码根目录 —— `src/`**（始终，所有项目都如此）。
- 测试 —— 位于根目录下的 `tests/`（被 `ruff` 排除，但 `pytest`
  通过 `testpaths = ["tests"]` 找到它们）。

**典型命令：**
- `uv sync` —— 安装依赖（首次运行时创建 `.venv`）。
- `uv add <pkg>` / `uv add --dev <pkg>` —— 添加 runtime / dev
  依赖。
- `uv run python ...` —— 在 `.venv` 中运行，无需激活。
- `uvx <tool>` —— 运行 CLI 工具，无需本地安装。

每次 `git push` 之前，**四项**必须以 0 错误通过的检查：
1. `uv run ruff check .`
2. `uv run ruff format --check .`
3. `uv run mypy <code>`
4. `uv run pytest`（包含 coverage 阈值 ≥ 80%）。

**作为一条链一次运行**，任何一步失败都会中断 commit：

```bash
uv run ruff check . && \
uv run ruff format --check . && \
uv run mypy <code> && \
uv run pytest && \
git add -A && git commit -m "..." && git push
```

**Catch-it-at-the-output：** 如果上一条命令的输出中看到 `FAILED`、
`Error`、`1 failed` 或类似标记 —— **不要继续**，检查原因。也不要
掩盖 exit code：`pytest | tail -5` 返回的是 `tail` 的 exit code，
而不是 `pytest` 的 —— 失败会悄悄混入 `git commit`。

未经开发者明确讨论，不得使用 `# noqa` / `# type: ignore` /
扩展 `ignore` 段。详见全局 `~/.claude/CLAUDE.md` 的「Linters」与
「Testing」章节。

## Git 工作流

流程的基础规则（在本项目中始终适用）：

- **任务有编号。** `BOARD.md` / `BACKLOG.md` 的每条记录有 ID
  `T<NNN>`；分支为 `T<NNN>-<slug>`；PR 为 `T<NNN>: <title>`。
  例外 —— 修改规则本身的方法论 PR（无 `T`-ID）。
- **禁止直接 push 到 `main` / `master`。** 任何变更 —— 通过
  feature 分支和 PR/MR。
- **一个 PR —— 一个 commit。** 在 feature 分支上可按工作需要随意
  commit，merge 前进行 squash。
- **每个 PR 在 merge 前都要经过 code review。** 默认 —— Claude
  （依据 checklist 进行 self-review：scope / 架构 / 代码 /
  linter / 文档 / 约定 / 安全）。偶尔 —— 由开发者完成。
- **不要忽视第三方 review。** 像 `qodo-code-review` 这样的 bot
  必须阅读、分析、与开发者讨论；决定要记录（采纳 / 弃用 / 推迟）。

## 规划纪律

不做 Scrum 仪式（sprints、story points、velocity、burndown）。
只保留有用的元素：

- **基于 milestone 的版本管理。** `CHANGELOG.md` 中的
  `[Unreleased]` 持续累积。切换到新版本 `[N.M.0]` 的时机是
  **有意义地完成**（软标准）：引入了显著变化，或一组逻辑相关的
  任务收尾，或累积了「足够」的内容可作为保存点。最终由开发者决定；
  没有形式化的指标 —— 形式化指标本身违背「无 Scrum-cargo」原则。
  版本格式 —— Keep a Changelog（`## [N.M.0]`，无 `v`-前缀）。
- **Retrospective 作为仪式** 在 milestone 关闭之后进行。三点式
  简短复盘：
  - 顺利的（work-as-expected，或令人愉快的意外），
  - 不顺利的（bundling、滑点、不必要的开销），
  - 方法论调整（在 `~/.claude/CLAUDE.md` / 项目 `CLAUDE.md` /
    模板中需要修改的内容）。
  位置：`CHANGELOG.md` 中对应版本条目内的 **`### Retrospective`
  小节**。不是单独文件 —— retro 与 milestone 紧密相关，便于一起
  阅读。
- **Acceptance criteria** 对于大于一行编辑的任务是必备项 —— 直接
  记录在 `BOARD.md` / `BACKLOG.md` 中的短块
  （`Acceptance: <为了使任务被视为关闭，必须达到什么>`），或对于
  大型功能记录在 `specs/T<NNN>-*/spec.md` 中。没有明确的 acceptance
  criteria，任务不被视为成熟到可以从 `BACKLOG → BOARD → Doing` 推进。
- **WIP-limit** 在 `BOARD.md → Doing`：最多 1-2 个任务。更多 ——
  失焦（经典 kanban 规则）。

如果开发者配置了全局 `~/.claude/CLAUDE.md` —— 那里有这些规则的扩展
版本（章节「不要直接 push 到 main」、「一个 PR —— 一个 commit」、
「每个 PR 的 code review」）。上面的简短版本已是自洽的来源。

## 项目特定规则

## 在本项目中通常进入 BACKLOG.md 而非当前编辑的内容

