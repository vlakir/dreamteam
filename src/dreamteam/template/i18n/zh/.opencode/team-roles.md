---
translated_from: i18n/ru/.opencode/team-roles.md
source_hash: 313acfd4f704304f9d838f7cd2ca1b2a82eb9e6e0c8f1fef11aab5702f103e54
translation_engine: agent-assisted-migration
translation_date: 2026-10-15
---
# OpenCode 团队角色

负责人协调实现、架构、设计和审查。长期知识保存在 AGENTS.md、CONCEPT.md、
DECISIONS.md、specs、BOARD.md 和 BACKLOG.md 中；外部记忆是可选的。

使用 Ensemble 创建团队，为任务设置真实返回的依赖 ID。每位开发者使用独立的
worktree，明确文件范围和验收标准，先从两到三位成员开始。使用 team_message
直接交流，使用 team_broadcast 发布共同信息。整合前执行测试和审查；done 状态
不代表允许合并到 main。mergeOnCleanup 默认关闭，必须明确整合分支并保留未合并
工作。BOARD.md 和 BACKLOG.md 是项目记录，Ensemble 负责执行状态，不另建待办来源。
独立 worktree 不能消除合并冲突。

@architect 是只读子代理，默认继承调用者的模型，也可配置 provider/model-id。
设计角色可选，可使用视觉模型或单独配置的 MCP 服务，不要求特定供应商或订阅。
更新代理后重启 OpenCode。模型和供应商在用户配置中设置，不提交密钥。仪表盘
显示任务与消息；不假定不同独立团队之间可以直接通信。

标准团队包含九个角色：tech-lead、architect（需求分析与架构）、designer（UX/UI）、frontend、mobile、backend、tester、reviewer 和 devops。所有角色均在 .opencode/agents 中提供，由负责人按任务选择参与者。
