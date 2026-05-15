---
translated_from: i18n/ru/BACKLOG.md
source_hash: 97561a99e58717c8b3c1493b0669d8e69849ccff9ed8694c913846ee8908efb1
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Backlog

存放想法、旁支发现以及「以后该修一下」的事项的停车场。

**规则：** 如果在做当前任务时，Claude 或开发者注意到与任务无关的
内容 —— 它进入这里，而不是当前 commit。这是抵御 scope creep 的
防线。

这**不是正式的任务追踪器**，没有 deadline 和指标 —— 它是想法的
停车场。但**顺序是有意义的**：上方 —— 计划近期处理的内容，下方
—— 不那么紧急的（默认 FIFO，可以把高优先级提到顶部）。从 backlog
拿出某项进入工作 —— 它成长为任务或 spec（`specs/T<NNN>-…`），
并从这里删除。

## 格式

`- **T<NNN>** —— [<发现日期>] <简短描述> —— <可选：上下文 / 从哪里冒出来>`

ID 在创建时分配；新 ID =
`max(BACKLOG.md、BOARD.md 与 CHANGELOG.md 中已有的 T-ID) + 1`。
ID 不重复使用，且在任务于 BACKLOG 与 BOARD 之间流动时保持不变；
release 之后，任务进入 `CHANGELOG.md`（带同样的 T-ID），这保证
ID 在 release 之间的唯一性。

## Items

<!-- 示例（填写模板时删除）：

- **T<NNN>** —— [<日期>] 日志在 stdout 和文件中重复 —— 看看 logging 配置。
- **T<NNN+1>** —— [<日期>] 函数 `parse_post` 增长到 80 行，需要拆分。
- **T<NNN+2>** —— [<日期>] 考虑给 /publish 加 rate limiting（在 Telegram 发布功能的 clarify 中冒出来）。

-->
