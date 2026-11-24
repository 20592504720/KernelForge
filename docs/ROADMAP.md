# KernelForge 开发路线图

更新日期：2026-11-24。以[最终安全验收报告](SECURITY_FINAL_ACCEPTANCE_2026_11_24.md)和[当前功能矩阵](STATUS.md)为准。旧路线图与历史阶段定义仍保留在[历史快照](https://github.com/20592504720/KernelForge/blob/4ac79893c19d95680bea4acc2374cc299fd6d2ab/docs/ROADMAP.md)，不将历史未完成描述误作最新状态。

## 已通过的阶段与当前边界

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 1 | 基础框架、Schema、CLI、CI | 范围内验收通过 |
| 2 | 构建引擎、GKI/Vendor 适配 | 软件通过；真实 Vendor 未验 |
| 3 | LLVM/GCC 工具链管理 | 软件通过；大型真实发行包待验 |
| 4–4.6 | KernelSU、BakaSU、SUSFS、版本锁 | 固定 ACK6.1 五组合真实编译通过 |
| 5 | 补丁管理、设备档案、源码及功能检查 | 范围内通过；设备构建与运行未验 |
| 6–6.5 | Git/Archive 安全获取、源码等价、兼容门禁 | 范围内通过；独立 Vendor 归档未验 |
| 7.1 | 环境只读预检 | 软件通过 |
| 7.2 | Release 镜像与可信回退 | 软件通过；实际镜像及许可待验 |
| 7.3 | ccache 安全隔离 | 软件通过；实际 ccache 待验 |
| 7.4 | 构建准入与可选构建时间 | 云端策略通过；本地锁和实际 OEM 构建受阻 |
| 安全收尾 | 四轮整改、专项修复、完整回归及报告归档 | 范围内通过，保留限制 |
| 文档中文化 | README、功能矩阵、路线图 | 本次文档更新 |

## 下一阶段：7.5 真实一加 13 快速 Image/vmlinux

[Stage 7.5 计划](STAGE7_5_FAST_IMAGE_PLAN.md)已启动离线证据工具与静态审计；实际构建尚未开始。先在原电脑核对本地 WSL2 锁摘要、35 项源码、固件、工具链与物理磁盘/RAM，确定真实 Kleaf 目标、DFR 依赖图和安全执行边界；后续查询及编译须独立授权。实际编译时间默认在构建开始时读取 UTC；可选有时区 ISO 8601，必须验证实际 Bazel action 传递。真实 ccache 默认关闭。后续 7.6 等环节依审核后的独立合同推进，不凭规划宣称完成。

## Stage 8：一加 13 官方 OKI 与十项选定目标

Stage 8 尚未开始实施。目标为 PJZ110/SM8750 官方 Linux 6.6 OKI；先完成未增强官方基线，再逐项集成及验证。完整合同见[十项功能矩阵](STAGE8_EXPANDED_FEATURE_MATRIX.md)和[验收标准](STAGE8_SCOPED_ACCEPTANCE.md)。

| 子阶段 | 目标 |
| --- | --- |
| 8.1 | 源码/固件/Kleaf/DFR 准入 |
| 8.2 | 官方 OKI 完整基线与 ccache 预检 |
| 8.3 | BakaSU + SUSFS、原生风驰 HMBIRD |
| 8.4 | BBR/Westwood、必要网络配置、ZRAM/兼容压缩 |
| 8.5 | Droidspaces、Mountify、Re:Kernel/Freezer/NoActive |
| 8.6 | 条件性 ADIOS I/O 调度器实验 |
| 8.7 | 十项独立验收与 Stage 9 交接 |

旧 21 条需求仍可追溯；D01–D14 暂缓不删除、不默认启用、不纳入本阶段完成率。具体见[暂缓清单](STAGE8_EXPANDED_FEATURE_MATRIX.md)。Linux 5.10–6.12 及 GKI/Vendor 框架目标保留，不扩大为已支持所有组合的承诺。

## Stage 9：自动化交付

待实现：可复现构建、产物与版本锁、签名、设备与固件匹配、恢复/OTA、安全发布门禁。没有完整 OKI、ABI/KMI、真机启动与授权，不得发布可刷写镜像。

## 执行原则

遵守[执行政策](EXECUTION_POLICY.md)：保护 main 与 PR #1，禁止未经批准的重型构建、源码同步、缓存删除和设备刷写。以实际验证层级和不可变证据为准，失败与暂缓项不得隐藏。后续项目主页介绍使用中文，状态变化同步 README、本路线图及功能矩阵。
