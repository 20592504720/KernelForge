# Stage 8 — 一加 13 精简功能矩阵（已选 10 项）

**状态：PLANNED_NOT_IMPLEMENTED；最后一次精简：2026-11-24。** 根据用户明确选择，将旧版 [21 条历史记录](evidence/stage8_feature_requirements.json) 分为 10 项主线、暂缓清单和基础验收控制。**仅更新要求与验收范围，不安装软件、不执行编译、不修改设备源码。**

## 一、主线范围与优先级

主要适配设备：**OnePlus 13 / PJZ110 / SM8750**，官方 Linux 6.6 OKI，已有 35 项官方源码锁。优先获得未经增强的官方 OKI 和固件/模块/ABI/KMI 证据，再一次引入一个新增功能，避免同时叠加多种补丁。保留 BakaSU + SUSFS 目标；不是让 KernelForge 自动支持所有 KernelSU 分支。

| ID | 级别 | 保留功能 | 技术范围与限制 |
| --- | --- | --- | --- |
| S01 | P0 | **一加 13 完整官方 OKI 基线** | 锁定的 PJZ110/SM8750 官方 35 项源码、对应固件/工具链/Kleaf、内核和厂商模块/DTB/DTBO/ABI/KMI；与其他机型或通用 GKI 扩展分开。 |
| S02 | P0 | **BakaSU + SUSFS** | 仅以固定 BakaSU、SUSFS 和内核 Commit 为批准组合；仅使用该版本兼容的 Hook，不引入其他 Root 分支。 |
| S03 | P0 | **原生风驰 HMBIRD** | 优先保留一加 13 官方 OEM 风驰及依赖模块；原版已有的能力不重复打补丁。 |
| S04 | P1 | **ccache 安全构建缓存** | 使用 Stage 7.3 的完整身份隔离、租约和失败隔离；真实 ccache 在获得可信二进制及编译入口后才可启用。 |
| S05 | P1 | **BBR + Westwood + 必需网络配置** | 仅对网络功能所需 Kconfig、netfilter、IPv4/IPv6、ipset/iptables 进行缺口补齐；保留 OEM 默认路由与拥塞控制。 |
| S06 | P1 | **ZRAM + 适配过的压缩算法** | 优先保留现有 ZRAM 和成熟 LZ4/zstd 支持；只有确认适配 Linux 6.6 后才选用升级补丁。 |
| S07 | P2 | **Droidspaces 支持** | 根据实际 Droidspaces 要求补全必要 namespaces、cgroups、seccomp、OverlayFS、veth 等；不全量开放不必要内核能力。 |
| S08 | P2 | **Mountify 兼容** | 优先验证现有 BakaSU/SUSFS 挂载接口；只有明确缺少的内核能力才允许最小补丁。 |
| S09 | P2 | **ADIOS I/O 调度器** | 明确列为条件性可选增强；若与 OEM UFS/blk-mq 路径冲突、KMI 破坏或没有收益，不强制合入。 |
| S10 | P2 | **Re:Kernel / Freezer / NoActive** | 按实际应用接口分别评估 Freezer/NoActive，优先复用现有内核能力；禁止无证据的功耗优化补丁。 |

这 10 项是**交付目标而非已实现声明**；当前总体为 `UNTESTED`。其中 S01 是基础门禁，S02/S03 与其紧密耦合，S09 是有冲突风险的**条件性**增强；S07/S08/S10 需要应用层真实兼容证据。安装或使用已有 BakaSU 与 SUSFS 不等于已验证其加入该锁定 OKI 源码。

## 二、执行顺序（精简为七个子阶段）

| 子阶段 | 核心任务 | 退出条件 |
| --- | --- | --- |
| **8.1** | PJZ110 源码/固件/Kleaf/DFR 前置准入 | 同一设备/固件/工具链/Manifest 锁可核验；DFR 实际依赖确定；不改锁。 |
| **8.2** | 未经增强的官方 OKI 基线与 ccache 只读预检 | Image、vmlinux、厂商模块、DTB/DTBO 与 ABI/KMI 的实际构建和校验；ccache 默认关闭，工具版本不明不得启用。 |
| **8.3** | BakaSU + SUSFS 与原生风驰 | 精确兼容组合、单一 Hook、模块/KMI、启动与用户授权设备测试记录。 |
| **8.4** | BBR/Westwood、必要网络与 ZRAM/压缩 | 配置与内核/网络/内存运行证据，默认保守。 |
| **8.5** | Droidspaces / Mountify / Re:Kernel / Freezer / NoActive | 分应用的实际接口、兼容性、隔离、安全与回滚记录。 |
| **8.6** | ADIOS I/O 独立实验与回归 | 冲突、KMI、性能、安全确认；不适配时明确 BLOCKED，不能强行整合。 |
| **8.7** | 全量选定范围验收与 Stage9 交接 | 每项 TESTED/UNTESTED/BLOCKED；完整基线、设备/许可授权的实测与可追溯产物。 |

每个子阶段只推进与它相关的选定功能。GitHub Actions、SHA256、构建记录、版本锁、报告与 Stage 9 发版门禁属于必要的**基础设施**，不是额外第 11 项功能。ccache 安全策略延续 Stage 7.3，默认关闭；是否真正加速需后续独立验证。

## 三、明确暂缓清单

下列历史需求保留备查，**不纳入本次 Stage 8 实现、构建矩阵或完成率**。不删除以前的补丁、文档或测试，但不继续为暂缓功能分配新开发任务。

| ID | 暂缓功能 | 原因 |
| --- | --- | --- |
| D01 | 跨设备通用 GKI、移植 F2FS 且免清数据的承诺 | 与本次一加13官方 OKI 基线不同；免清数据无安全保证。 |
| D02 | 其他 SM8750 设备及 6.6.30/.56/.57/.66/.89/.118 的多版本适配 | 不同内核版本/固件/厂商模块与 ABI 需独立证据；不扩大主线。 |
| D03 | MT6991（一加 Ace 5 至尊版）独立平台 | 不同 SoC，需另一套源码与厂商驱动。 |
| D04 | 官方 KernelSU、KernelSU-Next、ReSukiSU、SukiSU Ultra 及多 Hook 组合 | 本阶段只验收 BakaSU + SUSFS 的一个已审查组合；历史代码不删除。 |
| D05 | 公共 ccache-ECS 预置缓存、6 分钟编译承诺与14天自动清缓存 | 未核实供应链身份、命中率与指标；不得导入或自动删缓存。 |
| D06 | 额外 O2 编译优化补丁 | OEM 默认编译优化尚需核查，增益不足以成为强制目标。 |
| D07 | 强制 LZ4 1.10.0 / zstd 1.5.7 回移植及 ZRAM 内置化 | 仅保留与现有内核兼容的算法，特殊版本不作为里程碑。 |
| D08 | Brutal TCP 和未界定的 BBG | 只保留 BBR/Westwood；BBG 的原始含义/补丁来源尚待独立确认。 |
| D09 | 全量 iptables/ipset/高级网络选项 | 仅补 Droidspaces 和 BBR/Westwood 所必需的能力。 |
| D10 | Baseband Guard / 分区保护新补丁 | 可能干扰 OTA、恢复与权限模型；暂不纳入本次交付。 |
| D11 | GKI/F2FS 免清数据实验 | 风险高，现阶段不允许作为免清数据保证。 |
| D12 | NetHunter 监听模式 | 需要芯片/固件/驱动特异验证，与主要目标关联较低。 |
| D13 | kexec 内核切换 | Secure Boot、AVB、SELinux 与回滚风险较高。 |
| D14 | Unicode 零宽相关内核补丁 | 尚无明确源、补丁效果及安全性证据；保留历史需求，不实施。 |

特别说明：原需求中的 **BBG** 语义与补丁来源仍待确认，不把它误写成已经实现的 TCP 算法；**Baseband Guard** 作为未选中的独立安全补丁仍暂缓。Linux 5.10–6.12 与 GKI/Vendor 的历史**框架能力**不被删除，但在第八阶段不扩大为必须逐一构建所有内核/机型的承诺。

## 四、验收、安全及证据

独立验收合同见 [Stage 8 精简验收标准](STAGE8_SCOPED_ACCEPTANCE.md)。

- **官方基线优先。** 35 项源码 Git 身份、真实 Kleaf/OKI、内核和 vendor 模块、DTB/DTBO、ABI/KMI、固件匹配、实际启动（获授权时）分层计数，不能以历史通用 GKI 编译替代。
- **一项功能一份证据。** Root Hook/SUSFS、OEM 风驰、BBR/Westwood、ZRAM/压缩、Droidspaces、Mountify、ADIOS 和各功耗应用必须分别标 `TESTED`/`UNTESTED`/`BLOCKED`。
- **原版优先与最小修改。** 内核本来就支持的功能不重复打补丁。不得为了绿色 CI 关闭 CFI/KCFI、忽略 KMI 或自动加载未经验证的模块。
- **资源与供应链边界。** WSL2 约 3.77 GiB RAM / 1 GiB Swap，E 盘空闲曾约 184.4 GiB，均是历史采样；真实构建前需再次确认，不能因 Stage 8 规划自动下载/构建/清理。Stage 7.2 镜像许可阻塞、Stage 7.3 本地 ccache 缺失记录保留。
- **分层结项。** `OFFICIAL_OKI_BUILT` 不等于 `DEVICE_BOOT_VERIFIED`，也不等于 `SELECTED_SCOPE_VERIFIED`。存在尚未测试的选定项目时，只能宣布限定范围进展，不能宣称 10 项全完成。

## 五、历史追溯与变更控制

旧版 Stage 8 21 条功能（F01–F21）不删除，机器可读清单对每条保留旧来源和原始描述，并标记 `SELECTED`、`PARTIALLY_SELECTED`、`DEFERRED` 或 `FOUNDATION_NOT_COUNTED`。未来要重新启用暂缓功能，必须先得到明确要求并重新定义许可证/补丁源、设备矩阵、验收与回滚。Stage 8 实施尚未开始。

不自动更改 `main`、PR #1、固定官方源码 Commit、已有其他阶段报告，也不启动 OEM 构建、刷机或 Stage 9 发版。
