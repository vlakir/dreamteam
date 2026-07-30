---
translated_from: i18n/ru/CLAUDE.md
source_hash: 7eaae69f3591aa6e08d3aaa12ef0b3f0ac2158db49be286799b7c18e5848c934
translation_engine: claude-opus-4-8
translation_date: 2026-07-30
---
{%- set pm_run = {'uv': 'uv run ', 'poetry': 'poetry run ', 'pdm': 'pdm run ', 'hatch': 'hatch run ', 'pip': '.venv/bin/'}[package_manager] -%}
{%- set pm_install = {'uv': 'uv sync', 'poetry': 'poetry install', 'pdm': 'pdm install', 'hatch': 'hatch env create', 'pip': 'python -m venv .venv && .venv/bin/pip install -e .[dev]'}[package_manager] -%}
{%- set pm_name = package_manager -%}
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

**结构是问卷，而非 contract。** 上面的各节（目标 / 用户 / 核心功能 /
Out of scope / 约束）是**针对空白 `CONCEPT.md` 的 leading questions**，
而非最终文档的必需形式。如果项目已有任意形式的成型 `CONCEPT.md` /
需求文档 / vision —— Claude **原样接受**，并针对其内容的盲点进行
`clarify`，**不要求**将其套进模板标题。仪式唯一的必需环节是
**clarify**（反向提问）。`Out of scope` 仍是最有价值的章节（抵御
scope creep），但可以在既有文档中以任意形式表达。不可变性不变量
（固化后不再编辑）在任何情况下都保持。

`CONCEPT.md` 的填写在通过 `dreamteam init` 创建项目时（Claude 进行
反向提问）或之后手动完成。

## 项目描述

{{ project_description }}

## 技术栈

**模板的基础栈（适用于 Python 项目）：**
- Python 3.14+（`pyproject.toml` 中的 `requires-python`）。
- 依赖与环境管理器：**`{{ pm_name }}`**（在 `dreamteam init` 时
  通过 `package_manager` prompt 选择；备选：`uv` / `poetry` /
  `pdm` / `hatch` / `pip`）。
- Linter：`ruff`（规则 `select = ["ALL"]`，搭配固定的 `ignore`）。
- Type checker：`mypy`，`mypy_path = "src"`。
- 测试栈：`pytest` + `pytest-cov` + `pytest-asyncio`。Coverage
  阈值 ≥ 80% 行覆盖率（针对 `src/`，`--cov-fail-under=80`）。该阈值
  由 pre-push gate 和 CI 里的**显式命令**强制执行，而不是放在默认
  `addopts` 里 —— 默认的 `pytest` 刻意保持轻量（见下文「重量级测试运行
  —— 通过互斥包装器」）。
- **源码根目录 —— `src/`**（始终，所有项目都如此）。
- 测试 —— 位于根目录下的 `tests/`（被 `ruff` 排除，但 `pytest`
  通过 `testpaths = ["tests"]` 找到它们）。

**典型命令（针对所选 `{{ pm_name }}`）：**
{%- if package_manager == 'uv' %}
- `uv sync` —— 安装依赖（首次运行时创建 `.venv`）。
- `uv add <pkg>` / `uv add --dev <pkg>` —— 添加 runtime / dev
  依赖。
- `uv run python ...` —— 在 `.venv` 中运行，无需激活。
- `uvx <tool>` —— 运行 CLI 工具，无需本地安装。
{%- elif package_manager == 'poetry' %}
- `poetry install` —— 安装依赖（首次运行时创建 venv）。
- `poetry add <pkg>` / `poetry add --group dev <pkg>` —— 添加
  runtime / dev 依赖。
- `poetry run python ...` —— 在 poetry venv 中运行，无需激活。
- `poetry env activate` —— 打开激活了 venv 的子 shell。
{%- elif package_manager == 'pdm' %}
- `pdm install` —— 安装依赖（首次运行时创建 `.venv`）。
- `pdm add <pkg>` / `pdm add -dG dev <pkg>` —— 添加 runtime /
  dev 依赖。
- `pdm run python ...` —— 在 `.venv` 中运行，无需激活。
{%- elif package_manager == 'hatch' %}
- `hatch env create` —— 创建带 dev-deps 的 `default`
  environment。
- 依赖在 `pyproject.toml` 的
  `[tool.hatch.envs.default.dependencies]` 中编辑。
- `hatch run <cmd>` —— 在 `default` env 中运行命令，无需激活。
- 脚本定义在 `[tool.hatch.envs.default.scripts]` 中，通过
  `hatch run <script>` 调用。
{%- else %}
- `python -m venv .venv && .venv/bin/pip install -e .[dev]` ——
  创建 venv 并安装 dev 依赖。
- `.venv/bin/pip install <pkg>` —— 安装包（之后手动将其加入
  `pyproject.toml` 的 `[project.dependencies]`；pip 不会自动
  更新清单）。
- `.venv/bin/python ...` 或激活 venv（`source .venv/bin/activate`）
  然后运行 `python ...`。
{%- endif %}

每次 `git push` 之前，**四项**必须以 0 错误通过的检查：
1. `{{ pm_run }}ruff check .`
2. `{{ pm_run }}ruff format --check .`
3. `{{ pm_run }}mypy <code>`
4. `scripts/pytest-guard.sh --cov=src --cov-report=term-missing --cov-fail-under=80`
   —— 带 ≥ 80% coverage 阈值的完整运行，**通过互斥包装器**（见下文
   「重量级测试运行 —— 通过互斥包装器」）。

**作为一条链一次运行**，任何一步失败都会中断 commit：

```bash
{{ pm_run }}ruff check . && \
{{ pm_run }}ruff format --check . && \
{{ pm_run }}mypy <code> && \
scripts/pytest-guard.sh --cov=src --cov-report=term-missing --cov-fail-under=80 && \
git add -A && git commit -m "..." && git push
```

**Catch-it-at-the-output：** 如果上一条命令的输出中看到 `FAILED`、
`Error`、`1 failed` 或类似标记 —— **不要继续**，检查原因。也不要
掩盖 exit code：`pytest | tail -5` 返回的是 `tail` 的 exit code，
而不是 `pytest` 的 —— 失败会悄悄混入 `git commit`。

未经开发者明确讨论，不得使用 `# noqa` / `# type: ignore` /
扩展 `ignore` 段。详见全局 `~/.claude/CLAUDE.md` 的「Linters」与
「Testing」章节。

## 重量级测试运行 —— 通过互斥包装器

当多个 `git worktree` 共享一台机器时（见下文「在多个 git worktree 中并行
工作」），共享资源是**内存**。完整 / coverage 运行会占用可观的 RSS；两三个
同时跑（旁边还开着重量级 IDE）会叠加成 **OOM 或卡死**。包装器
`scripts/pytest-guard.sh` 通过一个共享的 per-user 锁，把重量级运行在所有
worktree 之间串行化（并发度 1，阻塞等待：第二个运行排队，等前一个释放锁后
自行启动）。只有**启动**被串行化 —— 代码和未提交的会话状态从不被触碰。

**规则 —— 什么走包装器，什么直接跑：**

- **完整 / coverage 运行和 pre-push 测试 gate —— 走包装器**
  （`scripts/pytest-guard.sh …`），而不是裸 runner；尤其是在有并行会话
  存活时。
- **单文件运行**（轻量、一次性）—— 可以直接跑
  （`{{ pm_run }}pytest tests/test_x.py`）；互斥不是必须的。
- **CI —— 直接跑**（隔离的 runner，无可共享）。

**轻量的默认运行。** coverage 被刻意排除在默认 `addopts` 之外（coverage
追踪器会抬高 RSS/CPU）：默认的 `{{ pm_run }}pytest` 保持轻量，便于反复的
本地迭代。≥ 80% 阈值仍被强制执行 —— 只是改由**显式命令**（上面的 gate 4
和 CI）承担，而不在默认里。

**可选的单次运行内存上限。** 变量 `PYTEST_GUARD_MEM_MAX`（例如 `4G`；`0`
或未设置 —— 关闭）：在带 systemd 会话的 Linux 上，运行会被放进一个带 RSS
限额的临时 cgroup，让失控的测试被 OOM-killer **在它自己的 cgroup 内**杀掉
（该次运行失败，但机器和 IDE 存活），而不是拖垮整个系统。在 Linux/systemd
之外（macOS、Windows、容器）它是 no-op —— 运行仍走互斥。

**跨平台。** `flock` 属于 util-linux（Linux / 类 macOS）。在没有它的地方
（Windows），包装器会**优雅降级**：打印一行提示，直接跑测试（不做串行化），
绝不失败。

## Git 工作流

流程的基础规则（在本项目中始终适用）：

- **任务有编号。** `BOARD.md` / `BACKLOG.md` 的每条记录有 ID
  `T<NNN>`；分支为 `T<NNN>-<slug>`；PR 为 `T<NNN>: <title>`。
  例外 —— 修改规则本身的方法论 PR（无 `T`-ID）。
- **禁止直接 push 到 `main` / `master`。** 任何变更 —— 通过
  feature 分支和 PR/MR。
- **一个 PR —— 一个 commit。** 在 feature 分支上可按工作需要随意
  commit，merge 前进行 squash。
- **关闭任务 —— 在其自身的 PR 中完成。** 将条目从 `BOARD.md →
  Doing` 移到 `Done` 是在该任务 PR 的**同一个 squash commit** 中完成，
  而非单独的 chore-PR（merge 后任务本就 Done —— `BOARD.md` 只是反映
  现实）。PR 边界按任务的逻辑内聚划分；仅为「PR 更短」而拆分相关改动
  是 anti-pattern（额外的 review overhead、消耗 review bot 配额）。
- **每个 PR 在 merge 前都要经过 code review。** 如果项目接入了可用的
  自动 review bot（CodeRabbit、qodo-code-review 或类似，逐一 review
  每个 PR）—— 它即 baseline，**默认不需要 Claude 单独 self-review**。
  Claude 的 self-review 在三种情况下需要：(1) **docs / 方法论** ——
  仅改动 markdown / 规则 / spec 的 PR（bot 对散文 review 较弱）→
  self-review 仍为默认；(2) **非平凡代码** —— 针对风险区（架构、安全、
  复杂 scope）的 targeted deep-review，由开发者请求或 Claude 主动发起；
  (3) **fallback** —— bot 不可用（rate-limit、宕机、合理时间窗内未反馈）。
  self-review checklist：scope / 架构 / 代码 / linter / 文档 / 约定 /
  安全。
- **不要忽视第三方 review。** 像 CodeRabbit / `qodo-code-review`
  这样的 bot 必须阅读、分析、与开发者讨论；决定要记录（采纳 / 弃用 /
  推迟）。

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

## 项目知识存放在哪里（memory-agnostic）

**核心原则：所有 durable 的项目知识都存放在项目内部** —— 在其仓库里
（`CLAUDE.md`、`DECISIONS.md`、`docs/`、`specs/`、`BOARD.md` /
`BACKLOG.md`）。助手的任何**外部**持久记忆层（如果开发者有的话 ——
也可能没有）都**只是可选的副本 / 兜底**；方法论必须在**没有**它时也能
运转。

原因有二：

1. 助手的外部记忆常绑定到某个路径 / 机器，不随工作副本（worktree）与
   平台迁移或共享。
2. 关于项目的知识应当随仓库一起，交给任何克隆它的人。

**规则：**先把事实记入项目文件，之后（如果存在这样的机制）再可选地把它
镜像到外部。「想镜像就镜像，但关于项目的一切都在项目里。」

## 在多个 git worktree 中并行工作

多个任务可以**同时**推进，每个在自己的 `git worktree`（仓库的独立工作
副本，共享 `.git`）里，从而不必在同一个 checkout 里切换分支。这种时刻，
不同文件夹里可能有**多个 Claude 会话**并行工作 —— 每个 worktree 一个。
它们必须彼此知情，不相互冲撞。

**注册表就是内置的 `git worktree list`。**所有 worktree 共享一个
`.git`，所以从任何克隆文件夹执行 `git worktree list` 都会列出全部同级
worktree（路径 + 分支 + HEAD）。不需要自制的注册表文件。

**启动仪式。**会话开始时 —— `git worktree list` +
`git branch --show-current`。如果 worktree 多于一个，旁边**可能有另一个
会话**在别的分支上工作；它的路径和分支是**别人的领地**。

**隔离（硬性）：**

- 一个 worktree = 一个任务 = 一个分支。不要 checkout、commit、rebase 或
  push 到别人的分支；不要编辑别人 worktree 路径下的文件。
- gate 和测试从**自己的**环境里跑。继承来的虚拟环境变量可能指向**另一个**
  文件夹的环境 —— 激活 / 指向你自己的，否则你是在错误的环境里跑检查。
- **共享的「从顶部追加」日志**（`DECISIONS.md`、`CHANGELOG.md`、
  `BOARD.md`、`BACKLOG.md`）在两个并行任务合并时几乎总会冲突。只碰**你
  自己任务的条目**；PR 前务必 `git fetch` + `git rebase` 到最新的
  `main` 并解决冲突（通常 —— 保留别人的条目，写入你自己的）。不同任务的
  代码通常干净合并 —— 冲突的正是日志文本。

**worktree 生命周期：**

- 创建：`git worktree add ../<repo>-T<NNN> -b T<NNN>-<slug>`（或基于已有
  分支）。
- PR 前：`git fetch` → 到最新 `main` 上 rebase → squash 成一个 commit
  （「一个 PR 一个 commit」规则）→ push → PR → review。
- 合并后：`git worktree prune` + 删除本地分支。

**收拾好自己的东西 —— 先征得许可。**一个任务或一组相关任务完成后，
**提议移除克隆文件夹**（worktree）。但克隆可能含有需要的东西（未提交的
工作、本地笔记、产物），所以 `git worktree remove` —— **只有在开发者
明确说「可以」之后**才做。不要默默删除。主 checkout 和别人的 worktree
在收拾时不碰。

**共享 dev 服务 —— 每个用户一个实例。**如果启动应用会拉起共享资源
（数据库、容器、本地配置、被占用的端口），两个并行副本会**共用**它们
—— 迁移 / 状态发散、争抢端口。要预警，并演示如何隔离（每个 worktree
一份单独的 DB / 配置 / 端口）。

**记忆在文件夹之间并不共享。**助手基于文件的自动记忆（若有）通常绑定到
cwd 路径：在克隆文件夹**内部**启动的会话得到一份**单独的（空）**记忆，
**看不到**主文件夹的记忆。因此把 durable 知识放在仓库文件里（每个
worktree 都有）—— 见上文「项目知识存放在哪里（memory-agnostic）」。默认
优先从主文件夹启动会话，并通过绝对路径操作 worktree。

## 项目特定规则

## 在本项目中通常进入 BACKLOG.md 而非当前编辑的内容


## 团队角色（架构师 + 设计师）

本项目自带一套可复用的协作机制：主导会话（本会话）、只读的架构师子代理，以及
外部的设计师（Claude Design）。如何调用它们、咨询的仪式，以及「提议 → 由人
拍板 → ADR」的循环，都在一个单独的文件里：

@.claude/team-roles.md
