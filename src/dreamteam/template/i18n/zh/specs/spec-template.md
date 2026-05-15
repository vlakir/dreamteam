---
translated_from: i18n/ru/specs/spec-template.md
source_hash: 0f45d2d1435c67a85ab50b0aa1d9f10e3c089615ee91c53712e6b80a55e4513c
translation_engine: claude-opus-4-7
translation_date: 2026-05-15
---
# Spec：<功能名称>

**状态：** Draft | Clarified | Analyzed | In Progress | Done
**创建日期：** <YYYY-MM-DD>
**相关文档：** <如有，指向 DECISIONS、其他 specs 的链接>

---

## 1. Overview

<!-- 关于功能的 2-4 句话。是什么、为何需要。不写技术细节 ——
     以产品经理而非工程师的口吻书写。 -->

## 2. User Stories

<!-- 场景格式：
     「作为 <角色>，我想要 <动作>，以便 <目标>。」

     对于没有明确用户的项目（脚本、基础设施、硬件）—— 改用
     「使用场景」，描述功能适用的情形。
-->

- ...

## 3. Functional Requirements

<!-- 系统**必须**能做什么。使用「必须 / 可以 / 不得」的措辞 ——
     以保持明确。 -->

- 必须：…
- 可以：…
- 不得：…

## 4. Success Criteria

<!-- 可衡量的成功条件。具体数字、时延、行为。
     差：「跑得快」。
     好：「典型请求响应 < 200 ms」。 -->

- ...

## 5. Key Entities

<!-- 功能所操作的实体和数据。不写 DB schema 和 API —— 只在概念
     层面：是哪些对象、关键字段是什么、彼此如何关联。
-->

- ...

## 6. Assumptions & Constraints

<!-- 我们视为给定的内容 / 限制解决方案的内容。
     示例：
     - 目标平台 —— Raspberry Pi Zero W (ARMv6)。
     - 用户始终为一个，无并发访问。
     - 外部 API 有每分钟 60 个请求的限制。
-->

- ...

## 7. Out of Scope

<!-- 此功能**有意**不包含的内容。Scope-creep 的防线。 -->

- ...

---

## Clarify（由 Claude 填写）

<!-- Claude 重读 spec，针对盲点提出反向问题。类别：auth、
     validation、errors、edge cases、performance、安全、
     integrations。开发者的答案被回缝到上方相应的章节。 -->

### Open questions

- ...

### Resolved（带答案）

- ...

---

## Analyze（由 Claude 填写）

<!-- Claude 阅读 spec（如有 plan，也读 plan），寻找矛盾、不一致、
     遗漏、技术不可能。

     带标记的 Issues 列表：
     - 🔴 Critical —— 实现开始前修复。
     - 🟡 Warning —— 讨论，可能修复。
     - 🟢 Note —— 备查。
-->

- ...
