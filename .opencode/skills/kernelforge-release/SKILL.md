---
name: kernelforge-release
description: 只读审查 KernelForge 分支、PR、GitHub Actions、Required Checks、Rulesets 和发布产物。
---

## 触发条件

涉及 PR 审查、CI 状态、规则集、版本、Release、发布 SHA256 或远端权限时使用。

## 执行流程

1. 先确认当前分支、授权范围和远端目标；优先使用只读 GitHub MCP 或已有 `gh` CLI。
2. 核验 required checks、Rulesets、工作流权限、版本来源和产物摘要。
3. 对远端写入、发布、合并和推送明确停住并要求独立授权。
4. 记录查询、时间、退出码、权限和无法验证的项目。

## 验收标准

- 本技能不授予远端写入权限，不自动创建 PR、Release、评论、标签或规则集。
- 发布结论必须有可追溯版本和 SHA256 证据。
