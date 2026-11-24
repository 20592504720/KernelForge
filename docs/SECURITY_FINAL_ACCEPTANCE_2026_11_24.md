# KernelForge 最终安全验收报告（第一阶段至 7.4）

**结论：SCOPED_PASS_WITH_DEFERRED_BLOCKERS（约定范围内通过，保留明确限制）。** 验收完成于 2026-11-24 19:26:21（UTC+8）。本报告归档已执行的验证，不将未测试事项标记为通过。

## 1. 不可变基线

- 功能代码提交：`176834803cdca2310d023ef72351d08af238d131`
- 验收提交：`0a6e702dda6d1851153490ac0aea22814bb06c49`；Tree：`c670eed00c39c21dbeed8ced993e4bf754122042`（仅增加一次性验收请求相对于代码基线的变化）。
- [完整验收 Run 45375493788](https://github.com/20592504720/KernelForge/actions/runs/45375493788)：12/12 成功，0 失败、0 跳过的 Actions Job。最终汇总 job 138410554356 输出 `STAGE1_6_SCOPED_GATES_PASSED_WITH_DEFERRED_BLOCKERS`。
- 开发分支 `stage1/initial-foundation`；main 保持 `77af49c47acbfd384a4e22993797eebfa8d9eee6`，不合并 PR #1。

## 2. 安全整改与检测

前四轮整改记录见 [第一轮](SECURITY_HARDENING_2026_11_24.md)、[第二轮](SECURITY_HARDENING_ROUND2.md)、[第三轮](SECURITY_HARDENING_ROUND3.md)、[第四轮](SECURITY_HARDENING_ROUND4.md) 和 [收尾整改](SECURITY_FINALIZATION.md)。收尾修复 Windows 归档路径及设备别名、Git 参数边界，并新增 CodeQL 实际结果计数。五项新增负向测试已通过。

| 检测 | 结果 | 证据 |
| --- | --- | --- |
| CodeQL | 两次 SARIF 实际结果均为 0 | [PR](https://github.com/20592504720/KernelForge/actions/runs/45334703072) / [Push](https://github.com/20592504720/KernelForge/actions/runs/45334695163) |
| Bandit | 高 0、中 1、低 56、扫描错误 0 | [安全审计](https://github.com/20592504720/KernelForge/actions/runs/45334703123) |
| pip-audit | 锁定开发依赖未发现已知漏洞 | [安全审计](https://github.com/20592504720/KernelForge/actions/runs/45334703123) |
| Gitleaks | 149 个可达提交，0 项发现 | [历史扫描](https://github.com/20592504720/KernelForge/actions/runs/45375493960) |

前三项扫描对应功能代码基线；验收提交仅修改请求标记。扫描零结果不代表不存在任何漏洞，也不代表上游内核全部 CVE 已审查。历史 Code Scanning 告警列表未独立读取。

## 3. 完整回归

| 环境 | 总测试 | 通过 | 条件跳过 | 失败/错误 |
| --- | ---: | ---: | ---: | ---: |
| Linux Python 3.11 | 479 | 479 | 0 | 0 |
| Linux Python 3.12 | 479 | 479 | 0 | 0 |
| Windows Python 3.11 | 479 | 439 | 40 | 0 |
| Windows Python 3.12 | 479 | 439 | 40 | 0 |
| 合计 | 1916 | 1836 | 80 | 0 |

Python 语法、配置、Schema、YAML 与完整软件测试均通过。额外 [Validate](https://github.com/20592504720/KernelForge/actions/runs/45375493832) 四环境通过，不重复计入上表。已重放两份 SM8750 manifest 及历史源码证据；未进行新的 35 项目同步或本地现场审计。Stage 7.4 默认及自定义时间策略通过，报告仍为 `POLICY_TESTED_SOURCE_UNTESTED`、`build_eligible=false`。

## 4. 五组真实 ACK6.1 ARM64 GKI 编译

固定内核 Commit：`498f91c17b0822a09aede17d26a63bf8c6813725`。五份下载的实际 Image 均与构建报告的字节数和 SHA256 一致；Kconfig、ARM64 目标文件、可重定位链接和完整 Image 均通过，报告中未解析 Root hooks 为 0。vmlinux 摘要由 runner 报告，归档未含 vmlinux 本体，未独立重算。

| 组合 | 对象数 | Artifact ID | 独立复核 Image SHA256 |
| --- | ---: | ---: | --- |
| official-susfs-off | 40 | 14912337049 | `9e656ca02cd81174b31ad543ad597ee15e2fa7518f41ea349df8158d2e1abd53` |
| official-susfs-on | 61 | 14912157883 | `f080665340ca6b7e116cb2d6fcfea06bb1ede7d2cb6eca0a9448ca3d22826d07` |
| bakasu-susfs-off | 44 | 14912584813 | `f77b8d000066e68db1116e759b2d579f798de11470648db79440fbc6f4f46801` |
| bakasu-susfs-on | 67 | 14915560681 | `f8657643a71c2a448154ac66ff4505250ba7a095e58980cdc40889a41f228570` |
| bakasu-reviewed-new-susfs-on | 67 | 14914244085 | `5b306d972937c7aed56b7796868c8cbd89b621e5f1ba6a654fc535a4737038aa` |

这些是通用 GKI 编译验证，不是 OnePlus13 真机刷机包。

## 5. 原始证据完整性

全部七份 GitHub Actions ZIP 已实际下载并独立重算 SHA256，与 GitHub 返回的摘要一致。五组 Image 已独立复核；最终汇总 JSON 已严格解析，四道门禁均为 success，device_release_eligible=false。证据清单见 [机器可读验收记录](evidence/security_final_acceptance_2026_11_24.json)。

| 归档 | ID | ZIP SHA256 |
| --- | ---: | --- |
| stage1-6-full-outcome | 14916045051 | `5dd4448c3bbb9cb6283bbd09257e750af23b6bd34e1378016ae80f8457799e8d` |
| stage1-6-real-gki-bakasu-susfs-on | 14915560681 | `06643bf7bfbf030e9606e4ca971c575771ee6d0f9170e9bbbb7625fb66238360` |
| stage1-6-real-gki-bakasu-reviewed-new-susfs-on | 14914244085 | `44cb8f411683bee772d5b4e07e1aa2c78b330f2050f14cca48fabf7d04153622` |
| stage1-6-real-gki-bakasu-susfs-off | 14912584813 | `f01822d4f29fde1250e7e9036725389549bf1d70608dd516567f34c97efa096a` |
| stage1-6-real-gki-official-susfs-off | 14912337049 | `ae7dee68dcf19012187bd5e3623a3265ab88261619c5ad79bdbba2402125fcd3` |
| stage1-6-real-gki-official-susfs-on | 14912157883 | `7c9cf99a94892d63e59919049bbe9289950017133beb3dc23c76a7fa5ceff0c7` |
| stage1-6-reconciled-evidence | 14911266016 | `b4c219310fdf73e8eacccdef0409a5728aa96f66713da93c1a1f60f7521acab3` |

原始 Actions 归档将于 2026-12-24 到期（UTC 精确时间见 JSON）。Git 保存报告及摘要，不将大体积二进制加入源码仓库。原始归档需另存至用户控制的长期存储。

## 6. 未关闭风险与限制

- B314：XML 已拒绝 DTD/实体，限制 2 MiB、32 层、20,000 元素；主机 Expat 版本仍需核验，保留中风险告警，不通过 suppression 消除。
- B404/B603/B607/B405：56 项低风险库存，外部工具仍需要可信 PATH、Git/SSH 配置与可信构建输入；不存在针对恶意特权本机进程的通用沙箱保证。
- 源码锁远端 Blob `814f568d1431fb2a6682ef4d4634b9c25c818c13`，SHA256 `22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7`。历史本地摘要 `7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e` 不一致，原因未查明。不得修改锁或把云端策略验证视为本地准入。OEM 编译前必须现场核验。
- DFR include：BLOCKED_UNDETERMINED。独立 Vendor 归档来源与等价性、OnePlus13 完整 OKI、模块 ABI/KMI、真机 boot/Root/SUSFS、实际 OEM Bazel 编译时间传播：UNTESTED。
- Stage 7.5 与 Stage 8 是独立后续任务，禁止将计划或配置骨架认定为真实构建验证。

## 7. 验收决定

本轮约定范围的云端安全与回归验收通过。可进入项目主页中文化和功能状态矩阵；此决定不授权 OEM 编译、发布、刷机或合并 main。后续功能介绍须区分已实现且验证、已实现待验证、开发中、待实现、暂缓、明确不支持。保持历史证据原样。
