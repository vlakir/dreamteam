---
translated_from: i18n/ru/BOARD.md
source_hash: a34bdadb4bacaae4c37715eff6d323c0c0552189b61a1c1d266c8c75927febb0
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Board

单 markdown 文件上的轻量 Kanban 替代方案：三列（To Do / Doing /
Done），纳入 git 管理，无需外部服务和工具。

## 与其他文件的关系

- `BACKLOG.md` —— 想法与旁支发现的长队列。「以后再想」、「现在不
  做」掉到这里。Scope 的停车场。
- `BOARD.md`（本文件）—— 活跃的工作流。我们已经拿起或即将拿起的
  任务。
- `specs/T<NNN>-*/spec.md` —— BOARD 中的大任务在被发现为 >1 天
  的功能时成长进入的位置。

任务的生命周期：`BACKLOG.md` 中的想法 → 成熟 → 在此挪到 `To Do`
→ 进入工作（`Doing`）→ 关闭（`Done`）→ release 之后进入
`CHANGELOG.md`（条目必须包含 T-ID），从这里删除。**`CHANGELOG.md`
是已完成任务 T-ID 的唯一持久化存储**，没有它，「ID 不重用」的
规则就会失效。

## 任务格式

每个任务 —— `- **T<NNN>** —— <简短描述>`。ID 在创建时分配：
新 ID = `max(BOARD.md、BACKLOG.md 与 CHANGELOG.md 中已有的 T-ID) + 1`。
ID 永不重用。ID 在 `BOARD.md` 与 `BACKLOG.md` 之间共享 —— 在两者
之间流动时保持不变；release 之后任务落入 `CHANGELOG.md`，带同样
的 T-ID，这保证 release 之间编号的唯一性。

分支名：`T<NNN>-<slug>`（不带 `fixes/` / `feature/` 等 namespace
—— ID 本身已提供识别）。PR 名：`T<NNN>: <title>`。大型功能的
规格：`specs/T<NNN>-<slug>/spec.md`。

可按口味添加：

- 拿起日期的标签，
- 指向 spec 的链接，
- 分支名。

示例：

```
- **T<NNN>** —— Telegram 中的 post 预览
  (`specs/T<NNN>-telegram-preview/`, 分支 `T<NNN>-telegram-preview`)。
```

---

## To Do

<!-- 准备好被拿起的事项。默认 FIFO 队列，可以把高优先级提到顶部。 -->

<!-- 任务条目格式为 `- **T<NNN>** —— 描述`。见上方「任务格式」章节。 -->

## Doing

<!-- 现在正在做的。保持简短：每个开发者最多 1-2 个任务，否则会
     失焦（Kanban 经典的 WIP-limit 规则）。 -->

- ...

## Done

<!-- 已关闭、等待在下一次 release 或显著节点移入 CHANGELOG.md
     的任务。移入之后 —— 清空。 -->

- ...
