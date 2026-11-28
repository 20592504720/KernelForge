# KernelForge 项目长期记忆、任务总账与交接记录

- 初版：2026-11-27（UTC+08:00）
- 仓库：20592504720/KernelForge；主开发分支：stage1/initial-foundation；PR #1
- 本文位置：独立文档分支 docs/project-memory 的 docs/PROJECT_HANDOFF.md
- 范围：Stage 1–9，以及经用户批准的未来阶段。本文是持续维护的跨会话项目记忆，不是可执行授权、构建配置或替代原始验收证据的报告。
- 来源：本仓库既有路线图、状态矩阵、执行政策、阶段报告、T09 交付报告及截至本日可恢复的用户指令与历史对话。早期对话逐字全文未能全部恢复，摘要不得冒充用户原话。

## 0. 如何使用本文件（所有执行端）

每次恢复项目、新开对话、生成执行指令、接手其他代理报告，先读取本文件最新版本；再读取实际开发分支最新 HEAD/Tree、开放 PR、最新交付分支、报告及未完成事项。不要因历史记忆而重新从 main 开始，不要将磁盘审计 CDriveAudit 等无关项目混入。本文中的快照是带日期的历史记录，不证明当前 HEAD 或本地状态。

用户新增要求、调整范围、暂停/恢复、确认验收、重大失败、证据更新、功能完成时，在当次有 GitHub 写权限且得到相应授权的交互内更新本文：先读取当前 blob SHA；增量修改当前有效要求和任务状态；在变更日志追加日期、来源、变更原因、旧要求的取代关系、状态及证据链接；写回后重新读取核验。发生并发冲突先合并内容，不覆盖他人更改。没有写权限时明确报告，并输出待追加条目，不能声称已同步。不得在后台自行修改，不记录凭据、私钥、Token、临时签名 URL 或个人无关信息。文档分支只用于记忆归档，不是新代码开发分支，不用于合并或发布；代码执行仍遵守原有分支及授权边界。

信息优先级：最新明确用户指令 > 同范围经用户接受的验收合同 > 对应 Commit/Tree 的原始机器证据及报告 > 本文历史摘要。实际运行证据与用户希望实现的规划需分开。矛盾时标明待核实，不能猜测。技术状态保留 IMPLEMENTED / TESTED / UNTESTED / NOT_IMPLEMENTED / BLOCKED / IN_PROGRESS / PLACEHOLDER，以及限定范围验收。区分代码存在、静态检查、软件测试、真实编译、设备启动、Root 运行、可发布；跳过不算通过。

## 1. 总体目标与长期约束

面向 Android Linux 内核的模块化、可复现、可审计自动化构建框架。历史框架目标覆盖 Linux GKI 5.10、5.15、6.1、6.6、6.12 与独立 Vendor 构建模式；不承诺所有版本、设备或补丁任意组合可用。当前主设备为 OnePlus 13 / PJZ110 / SM8750，官方 Linux 6.6 OKI；Ace 6 为独立参考档案，不是本阶段设备交付。用户早期提出 SUSFS、BBG、Unicode 零宽相关修复、BBR、Westwood、压缩、风驰及编译优化、后续 BakaSU 和应用兼容等；以 Stage 8 精简后明确批准的清单为当前范围，历史需求不得直接恢复为当前必做。

- 优先安全、稳定、正确性、可维护性和供应链可追溯；不为速度关闭 CFI/KCFI、SELinux、签名、KMI 或必要模块。
- 主代码开发保留 stage1/initial-foundation；保护 main、PR #1、E 盘工作区、既有源码、缓存、备份和历史证据。不覆盖未提交工作、不 reset/force push、不擅自合并、创建重复 PR、发布或改变官方锁。
- 用户授权只适用于明确范围；源码同步、真实重型构建、缓存删除、刷机、签名、发布、付费/自托管资源等重大操作须单独批准。本文归档授权不授予代码或设备执行权限。
- 所有外部来源应核实项目、许可证、Commit、哈希、版本、布局和兼容性；未知或移动版本失败时不静默回退。允许审查原生风驰公开候选仓库，但不等于批准集成。
- 安全修复必须做影响分析、负向测试和必要全量回归；扫描零命中不是零漏洞。保留失败、取消、跳过、阻塞和历史原始证据。
- 默认构建时间为实际构建开始时读取的 UTC；自定义必须为含时区的合法 ISO 8601，统一归一化 UTC，验证 KBUILD_BUILD_TIMESTAMP / SOURCE_DATE_EPOCH 进入真实 OEM Bazel action。若 workflow dispatch 与实际开始存在时间差，不擅自将二者等同；以实际已审核合同为准。

## 2. 阶段 1–6：规划、历史验收和保留事项

| 阶段 | 主要工作、验收与边界 |
| --- | --- |
| 1 | 基础工程框架、目录、严格 JSON Schema、CLI、配置和补丁清单校验、CI。软件范围已验。 |
| 2 | 源码检出及固定 Commit 校验、独立 GKI/Vendor adapter、构建引擎、命令和失败报告、日志与产物哈希。真实 Vendor 构建仍未验证。 |
| 3 | LLVM/GCC Toolchain Manager，HTTP 下载、可信 SHA256、ZIP/TAR 安全解压、原子安装、缓存、并发锁、租约，AUTO/LOCAL_ONLY/DOWNLOAD_ONLY；初期 81 项测试通过。真实大型发行包待单独核验。 |
| 4 | 官方 KernelSU、BakaSU、GKI 组合及版本/配置管理。固定组合与实验性开发组合区分；其他 Root 分支不自动支持。 |
| 4.5 | pinned/latest_release/latest_prerelease/latest_branch；固定版本仍核验 expected_commit；移动 ref 仅解析一次并锁定；现代 Kbuild/旧版适配、真实 SUSFS 布局及补丁事务、BakaSU 内置 KSU-side SUSFS 不重复应用、单一兼容 Hook；不兼容时失败。latest_branch 仍有历史阻塞，不能自动称支持所有组合。 |
| 4.6 | E 盘迁移（历史核验 1361 文件），Linux/Windows Python 3.11/3.12 回归；历史 142 本地测试及 8/8 真实源码 Job 成功，保留 CONFIG_CFI_CLANG=y；Image 证据不等于 boot/Root/ABI。 |
| 5 | Patch Manager：依赖排序、SHA256、基线 Commit、重复/冲突识别、失败回滚；设备档案、SM8750 源码及 TCP/ZRAM 能力检查。用户已接受限定范围验收，不重复启动 Stage 5 验收。历史 45108869968/45108874520 CI 证据可在匹配后复用；固定 GKI 通过，完整 OKI/ABI/KMI/启动/Root 未验。 |
| 6.1 | 初步源码获取与环境审计；可完成项通过，历史 2 项跳过，不算通过。 |
| 6.2 | Git/Archive 双模式、下载校验、解压隔离、来源和等价证据。独立 Vendor archive 不直接准入 Git Patch Manager/构建。 |
| 6.3 | 官方 35 项锁定源码工作区、repo 元数据/缺失链接只读排查。历史 29 条缺失链接，精准审计 23 条 VERIFIED_NOT_REQUIRED（20×LLVM r522817、2×Rust linux-musl、mkdtboimg.py），DFR include BLOCKED_UNDETERMINED；限定范围结项 SCOPED_COMPLETE_WITH_BLOCKERS，不能把未确定路径当作可删除。 |
| 6.4 | 精确源码/Root/SUSFS/工具链组合兼容门禁，未验证组合拒绝正式构建。 |
| 6.5 | Stage 1–6 集中验收，复用匹配的原始证据，保留实际 GKI 和独立 Vendor 的区别。 |

历史固定 ACK6.1 ARM64 五组完整 Image：官方 KernelSU（SUSFS OFF）、官方 KernelSU+SUSFS、BakaSU（SUSFS OFF）、BakaSU+SUSFS、新版精确锁定 BakaSU+SUSFS。7 ZIP、5 Image 独立 SHA256 匹配。仅代表对应锁定 GKI 组合，不能替代 SM8750/OKI、模块、KMI/ABI 或设备测试。

原始索引（开发分支）：
- [功能矩阵](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STATUS.md)；[路线图](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/ROADMAP.md)
- [Stage 4.5 报告](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE45_REPORT.md)、[版本策略](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/DEVELOPMENT_TRACKING.md)、[迁移](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/WORKSPACE_MIGRATION.md)
- [Stage 5 最终门禁](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE5_FINAL_ACCEPTANCE_GATE.md)、[证据对账](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE5_EVIDENCE_RECONCILIATION.md)
- [Stage 6.2](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE6_2_IMPLEMENTATION.md)、[6.3 最终依赖审计](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE6_3_FINAL_DEPENDENCY_AUDIT.md)、[6.4](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE6_4_COMPATIBILITY_GATE.md)、[6.5](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE6_FINAL_ACCEPTANCE.md)、[全量回归历史](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE1_6_FULL_RUN_VERIFICATION.md)。

## 3. Stage 7.1–7.4：构建前置、安全、性能复审

- 7.1：只读环境、源码和资源预检，历史 exit 0，不代表运行 Bazel 或编译。
- 7.2：锁定工具链和 Release 镜像身份、可信同摘要回退；历史 Clang r510928 / Clang 18.0.0 / LLD 18.0.0 / Make 4.3，Bazel 7.1.1 已清点。实际生产镜像许可证/Asset 未批准，不自动启用。
- 7.3：ccache 身份隔离（源码、编译器、参数、配置等）、租约/并发锁、失效和失败隔离；真实 ccache 未验，默认 OFF；公共缓存未经批准禁用。
- 7.4：快速构建准入、源码锁、资源检查、默认/自定义时间、报告防覆盖、性能及安全；历史本地 18/21 后修复为 21/21，35/35 HEAD 匹配，E 盘约 184.34 GiB，云端修复 Run 45272620184 4/4。后续必须重新核对现有源码和资源，不挪用历史通过。
- 7.4-O：优化候选、冷/热缓存/算法对照、真实资源与耗时评估；云端微基准不是本机或真实编译加速，本地真实性能 INCONCLUSIVE；历史 O5/O6 阻塞及失败证据保留，不能以合成数据填补。T09 为 7.4 最后集中整改与验收，不设置 T10，不再将 O1/O2/T01–T09 人为拆为用户逐项批准的轮次。
- 四轮安全加固及集中收尾：路径穿越、symlink/Junction、原子写和报告覆盖、下载/归档资源限制、并发隔离、依赖锁、诊断脱敏、XML DTD/ENTITY 与资源限制、Windows 原生权限及兼容性等；以实际报告为准，保留 XML/Expat、可信 PATH/Git/SSH 等残余风险。

### 3.1 历史验收与最新候选不得混淆

2026-11-24：开发分支约定范围云端验收 [45375493788](https://github.com/20592504720/KernelForge/actions/runs/45375493788)，12/12 Job；四环境每环境 479 项，1836 非跳过通过、80 平台跳过、0 失败；五组 GKI Image 及 7 ZIP/5 Image SHA256。CodeQL 0，Bandit 高0/中1/低56，锁定依赖无已知漏洞，Gitleaks 149 可达提交无发现。

2026-11-27 T09：以[独立交付报告](https://github.com/20592504720/KernelForge/blob/delivery/stage7-4-t09/docs/T09_CLOUD_ACCEPTANCE_2026_11_27.md)为准。候选 Commit 451fb613f3fc0f4e7afbeb648742f60539ec07c4；Tree 6d008af76a85926bbe8ec97edd508a251ed89a97；259 tracked files。原本地 df8ce3a0cc16e08c2ea38d5118571508563a6be1 与参考开发 ccc8f1184d13a78a6d6a35ccae7c6d94cc51380f 保留；113 文件差异（81修改32新增0删除），独立逐行语义审计未全部完成。Windows 原生异主账户、历史 WinError 32 与并发锁超时根因仍未完全验证。

- [Validate 45948966996](https://github.com/20592504720/KernelForge/actions/runs/45948966996) 4/4；[CodeQL 45948967060](https://github.com/20592504720/KernelForge/actions/runs/45948967060) 0；[依赖安全 45948966997](https://github.com/20592504720/KernelForge/actions/runs/45948966997) 3/3；[Gitleaks 45948966987](https://github.com/20592504720/KernelForge/actions/runs/45948966987) 175 可达提交、0 命中。合计 9/9 Job。
- 四环境各568项，共2272项次，2160非跳过通过、112条件跳过、0 failures/errors，退出码均0；Bandit 高0/中1/低53，pip-audit 无已知漏洞。离线 pip 初始化、精确清理隔离 checkout Git 配置、数字 SID/ACL、长路径/Junction 检查回归通过。
- 该候选源码锁文件 SHA256 为 22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7；历史 CRLF/LF 差异重建验证未改变 35 项源码身份。旧合同记录的摘要不同，不直接替换或重新锁定；先匹配实际候选和规范化证据。
- 软件全量回归 PASS，不代表 T09 独立语义审计全完成，不代表当前候选重编译 GKI 或获得设备构建/发布准入。KF-SEC-001 保留，精确范围以原报告核对。
- 原开发分支、audit/stage7-4-t09、integration/stage7-4-t09、delivery/stage7-4-t09 各自证据隔离。不得将交付分支的验收结果冒称原开发 HEAD 的新验收。

参考：[7.1](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_1_WSL2_ENV_AUDIT.md)、[7.2](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_2_LOCAL_TOOLCHAIN_REVIEW.md)、[7.3](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_3_CCACHE_POLICY.md)、[7.4](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_4_LOCAL_CODEX_AUDIT.md)、[7.4-O 性能对账](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_4_O_RECONCILIATION_ADDENDUM.md)、[11月24日最终安全报告](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/SECURITY_FINAL_ACCEPTANCE_2026_11_24.md)。

## 4. Stage 7.5：真实锁定源码 Image/vmlinux 性能基线

仅针对未增强、锁定的官方 OnePlus13 快速 Image/vmlinux，先做真实基线与安全准入，非完整 OKI、非可刷机镜像。保持官方 35 项源码、Manifest、DFR、权限与源码锁；不能使用历史 ACK6.1 替代。

按合同完成：本地源码/BUILD/wrapper 核验、真实 Kleaf labels 和 DFR 依赖图、资源受控的离线 nofetch 查询及 action/output groups、实际编译器和时间 action 传递、一次获准单 variant 构建、日志与产物独立核验、软件回归和验收。内核 Image 必须真实且非 ELF 冒充；vmlinux 为 AArch64 ELF64 little-endian，保留最终 .config、build.log、build-time.json、SHA256、大小、进程退出码、目标、实际资源耗用、源锁及编译器身份。离线 receipt 只能证明 ARTIFACT_BYTES_CHECKED_BUILD_UNATTESTED。

较早历史交接（2026-11-27，已被下述 §12.1 最新检查点取代）：LOCAL_PREPARATION_COMPLETE_REAL_BUILD_BLOCKED 后，出现 BLOCKED_WSL_RUNTIME_BEFORE_BAZEL_QUERIES；WSL 两次约90秒退出，18个审计文件零字节，五项 Bazel 查询均未启动，真实编译未执行，perf 命令只是未经授权、未经验证草案。Android repo 链接修复为候选，不自动写官方源。--make_jobs=2、Bazel --jobs=1、ccache OFF；优先 perf common base，不能代替完整 SM8750 OKI。静态宏追踪提示 core sun_perf/sun_consolidate 不选择独立 DFR external DDK，仍需真实本地 Bazel 图确认，外部 DFR include 缺失状态 BLOCKED_UNDETERMINED 不变。build_eligible=false，device_release_eligible=false。真实性能 INCONCLUSIVE/未验证。

下一步：以 §15 为当前状态。local_config_platform 限定初始化、官方链接整改、生成仓库集中静态审计均已完成；当前不存在保持 nofetch 的已验证初始化 argv。待用户决定是否单独授权隔离、指定仓库的离线物化例外，不重复静态审计。旧 WSL 运行时故障及无损恢复记录保留，不重复已经通过的准入。不得无条件重试同一故障、运行未经审核 repo sync、下载新二进制、修改 DFR 或源码锁。取得单独授权后才执行有界 nofetch 查询，核对结果及完整安全合同后才启动真实构建。用户规定 Stage 7.5 整阶段最多两轮；内部步骤非额外执行轮次，重大风险仍须批准。

参考：[7.5 快速构建合同](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_5_FAST_IMAGE_PLAN.md)、[Antigravity 交接](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_5_ANTIGRAVITY_HANDOFF.md)、[DFR 静态补充](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_5_DFR_STATIC_REACHABILITY_ADDENDUM.md)。

## 5. Stage 8：用户批准的最终精简范围

状态 PLANNED_NOT_IMPLEMENTED；十项主线（构建时间为跨阶段基础控制，不新增第十一项设备功能）。原始21条需求 F01–F21 不删除，保留选择、部分选择、暂缓、基础设施映射。验收以[精简矩阵](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE8_EXPANDED_FEATURE_MATRIX.md)、[验收合同](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE8_SCOPED_ACCEPTANCE.md)、[历史机器清单](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/evidence/stage8_feature_requirements.json)为准。

| ID | 功能 | 必要条件与边界 |
| --- | --- | --- |
| S01 P0 | 一加13完整官方 OKI 基线 | PJZ110/SM8750、官方35项锁、对应固件/工具链/Kleaf、Image/vmlinux、厂商模块、DTB/DTBO、ABI/KMI；先无增强基线，不能使用通用 GKI 冒充。 |
| S02 P0 | BakaSU + SUSFS | 固定精确组合、单一兼容 Hook；核对模块/KMI、获授权后启动/Root/SUSFS 运行验证。其他 Root 分支不纳入本阶段。 |
| S03 P0 | 原生风驰 HMBIRD | 优先保留 OEM 原生能力和依赖，避免重复补丁；公开候选需审核来源、许可证和兼容性。 |
| S04 P1 | ccache 安全构建缓存 | Stage7.3 身份隔离、租约、失败隔离；真实可信二进制及编译入口、冷热对照后才启用；默认关闭。 |
| S05 P1 | BBR + Westwood + 必需网络配置 | 仅补实际所需 Kconfig、netfilter、IPv4/IPv6、ipset/iptables 缺口，保持 OEM 默认路由与拥塞控制。 |
| S06 P1 | ZRAM + 适配过的压缩算法 | 保留成熟 LZ4/zstd；升级必须适配 Linux6.6 且有证据，不强制特定版本。 |
| S07 P2 | Droidspaces | 按实际要求最小补齐 namespaces、cgroups、seccomp、OverlayFS、veth 等；不无条件放开能力。 |
| S08 P2 | Mountify | 先验证现有 BakaSU/SUSFS 挂载接口，仅对明确缺口最小修复。 |
| S09 P2 | ADIOS I/O | 条件性选项；独立评估 OEM UFS/blk-mq、KMI、安全与收益，冲突或无收益则阻塞/不强行合入。 |
| S10 P2 | Re:Kernel / Freezer / NoActive | 分应用验证真实接口和功耗、隔离、安全、回滚，不添加无证据的功耗补丁。 |

阶段内部技术顺序：官方源码/固件/DFR 准入 → 官方 OKI 基线及 ccache 预检 → Root/SUSFS/原生风驰 → 网络/ZRAM → 应用兼容 → ADIOS 条件实验 → 十项独立证据和 Stage9 交接。原文 8.1–8.7 是工作包，不再作为独立对用户汇报的执行轮次。每个功能明确 TESTED/UNTESTED/BLOCKED；OFFICIAL_OKI_BUILT 不等于 DEVICE_BOOT_VERIFIED 或 SELECTED_SCOPE_VERIFIED。

### 5.1 暂缓清单（原 D01–D14）

| ID | 暂缓需求 |
| --- | --- |
| D01 | 跨设备通用 GKI、移植 F2FS 且免清数据承诺 |
| D02 | 其他 SM8750 设备及 6.6.30/.56/.57/.66/.89/.118 多版本适配 |
| D03 | MT6991 / Ace5 至尊版独立平台 |
| D04 | 官方 KernelSU、KernelSU-Next、ReSukiSU、SukiSU Ultra、多 Hook 的 Stage8 设备组合 |
| D05 | 公共 ccache-ECS、6分钟速度承诺、14天自动删缓存 |
| D06 | 额外 O2 编译优化补丁 |
| D07 | 强制 LZ4 1.10.0 / zstd 1.5.7 回移植及 ZRAM 内置化 |
| D08 | Brutal TCP 与含义/来源尚未确认的 BBG |
| D09 | 全量 iptables/ipset/高级网络配置 |
| D10 | Baseband Guard / 分区保护新补丁 |
| D11 | GKI/F2FS 免清数据实验 |
| D12 | NetHunter 监听模式 |
| D13 | kexec 内核切换 |
| D14 | Unicode 零宽相关内核补丁 |

暂缓不删除历史代码、证据与需求，不计入当前完成率，不未经批准启动开发。BBG 不擅自解释为 TCP 算法或与 Baseband Guard 合并。保留框架已有官方 KernelSU GKI 验证，与 Stage8 的 BakaSU 设备范围不冲突。

## 6. Stage 9：统一自动化构建、交付及发布体系（已规划，未开始）

用户已确认保留 Stage9，不能遗漏；不是 Stage8 的自动附带成果。结合[当前路线图](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/ROADMAP.md)与历史对话，落实统一 GitHub Actions 入口，设备/固件/Root/增强功能配置、Git 与固定 Commit 快照来源模式、既定版本策略和锁定、工具链安全获取、缓存隔离/复用、默认与自定义构建时间、构建/验收报告和产物参数。参数确切键名、合法组合及 UI 形式尚待本阶段合同和实际实现，不能把摘要当成已定 schema。

验收工作：参数和不兼容组合拒绝；输入/输出和版本锁可复现；隔离缓存和安全回退；受控失败、恢复、资源限制；产物归档、哈希、签名、完整性与来源证明；设备、固件及 ABI/KMI 匹配；恢复/OTA 与发布门禁；必要实际设备验证及明确发布授权。通用 build.yml 目前为预检占位，release.yml 仍禁用发布门禁；实际状态以对应分支最新证据为准。不通过推送/合并 main 绕开 dispatch 限制。未经完整设备验证的产物不得作为正式可刷入内核发布。尚未恢复 Stage9 的逐字参数合同，待取得原文时追加；没有已确认的 Stage10。

## 7. 用户长期强制要求：中文主页和后续待实现功能

用户 2026-11-24 明确要求先完成代码安全加固，Stage1–7.4 全量回归通过，最终安全验收报告归档，然后统一中文化 GitHub README、仓库简介和其他面向用户的主页介绍。2026-11-27 再次强调：中文主页及后续待实现功能是必须完成的任务关键点，非可选文档优化。

实际核对（2026-11-27）：[main README](https://github.com/20592504720/KernelForge/blob/main/README.md) 已为中文，展示11月24日历史验收；[开发 README](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/README.md) 已中文；[T09交付 README](https://github.com/20592504720/KernelForge/blob/delivery/stage7-4-t09/README.md) 已更新11月27日候选软件验收。默认主页尚未同步最新 T09 交付状态，仓库简介实际状态本次未核验。不能说首次中文化完全未实施，也不能说最新交付已全部同步。独立语义审计和其他验收缺口继续保留。更新 main/简介需用户授权，不能借文档归档变更主分支。

长期维护：每个阶段验收、功能交付或重大证据变化时同步 README、STATUS、ROADMAP、仓库简介/必要用户页面；显示已实现并验证、已实现待验证、开发中、待实现、暂缓、不支持；逐项列功能、验证层级、支持设备、版本、构建方法、安全机制、限制、当前阻塞、后续规划。技术名词、命令、配置键、路径与状态码保留原样。Stage7.5 完成更新真实构建和性能，Stage8 完成更新设备和增强功能，Stage9 完成更新 Actions 使用与安全发布。不得删掉未选功能的历史记录或将待实现功能标为已实现。

## 8. 执行效率、代理协作与资源（长期）

- 从 Stage6 开始减少反复验收，每轮一个核心目标；Stage7.5、8、9 原则上各最多两轮：第一轮整阶段集中实施，第二轮集中整改及统一验收。普通内部检查不拆成用户逐轮指令；不能为了两轮而跳过质量、安全或重型操作授权。无法完成时记录 BLOCKED 并由用户决定。
- GitHub Actions 同一批长任务轮询间隔至少10分钟，通常15–30分钟；批量检查，完成即停止。新增故障、安全决策、完成事件、产物即将过期可例外并说明。登记 Run ID、URL、Commit/Tree、源码及工具链锁、参数、资源、开始时间、日志、产物 SHA256，记录上次/下次检查。避免重复启动已有有效任务；文档变更不应触发重型编译。
- 复用已完成 CI 必须核对 workflow/Run/Commit/Tree、配置、源码/Root/SUSFS/工具链身份和产物；移动上游不能仅凭 Tree 相同推断。先静态检查、针对测试、共享代码完整软件回归，再按改动与合同进行真实编译/设备验证。
- 额度约20%停止低优先研究并保存交接；10%收尾当前单元；5%不再新增功能，按权限保存已检查工作、运行证据和后续状态；不虚报额度或验收。
- Stage7.5 及后续用户曾指定 Antigravity，每轮只指定一个模型（历史可用4个）；跨模型不自动共享历史，交接提供仓库、分支、当前 HEAD/Tree、目标、已验证证据、禁止操作、阻塞和验收条件。首次使用先验证模型/provider、读写/创建/修改/重命名/删除临时对象、Windows、WSL2、本地 Git 和 GitHub 权限，仅操作隔离对象并清理；不要误报整个 E 盘零变化。Codex/OpenCode 可按用户后来指令承担独立任务，不能假设当前可用或擅自改变执行端。不得把一轮测试报告当作下一轮执行授权。
- Windows 工程历史路径 E:\内核构建\project；完整源码位于 WSL2 ext4（不是 /mnt/e 的 NTFS）/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750。历史 WSL2 8 CPU、3.77 GiB RAM、1 GiB swap，E盘184 GiB上下，后续样本有下降；实时复查。Stage7.5 E盘物理保留50 GiB、ext4保留20 GiB及 inode；历史首次完整同步合同另有120 GiB物理预检，不混用。资源不足时无损停止、保留日志。
- Hosted runner：测量块/inode/实际空间，排查磁盘、内存、超时、网络、工具链、编译、缓存和 artifact quota，不把磁盘错误自动解释为内核缺陷。历史试点44988567235 回收 6,584,580 KiB，仅 Ubuntu24.04 /usr/share/dotnet 经守卫测试；35GiB 是临时 floor，10GiB 是首次受控同步保留量，非通用规则。不得扩张清理白名单、清本地 E/F/C 或未审查系统目录。禁止未经授权重型同步、付费 runner/公开自托管。
- 详细规则以[执行政策](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/EXECUTION_POLICY.md)为准。

## 9. 当前待办总账（2026-11-27 快照，不是新的运行结果）

| 优先级 | 待办 | 状态 |
| --- | --- | --- |
| P0 | T09 剩余独立113文件语义审计、残余风险/权限边界及验收证据归档 | 软件回归已过；审计未全完，不能伪造通过 |
| P0 | 核验此前生成仓库物化与五查询原始证据 | §16.1 执行端报告已通过并进入真实构建；独立收据待验，不再将§15旧阻塞当当前唯一问题 |
| P0 | 7.5 五项有界 nofetch Bazel 查询、实际 action graph、资源与时间传递 | 执行端报告五查询通过；原始图/收据及时间链待独立验收（§16.1）；保留§14历史失败 |
| P0 | 7.5 解除BTF容量及Windows提交余量阻塞，重新准入后真实构建、产物及最终验收 | 首次Make2/Bazel1基线运行3049.913秒后MEM_AVAILABLE_LOW受控停止，清理PASS，无完整产物；当前无新构建（§16.3） |
| P0 | 最新中文交付、默认主页/仓库简介状态核验和经授权同步 | 部分已实施；持续必做 |
| P1 | Stage8 十项设备功能与完整官方 OKI 验收 | 未实施 |
| P1 | Stage9 统一 Actions 自动化、产物签名、恢复和发布安全门禁 | 未实施 |
| P2 | D01–D14 历史暂缓项 | 不进入当前任务，重启须用户决定 |
| 持续 | 本文增量更新、README/STATUS/ROADMAP 同步、保留历史证据 | 长期任务 |

## 10. 用户要求变更日志（恢复摘要，不冒充逐字原文）

- 2026-11-20：建立 GKI/Vendor 双适配及增强内核规划，随后扩展工具链、版本锁、安全补丁及设备支持。
- 2026-11-21：Stage4.6 后保护 E 盘工程、main、PR #1；保留已测试/未测试界线，增量交接。
- 2026-11-22：长任务至少10分钟轮询、节省额度、复用已通过 CI；重型任务安全边界。
- 2026-11-23：接受 Stage5 限定范围结果，不重复验收；Stage6 能完成的先做，其余交本地执行端；Stage7.4 保留失败与设备门禁；7.5 后续交 Antigravity、单轮单模型、首次权限验收。
- 2026-11-24：Stage8 精简至 S01–S10、其他 D01–D14 暂缓；新增构建时间自定义默认当前实际时间；安全加固与 Stage1–7.4 全量回归、最终安全报告之后中文化，后续项目主页默认中文。
- 2026-11-24 至 27：要求全面代码、漏洞和语法检查，逐轮安全整改、全量回归，不以局部检查代替；T09 收尾，保留历史失败。性能复审以真实证据为准。
- 2026-11-27：Stage7.5/8/9 整阶段集中执行，每阶段原则上最多两轮；T09 为 7.4 收尾，无 T10。确认 Stage9 正式规划；重申主页中文化和待实现功能是正式必做任务。较早 WSL 阻塞保留；后续首条查询失败，见 §12.1；真实编译未执行。
- 2026-11-27：用户要求在 GitHub 建立可长期读取和更新的项目云端记忆文档，记录全阶段规划、用户指令、变更与要求；本文件初建。选择独立文档分支以不移动原开发 PR、main 或 T09 证据分支，不是代码分支迁移。

## 11. 记录模板（后续追加）

日期/时区 | 用户确认或报告来源 | 影响阶段及任务ID | 新要求或状态 | 原要求（如被替代） | 验收标准/证据 Commit、Tree、Run及路径 | 未完成和阻塞 | 授权边界。历史记录保留，当前任务总账同步更新。无证据填“待核实”，不要补造。

**本初版已尽可能整合可恢复历史与仓库合同，但不声称恢复了所有聊天逐字全文。精确缺失项：部分 Stage1–6 早期子任务原文、Stage7.4 T01–T08 原始合同与部分原始日志、Stage7.5 完整终端原始日志、Stage9 完整历史参数合同及仓库简介实时状态。O1–O8 逐项报告及更新的 Stage7.5 检查点已在 §12 补充。后续获得相应原始证据时增量补充。**


## 12. 第二次历史恢复与纠错（2026-11-27，增量补遗）

本节来源于第二次历史会话检索及用户文件库原报告；不把检索摘要当逐字原文，不把文件库附件假称已上传到 GitHub。历史证据按原文件名、Commit/Tree、日志和摘要标识，原始报告与本总账分开保管。仓库为公开项目，本次不公开原始个人聊天全集、凭据、完整本地进程环境或无关个人信息。引用的报告内容为必要工程事实。

### 12.1 最新 Stage7.5 检查点：取代“查询尚未启动”的旧状态

来源：用户文件 checkpoint(4).json（created 2026-11-27T09:37:25.962434+00:00）、revised_commands.json（2026-11-27T09:25:56.244070+00:00）、PENDING_COMMANDS.md（历史待授权命令）；历史用户报告更新于 09:43 UTC。状态 STOPPED_ON_FIRST_QUERY_FAILURE；当前阻塞 BLOCKED_OFFLINE_REPOSITORY_NOT_PREPARED。

- 已有明确五项离线查询授权，范围为 AUTHORIZED_FIVE_OFFLINE_QUERIES_ONLY，不包含真实编译、下载或发布。早期两次 WSL 约91–92秒退出1、18个零字节文件为历史故障。
- 续接源码35项 PASS；107份源码命令收据验证通过，未重复源码审计。补充准入通过；清理最终 PASS。不能据此声称 WSL 永久稳定。
- query-definitions：QUERY_BLOCKED_OR_FAILED，Bazel exit 37、guard exit 1，缺 @@local_config_platform，原文错误：External repository @@local_config_platform not found and fetching repositories is disabled.
- query-deps、cquery-perf-files、cquery-consolidate-files、aquery-core-actions：NOT_RUN。1项开始并结束、0项成功、其余4项未启动；没有 action graph 或 output paths，真实构建未执行。
- 证据路径（对应报告包）：runtime-validation-v2/result.json、admission-completion/result.json、sequence-resume/result.json、observations/query-definitions/query_receipt.json、query-definitions/query.log、handoff-resume-20261127/checkpoint.json。
- 保留 nofetch、no_internet、禁下载、网络隔离、进程与资源守卫、隔离缓存；下一步先审查 local_config_platform 缺失是本地生成配置还是外部依赖，核对真实 Bazel 版本/规则与离线准备合同。不得擅自打开网络、取消 nofetch、伪造仓库、改源码或重新运行已停止序列。任何超出五项既有授权的准备或构建须独立批准。perf 命令仍为未获构建授权的候选。

### 12.2 Stage7.4-O 原始报告恢复（R2 → O-Final → T09）

A. 用户文件 R2_FINAL_REPORT.md（执行11月25日，整理11月26日）：R2 定向安全修复及 Windows/WSL 回归完成；整体 IN_PROGRESS。原始中文 r2-final-report.md 曾损坏为问号，交付整理版依据原始 JSON/日志/Git 报告，不是重新执行测试。基线 da2ed84a185b88ffd782e564c740de893bb173f8；修复 d91712df2daf1f63e313c5b4d68ef2446d916e78；最终 HEAD 781c1102ddeac0d859837c583ed2bfeabcb15dac，Tree 28a17ee6961d41cb161abc2156da6ebc8e2a2f2f。20文件、790新增/42删除。Windows Python3.12 137项（116通过、21跳过），WSL 137项（136通过、1跳过），均0失败/exit0；七个定向模块，非全量。Windows 原始日志 SHA256 8364c535cc1650297a98fcedd11c173544d08feda8fdc5c1f16160a55be3534e；WSL d210419235e2e88f1bc7a0aceaed3b1fdaf4ba3d97b1af0c48645e45bd24f321。同步322文件、0摘要差异。Git 环境隔离、URL userinfo拒绝、junction元字符防护、行尾策略及证据记录；保留正式工作区和历史源锁，不启动正式编译。用户曾取消自动关机，不应恢复。

B. 用户文件 REPORT.md（标题 Stage 7.4-O-Final 独立复审交付报告，生成 2026-11-26T02:21:51.761617+00:00）：最终 Commit 03ed5571da39d498f9fdcfe8a94f5bf740aeed8b、Tree 139092d089d569dedc1bf8ccd89fe1cbb5202a8a，41文件922新增/89删除，Windows正式/隔离/WSL同身份；完整补丁139073字节 SHA256 174e6ac581b024b0b19bbae6813f5fe0c9f78ab0056f1b715137ec9a79bfb600，隔离恢复249文件一致。34测试模块，双平台 Python3.12 各517测试方法：Windows Ran517、OK(skipped=49)、291.720秒（子测试跳过计数不能简单相减推导方法通过）；WSL 513通过/4跳过、42.084秒；两平台exit0。Python3.11运行时未发现，静态通过不能代替。Ruff exit1（217条，208基线对应、9新增/变化）；actionlint/ShellCheck exit1（release.yml常量false禁用提示，保留门禁），Pyright 3.11/3.12静态0错误，Gitleaks 0。整体 PARTIAL_BLOCKED，不等于所有检查通过。Git裸库/common config/worktree审计、进程隔离、Win32 junction、原子不可覆盖证据、行尾和长路径整改；TOCTOU状态 MITIGATED，同用户并发写入与可信PATH/Git/SSH仍为边界。历史5项Windows失败/错误复验通过，不覆盖原失败。

| O项 | O-Final 报告中恢复的任务和结论（2026-11-26） | 剩余真实验收 |
| --- | --- | --- |
| O1 | 计时与失败路径软件PASS | 真实构建计时未验 |
| O2 | CI触发/去重与required checks/Rulesets审查；REST 200、Rulesets=[]、保护接口404，保留策略 PARTIAL_BLOCKED | 不以无规则返回推断允许删减CI；管理员只读核验 |
| O3 | Git checkout 优化对照；SHA-1/SHA-256 × commit/branch/tag ×3，Commit/Tree一致及fsck通过 | 未采纳生产算法；真实远端、大仓及任意SHA拒绝边界未验 |
| O4 | 工具链缓存校验；单次读取双格式证明、独立复解压和篡改测试通过；可信锁内Clang已核验 | 无可信大型压缩包完整冷下载/校验/解压/热缓存对照 |
| O5 | 并发与资源：轻量AArch64 C负载1/2/4 workers各3次，摘要一致 | 真实内核吞吐BLOCKED；保留-j2，比较同源/配置/工具链/时间戳至少3次，记录中位数、离散度、RAM/CPU/I/O/swap/磁盘 |
| O6 | ccache未发现、未安装、未启用，BLOCKED | 可信二进制、编译器拦截、关闭/首次填充/热构建/单文件变更/不匹配拒绝对照；命中、耗时及产物一致性 |
| O7 | 证据流式哈希、原始字节、UTF-8、原子不可覆盖JSON、恢复归档本地PASS | 外部持久存储、访问与到期策略PARTIAL |
| O8 | 正式双平台3.12各517项软件回归PASS | 当时3.11运行BLOCKED；T09后来四环境软件通过，但必须按对应Tree认定，真实构建仍未验 |

O4/O5/O6 原始实验合同还见用户文件 KernelForge_T09_cloud_verified_complete.patch（其中 O4/O5/O6 性能后续清单）及对应 GitHub 交付分支。每次真实实验保存原始命令、环境、退出码、资源采样、产物哈希、失败；不从小程序/微基准外推实际内核收益。

C. T09 已在 §3.1 记录；补充用户文件 KernelForge_T09_cloud_acceptance.json：候选259文件独立ZIP blob匹配；Python3.11 AST 102文件、YAML 14工作流、diff check PASS；81修改32新增、4208新增行/560删除行。完整patch SHA256 d7d6513fa2f7299b35b742fcda0feab2d212bdf75ce9adbe3ffb2e316eaca246，代码ZIP SHA256 8e15f4385c267ca45e3367222d44216e300007eb7d333ed3db748ef393ebb967。交付文档 Commit 14467ced92092c564a56d6b5936f7049eb56b62c、Tree a754947495d0e39992d3eb0a430bb2fbc601c9a4（仅 README/ROADMAP/STATUS/T09报告更新，不重跑程序）。结论 SOFTWARE_ACCEPTANCE_PASS; FULL_STAGE_CLOSURE_NOT_CLAIMED; BUILD_NOT_AUTHORIZED。T01–T06 精确任务名/逐字合同仍未恢复；T07、T08 原始专项报告已在 §13 补齐，不把 O1–O8 强行映射为 T01–T08。

### 12.3 更早回归及用户指令的原文/摘要分离

用户文件 KernelForge_Stage1-7_4_Audit_Evidence_2026-11-24.json：Commit afe8fb7121680a089e5b11a1c505bdbcdffa7fad、Tree dfa99a2ad5e46a559847bb6afb97128b6880dc89；Validate 45278671842 attempt2 4/4，1672项次、1596通过/76跳过、0失败错误；独立 7.1 45278691030、7.2 45278686273、7.3 45278686100、SM8750 45278687515；历史 Stage1–6 一次性验收45184293290五组GKI成功（本轮未重跑）。初始安全发现 F1 symlink输出覆盖、F2 patch schema路径穿越、F3工具链归档资源限制、F4诊断脱敏、F5 7.5设备构建准入未集成、F6开发依赖图未固定。后续整改和11月24/27最终证据须分层对照，非同一轮结果。

可见历史用户原句（来自本次会话可见的历史摘要中保存的直接引文，按现有文本引用，不声称拥有完整原始聊天导出）：

- “对了，我希望行动里再加上内核构建时间的自定义，默认是当前时间”
- “运行一次全量的代码检查与全量的第一阶段到7.4的回归性测试，注意尽可能是全面性的，因为我想筛查一下有没有错误，为后续做好准备，同时排查一下是否有漏洞，代码语法等是否正确，此回答不设定限限定的回答时间，直到本次安排的任务全部完成为止”
- “ OK，进入第四轮。第四轮完成后，进行全量化的第一阶段到7.4回归运行测试，注意是全量，主要确保全阶段未出现修复漏洞或隐患产生的冲突”
- “请将 KernelForge 第八阶段规划按以下选择精简，并保留没有选择的项目作为明确的暂缓清单。保留项目：一加 13 完整官方 OKI 基线、BakaSU + SUSFS、原生风驰 HMBIRD、ccache 安全构建缓存、BBR + Westwood + 必需网络配置、ZRAM + 适配过的压缩算法、Droidspaces 支持、Mountify 兼容、ADIOS I/O 调度器、Re:Kernel / Freezer / NoActive。请先检查最新开发分支，安全更新功能矩阵、路线图和验收条件；不要启动内核编译或修改 main。”（历史记录中的用户侧指令文本）
- 2026-11-27T01:33:16Z 历史检索明确标为用户接受：Stage7.5/8/9每阶段最多两轮，第一轮整阶段、第二轮集中修复最终验收；不再拆 7.5-1/2、O1-O2、T01-T09 等交接批次；普通错误授权范围内自主修复，重大阻塞未经批准不增轮。此条是恢复的摘要，不是逐字引文。
- 本次用户明确长期授权维护本文件，要求新对话优先调用链接，保留所有重要历史决策、用户指令与任务调整，主动帮助纠正潜在错误；文档长期维护权限不等于全仓库、真实编译或发布授权。跨对话自动记忆写入/召回不可保证；如未能自动恢复，按仓库和固定路径定位。

### 12.4 Stage9 参数合同恢复程度与待核验项

已确认 Stage9 为正式阶段；统一 Actions 构建和安全交付需求见 §6。再次检索未找到逐字段已批准的 workflow_dispatch 原始合同，不能虚构字段名、选项枚举、默认值、必填性、签名策略或矩阵规则。以下为现有合同可追溯语义，不是新增决策：设备/固件匹配、内核版本/源码模式、Root与SUSFS兼容、增强功能、四种版本策略（已有框架键）、工具链模式（已有三种）、安全缓存、时间、报告、产物与发布。现有框架字段不自动等同未来 Actions 输入。

时间语义有真实冲突待复审：仓库 Stage7.5 合同/README 写实际构建开始UTC；用户文件 PENDING_COMMANDS.md 的后续 Stage7.5 命令说明为默认 dispatch 时采样，参数 --build-timestamp、自定义示例 2026-11-24T17:30:00+08:00。须同时保存 dispatch 与实际构建开始时间及最终 action 环境证据；Stage9 的最终默认语义以最新明确批准合同为准，不擅自选定。Stage7.5 默认-j2、ccache OFF、不自动下载/刷写/打包不是已经批准的 Stage9 全部默认参数。

恢复缺口保持 OPEN：Stage9 原始参数表及逐字用户确认、T01–T06 精确原始合同、T07/T08 用户原始指令全文、早期阶段完整聊天逐字文本；本次没有足够证据将其标记已恢复。

### 12.5 持续维护授权与变更记录

2026-11-27 用户再次授权对固定文档长期增量维护，要求每次新会话恢复项目时先查此文件、在当次授权交互中追加新规划/调整/要求/证据/错误修正，历史记录保留；不另造替代总账。第二次补遗修正最新7.5阻塞、补齐O1–O8报告与早期安全证据、区分逐字可见引文与历史检索摘要、登记Stage9时间语义冲突及精确缺口。文档更新不触发真实构建、改变原代码分支、main、PR或发布。

## 13. 第三次历史恢复（2026-11-27）：T07/T08、R1/R5、现有 Actions 参数及早期决策

本轮经用户明确授权，使用历史上下文检索、ChatGPT 附件库搜索与原报告读取、GitHub 开发/验收/交付分支差异及文档读取交叉核验。只将工程必要事实和证据摘要归档，不公开无关私人资料或凭据。PR #1 讨论读取结果无评论；不能推断未检索到的聊天或附件不存在。新增证据与历史检索摘要分开标注。本轮未执行代码测试、编译、分支整合或新阶段实施。

### 13.1 项目起点与用户长期约束（历史检索摘要）

- 2026-11-20 03:30:07 UTC：初始目标为构建 KernelForge，用于 KernelSU 及第三方修改分支，支持 Linux 5.10–6.12、SUSFS/BBG/Unicode 零宽相关修复、BBR/Westwood TCP、增强压缩、风驰、编译优化。03:30:46 用户接受新建仓库、GKI+Vendor 双适配、仓库名 KernelForge。上述为可检索用户消息摘要，非完整逐字文本；助手提出的更多算法/Root候选不等同用户最终批准清单。Stage8 精简范围仍优先。
- 2026-11-23 12:43–12:45 UTC：Antigravity 首先完成 GitHub 接入，不因此开始正式开发；每轮不得与上一轮重合，基于报告执行未完成项。
- 2026-11-24 12:21:41 UTC：用户曾特许仅修改 main 的 README 进行中文首页更新，不合并 PR、不改功能代码。该历史例外解释 main 已中文；不是未来任意修改 main 的常设授权。
- 2026-11-27 06:07:39 UTC：用户明确认为分支过多造成混乱；后续尽量复用现有分支，不为每项检查创建新分支。先由 ChatGPT 完成可独立完成工作，本地真实构建/设备验证才交执行代理。文档更新复用 docs/project-memory，不再新建归档分支；需要新分支时说明必要性和风险。该约束补入 §8 执行制度。
- 2026-11-27 本轮：用户授权历史记忆、该 GitHub 仓库及 ChatGPT 附件库相关文件的读取，以恢复任务记忆；此前总账持续写入授权继续有效。授权不增加实际工具能力，不等于任意修改仓库或设备。不能保证恢复所有旧聊天全文或跨对话自动记忆。

### 13.2 R1 与 Stage7.4-O 第一批证据

附件 r1-final-report.md（2026-11-25）为原始第一轮集中环境整改及可靠性报告：基线 da2ed84a185b88ffd782e564c740de893bb173f8，Tree 39a1d9173ff4fc885173667dfdc56da9527c9d0d；38个文件263845字节证据备份逐项验证。隔离复现缺失 GIT_CONFIG_VALUE_0、混合行尾锁摘要问题；单次 core.autocrlf=false LF 检出复验，正式共享工作区旧锁17319字节/363 CRLF 保留，独立LF锁为22cde7f2…e79a7。Windows 三定向模块通过；短路径专项通过，longPathsEnabled=0、WinError145仍阻塞。WSL Python3.12.3既有venv、7项依赖导入通过；独立LF克隆Stage7.4 22项、SM8750同步模块14项、Stage6源码等价29项通过；正式共享树仍BLOCKED。PowerShell Restricted不绕过。历史48跳过未计PASS。GitHub只读审计当时报告 main 未启用分支保护，Actions默认read，PR open/dirty；项目保护main是用户执行政策，不能冒称平台技术保护实时已启用。该轮未运行正式全量回归或真实编译。

仓库原始证据：[O专项优化合同](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/STAGE7_4_O_OPTIMIZATION.md)、[第一批机器证据](https://github.com/20592504720/KernelForge/blob/stage1/initial-foundation/docs/evidence/stage7_4_o_first_batch.json)。精确 O1 为 monotonic_ns 分阶段计时/失败阶段，O3为精确浅层获取，O4为安装树单次读取双格式摘要、仍保留独立复解压复核，O7为流式Image双哈希及长期归档。首次软件候选 Commit66a51aabbe749a2b40efa39ad467362f2a347c58，Validate45432517564四环境各486项，共1944项次、1862通过/82跳过、0失败错误；CodeQL45432517594为0、依赖审计45432517551高0中1低56、Gitleaks45432517601扫描153提交0发现、镜像45432517742 4/4。旧真实GKI基线45375493788整体55分29秒，五主步骤1018/989/1035/1754/1019秒（含获取、集成、构建，不是纯编译时间）。隔离Linux等价算法微基准（非WSL/完整构建）：Image 36293120字节，五次中位34.52→25.51ms，Python追踪峰值36297658→267345字节（不是RSS）；16×1MiB模拟树读取32→16MiB、27.64→13.71ms，摘要一致。一次Git file:// 20提交对照89→55ms、对象270889→262443字节，未采纳生产。不可将这些比值作为真实内核加速。

### 13.3 R5、T01–T06 合并验收与证据计数

附件 r5-delivery-summary-20261127.md、r5-completion-checkpoint-20261127.json、r5-delivery-verification-20261127.json、r5-package-execution-20261127.log：
R5 最终候选 Commit 100f327120023b70f20f6a6707e2cf5a8daa66e2 / Tree a193f2223bfed0db639fad8d9d93908f9b410eba，正式本地分支干净，未推送。37正式步骤退出0，原始日志摘要重核；八组Pyright零错误/警告，Python3.11仅静态。R4历史544方法保留，两平台新增相同10个。Windows Python3.12 554方法，502完成且无跳过、53跳过记录涉及52方法（51整方法、2子测试），391.029秒；WSL 554方法546通过/8跳过、66.426秒；两平台0失败错误。R5软件核心通过但补充检查有未验项，Bandit/pip-audit/CodeQL当时未运行。12技能发现、102内置插件active、两MCP只读调用有报告，桌面设置UI未视觉验收。Stage7.5只读预检阻塞；主页仅独立中文草稿未更新正式文件。交付ZIP KernelForge-Stage7.4-O-R5-20261127.zip，112182844字节、555成员（554载荷+SHA256SUMS.json），SHA256 f48490e73798e554f5fff4019b22348244d6d5fccc3d7788fd7e9c313a67bda9，CRC/成员SHA/实际解压均通过；原证据保留，临时汇总目录限定清理。交付扫描原始exit1、2项公开上游文档示例经审核裁定，不改写原命中为0。历史C盘限定清理9807文件、276000568逻辑字节（原有授权仅该次），不构成再次清理授权。

历史会话检索（2026-11-27 00:25:15 UTC 助手交付总结）：T01–T06合并 PARTIAL_PASS；同一554项矩阵统计与R5报告一致，不作为另一次独立回归计数。Python3.11两环境运行BLOCKED，源锁、35项HEAD/clean及1226份证据、232组日志获历史确认；Gitleaks原始exit1的6项公开Git/合成缓存标识经裁定（与R5交付ZIP两项扫描是不同范围，不合并）。无代码修改、提交、推送或真实内核构建属于该T01–T06总结范围，不覆盖R5历史候选修改。仍未取得T01、T02、T03、T04、T05、T06逐项原始任务名称和独立验收合同，不能由R5的core/workspace/review/extensions/stage75/homepage/delivery字段反推编号。

### 13.4 T07 原始专项报告恢复：本地候选代码安全交付

附件 T07_CANDIDATE_EXPORT.md（原报告标题与全文已读）：T07 PASS，仅Git对象导出、差异证据、安全检查。候选100f327120023b70f20f6a6707e2cf5a8daa66e2 / a193f2223bfed0db639fad8d9d93908f9b410eba；远端参考 ccc8f1184d13a78a6d6a35ccae7c6d94cc51380f / 39a1d9173ff4fc885173667dfdc56da9527c9d0d。候选 kernelforge_local_candidate_100f327.zip，256 tracked文件、620698字节，SHA256 4ebc9a8bd2ee1cf87384166dd560cea00b922915bf1d7ac00508f033877dfa29；直接Git blob导出，逐文件SHA1/SHA256/大小、ZIP CRC、路径、Unix mode验证；Archive export-ignore/subst/模式差异0，256项100644、0符号链接。远端227→本地256文件，109差异（80修改29新增、3578新增行554删除行，无二进制差异/既有模式变化）；完整full-index/binary diff，不启用rename/textconv/外部驱动；本地164、远端156独有提交，merge-base exit1无共同祖先证据，未整合。四份锁字节SHA256一致为22cde7f2…e79a7，未重新核验35源码。Gitleaks8.30.1候选扫描exit0零发现；配置环境变量占位符经复核非字面Token，保留裁定，不导出凭据/完整.git/官方源码/缓存。交付包 kernelforge_stage7_4_t07_candidate_export.zip 及相邻delivery.json/sha256；证据 local_vs_remote.patch、两侧tree manifest、git_history_reconciliation.json、source_lock_identity.json、security_review.json、commands.jsonl、evidence_sha256.txt；只读verify_export.py。T07 不等于109文件逐行审计、版本整合或完整新回归。

### 13.5 T08 原始专项报告恢复：KF-SEC-001 Git 所有权保护整改复验

附件 T08_GIT_OWNERSHIP_VALIDATION.md、final-verification.json：T08 PARTIAL_PASS；原候选100f327…/a193f222…，补丁 KernelForge_KF-SEC-001_candidate.patch 3556字节，SHA256 4add75dc6dbca7c1bcc28164ae0413b35206b7f7337e3d5cea46b0d051e2db0b；两平台隔离detached worktree，apply --check后原样应用，仅 git_policy.py/test_git_policy_final.py，working diff SHA256 59db928a07dfec85af2376a3212efe28f8022b15a1c036eaf84864906a9e20e2，测试后字节不变。未提交，原HEAD/Tree不包含修复，不能将其当新Tree。每平台8个定向模块：git_policy_final14、security_hardening31、review_boundaries3、build18、patch_manager3、kernelsu24、stage7_4_fast_build_gate22、exact_gki_validation17；各132执行，Windows129PASS/3跳过、WSL126PASS/6跳过，0失败错误，所有模块exit0，发现集合一致。未重跑554全量。
- 正常/裸/linked worktree/真实子模块/separate gitdir/嵌套/连续-C各平台7项布局探针通过。发现身份不匹配拒绝（模拟返回另一个隔离仓库，不是假称OS重定向）。
- WSL真实异主隔离ext4与NTFS：uid1001读取uid0仓库，原生Git exit128 dubious ownership；固定git-dir/work-tree的旧路径可绕过原生检查（隔离只读复现），修复后在业务命令前抛GitPolicyError。Windows无第二登录令牌，真实异主BLOCKED，模拟覆盖不能替代；没有新增用户、修改ACL/所有权、safe.directory例外或全局配置。
- 首次WSL命令被重启中断，保留INTERRUPTED；恢复脚本只修显示解码，未改补丁；保留全部夹具。最终只读复验300稳定文件、67命令记录、18 ownership探针通过/1阻塞；report SHA256 a192b9ad8e8e6751728aee1818459644d20d5dc364418d0b0d8ef852b499748d。状态 T08_COMPLETE_STOPPED_AWAITING_CHATGPT_REVIEW。正式候选整合需另行全量验收；KF-SEC-001 后续保留真实Windows异主验证缺口，不能宣称全部解决。

### 13.6 T09 本地至云端候选的演化

历史会话检索：2026-11-27 05:22:39 UTC 本地T09 df8ce3a0cc16e08c2ea38d5118571508563a6be1、Tree前缀65d3e00；Python3.12双平台562方法，Windows509PASS/53跳过、WSL554PASS/8跳过、0失败；Python3.11、安全扫描及真实构建待验，PARTIAL_PASS。05:23:24独立复核：原本地差异111文件（81改30增）；源锁混合行尾根因明确。05:39:32云端流程exit2，后续定位Git配置门禁，不等于562单测失败。随后11月27云端最终候选451fb613…扩为113文件（81改32增），四环境568项/2160非跳过通过、112跳过及9/9Job，见§3.1。109→111→113是不同候选的差异规模，不得相互替换；本地562与云端568同理。独立完整语义审计仍未全完。

### 13.7 Stage9 已存在参数的源码核实（不是完整历史合同）

实际读取 T09 交付分支 [build.yml](https://github.com/20592504720/KernelForge/blob/delivery/stage7-4-t09/.github/workflows/build.yml) 和 [release.yml](https://github.com/20592504720/KernelForge/blob/delivery/stage7-4-t09/.github/workflows/release.yml)，可确定现有占位 workflow_dispatch 的精确输入如下：

| 当前字段 | 类型 | 必填 | 选项/默认 |
| --- | --- | --- | --- |
| kernel_version | choice | 是 | 5.10/5.15/6.1/6.6/6.12；未显式写default |
| build_mode | choice | 是 | gki/vendor；未显式写default |
| source_repository | string | 否 | 无显式默认 |
| source_ref | string | 否 | 无显式默认 |
| device | string | 否 | 无显式默认 |
| build_timestamp | string | 否 | 空字符串，描述为current UTC；示例2026-11-24T17:30:00+08:00 |
| artifact_path（独立release.yml） | string | 是 | 无显式默认 |

build.yml当前contents:read、10分钟预检、Python3.12、解析时间并校验后明确停止；名称/描述存在早期占位文字，不能据此断言实际build engine不存在。release.yml contents:read、唯一workflow_dispatch、不可满足条件 github.event_name == 'kernelforge_release_disabled'，保持禁用。以上是已存在代码事实；并非最终Stage9参数契约，不能据此省略Root/功能/缓存/签名/安全门禁。完整历史用户批准字段表仍未找到；未来Stage9第一轮须从历史高层需求、Stage8实测范围、现有Schema及安全合同推导候选并明确与原批准项的区别。中文选项UI、参数格式/组合、默认值、签名及发布行为均不虚构为已批准。

### 13.8 本轮仍未恢复与更新边界

已补齐T07/T08实际报告、T01–T06合并历史结论、R1/R5、O第一批机器证据、T09候选演化、现有Actions七字段、早期起点及分支复用/中文首页历史例外。T01–T06逐项原始指令、Stage9最终完整参数合同、早期用户逐字聊天全文仍OPEN。仓库可读与附件检索权限不意味着可以绕过工具对历史全文/索引的限制。本节历史恢复时的Stage7.5阻塞按§12.1记录；随后实际执行报告已更新为§14，不应再将旧阻塞当作当前状态。用户要求继续增量维护总账，本次不创建新分支、不改变原代码分支、main、PR、源码锁或构建设置。


## 14. Stage 7.5 官方工作区初始化整改与生成仓库新阻塞（2026-11-27 10:38 UTC）

来源：用户最新执行报告及六份上传附件 REPORT_ZH(1).md、checkpoint(6).json、perf_command_review_candidate(1).json、manifest(1).json、verification(1).json、evidence_sha256(5).txt。对应本地证据根 E:/内核构建/reports/stage7_5_official_workspace_initialization_20261127。报告时间 2026-11-27T10:38:26.548452+00:00；检查点更新 10:38:26.675251Z；封存回执 10:38:31.109625Z。此节取代 §12.1 的当前阻塞，但保留历史失败和后续 local_config_platform 限定初始化已消费授权的事实。不构成新阶段、新构建授权或软件全量回归。

### 14.1 已接受的整改范围

- 序列 NOFETCH_QUERY_FAILED_STOPPED；官方源码工作区初始化 PASS，实际新增1个经验证的非 tracked symlink：build/msm_kernel_extensions.bzl → ../msm-kernel/msm_kernel_extensions.bzl。原因是直接调用 Bazel 未执行官方 wrapper 的 setup_extensions()。原文件存在；以不覆盖方式创建并读回目标文本与设备/inode 身份，未改 tracked 内容、权限或既有对象。首次只读检查300秒超时记录保留，补充检查复用已验清单。
- MSM Commit 6028f47faddaa27700f8dd3a1d83906ea8f27170；modules/devicetree Commit d50b305f7da9e14715a25120a4ac7b1a4b8b97c3。三个 Blob：build_with_bazel.py cf8cf4f8505d15ffd9108a8d2bc3093cbf4d58bb；msm_kernel_extensions.bzl 5a5ec8cca6219a810b4d381545e4fe0305f0c7ce；prepare_vendor.sh a1b39fb58f59937c19b08c1e0b8fb9a8bffa3431。报告记录 HEAD/index/工作区字节均匹配。
- ABL 扩展源不存在，不建立悬空链接；已有 Device Tree vendor 链接指向 qcom/opensource/devicetree；oplus/qcom 的 platform_map.bzl 已有且经 Blob 核验，不增加无官方依据的 build/platform_map.bzl。活动 Manifest 两项 linkfile 匹配，无 copyfile，不应用未选 Manifest 的映射。
- Windows/WSL2 保护和清理 PASS；preparation/stage7-5-20261127、原 HEAD/Tree、5个未提交路径、空暂存区不变；tracked 内容、源锁、Manifest、DFR 原链接、既有缓存保护通过。原 local_config_platform 四个文件及输出根复用、摘要一致。原报告中的 no_system_configuration_permission_or_source_changes=false 是非 tracked 链接写入范围的记录，与更精确 no_system_configuration_permission_or_tracked_source_changes=true 并不矛盾。
- 原 Linux 守护器、Windows 提交内存1536/512 MiB门槛、独立监督器、净环境、PID/network namespace及身份绑定清理保持。没有 fetch、完整官方 wrapper、真实编译、设备操作或新增分支/提交/推送/合并；不重复已通过的专项、心跳、源码准入和T09全量回归。

### 14.2 最新阻塞与准入

当前 BLOCKED_GENERATED_REPOSITORY_NOT_INITIALIZED_NOFETCH；图审查 BLOCKED_NO_COMPLETE_GRAPH。首次 query-definitions 返回 Bazel exit 7、清理 PASS；query-deps、cquery-perf-files、cquery-consolidate-files、aquery-core-actions 均 NOT_RUN。该轮1条实际查询、0成功；累计原查询尝试3次、成功0次。错误：External repository @@_main~kernel_toolchain_ext~kernel_toolchain_info not found and fetching repositories is disabled. 生成仓库 canonical 路径不存在。与上一轮官方工作区 symlink 问题不同层次；不能据此判定锁定官方源码不完整或DFR可达性。

对应 kernel_toolchain_ext.bzl HEAD Blob fd0357f3ac0a0f0629d178231ae60cda6ac23404；报告确认工作区字节匹配；第28–30行调用 declare_toolchain_constants.declare_repos 和 declare_host_tools.declare_repos。仅已读取声明，尚未实际执行/审计完传递规则。前次唯一限定仓库初始化授权已消费，additional_fetch_authorized=false、real_build_authorized=false。禁止把错误日志中通用 bazel fetch //... 当获准命令；禁止无条件逐个初始化缺失仓库、开启网络、伪造外部仓库、修改源码锁/DFR 或取消原安全门禁。

perf 草案状态 BLOCKED_REVIEW_DRAFT_NOT_GRAPH_VERIFIED_NOT_AUTHORIZED；authorized/executed/is_final_verified_perf_command 全 false。目标候选 //common:kernel_aarch64/Image、//common:kernel_aarch64/vmlinux、//common:kernel_aarch64_config；make_jobs=2、jobs=1、local_cpu_resources=2、local_ram_resources=2048、JVM Xmx768m、ccache OFF、独立监督器、21600秒上限均只是草案约束，不证明可运行。新日志目录仅在草案中重定位、未创建。须证明实际 DFR 可达性、产物归属、配置生产者、工具链及时间戳 action 链，刷新源码/资源准入后另获真实构建授权。仍非完整一加13 OKI。

### 14.3 封存及 ChatGPT 独立核验边界

报告称旧696文件与三个发布文件逐项不变，新204文件（7434563字节）全部读回无差异。封存文本清单 SHA256 4c50be608eff90a61847fd61689ac3dbafbf3040d6448372d41c76221e6bf5f2；JSON清单 SHA256 9dd8d828fb0ec0905ec062909a1b39b70db89bb13313fdcde9e75cd03b6b3644。ChatGPT 实际计算上传附件原始字节摘要：两份清单均与回执一致、204唯一记录且总大小一致、文本记录与JSON逐项一致；REPORT_ZH.md 6ee84f1240d11897d7b200998c67d8853224e029031932951d2feba72ca6aa69、checkpoint.json 8cb73c8a78ac8c88f129170aa6cca75989307e70ba5e45fb39acb60cf53938e6、perf_command_review_candidate.json b7a6cae3468e197455fadfa019fbf08153870cf8f09ce2c5230663ec7950d372 三份实物与清单匹配。verification.json 实物摘要 211c61281d65513f8034c552a77217c4c8635d42c59ae2f68b3d4808e0329522。其余201封存文件及旧696实物未上传本次，不声称ChatGPT独立全量重哈希。证据路径包含 query-sequence/result.json、graph-review.json、layout-plan.json、initialization/result.json、closeout/linux/blocker-source/、closeout/linux/native-evidence.tar.gz、seal/verification.json；新增链接回退只在设备/inode身份核实后且明确需要时移除该新增链接。

### 14.4 下一步（建议审查合同，尚未授权新的执行写入）

继续归属Stage7.5，不另建阶段或分支。优先进行一次集中只读生成仓库闭包审计：核对锁定的 kernel_toolchain_ext.bzl、两个 declare_repos 声明的实际路径/Blob/SHA256、全部 load/调用、模块扩展与 use_repo、仓库规则实现、主机工具/环境变量/路径及所有读取写入、网络下载和 subprocess 行为。区分本地可确定生成、已锁定可离线复用、需网络或其他授权、未确定/有风险四类，建立完整最小初始化集合及依赖关系，避免每次仅修一个报错后反复试跑。先复用旧封存和收据并核对进程停止；只读阶段不 fetch、不触发 repository rule、不运行查询或完整 wrapper、不改工作区、缓存、系统或源码。提供带精确命令、作用路径、预期输出和失败停机条件的待审初始化合同；实际初始化须另行明确授权。仅在安全准备获准完成、原门禁仍有效且复审通过后续接五项原查询；真实编译继续独立授权。不能预先保证所有生成仓库可离线初始化。若需要新的依赖或系统修改，完整报告原因和范围后停止。


## 15. 云端仓库目录与任务定位索引（2026-11-27）

用户要求熟悉云端所有目录与数据以支持后续任务。本节是实际读取的分支、PR文件清单、分支差异及选定关键文件的导航索引，不是新一轮全量代码语义审计。采用T09 delivery分支作为已交付软件结构的阅读参考，不擅自改变本地Stage7.5工作分支、原开发PR或main；实际修改前仍须核对授权目标HEAD/Tree。本次只写现有docs/project-memory总账。

### 15.1 云端分支与证据关系

2026-11-27实际分支分页读取结果共6个，后续页为空。仓库公开，默认main；当前连接器返回读/写/管理权限，但技术权限不等于用户对任何工程操作的授权。

| 分支 | 职责 | 与原开发分支 ccc8f1184d13a78a6d6a35ccae7c6d94cc51380f 的比较结果（本次快照） |
| --- | --- | --- |
| main | 默认首页，不等于完整开发树 | 不作为构建基线 |
| stage1/initial-foundation | 原主开发分支、PR #1 | 参考基线 |
| audit/stage7-4-t09 | T09审计工作流与证据 | ahead18/behind0，116差异：84修改32新增 |
| integration/stage7-4-t09 | 本地候选整合 | ahead4/behind0，111差异：81修改30新增 |
| delivery/stage7-4-t09 | 云端验收及交付文档 | ahead9/behind0，117差异：84修改33新增 |
| docs/project-memory | 本总账 | 更新本节之前ahead4/behind0，仅1新增文档 |

上述是比较整个分支的差异数；T09验收候选451fb613…的113项代码差异仍是历史固定证据，不能与包含后置交付文档/工作流的117项差异互换。后续不因为分支多而擅自删除或合并。入口：[分支](https://github.com/20592504720/KernelForge/branches)、[PR #1](https://github.com/20592504720/KernelForge/pull/1)、[交付分支](https://github.com/20592504720/KernelForge/tree/delivery/stage7-4-t09)。

### 15.2 模块地图与未来问题定位

本次实际读取关键文件（以下API名为源码索引，非新功能交付）：

| 任务 | 首选代码或数据 | 对应证据/测试入口 |
| --- | --- | --- |
| CLI、配置 | kernelforge/cli.py 的 build_parser/main；configs/defaults.json、schemas/project.schema.json、schemas/build.schema.json | tests/test_config.py、scripts/validate.py、Validate CI |
| GKI/Vendor 构建引擎 | kernelforge/build.py，GkiAdapter/VendorAdapter.plan、run_build、_artifacts、_write_report、_prepare_opt_in_ccache | tests/test_build.py、test_exact_gki_validation.py、test_stage7_3_build_integration.py；官方Kleaf仍需单独验收 |
| Git锁定、源码获取 | source.py checkout/validate_repository；source_acquisition.py acquire_archive/acquire_locked_git/acquire_locked_source | tests/test_stage6_source_acquisition.py、test_stage6_source_archive.py、test_sm8750_sync.py |
| 源码等价、repo工作区 | source_equivalence.py workspace_plan/verify_archive_git_tree；repo_workspace_audit.py audit_locked_workspace；manifests/；scripts/verify_sm8750_sync.py | Stage6原始审计、test_stage6_source_equivalence.py、test_stage6_repo_workspace_audit.py |
| 兼容性准入 | compatibility_gate.py evaluate_reviewed/require_release_eligible | test_stage6_4_compatibility_gate.py；锁定组合而非任意版本 |
| Root/SUSFS | kernelsu.py integrate；susfs.py requirement/inventory/integrate；configs/kernelsu/、patches/compat/susfs/ | test_kernelsu.py、test_exact_gki_validation.py、docs/KERNELSU.md、SUSFS_COMPATIBILITY.md |
| 补丁事务 | patch_manager.py order/lock_series/verify_lock/apply_series/apply_reviewed_operations/rollback_files | test_patch_manager.py、Stage5报告、patch manifest schema |
| 工具链 | toolchains/manager.py ToolchainManager.prepare/release/list_cache/clean_cache；ArchiveSourceAdapter；archive/download/locking/release_mirror | test_toolchains.py、test_stage7_2_release_mirror.py、Stage7.2合同 |
| ccache | build_cache.py verify_identity/cache_key/BuildCacheNamespaces/CacheLease | test_stage7_3_build_cache.py、test_stage7_3_build_integration.py；真实ccache仍OFF，prune默认dry_run不等于自动清理获准 |
| 构建时间 | build_timestamp.py resolve_build_timestamp/kernel_build_environment；scripts/resolve_build_timestamp.py | test_build_timestamp.py、docs/BUILD_TIMESTAMP.md；真实OEM action待验 |
| Git安全 | git_policy.py git_environment/repository_layout/audit_repository/git_command；CI normalize_ci_checkout | test_git_policy_final.py、test_ci_checkout.py；KF-SEC-001保留Windows真实异主限制 |
| 证据安全 | evidence.py write_json/read_json；file_safety.py/path_policy.py（已登记路径，具体实现后续按需审读） | test_review_evidence.py、test_review_boundaries.py；保留原始字节、摘要和不可覆盖发布 |
| Python环境 | python_environment.py locked_requirements/validate_environment/initialize、SID/DACL/密封记录；scripts/environment_preflight.py | test_review_environment.py；隔离离线初始化、显式repair、原失败保留 |
| Stage7.4 | scripts/stage7_4_fast_build_gate.py inspect_policy/sample_capacity/inspect_source/evaluate | test_stage7_4_fast_build_gate.py；软件/源码准入不授予编译权限 |
| Stage7.5 | scripts/stage7_5_artifact_evidence.py inspect_bundle、ELF/时间/普通文件校验；Stage7.5 plan与DFR addendum | test_stage7_5_artifact_evidence.py；合成产物仅完整性证明、真实Action Graph仍待验 |

已实际读取8份关键测试源码并检索方法名称：test_git_policy_final 14、test_stage7_4_fast_build_gate 22、test_stage7_5_artifact_evidence 18、test_stage7_3_build_cache 19、test_kernelsu 24、test_toolchains 62、test_review_environment 23、test_review_evidence 10（静态def test_计数，不是本次运行测试数，也不代表完整发现数量）。重点覆盖原生ownership拒绝、错误锁、预检时间、ELF架构/伪Image、缓存身份隔离、junction、工具链版本与架构、离线环境篡改、原子证据及文件竞态边界。

### 15.3 配置、设备、工作流和文档的实际关系

- configs/defaults.json：jobs=2、reproducible=true；KernelSU/SUSFS默认false，tcp_congestion/zram_algorithms为空；工具链defaults AUTO、require_sha256=true、下载60秒/2重试、cache .cache/toolchains、锁120秒。它们是通用配置默认值，不等于本次Stage7.5可下载授权。
- schemas/build.schema.json 顶层要求 schema_version/source/build/toolchain/artifacts；还支持patch_series、device/device_profile、kernel_version、defconfig、environment、kernelsu、susfs、validation。$defs包含tool/toolchainProfile/adapter/kernelsu/reviewedReleaseLock/ccachePolicy。Stage9须沿实际Schema及新合同设计，不用猜测替换现有键。
- devices/oneplus/pjz110/device.json是早期unverified档案；devices/profiles/oneplus13-pjz110.json是PJZ110/SM8750 6.6官方档案，Manifest oneplus_13_b.xml commit f8e50677874c65b6da41057d2f39be7b4ef3c08a；Ace6 PLQ110独立6.6.118档案，不能混用。一加13固件、ABI/KMI、Root、full_build、device_boot仍待验。manifests/oneplus13-pjz110-sm8750-source.lock.json精确35项目，common e1b346b6b4f4096eb342ae3684838a942fd6f6c4、msm 6028f47faddaa27700f8dd3a1d83906ea8f27170；锁JSON自带历史UNTESTED字段不否定后续有证据的本地源码准入，也不自动升级整个构建。
- SUSFS兼容manifest固定 android14-6.1、ACK6.1.155及三方精确SHA、补丁摘要；其中早期67/67对象与relocatable link证据保留。后续五组完整Image验收另见最终安全报告，不可将6.1补丁直接用于6.6 OKI。
- validate.yml实际是Ubuntu/Windows × Python3.11/3.12四环境；compileall、validate、精确checkout配置清理、行尾锁、YAML、Windows隔离runner及Unix unittest；push、PR、手动触发。stage7-4-fast-build.yml仅手动只读准入，job条件限定stage1/initial-foundation，不因delivery具有文件就认为delivery可dispatch。build.yml仍预检停止；release.yml仍不可达发布门禁（见§13.7）。文档更新也可能触发已有CI，不能宣称绝不触发；未主动启动Actions或重型任务。
- README/STATUS/ROADMAP及T09报告为当前交付状态主要入口；docs/ARCHITECTURE.md、CONFIGURATION.md、DEVELOPMENT.md保留早期设计，部分文字（如Stage1补丁未实施、配置合并规划、build.yml早期占位标题）可能过时。不能用历史描述覆盖真实代码和最新证据；后续中文文档维护时按授权集中纠错。
- docs/BUILD_TIMESTAMP.md与最新ROADMAP明确实际构建开始UTC，preflight仅预览，改变构建时间应参与缓存身份；原历史dispatch语义差异仍以最新批准合同及真实action为准，不在本次自行改策略。
- AGENTS.md要求根因优先、跨代理继承、资源复用、限定清理、版本和SHA256校验、持久化checkpoint及简体中文报告；.opencode/skills下九项项目技能路径已登记，后续按任务读取实际SKILL.md，不把存在路径当成已加载或运行验证。
- 当前Stage7.5本地官方35个子仓库、Bazel output/cache及完整日志在用户电脑/附件，不是KernelForge Python仓库本身；不能从该云端源码框架的目录列表推断所有OEM源码文件已可访问。继续§14生成仓库审计时须读取实际锁定官方文件和本地报告，而非修改KernelForge通用构建引擎来规避Bazel门禁。

### 15.4 可检索文件路径索引

来源为完整PR #1变更文件列表（227项）与开发→交付分支差异（117项）的合并去重，共260个路径、41个直接父目录分组。此索引包括已读取文件及尚未逐字审读文件；PR变更列表不保证覆盖未发生变化的根文件或所有Git对象，不称为独立完整Git Tree遍历。docs/project-memory的PROJECT_HANDOFF.md另属当前文档分支，不混入交付树。后续使用时查实际分支路径并校验HEAD/Tree。

- `（根目录）`（7）：`.gitattributes`、`.gitignore`、`AGENTS.md`、`LICENSE`、`README.md`、`requirements-dev-pins.txt`、`requirements-dev.txt`
- `.github`（2）：`stage5-exact-gki-request.json`、`stage6-full-acceptance-request.json`
- `.github/workflows`（14）：`build.yml`、`codeql.yml`、`history-secrets.yml`、`release.yml`、`runner-disk-pilot.yml`、`security-audit.yml`、`source-audit.yml`、`stage1-6-full-acceptance.yml`、`stage7-1-preflight.yml`、`stage7-2-release-mirror.yml`、`stage7-3-ccache.yml`、`stage7-4-fast-build.yml`、`upstream-validation.yml`、`validate.yml`
- `.opencode`（1）：`opencode.jsonc`
- `.opencode/skills/kernelforge-build`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-documentation`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-environment`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-handoff`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-performance`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-regression`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-release`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-root-cause`（1）：`SKILL.md`
- `.opencode/skills/kernelforge-security`（1）：`SKILL.md`
- `configs`（1）：`defaults.json`
- `configs/features`（1）：`defaults.json`
- `configs/kernels/5.10`（1）：`kernel.json`
- `configs/kernels/5.15`（1）：`kernel.json`
- `configs/kernels/6.1`（1）：`kernel.json`
- `configs/kernels/6.12`（1）：`kernel.json`
- `configs/kernels/6.6`（1）：`kernel.json`
- `configs/kernelsu`（4）：`bakasu-development.json`、`bakasu.json`、`official-development.json`、`official-legacy.json`
- `configs/toolchains`（1）：`defaults.json`
- `devices/oneplus/pjz110`（1）：`device.json`
- `devices/profiles`（2）：`oneplus-ace6-plq110.json`、`oneplus13-pjz110.json`
- `docs`（66）：`ARCHITECTURE.md`、`BUILD_TIMESTAMP.md`、`CONFIGURATION.md`、`DEVELOPMENT.md`、`DEVELOPMENT_TRACKING.md`、`EXECUTION_POLICY.md`、`KERNELSU.md`、`ROADMAP.md`、`SECURITY_FINALIZATION.md`、`SECURITY_FINAL_ACCEPTANCE_2026_11_24.md`、`SECURITY_HARDENING_2026_11_24.md`、`SECURITY_HARDENING_ROUND2.md`、`SECURITY_HARDENING_ROUND3.md`、`SECURITY_HARDENING_ROUND4.md`、`STAGE1_6_FULL_RUN_VERIFICATION.md`、`STAGE45_REPORT.md`、`STAGE5_BAKASU_SUSFS_DELTA_AUDIT.md`、`STAGE5_CLOUD_READINESS.md`、`STAGE5_EVIDENCE_RECONCILIATION.md`、`STAGE5_EXACT_GKI_LIGHT_VALIDATION.md`、`STAGE5_FINAL_ACCEPTANCE_GATE.md`、`STAGE5_HANDOFF.md`、`STAGE5_KLEAF_FEASIBILITY_AUDIT.md`、`STAGE5_LOCAL_CODEX_HANDOFF.md`、`STAGE5_PATCH_SERIES.md`、`STAGE5_REPORT.md`、`STAGE5_THIRD_ROUND.md`、`STAGE6_2_IMPLEMENTATION.md`、`STAGE6_3_BLOCKER_CLOSURE.md`、`STAGE6_3_FINAL_DEPENDENCY_AUDIT.md`、`STAGE6_3_PARTIAL_HANDOFF.md`、`STAGE6_3_WSL2_BLOCKER_DIAGNOSIS.md`、`STAGE6_3_WSL2_REPORT.md`、`STAGE6_4_COMPATIBILITY_GATE.md`、`STAGE6_FINAL_ACCEPTANCE.md`、`STAGE6_PRELIMINARY_HANDOFF.md`、`STAGE7_1_GITHUB_AUDIT.md`、`STAGE7_1_LOCAL_CODEX_HANDOFF.md`、`STAGE7_1_WSL2_ENV_AUDIT.md`、`STAGE7_2_LOCAL_CODEX_HANDOFF.md`、`STAGE7_2_LOCAL_TOOLCHAIN_REVIEW.md`、`STAGE7_2_RELEASE_MIRROR.md`、`STAGE7_3_CCACHE_POLICY.md`、`STAGE7_3_LOCAL_CODEX_HANDOFF.md`、`STAGE7_3_WSL2_CCACHE_AUDIT.md`、`STAGE7_4_FAST_BUILD_GATE.md`、`STAGE7_4_LOCAL_CODEX_AUDIT.md`、`STAGE7_4_LOCAL_CODEX_HANDOFF.md`、`STAGE7_4_O_FINAL_SECURITY.md`、`STAGE7_4_O_LOCAL_BENCHMARK.md`、`STAGE7_4_O_LOCAL_HANDOFF.md`、`STAGE7_4_O_OPTIMIZATION.md`、`STAGE7_4_O_RECONCILIATION_ADDENDUM.md`、`STAGE7_4_O_RESUME_HANDOFF_2026-11-25.md`、`STAGE7_5_ANTIGRAVITY_HANDOFF.md`、`STAGE7_5_DFR_STATIC_REACHABILITY_ADDENDUM.md`、`STAGE7_5_FAST_IMAGE_PLAN.md`、`STAGE7_5_PINNED_OEM_STATIC_AUDIT.md`、`STAGE7_KICKOFF.md`、`STAGE8_EXPANDED_FEATURE_MATRIX.md`、`STAGE8_SCOPED_ACCEPTANCE.md`、`STATUS.md`、`SUSFS_COMPATIBILITY.md`、`T09_CLOUD_ACCEPTANCE_2026_11_27.md`、`WORKSPACE_MIGRATION.md`、`stage7_4_o_review.md`
- `docs/evidence`（20）：`security_final_acceptance_2026_11_24.json`、`stage1_6_full_run_verified.json`、`stage6_3_final_dependency_audit.json`、`stage6_3_wsl2_acceptance.json`、`stage6_3_wsl2_blocker_diagnosis.json`、`stage6_final_acceptance.json`、`stage7_1_cloud_acceptance.json`、`stage7_1_wsl2_environment.json`、`stage7_2_cloud_acceptance.json`、`stage7_2_local_toolchain_review.json`、`stage7_3_cloud_acceptance.json`、`stage7_3_wsl2_ccache_audit.json`、`stage7_4_cloud_acceptance.json`、`stage7_4_local_source_admission.json`、`stage7_4_o_first_batch.json`、`stage7_4_o_local_benchmark.json`、`stage7_4_o_reconciliation_2026-11-25.json`、`stage7_4_o_resume_checkpoint_2026-11-25.json`、`stage7_5_dfr_static_reachability.json`、`stage8_feature_requirements.json`
- `kernelforge`（39）：`__init__.py`、`__main__.py`、`archive_link_proof.py`、`bounded_process.py`、`build.py`、`build_cache.py`、`build_timestamp.py`、`capabilities.py`、`cli.py`、`compatibility.py`、`compatibility_gate.py`、`development.py`、`evidence.py`、`file_safety.py`、`filesystem.py`、`git_policy.py`、`http_safety.py`、`kernelsu.py`、`objects.py`、`patch_manager.py`、`path_policy.py`、`performance.py`、`providers.py`、`python_environment.py`、`real_patch_probe.py`、`repo_workspace_audit.py`、`security.py`、`source.py`、`source_acquisition.py`、`source_archive.py`、`source_equivalence.py`、`source_provider.py`、`susfs.py`、`toolchain.py`、`validation.py`、`versions.py`、`windows_junction.py`、`workspace.py`、`xml_safety.py`
- `kernelforge/toolchains`（6）：`__init__.py`、`archive.py`、`download.py`、`locking.py`、`manager.py`、`release_mirror.py`
- `manifests`（2）：`oneplus-ace6-plq110-sm8750-source.lock.json`、`oneplus13-pjz110-sm8750-source.lock.json`
- `patches/5.10`（1）：`manifest.json`
- `patches/5.15`（1）：`manifest.json`
- `patches/6.1`（1）：`manifest.json`
- `patches/6.12`（1）：`manifest.json`
- `patches/6.6`（1）：`manifest.json`
- `patches/common`（1）：`manifest.json`
- `patches/compat/susfs`（3）：`LICENSE.upstream`、`android14-6.1-498f91c-756abbf.patch`、`manifest.json`
- `schemas`（8）：`build.schema.json`、`device-profile.schema.json`、`device.schema.json`、`kernel.schema.json`、`patch-manifest.schema.json`、`project.schema.json`、`susfs-compat.schema.json`、`toolchain.schema.json`
- `scripts`（18）：`audit_patch_candidates.py`、`audit_sm8750.py`、`check_repository_text_policy.py`、`dependency_lock_candidate.py`、`environment_preflight.py`、`normalize_ci_checkout.py`、`resolve_build_timestamp.py`、`stage5_exact_request.py`、`stage6_acceptance.py`、`stage6_full_request.py`、`stage7_1_preflight.py`、`stage7_4_fast_build_gate.py`、`stage7_5_artifact_evidence.py`、`validate.py`、`validate_upstreams.py`、`verify_sm8750_sync.py`、`windows_test_launcher.py`、`windows_test_runner.py`
- `tests/fixtures/susfs-context`（3）：`adapted.patch`、`metadata.json`、`original.patch`
- `tests/fixtures/susfs-context/fs`（2）：`exec.c`、`namespace.c`
- `tests`（39）：`test_auxiliary_timeouts.py`、`test_build.py`、`test_build_timestamp.py`、`test_ci_checkout.py`、`test_config.py`、`test_development.py`、`test_exact_gki_validation.py`、`test_final_reliability.py`、`test_git_policy_final.py`、`test_kernelsu.py`、`test_patch_manager.py`、`test_real_patch_probe.py`、`test_repository_text_policy.py`、`test_review_boundaries.py`、`test_review_environment.py`、`test_review_evidence.py`、`test_security_hardening.py`、`test_security_round3.py`、`test_security_round4.py`、`test_sm8750_sync.py`、`test_stage46.py`、`test_stage5.py`、`test_stage6_4_compatibility_gate.py`、`test_stage6_5_acceptance.py`、`test_stage6_5_full_request.py`、`test_stage6_archive_link_proof.py`、`test_stage6_repo_workspace_audit.py`、`test_stage6_source_acquisition.py`、`test_stage6_source_archive.py`、`test_stage6_source_equivalence.py`、`test_stage7_1_preflight.py`、`test_stage7_2_release_mirror.py`、`test_stage7_3_build_cache.py`、`test_stage7_3_build_integration.py`、`test_stage7_4_fast_build_gate.py`、`test_stage7_4_o_performance.py`、`test_stage7_5_artifact_evidence.py`、`test_toolchains.py`、`test_windows_test_launcher.py`

### 15.5 后续使用及核验边界

任务开始：先总账当前状态→目标分支README/STATUS/ROADMAP→对应阶段合同及evidence JSON→对应Schema/配置/实现和测试→原始日志/Commit/Tree。Stage7.5优先§14及当前附件；Stage8使用S01–S10及D01–D14矩阵；Stage9从真实build/release工作流、Schema、已验证设备范围和发布合同设计。文件名索引帮助快速定位，不是运行测试结果；此轮未独立逐行审计所有文件、未重新运行测试、未验证真实编译、未改变代码或阶段状态。当前最新阻塞仍按§14，后续只有新证据才更新。用户要求长期熟悉云端内容，每次工作按需读取最新版本并增量修正总账。


## 15. Stage 7.5 生成仓库闭包集中静态审计（2026-11-27 11:08 UTC）

来源：用户上传 REPORT_ZH(2).md、REPOSITORY_MATRIX_ZH.md、INITIALIZATION_CONTRACT_ZH.md、HANDOFF_ZH.md、verification(2).json。执行报告11:05:50.900594Z，封存11:08:43.464157Z；本地证据根 E:/内核构建/reports/stage7_5_generated_repository_closure_audit_20261127。独立复审接受限定静态审计范围，不接受初始化、图证明或真实编译准入。根因仍 BLOCKED_GENERATED_REPOSITORY_NOT_INITIALIZED_NOFETCH；合同 BLOCKED_NO_ADMISSIBLE_INITIALIZATION_COMMAND_UNDER_UNCHANGED_NOFETCH，initialization_argv=null、authorized/executed/is_runnable_contract=false。累计原查询3尝试0成功不变，本轮初始化/fetch/查询/编译/下载均0。

- 报告收集520文件、2769677字节，483官方文件绑定source.lock Commit/HEAD及index Blob/工作字节SHA256，37缓存文件另列。入口 kernel_toolchain_ext.bzl Commit d50b305f7da9e14715a25120a4ac7b1a4b8b97c3、Blob fd0357f3ac0a0f0629d178231ae60cda6ac23404、SHA256 7c0ccb101a0f12058dddccedd74cd29432206a14fbe3d95d6287cdcb27105792；declare_toolchain_constants Blob869efc9c082a5e6cc1b544ffc452fbd618f72ed0/SHA256 5a05169e5dfaad1ce35baed819d15fdc34bd53ba4c107a72f0fc00b0383329ee；declare_host_tools Blob a4b207ff9517e47979dba497d0b2af41ba22f4ff/SHA256 ac252f8caab9a5692720add500cae229715594e47272ffde10d6fe385a0c8125；Clang独立预编译Commit b099698c583b8361ca771f3cc8d6af6f729f39b3。
- 核心三仓库：kernel_toolchain_info 读取common/build.config.constants四常量、写BUILD/dict.bzl，无execute/download，生成BUILD依赖bazel_skylib；kleaf_clang_toolchain 默认无KLEAF_USER_CLANG_TOOLCHAIN_PATH时仅生成WORKSPACE/BUILD，依赖常量及本地锁定Clang；kleaf_host_tools 默认PATH=/usr/bin:/bin，对bash/perl/rsync/sh/find只which与链接，sh→dash。CLANG_VERSION=r510928、AARCH64_NDK_TRIPLE=aarch64-linux-android31、X86_64_NDK_TRIPLE=x86_64-linux-android31、ARM_NDK_TRIPLE=arm-linux-androideabi31，不证明实际action工具链。
- 独立重计81行 A13/B11/C46/D11（含动态仓库族，非实际闭包仓库总数）。A=核心三仓库+host_platform+九个本地覆盖libcap/libcap_ng/lz4/toybox/zlib/zopfli/pigz/prebuilt_ndk/dtc；B=既有11个external映射/embedded_tools/local_config_platform，仅有限身份复验；C=未物化Java/JDK及14 Python wheel等；D=Python解释器族（含下载zstd后make --jobs=4）、local_config_cc编译探测、local_jdk执行探测、Apple条件分支及其他未确定族。A不是执行许可，B不是完整缓存逐字节验证；C/D未证明实际可达，禁止自动放行。--jobs=1/--make_jobs=2不约束repository_ctx.execute内部并发。
- 静态识别30 repository_rule、11 module_extension、249操作候选。初始926 load边/119未解析，修正984边/27原始未解析，新增17帮助/覆盖文件；保留原始错误与静态缺口。Python AST不等于Starlark/Bzlmod实际求值，不能声称完整实际依赖图。DFR/产物归属/配置生产者/action工具链/时间戳仍BLOCKED；perf草案三个授权执行验证字段false。
- 资源门槛：E/ext4启动70/40 GiB、停止55/25、保留50/20；inode启动1000000/停止100000；MemAvailable1536/512 MiB、SwapFree512/256、Windows提交余量1536/512；JVM768m、make_jobs2/jobs1/CPU2/RAM2048、ccache OFF。原五查询600/900/1200/1200/1200秒；历史argv/日志路径不得直接重用。原网络隔离/禁下载/净环境/进程守卫保持。报告称双平台HEAD/Tree、preparation分支、5未提交路径、空暂存区、源锁/Manifest/DFR/源码链接/所观察缓存及历史204/696和发布文件均不变。
- 封存回执PASS，1099文件11336439字节、无差异；文本清单SHA256 cdf8bef695e9136da14c02651b28a73dbeeb90906289794ab166530020b39c3d；JSON清单65f0f48d02bc4414cfea08dd9e1a421b47bd6408b358b77531968e6ae1285046。ChatGPT实际读取五附件并独立计算SHA256：REPORT 149bf81d2d629813e7cc404b50d87f41ca4f64809bb68764feec139d6703db61；MATRIX bf066cbe14108e49a0105ee7457b9f825c1a7353b0ef6356f55822952dd1da08；CONTRACT 25f6cb1fd9cb16de7b10f43059f1dca36f0a46888f9f192f82206fe08d102e4c；HANDOFF ab94975aa983232ae4a168875ab2d82a2975a576581424274871180703c18b53；verification 941fe0bed84c6790585dfa2c1a10d0562cf94fb9333ac047994cfb7f09d37b35。未上传完整1099文件及两份manifest，不能独立验证全封存或五附件与封存摘要的匹配；不能声称源码483文件已由ChatGPT独立重验。

### 15.1 下一步决策（建议，非已授权）

不重复闭包静态审计。Bazel fetch语义包含本地repository rule物化，并不等于必然联网；nofetch对当前缺失仓库阻止物化。官方文档 https://bazel.build/versions/9.2.0/external/faq 描述指定仓库fetch --repo；不能把新版说明当作锁定本地Bazel支持证据，必须核实实际二进制身份、版本、帮助、wrapper和精确repo映射。建议用户明确授权一次性限定初始化例外，仅允许经复审A类必要仓库在独立受控输出根中物化，B类可信只读输入，拒绝C/D、未知仓库、未授权execute/编译/下载/系统写入；不得执行 broad fetch、--force、repo sync、手造marker、全量wrapper或改生产源码。保留网络隔离、禁下载、无远程缓存/执行、资源守卫；仓库规则自身须有可实施的阻断机制，不仅事后日志；若现有工具无法强制仓库/进程/文件边界或实际版本不支持限定命令则停，不能放行。隔离输出根策略须考虑完整缓存复制、绝对路径、marker和Bazel元数据，不直接拼接external或把生成结果盲移生产缓存。仅获用户明确授权后进行最小指定仓库初始化并复验，如通过再恢复原nofetch五查询（须覆盖当次查询授权），任何非零或未知依赖停止。真实编译、网络下载及C/D实际探测另行审批。此为整改建议，不意味着历史合同已可运行或用户已授权。原项目阶段、分支、PR/main及历史证据保护保持。


## 16. Stage 7.5 最后一轮集中整改与 Stage 8 条件启动（2026-11-27）

用户最新明确指令原文：“7.5最后一轮修复，这一轮要求全部修复完成，然后开始第八阶段”。

执行制度更新：此轮以 Stage7.5 全部验收目标为核心，集中处理依赖准备、受控生成仓库物化、真实五项查询、图审查、一次真实锁定官方 fast Image/vmlinux 构建、产物及安全验收、中文主页更新与Stage8交接。禁止继续人为拆分静态审计轮次、逐项例行停机、重复既有有效证据。普通故障在获准范围内自主定位、修复并按影响复验，必要的内部步骤不是新轮次。用户要求全部完成并随后启动Stage8，不表示当前已完成或允许虚报，亦不等同于不受限网络/系统/设备/发布权限。

以§15的真实BLOCKED状态起步，保持历史1099/204/696封存及源锁、Manifest、DFR、工作区、PR/main保护。拟交执行端的一次性集中合同将明确所需的最小仓库物化权限、独立输出根、精确身份及可执行约束，处理已证明必要的固定来源依赖或有限本地工具探测时应在用户实际发出的合同授权范围内实施。不得擅自启用未知动态规则、任意联网下载、系统安装或降低安全门禁。原资源限制保持；若缺少安全可执行机制、关键依赖身份或发生超范围风险，必须如实停止并一次性报告全部已知阻塞，不能循环重试或自动增加阶段。

Stage7.5 必须按 docs/STAGE7_5_FAST_IMAGE_PLAN.md 的 A–F 合同通过：实际图及DFR、工具链/时间戳、资源守卫、单variant实际编译exit0、真实Image/vmlinux/.config/log/build-time及独立溯源核验、最终软件回归及报告。默认构建时间按当前正式Stage7.5/8文档为实际编译开始UTC，历史dispatch差异继续保留供对账；自定义含时区ISO8601且验证实际action传递，不伪造时间或重复重型构建只为测试参数。源锁历史字节摘要冲突须依据可信证据核验，不静默re-pin。离线产物收据ARTIFACT_BYTES_CHECKED_BUILD_UNATTESTED不是编译证明。T09历史通过和残余独立语义审计/安全边界不得混淆，所有影响构建准入的缺口必须解决。

Stage8 条件启动：仅在Stage7.5全部强制门禁通过、真实证据完整且按合同独立验收后，依据用户本次批准启动Stage8第一轮；不新增中间阶段，不先行集成增强功能。Stage8第一轮按 docs/STAGE8_SCOPED_ACCEPTANCE.md 和 docs/STAGE8_EXPANDED_FEATURE_MATRIX.md，从S01完整官方OKI参考基线、固件、厂商模块、DTB/DTBO、ABI/KMI、DFR适配入手，随后按依赖顺序集中实施S02–S10既定范围。不得把fast common Image当完整OKI，不重启D01–D14；设备启动/Root实际验证须单独硬件授权及恢复方案，签名/发布/OTA按Stage9门禁另行授权。Stage8仍遵守最多两轮集中执行政策，不因本轮条件启动而自动宣称实施或验收完成。

中文README、STATUS、ROADMAP、仓库简介及待实现功能清单必须随阶段验收更新，保护默认分支及原开发PR，未经明确对应写权限不改main。总账长期增量记录实际结果、Commit/Tree/Run/证据及未验证事项。本次仅更新文档；未执行本地命令、物化、查询、编译或Stage8代码变更，当前仍为§15所记BLOCKED。详细执行指令需由用户实际交给有本地能力的执行端，授权范围按当次明确合同执行。

### 16.1 运行中观察（2026-11-27 21:32 UTC+8，用户截图，尚未独立验收）

本地执行端界面报告五项真实 --nofetch 查询及构建前准入已通过、35源码项目身份匹配且 tracked 文件干净、锁定 common perf 进入 Bazel build；Make 2/Bazel 1/ccache OFF、网络隔离及官方安全配置保留。首次启动在 Bazel 前因目录检查错误停止，执行端称已修复并保留失败记录。截图显示 Shell 已运行42分48秒，仍在等待构建回执，未确认 Image/vmlinux 成功，Stage8未启动。仅为运行中界面报告，不将查询或构建标为独立验收PASS；待取得五查询原始收据、实际进程退出码、日志、产物和时间戳证据后更新正式状态。若仍有进程/日志进展，不因40分钟耗时中断；只读检查心跳、子进程、资源、日志增量与守卫，不重复启动或放宽资源门槛。沿用当前已获准执行轮次，不新增阶段或任务。


### 16.2 并发构建策略调整（用户新增要求，2026-11-27）

用户原文：“改为多进程并发构建”。记录为本轮及后续构建的并发优化要求。当前运行中的 Stage7.5 基线据截图使用 Make 2、Bazel 1，本身已有 Make 层有限并行，不能将其称为全串行；运行中的构建参数不能由 ChatGPT 远程热修改。建议优先让已有基线自然结束，保留真实冷构建性能证据；如果需要立即切换，须由本地执行端确认当前进度、受控停止并验证进程树完全退出、保留日志/输出与缓存、重新准入后才启动单个新构建，禁止同时启动第二个重型构建。后续采用资源感知的多进程：在实测 CPU/cgroup、可用内存/swap、Windows提交余量及磁盘门槛均符合原合同且有证据支持时，Make 4/Bazel 1 为优先候选；资源不足回退 Make 2，不默认-j8，也不同时扩大两层并发。实际 Bazel local resource 参数应与选定配置及守卫一致，不能仅改线程参数而绕过内存/资源限制。保持源码/工具链/配置/时间戳身份、网络隔离、ccache OFF（Stage7.5）、原安全选项与阶段门禁。任何提速结论须有真实对照，不将并发候选视为已生效或已验收。本次仅记录用户要求和建议，不代表本地构建已修改、停止或重新运行；待执行端实际报告更新。


### 16.3 资源感知策略交付与真实基线容量阻塞（2026-11-27）

来源：用户上传 RESOURCE_AWARE_BUILD_POLICY.md（实物SHA256 deffa7a193b37c2ba4a163aa273abb19b872afc6d4a643568b88ef47d29a526b）与 FINAL_REPORT.md（196662dfb97029473ac075885cce72b042794716db38ee42bcf53ca328edfdb5）。本次ChatGPT读取并计算两份附件摘要，接受报告所述软件策略限定范围通过；原始补丁、测试日志、完整采样及封存清单未随本次上传，不能声称独立复跑36测试或逐文件核验。

- 当前真实构建BLOCKED，先前§16.1运行中观察更新为：Make2/Bazel1基线运行3049.913秒（50分50秒），MEM_AVAILABLE_LOW受控停止、清理PASS，Image/vmlinux未完成。pahole BTF阶段实际-j1，VmHWM 2221944832字节（约2.07GiB），构建进程RSS合计峰值3142443008（约2.93GiB，可能重复共享页），WSL最低MemAvailable378163200（约361MiB），Windows最低提交余量561614848（约536MiB），接近512MiB硬阈值。守卫子进程exit130、Windows监督器exit2；Bazel独立退出回执未完整落盘，不冒称Bazel退出码。直接触发点为BTF阶段内存不足，不足以确认所有分配成因或实际内核OOM事件。旧基线CPU/I/O样本不完整，禁止补造。
- 用户要求的资源感知并发策略据报告已实现：Bazel1，Make4优先、Make2回退、两档不足则BLOCKED，Stage7.5/8/9统一使用。kernelforge/resource_policy.py、resource_sampling.py、host_resources.py、resource_monitor.py及本轮独立监督器入口更新；Windows/WSL2 Python3.12各18/18通过、0跳过，真实计数器读及模拟回退控制通过，初版模拟失败保留。未真实执行Make4，性能UNVALIDATED。当前约3.77GiB WSL环境未通过Make4，Make2同容量失败尚未重新准入，无新内核任务。
- 启动至少7连续有效样本覆盖30秒、间隔<=10秒、最后样本距派发<=10秒，双平台真实指标齐全。Make2最低MemAvailable2560MiB、SwapFree512MiB、Windows提交余量1536MiB；Make4额外WSL总RAM>=8GiB、可用>=6GiB、Windows提交余量>=4GiB、有效CPU>=4、WSL/Windows忙碌率<=75/80%、iowait<15%、磁盘忙碌<85%、IO PSI avg10<10%、E盘平均队列<2且延迟<30ms；两档E/ext4启动70/40GiB、inode1000000。硬停止MemAvailable512MiB、SwapFree256MiB、Windows提交余量512MiB、E/ext4 55/25GiB、inode100000。Make4连续3样本压力触发STOP_THEN_READMIT_MAKE_2：MemAvailable<1536、SwapFree<512、Windows提交余量<1536MiB，或IO iowait>=25%、busy>=95%、PSI>=20%、Windows队列>=4/延迟>=50ms。运行约每5秒采样、boot/PID/start ticks身份绑定、单构建锁、原守卫及Landlock、network/PID namespace、nofetch、官方配置/BTF、ccache OFF均保留。CPU高本身不触发回退。无热切换；清理PASS、身份复验及新鲜准入后才接续。原生Linux CI须实现真实主机容量适配，不能伪造Windows指标。
- 性能合同：当前策略文档要求每档至少2个完整成功样本，历史O5已要求至少3次对照，正式O5性能验收保留较严格的历史合同，不因策略文档最低值自动降低；Stage7.5一次成功基线与后续性能对照是不同门禁，不为测速度无意义重跑。缓存有效性按实际Kleaf/Bazel action判定，不保证无损断点续编。
- 证据根 E:/内核构建/reports/stage7_5_final_acceptance_20261127/resource-aware-concurrency；final-report.json、baseline-resource-analysis-v2.json（1513资源样本、7585进程树样本）、admission-window.jsonl、policy-selection.json、final-build-state.json、verification/、resource-policy-only.patch、full-worktree.patch、prior-runner-sources/、final-runner-sources/、evidence-manifest-v2.json、checkpoint.json。初版封存摘要含写入中stdout，原件保留，v2替代。Stage8/9未启动。
- 下一步先确认宿主机物理RAM、真实提交限额/已提交/余量、分页文件、.wslconfig现状、WSL实际cgroup限额、内存占用与磁盘，再评估容量调整。若宿主机有足够物理内存与提交空间，优先考虑为WSL分配至少8GiB并保证宿主机余量；若容量不足，降低并发或增Swap本身不能保证BTF成功，不盲重试。系统配置修改、扩容Swap、WSL shutdown或额外硬件/云构建需要相应用户授权，先形成最小变更及恢复方案；不禁BTF、不降低原阈值、不清缓存、不重放旧任务。通过新准入才启动下一次单构建。保留Stage7.5最后一轮目标及Stage8条件启动，当前不得标完成。


### 16.4 宿主机物理容量确认（2026-11-27，用户系统信息截图）

用户确认宿主机仅8GB DDR3（系统可用物理总量7.88GB），Intel Core i7-4770K 4核8线程，GIGABYTE G1.Sniper Z87，Windows11 Pro Insider Preview。7.88GB是可用物理总量而非当前空闲量；当前提交限额、分页文件、磁盘类型及空闲量仍需实测。截图中的设备/产品ID不归档。现有Make4门槛要求WSL总内存>=8GiB，故该宿主机不适合本地Make4试验，暂以Make2为目标，不降低门槛。建议先只读审计Windows物理及提交内存、分页文件、WSL配置和各磁盘，确认无运行任务；若资源支持且用户授权，备份并合并.wslconfig现有配置，试验memory=5GB、swap=4GB（磁盘适合时可评估6GB）、processors=4，保留其他设置，必要时将swapFile指定到经核验有足够空间的SSD，Windows分页文件保持系统管理并检查提交余量。该配置是候选，不是已通过容量验证；避免同时用光宿主机内存，WSL shutdown前保存所有任务并确认授权，重新采样满足Make2门禁才启动单个构建。若仍不足，优先评估升级16/32GB DDR3（主板官方规格4槽最高32GB，实际修订版、插槽及条型另核实）或有足够资源的原生Linux/云端构建方案；任何新环境/费用/系统配置修改须相应授权。不得禁用BTF、清缓存或强行重试。Microsoft WSL配置参考 https://learn.microsoft.com/windows/wsl/wsl-config ，主板规格参考 https://www.gigabyte.com/sg/Motherboard/G1Sniper-Z87-rev-11/sp 。当前仍为§16.3容量阻塞，未执行配置修改或新构建。


### 16.5 低内存构建及后台资源释放（用户新增要求，2026-11-27）

用户明确说明升级物理内存不现实，愿意接受更慢的构建，并授权执行端关闭不影响正常运行的非必要后台项目及第三方应用。拟在既有资源感知策略中增加LOW_MEMORY/Make1候选档，Bazel1、pahole原-j1、ccache OFF、BTF及官方安全配置不变；Make4/2原门禁保留，Make1须新增经过实测支持的容量准入、独立测试及守卫集成，不能通过降低原硬停止阈值获得准入。Make1降低并发峰值而不能消除pahole单进程内存需求。优先正常退出已确认无未保存内容、无活动任务、非执行链依赖的用户态应用（空闲浏览器、聊天/游戏启动器、非必要托盘应用等），暂停安全可恢复的非必要同步任务；逐项记录PID/start身份、路径、用途、依赖、关闭方式及前后物理内存/Windows提交余量，未知或不可确认安全的一律保留。保留Windows核心进程、系统服务及安全组件、驱动、网络/代理、OpenCode/执行端及全部监督器、WSL/虚拟化、文件系统、远程连接、用户正在使用或含未保存数据的程序。禁止批量强杀、关闭安全防护、永久更改服务启动项、注册表清理或清缓存。用户授权仅限安全释放后台资源，不自动授权修改系统配置或中断其他任务。先释放资源、核实分页文件与WSL容量；如仍不足，按§16.4提出可回滚的5GB RAM/4–6GB Swap候选，实际调整及WSL重启须对应授权并确认所有会话安全停止；Swap须检查SSD与磁盘余量。微软配置依据 https://learn.microsoft.com/en-us/windows/wsl/wsl-config 。建议按实际进展核定较长构建超时（例如12小时上限为待批准候选），保留心跳、硬资源门槛及无进展诊断；不能以延长超时掩盖停滞。先完成资源准入再启动单个低并发构建，尽量复用有效Bazel/Kleaf缓存但不保证无损断点；容量仍不够则停止报告，不反复在相同条件下重试。此调整归属Stage7.5最后一轮，后续Stage8/9可复用经验证低内存档，不新增阶段，不提前启动Stage8。本次只更新云端总账，未执行Windows后台关闭、配置修改、代码实现或新构建。


### 16.6 跨主机构建迁移方案（用户提出，2026-11-27）

用户提出将所有项目相关文件以尽可能高的无损压缩率打包，携带到单位电脑继续构建；目标电脑据用户估计为16GB内存、更强CPU，尚未实际核验。此为替代当前8GB宿主机容量阻塞的候选方案，优先迁移准备，不代表已打包、已获单位IT许可、已配置目标机、已完成构建。迁移前确认单位允许个人项目、外部存储介质、WSL/虚拟化及所需资源，不绕过企业安全策略；未经许可不传输或运行。不得携带个人API Key、SSH私钥、Token、浏览器数据、与项目无关资料或单位数据。原家用电脑工作区和所有历史证据完整保留。

迁移范围：Windows E:/内核构建中相关工程、全部必要Git对象/refs/index及worktree关联、未提交与未跟踪成果、脚本/配置/锁、完整历史报告/日志/封存；WSL ext4内35项目官方源码、.repo及Git对象池/alternates、符号链接/硬链接/权限/UID/GID/xattr/ACL等必要元数据、工具链、已锁定Python环境与依赖、Bazel/Kleaf输出根及有效缓存和失败中间成果。须追踪绝对路径、Git worktree/common-dir与repo对象池，不按目录名推断完整；原有凭据配置、套接字、活动锁、机器身份、无关系统数据须隔离或排除并记账，不能删除源文件。禁止在活动构建期间打包、跟随链接重复复制、全量导出含私人凭据的发行版或直接把Linux树解压到NTFS。完整发行版导出仅适用于经过隐私与权限审核的专用环境，Microsoft参考 https://learn.microsoft.com/en-us/windows/wsl/basic-commands 。

先只读统计逻辑/实际占用、文件数、硬链接组、稀疏文件、压缩样本、源/输出/恢复临时空间及移动介质文件大小限制；若空间不足停止，不清理原数据。推荐分区归档：Linux tar（保留必要元数据、不dereference，GNU tar支持情况先核实）+XZ -9e单线程，按资源限制设置内存上限并实测，Windows 7z/LZMA2 Ultra固实压缩（字典/线程受8GB宿主资源约束，必要Windows链接/ACL/ADS另作清单及可恢复归档），不同数据类型小样本比较，选实际最小且可安全恢复的配置；不承诺任何算法绝对最小，已压缩对象可能收益有限。按传输介质需求分卷；在独立输出目录生成SHA256SUMS、文件级SHA256/类型/模式/链接目标/对象身份清单、归档测试及恢复说明，记录排除项和原因。不得改变源锁/源码或原历史证据，不重复跑真实构建。对完整归档逐项读回，条件允许在隔离位置实际恢复验证；空间不足时仅作流式全成员核验并明确未实解压限制，不冒称完整恢复通过。授权的安全工具可用于归档，缺失软件另行确认，不擅自安装或联网。敏感项目材料按获准加密方案保护，校验清单与密钥分离。

目标机先核验实际RAM/CPU/Windows提交余量/磁盘/WSL版本和单位许可，保留现有单位环境，使用独立发行版/目录，尽量复现原Linux绝对路径、UID/GID及Windows映射（若盘符不同，使用审核后的路径适配而非批量替换）；验证Git worktree/alternates、35源码锁、工具链、资源守卫、报告目录、时间戳及缓存身份。Bazel/Kleaf缓存、Python venv和未完成action可能依赖主机/绝对路径，禁止直接复用失效锁、marker或盲移缓存；验证后复用，必要时隔离重建相应缓存，不保证断点续编。16GB宿主机可先评估WSL8GB、Swap4GB、Bazel1、Make2/4按真实采样选择，保留BTF和所有原门禁；不默认Make4通过。待恢复验收、资源准入与实际图/命令证据匹配后继续当前Stage7.5最后一轮真实构建，不新增阶段、分支或重复有效回归。Stage8仍以7.5全部强制门禁通过为条件。归档不是构建成功证明；本次仅更新总账及迁移执行建议，未在本地执行打包、移动、安装或构建。


### 16.7 迁移后集中执行与三轮上限（2026-11-27 用户决定，拟于2026-11-28接入新主机）

用户原文：“明天所有当前电脑无法完成的事情，都优先在运行内存16G电脑接入后去安排完成，不计时间，追求尽可能一次性通过。如果一次性不通过，最多有第二轮和第三轮，不可出现第四轮”。

适用范围：此次8GB主机无法完成、迁移至预计16GB主机后接续的全部已批准任务，尤其Stage7.5真实构建、资源/环境相关阻塞、尚缺的真实图与产物验收证据及最终回归。新主机实际资源与单位许可须先核验；迁移包实际完成及恢复状态待报告。本要求优先于为原8GB主机继续尝试LOW_MEMORY的方案，不在旧机重复重型构建。Stage7.5最后一轮的目标和Stage8条件启动保持；迁移接续最多三次集中执行/验收批次，不人为重新编号开发阶段，不借此自动扩大Stage8/9原有各最多两轮政策、功能范围或发布授权。

- 第一轮：集中核验迁移包、恢复环境、OpenCode及Provider、Git/源码/工具链/缓存身份、宿主容量和单构建锁；一次性处理所有已知阻塞，按依赖顺序执行真实构建、验证产物、软件与安全回归及中文文档交付。已有效证据经身份匹配复用；普通问题在授权范围内自主修复并复验，不以内部命令/步骤/日常检查另计轮次。不为赶时间缩减验收；保留安全停止、心跳、资源和合理超时，不因“不计时间”取消守卫。
- 第二轮仅在第一轮未通过时启动：集中定位第一轮全部剩余问题、整改及影响范围回归，保留第一轮完整证据，禁止同条件盲目重试。
- 第三轮仅在第二轮未通过时启动：最终集中修复及完整收口验收。仍失败则封存、明确未完成/阻塞及根因，停止，不存在第四轮、不换名规避上限、不虚报PASS；需用户另行决定项目处置。
- Stage8仅在Stage7.5强制门禁全部通过后按已批准S01–S10范围启动；Stage9仍依赖前置验收。设备刷写、发布、付费资源、单位系统权限变更及超范围操作保持原独立授权。不得把单位资料发往第三方AI服务或将个人凭据写进迁移包。
- OpenCode迁移补充：保留实际可用的XingChi Provider ID、Base URL、接口协议、模型ID及能力、推理档、MCP/Skills及项目规则的脱敏配置，恢复脚本先备份并合并目标机已有配置；安装匹配版本并人工录入API Key、重新授权GitHub，实际测试模型及工具调用。不得自行切换为历史出现503的Responses协议，不在归档/日志/公开仓库中携带API Key、Token或SSH私钥。该补充此前已向用户提出，尚未确认本地实施。
- 每轮必须有原始命令、退出码、完整日志、代码/配置版本及差异、资源样本、安全检查、产物SHA256、工作区保护和恢复检查点；完成即停止额外重跑。总账、README/STATUS/ROADMAP、待实现功能及阶段状态按实际验收同步，未经授权不修改main或合并PR。仅记录本次用户决定；ChatGPT未连接目标电脑、未在本地启动任务，也不承诺明日自动执行。


### 16.8 单位电脑实测硬件纠正（2026-11-28 08:34 UTC+8）

用户提供目标机系统信息截图：i5-12400（6核12线程）、8GB DDR4-3200（系统可用物理总量7.77GB），H610M K DDR4，238GB可见SSD容量、已用103GB、剩余约135GB（全盘显示值，具体卷可用量待验）。纠正§16.6–16.7此前预计16GB的假设：目标机CPU较家用i7-4770K更强，但物理RAM仍仅8GB，不能按16GB宿主机或Make4已准入处理；截图不提供当前空闲RAM、提交余量、WSL安装状态及工作区恢复容量。禁止归档设备/产品ID等无关标识。迁移三轮上限仍有效，不因发现容量不足盲目消耗执行轮次。优先只读核验实际各卷、归档体积/解压后实际分配量、WSL VHDX增长/Swap、原70GiB宿主物理及40GiB ext4启动余量、单位许可和可用资源。目标机本地SSD在保留70GiB启动余量时仅约65GB可供新增占用（显示单位为近似GB，须按字节/GiB实测），完整迁移是否容纳未知；不要把整个包直接解压C盘。若有经单位批准且空间足够的外接SSD，可评估独立WSL ext4 VHDX/Windows工作区放置其上，不直接在NTFS解包Linux源码，不擅自移动单位文件。若迁移容量和资源准入均满足，可评估§16.5低内存Make1/2、Bazel1、WSL5GB/Swap4–6GB候选及完整BTF安全配置；不能保证解除pahole单进程内存瓶颈，不能自动放行Make4。若无法满足则保留原机归档，优先评估经授权的更大内存主机或云端构建；未在目标机执行安装、修改或编译，Stage7.5仍BLOCKED，Stage8未启动。


### 16.9 租用远程主机部署（2026-11-28，用户确认已购买）

用户在比较云电脑与私人机房实体远程主机后确认已购买租用服务，要求部署。实际套餐、租期、OS、CPU、内存、存储、管理员权限及独享性质尚未确认；不得将此前推荐的套餐6/E5-2696 v3/64GB/500GB当实测。优先采用Windows+WSL2以复用已审的双平台守卫；若仅支持原生Linux，则须真实适配Linux资源/监督器及路径而非伪造Windows计数器。迁移前只读验收硬件、虚拟化、可用磁盘、持续负载/断连策略、网络与租期；确认许可及管理员权限。容量计算覆盖归档/解压/临时数据/VHDX实际增长及现有70GiB物理、40GiB ext4启动余量，禁止默认500GB足够。实际迁移包尚未见最终封存报告；先取得并验证分卷/成员清单和恢复脚本，优先恢复代码、锁定源码/对象池、工具链/必要依赖、报告，缓存按身份与空间择机恢复，不清除原机数据、不保证跨主机断点续编。保持Linux ext4及原绝对路径/用户身份；仅完整合法发行版tar使用wsl --import，项目tar.xz在已建立的Linux发行版内按审计清单恢复。若实测64GB可候选WSL memory=40GB、processors=16、swap=8GB，保留其他配置，实际按宿主余量调节；Make4/Bazel1先行且须通过现行门禁，不擅自提高至8/16。OpenCode安装匹配版本并恢复脱敏XingChi Provider配置，先用非敏感测试验证模型/工具。私人出租主机管理员有潜在读取/篡改能力，不上传长期API Key、主账号GitHub令牌/SSH私钥、签名私钥、私人或单位数据；如必须远程调用API，用可撤销、低额度、最小权限临时凭据，退租撤销，优先本机持有Git写权限及最终签名。上传使用经授权的安全传输并逐项核验哈希；云主机上的自报校验不能独立证明可信度，产物下载到可信本机复审。保留BTF/官方安全配置/单构建锁/资源守卫及nofetch；先复核迁移影响、实际五查询和构建准入再执行Stage7.5锁定基线；Stage8仍条件启动。§16.7迁移遗留任务最多三轮不变；Stage8/9既定政策不变。部署建议未实际执行远程命令、软件安装、传输、构建或支付；当前Stage7.5仍未验收。Microsoft参考 https://learn.microsoft.com/windows/wsl/install 和 https://learn.microsoft.com/windows/wsl/wsl-config ；OpenCode参考 https://opencode.ai/docs/config/ 和 https://opencode.ai/docs/providers/ ，具体配置以迁移版本为准。


### 16.10 远程主机初步硬件验收与WSL安装（2026-11-28，用户截图）

已通过ToDesk进入Windows 10 build 19045.4412管理员PowerShell。截图显示物理内存63.84GiB、HypervisorPresent=False（仅说明当时未检测到运行中的hypervisor，不证明BIOS虚拟化关闭）；Samsung SSD 860 EVO 500GB，Size=500107862016字节、MediaType=SSD、HealthStatus=Healthy（不替代SMART/持续负载测试）。C/D/E卷Size及SizeRemaining分别为64420311040/32194641920、397434408960/397269454848、18243670016/9164275712字节；D盘约370GiB可用，作为迁移归档、WSL2 VHDX、项目和缓存的主要候选盘，原E盘只有约8.53GiB可用，不可照搬旧路径。旧E盘资源门禁须按真实D盘映射进行受控适配并复验，不降低70/55/50GiB等容量门槛；计算归档、解包、VHDX增长及临时空间同时存在的峰值，D盘保留70GiB启动余量后约300GiB可供新增占用，最终是否足够取决于实际迁移包。CPU型号、核线程、固件虚拟化、独享性质、网络及实际租期尚待验证。

安装前VirtualMachinePlatform与Microsoft-Windows-Subsystem-Linux均Disabled；用户实际执行wsl --install --no-distribution --web-download，截图显示两项功能已安装、WSL下载39%，未确认安装结束或重启生效。先等待命令完成，确认ToDesk无人值守重连及商家允许重启，必要时重启；检查wsl --version、wsl --status、wsl -l -v及CPU/固件虚拟化。暂不默认向C盘安装发行版；按真实迁移包类型选择D盘wsl --import（完整可信发行版tar）或D盘独立发行版内恢复项目归档；先核对原Ubuntu版本。64GB宿主机候选memory=40GB、swap=8GB、processors=16（待CPU确认），Swap文件亦优先放在有足够空间的D盘并计入容量预算。Make4/Bazel1仍须实际准入；不盲目调至8/16，不上传长期凭据或签名私钥。此记录为截图初步证据，未执行远程操作或独立硬件测试；Stage7.5仍待验收，迁移三轮限制不变。

### 16.11 远程主机CPU与WSL安装回执（2026-11-28，用户截图）

截图确认Intel Xeon E5-2696 v3 @ 2.30GHz，18核36线程，VirtualizationFirmwareEnabled=True、SecondLevelAddressTranslationExtensions=True。结合§16.10的63.84GiB RAM及Samsung 860 EVO 500GB SSD，主要规格与套餐6一致；独享性、持续负载及磁盘实际性能仍未验证。wsl --install --no-distribution --web-download 已报告成功并明确要求重启才能生效；wsl --version显示3.0.5.0，WSL内核6.18.58.1-1（与待构建Android内核不同），Windows 10.0.19045.4412。重启前wsl --status及wsl -l -v 返回WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED，优先按安装提示重启，不重复安装或修改BIOS。须先确认商家允许重启及ToDesk无人值守重连，保存工作后执行；重连后复查两项可选组件及WSL状态，待核对原Ubuntu版本和实际迁移包类型再将发行版放入D盘。尚未验证WSL2实际运行、恢复迁移包或执行构建。Stage7.5状态及三轮上限不变。

### 16.12 WSL重启后基础状态验证（2026-11-28，用户截图）

重启后ToDesk已重新连接；wsl --version显示3.0.5.0、内核6.18.58.1-1，wsl --status成功返回默认版本2，wsl -l -v正常返回无已安装发行版。此前WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED不再出现。仅证明WSL基础软件与命令状态正常，尚未启动实际Linux虚拟机。下一步核对原Ubuntu版本和迁移包类型：若是项目文件归档，则使用与原环境一致的发行版，在D盘指定安装位置（wsl --install -d Ubuntu-24.04 --location D:\WSL\KernelForge --web-download 为24.04候选，须先核实版本、帮助与目录不存在/为空）；若为完整可信发行版导出则优先审查后导入D盘，不重复安装。候选.wslconfig memory=40GB、processors=24、swap=8GB、swapFile=D:\\WSL\\swap.vhdx，先检查已有配置并保留其他设置，实际启动后核验RAM/CPU/Swap和存储。源码放于ext4，不直接置于/mnt/d；实际安装和迁移尚未执行或验证，Stage7.5未验收。参考 https://learn.microsoft.com/en-us/windows/wsl/basic-commands 与 https://learn.microsoft.com/en-us/windows/wsl/wsl-config 。

### 16.13 远程主机本地OpenCode集中部署决定（2026-11-28）

用户决定直接在租用远程Windows主机安装、接入OpenCode，由该机本地执行端完成部署和构建，不再逐条手动执行命令。此处“本地”指租用主机，不是原8GB电脑。当前已核实E5-2696 v3/18核36线程、63.84GiB RAM、D盘约370GiB可用及WSL默认2；无Linux发行版的状态仍待处理。OpenCode安装、XingChi脱敏Provider恢复、模型/工具及最小权限检查后，先核对总账和真实迁移包、原Ubuntu版本及存储峰值；D盘恢复、40GB/24线程/8GB Swap候选按实测调整；仅在管理员授权、路径及资源准入通过后执行必要部署。用户不必手工逐项安装，不代表授权绕过系统安全、无限下载或不受限管理员操作。保留旧源锁、源码、历史证据及单构建锁、官方安全配置、BTF、ccache OFF、初始Make4/Bazel1、真实五查询/Action Graph及产物证明；跨主机缓存、绝对路径及签名密钥须复验，不上传长期凭据，重要产物回传可信主机独立审查。遗留任务最多三轮，争取一轮集中完成；第三轮未通过停止，无第四轮；Stage8仅在7.5实际通过后启动，Stage8/9原各最多两轮制度不变。OpenCode必须输出真实命令、日志、版本/差异、资源采样、产物哈希、安全验收、恢复检查点及中文报告。当前只记录部署执行端选择，未实际安装OpenCode、恢复迁移包或开始构建。


### 16.14 迁移包 v8 链接审计与剩余阻塞（2026-11-28 09:40 UTC+8）

来源：用户上传迁移进度与恢复交接-20261128-v8.md（3242字节，SHA256 7fa25569f2dd5f4d3c618cfb52c9e178f0101007300d66ec0e3c48891f151151）及 checkpoint(7).json（9376字节，SHA256 f46a0f00413385d0c83591ca75c58cc32e4f338deeb8560dbd4905417dc3bc67）。ChatGPT实际读取并计算两附件摘要，报告与checkpoint progress_report_sha256匹配，链接分类加总一致。封存时间2026-11-28T01:40:38.436622Z，checkpoint更新01:40:38.460144Z。原始101批次、SQLite索引、封存清单及成员实物未随本次上传，不能声称独立重验全量链接或证据包。

- 当前 MIGRATION_BLOCKED_LINK_CLOSURE_VERIFIED_TARGET_RESTORE_AND_SECURITY_AUDITS_PENDING，full_migration_accepted=false，archive_acceptance=NO_COMPLETED_PAYLOAD_ARCHIVE_FULL_MIGRATION_NOT_ACCEPTED。F:/KernelForge-Migration-20261127；Linux有效清单543842项（目录45565、文件297999、链接200278），逻辑字节170337479297（约158.64GiB，非实际分配量或归档体积）。v7链接源端实时复核exit0，EFFECTIVE_LINK_CLOSURE_VERIFIED_PENDING_TARGET_RESTORE，unresolved_count=0：目标在有效清单200048、原有悬空218、WSL运行时依赖10、私有空目录骨架1、补充文件1。私有内容未枚举；不宣称所有链接可用。报告记录101批连续序号/摘要核验、SQLite183504896字节/完整性ok；索引SHA256 f418bd96d7764d41c356cb2b6cbde831bc6668367bacefb5b553828f2b94dee3，源清单 a47cacca57c507ad60cdcb426d51dfd5dd633e34b1a2f1ea6d53d589d3bb7c87，有效清单 f7155f4e99a57dd29d28729f7bc0cc7ece26cfb0585fb0bdb5553609bfbec583。目标恢复及dependency_closure_accepted均false；复用本次审计，不重复全量扫描，源身份变化时精准复核；218项保留原链接文本，10项待真实WSL验证，评估实际构建相关性，不擅自修源。
- Windows清单v3读错误0，6脱敏证据/9 ADS、较v2新增30路径；深审记录36容器发现及2 Git发现已取得准确来源、268499存储对象读取OID验证。Windows v4归档27437文件、2684953293字节，ultra阶段SUSTAINED_SYSTEM_MEMORY_PRESSURE，无有效归档。权限角色映射9测试/端到端夹具10测试，未知本地SID=0，但完整工程及真实跨主机应用未验证。目录owner设置需当前不存在的权限；部分目标保留，未改ACL、未提权、未开始目标复制。不得将夹具测试当跨主机PASS；保留源安全描述符/ADS及SID角色清单，目标独立目录按最小权限适配，必要的owner恢复须明确授权且测试，不修改原机ACL或授予Everyone完全控制。
- Linux Git全对象审查CANCELLED_BY_SERVER_RESTART，15仓库读取回执缺持久完整发现摘要，不等于全对象通过。Linux容器审查14告警/17问题（7读取或格式错误、9加密成员、1需原生解码器）；两个bzip2夹具完整性错误，解码器回归通过不等于内容审查通过。10个选定容器已有精确公共来源证据，34原始候选有来源或保密排除计划但汇总待完成（32公开、1官方Bazel jar、1实际旧签名私钥排除；不得传输密钥）。依赖补充9清单项/2文件待最终合并。不能泛化公共来源证明覆盖全部嵌套成员或把加密内容当已扫。原始报告保留，逐项处置、记录来源/哈希/实际依赖及排除或重建方案；无法排除敏感性或未审核内容不可传往租用主机。
- OpenCode实际迁移检查点为2.4.2，4配置9资产，恢复未验；不要沿用旧版2.3.2.0假设，按真实脱敏配置恢复。主项目HEAD100f327120023b70f20f6a6707e2cf5a8daa66e2 clean，授权worktree HEAD14467ced92092c564a56d6b5936f7049eb56b62c，5 tracked修改/7 untracked，tracked diff SHA256 6ebad69235927c31ce6acf27e4f5f2818b8c4284742b5d2ec767074d8f26dc70，报告无源修改/提交/推送/合并。原机资源旧样本F盘可用288053985280字节、E盘193402880000、物理可用2847895552、提交余量7662727168，非当前实时值。封存 verification/progress-seal-20261128-v8/evidence-manifest.json 摘要410305ff93ceea540fac2a4147be5f4677ff120c222717aecc00a9cffea84b55，工具清单c1aaaf4044bff0cd556a1509bfc5b2b0d73704f6b62b18e65c97f61503c307b1（记录自checkpoint，未取得实物）。no_kernel_build=true，Stage7.5 BLOCKED_CAPACITY_ARTIFACT_ACCEPTANCE，Stage8未启动。关机取消且未执行，不创建自动关机任务。
- 用户已决定原机继续完成后使用ToDesk文件传输至租用主机D:/Migration，不传未封存归档。建议将最高压缩率调整为在原机资源守卫内尽可能高、以实际生成可恢复无损包优先：单线程、较小字典/较低压缩级别、按独立逻辑组分包，必要时采用无压缩归档；须保留Linux元数据和Windows恢复清单，不等于有损压缩或删除文件；用户原极限压缩目标不得静默改为普通压缩，建议以可恢复性优先的修订合同交执行端。Linux清单约158.64GiB，租机D盘约370GiB（旧快照），预算包括传输包、恢复占用、Swap/VHDX增长、临时空间及70GiB物理启动余量；避免全量归档和全量双份恢复同时挤爆D盘，分组校验恢复或将已核验的非必要缓存/测试夹具等单列并保留在原机须经用户确认，不能冒称全量迁移。优先完成原机必须的敏感数据审查、最小可用迁移归档、文件级校验与交接；真实跨主机权限、WSL运行时链接、工具链/缓存及功能恢复在租机验证。保持三轮上限，不因优化压缩或续接内部步骤另建阶段。此为报告审查及下一步建议，未实际修改原机或远程机、打包、传输或编译。

### 16.15 在线重建替代全量传输的可行性评估（2026-11-28）

用户询问可否不传输整个归档、由租用主机按现有数据重新下载部署。建议以锁定版本在线重建＋少量不可再生数据安全交接替代全量环境复制；此为方案评估，尚未获明确取消原归档任务或执行下载授权，不自动中止原机正在进行的任务。GitHub连接器本次实际验证：14467ced92092c564a56d6b5936f7049eb56b62c（T09文档交付）及451fb613f3fc0f4e7afbeb648742f60539ec07c4（T09代码候选）可读取；原机main HEAD100f327120023b70f20f6a6707e2cf5a8daa66e2远端Commit查询422 No commit found，不能假设原机全部已提交历史均在远端。已实际读取14467ced下manifests/oneplus13-pjz110-sm8750-source.lock.json，Git blob814f568d1431fb2a6682ef4d4634b9c25c818c13，锁定35项目、官方manifest f8e50677874c65b6da41057d2f39be7b4ef3c08a；尚未在租机验证全部上游Commit可达、网络、下载和工具链摘要。以授权worktree基线14467ced为候选，必须审查并交接5 tracked/7 untracked实际内容及只在本地的main历史/差异、阶段7.5生成仓库初始化规则和真实日志、必要补充文件与脱敏OpenCode2.4.2配置，不能将本地独有变更默认为可下载；原机可保留完整备份，禁止丢弃。若需远端严格零传输，则仅能复现已提交的可达基线，不能声称恢复未提交成果或完整原环境。下载准备须单独明确授权并按精确repo/commit、哈希/许可证和路径隔离、凭据最小化执行；不使用不受控repo sync、浮动latest或改锁；离线查询和真实构建仍保留nofetch/网络隔离、官方配置/BTF及资源守卫，重新生成必要本地仓库，缓存默认不迁移。原机全量归档、安全审查与跨主机ACL恢复不因新环境重建而标记PASS；不传输的遗留归档问题单列为不适用或暂缓（须确认），新下载输入和独有交接内容仍需安全审查。D盘容量、WSL配置、三轮上限、Stage8条件启动不变。未实际部署、下载或编译。

### 16.16 新租主机零授权初始化与等待原机交接（2026-11-28）

用户明确提醒：租用主机项目环境及相关授权均从零开始，后续可能需本人远程授权；当前先等待原电脑准备完成，不立即启动在线重建或取消原机任务。已验收的Windows/硬件/WSL基础安装仍有效，不将零项目配置误解为未安装WSL。下一轮集中任务增加前置环境初始化与授权验收：核对管理员、实际Linux发行版及sudo、D盘隔离目录读写/删除夹具、OpenCode版本（原机检查点2.4.2）、XingChi脱敏Provider/实际协议与模型工具调用、Git/GitHub CLI及所需仓库读权限、MCP/Skills、锁定官方源码与工具链下载网络和权限。公开仓库无需为读取额外登录时不强制授权；仅确有需要时用浏览器设备码或对应安全流程，由用户本人确认；GitHub写权限、系统变更/重启及额外费用单独授权，租用主机默认最小权限，不迁移主账号长期令牌、SSH私钥、旧签名私钥或长期API Key。需要人工操作的授权尽可能集中列出中文目的、范围、风险及具体步骤；不得代用户输入密码、绕过认证或自动批准权限，普通已授权操作自主执行。授权缺失列为真实阻塞，不把尚未认证/验证记为PASS，不为授权等待重复执行重型任务。待原机最终交接/检查点及不可再生数据清单到达后，再确定完整传输或锁定在线重建方案及统一执行指令；§16.15可行性建议保留，三轮上限、Stage7.5强制验收及Stage8条件启动不变。本次未操作原机或租机、未启动下载或构建、未安排后台监控。

### 16.17 租用主机提前准备（2026-11-28）

用户要求原机准备期间让租用主机并行提前准备，更新§16.16的暂缓范围：仅启动独立环境预部署和授权验收，不启动正式源码恢复/全量下载、真实Stage7.5构建或Stage8。原机任务继续，待最终交接决定传输或在线重建。执行端OpenCode先检查已存在环境、权限与磁盘，再在D:/KernelForge-Prepare及D:/WSL等独立目录按需建立环境；不重复安装已通过的WSL组件，不覆盖现有发行版或配置。Ubuntu版本尚无原机实证，先从真实项目依赖/交接信息确认；无法确认时先完成无关准备，暂缓发行版及版本依赖安装，或仅经明确同意建立可隔离候选环境。40GB/24线程/8GB Swap为候选，实际核验VHDX和swap在D盘、真实Windows及Linux资源计数器、70GiB宿主/40GiB ext4启动门槛、有限轻量I/O/CPU测试（不做重型压测）；保留所有现有安全门禁。按官方来源、可核验版本及最小权限准备Git、必要GitHub CLI、Python及已确定基础构建依赖，核验OpenCode 2.4.2目标/实际版本及星驰真实协议模型、MCP/Skills；不得猜测或替换已知正常Provider，临时最小权限凭据人工录入，日志脱敏。GitHub公开内容只读优先无需登录；仅确有必要时中文集中提示用户授权目的/权限/风险及具体步骤，设备码由本人在可信设备确认；不要索取长期令牌、SSH/签名私钥、自动批准UAC、关闭安全软件/防火墙或扩大Git写权限。允许小型项目代码只读检出、核对14467ced与35项锁定清单、网络/上游可达性和工具链下载计划；不执行全量repo sync、重型工具链/源码下载、Bazel仓库物化或真实构建；无需等待原机数据的部分完成即封存。对远程路径E→D适配仅形成清单或独立测试，未经授权不提交/推送/修改main。输出逐项PASS/BLOCKED/NOT_RUN、中文报告、命令/真实退出码/日志、版本与哈希、变更清单、权限需求、资源与安全证据、回退点、待原机输入及下一步清单；原始日志脱敏且保留可审查证据。前置准备不另计正式迁移三轮次数，不提前宣称Stage7.5通过。此为任务指令与决策记录，ChatGPT未连接或实际操作租用主机。

### 16.18 租用主机 OpenCode 首次文本调用成功（2026-11-28）

用户截图及汇报：OpenCode Desktop/捆绑CLI 2.4.2，实际CLI位于用户AppData Roaming ai.opencode.desktop/cli/2.4.2-x64/opencode-cli.exe。此前自定义xingchi配置出现缺认证、Invalid API key及模型不可用；直接脚本GET models返回200而POST responses返回403 client_not_allowed（中转站限制非支持客户端），不可用脚本伪装客户端。已改为用户提供的星驰官网V1模板（provider.openai.options、内置openai Provider、18个显式模型、store:false、推理档位），CLI实际列出openai/gpt-6.1-sol及其他变体。GPT公益分组下gpt-6及gpt-6.1-sol-healthcare实际返回无支持上游账户，普通gpt-6.1-sol CLI一度连续WebSocket 1013，用户报告重试6次后成功返回正常文本。说明至少一次文本生成成功，连接稳定性PARTIAL；尚无证据确认HTTP transport改动已实施或生效、Max实际传参、工具调用、长期运行、GitHub授权及前置部署完成。保留当前可用配置，不再反复重写；建议撤销已暴露旧凭据并使用独立限额新密钥，勿在总账/日志中记录密钥；若轮换须重新实测。先少量短请求及隔离目录真实工具测试，通过后执行§16.17前置任务，暂不启动真实构建；避免重试风暴及重复副作用。未实际操作租机，未验证当前凭据轮换状态。Stage7.5及原机交接仍待完成。

### 16.19 OpenCode 2.4.2 脱敏配置包独立复审及目标恢复（2026-11-28）

用户上传opencode-config-export-20261128.zip及SHA256、README、checkpoint。ChatGPT实际在容器读取ZIP 30322字节，SHA256 c3b8e611d15f1128eff4de27aedba57144cc83fb72572e7f3b49a15f38c2eaa3，与外部校验文件一致；25个成员CRC正常，23/23内部摘要匹配、完整覆盖（另2个为seal及sha256sums），seal绑定摘要一致，独立README/checkpoint与内部逐字节一致；常见API/GitHub令牌及私钥格式扫描无匹配，不能替代任意敏感内容审查。实际检查恢复/验证脚本：恢复前验证、12目标文件、WhatIf及现有文件逐一备份；当前容器无Windows PowerShell，原机报告的恢复/备份/篡改拒绝等PASS未独立重跑。脚本不负责事务性回滚或解决目标重解析点、额外配置覆盖，执行前核对真实路径及已存在配置；旧官网配置明文密钥备份应安全保管并撤销暴露旧密钥，不上传任何备份。原包保留不改。
- 实际全局V2 providers.xingchi.package=@opencode/ai/providers/openai/responses，baseURL=https://api.xingchiapi.com/v1，settings.apiKey={env:XINGCHI_API_KEY}、body.store=false；16个模型均含low/medium/high/xhigh/max variants及显式reasoningEffort，模型capabilities声明不等同上游实测；默认model及Build/Plan均xingchi/gpt-6，租机GPT公益曾拒绝gpt-6，建议目标恢复后单独测试/调整为已曾成功的普通gpt-6.1-sol，不修改源封存。目标全局配置恢复会替换当前官网模板，先隔离预览并保留备份；目标D:/KernelForge与D:/KernelForge/project仅作候选，正式项目检出未确定时可先只恢复全局文件（独立核对并备份），完整三层恢复待路径确定；项目9技能、工作区snapshots:false、Context7及GitHub readonly MCP（按需独立最小权限令牌）；不迁移会话/认证数据库/service.json。原机运行时预算200000/32000为客户端回退，不代表上游限额。GitHub MCP可暂缓，目标XINGCHI_API_KEY用户变量此前可能已删，恢复后需人工注入独立已轮换密钥及重新启动实际服务；不在命令参数、报告或Git写入秘密。先核验目标模型、普通Sol实际文本回复、Max和工具调用；历史CLI六次重试才成功且Desktop仍失败，不能认为恢复必然解决上游/客户端故障。若V2仍失败，保留原包、回退官网模板并按当前错误精准排查，不重复生成密钥或盲目重写。源包checkpoint SOURCE_EXPORT_COMPLETE_TARGET_RESTORE_PENDING，源Git HEAD100f327120023b70f20f6a6707e2cf5a8daa66e2；关联重建checkpoint只记录继承状态BLOCKED_WRONG_EXECUTION_HOST_REMOTE_TARGET_UNAVAILABLE、35源码锁SHA256 22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7，未独立取得关联重建包。Stage7.5未验收、Stage8未启动，前置任务仍待执行。此轮只复审包与指令，未实际连接或恢复租机。

### 16.20 云电脑 OpenCode 可用接入方案验证（2026-11-28）

用户截图确认目标机全局配置经文件直接覆盖后 JSON 可解析，16个模型计数为16、XingChi及Max显示恢复；手工粘贴曾导致7862字节损坏配置。恢复原机xingchi自定义Provider后，常规及standalone实际调用均返回Invalid API key，而当前用户环境变量凭据GET /v1/models返回200。随后在保留原providers.xingchi及16个模型完整定义的基础上，备份全局配置，增加内置ID openai 的Provider，名称XingChi Official，settings.baseURL=https://api.xingchiapi.com/v1、settings.apiKey={env:XINGCHI_API_KEY}、settings.transport=http、body.store=false，models复用xingchi的完整定义；未显式指定package，采用内置适配器。截图确认执行 opencode-cli.exe --standalone run --model openai/gpt-6.1-sol 后实际收到正常文本回复，无显示重试；用户随后确认本地可正常使用。此为实际文本调用PASS，不独立证明Max实际传参、全部16模型可用、HTTP长期稳定性或Desktop与CLI全部一致；同时改变Provider及transport，无法单独归因。保留可用方案，建议仅在需要时将默认model及Build/Plan改为openai/gpt-6.1-sol（原xingchi仍可能报错），不再反复更换密钥、重写模型或重装。先进行轻量工具调用验收，再执行§16.17前置任务；原机准备及Stage7.5未验收、Stage8未启动，GitHub/MCP/Skills目标机验收仍待完成。不得记录真实凭据，曾暴露密钥须撤销；当前轮换状态未独立核实。ChatGPT未直接操作租机。

### 16.21 租用主机正式在线重建与后续任务连续执行授权（2026-11-28）

用户明确要求进入下一阶段，在租用主机本地重新构建并完成后续任务，争取一次集中完成，遇普通问题自主解决、允许联网，优先恢复原机全部插件及其他有实际帮助的可信插件。此授权解除§16.17仅预准备、不全量下载/构建的限制：可按锁定版本在线重建、在独立目标目录安装必要依赖、恢复并验证MCP/Skills、进行授权范围内的本地代码修复、测试和Stage7.5真实构建。保持§16.20已实测可用的openai内置Provider+星驰API+HTTP+环境变量引用，默认及Build/Plan使用openai/gpt-6.1-sol，保留16模型及五档，恢复时不得覆盖成已失败的xingchi认证路径；Max及工具调用须实测。已知源端资产：Context7、GitHub readonly MCP及9个kernelforge Skills（build/documentation/environment/handoff/performance/regression/release/root-cause/security）；以脱敏ZIP和原机实际清单为准，额外插件须核实官方/可信来源、版本、权限、必要性及安全性，禁止盲装、执行不可信远端脚本或向第三方泄露项目/凭据。确需用户OAuth、设备码、密钥、UAC、额外付费、重启或扩大权限时集中中文请求，不绕过；可先继续不依赖阻塞的任务。
执行顺序：核验真实主机/可用API及工具→插件授权/恢复→D盘Windows项目与ext4/WSL2环境→锁定T09候选451fb613及文档14467ced、35项源码和工具链→独有本地成果及交接差异（未收到不能假定恢复；不得丢弃原机成果）→复核资源守卫、受迁移影响的Stage1–7.4回归及历史未闭合安全事项→官方生成仓库受控物化、五查询/图/真实Stage7.5构建及完整证据→全部强制门禁且按合同独立验收后进入Stage8 S01–S10；Stage9依赖前置验收，可在既定范围继续本地自动化开发/验证，不授权实际发布、刷机、签名私钥迁移或main变更。下载与离线构建分离，禁止改锁、混用设备或关闭BTF/资源守卫；缓存重建不迁移。一次集中任务是连续自主执行目标，内部修复/恢复不要求逐次确认、不代表一次编译必成或无限重试；正常进展无固定时间上限，原三轮硬上限、Stage8/9各两轮及独立验收门禁仍保留，除非用户明确改动。若硬阻塞，封存真实日志和检查点，继续其他安全独立任务，不虚报完成；最终交付完整可审计证据及中文报告，重要产物回可信机器复核。原机完整归档未验收，不自动取消、删除或标为PASS。此为用户任务授权及执行指令记录，ChatGPT未直接连接租机、未安装插件、未下载或编译。

### 16.22 正式重建新增时间、成本与多进程并发要求（2026-11-28）

用户补充§16.21：本次任务不计时间、不计成本、多并发进程完成任务。正常执行不设人为时限，不因节省既有授权API Token、调用次数、租用主机使用时间或本地计算资源而缩减范围、跳过必要测试/审计或降低质量；优先真实完整交付。允许执行端在真实资源和依赖约束下采用多Agent/多进程并行开展插件恢复、文档检索、独立源码下载、工具链准备、代码审计、测试、日志及报告等工作，按CPU/RAM/Swap/Windows提交余量/物理盘及ext4空间/I/O/网络/API限流动态调度，建立任务DAG、独立工作目录/日志、写入锁、缓存隔离和汇总检查点。并行不等于无限进程；同一构建工作区、源码树、缓存或共享配置的冲突写入须串行/加锁；保留单真实内核构建锁，构建内部并发按已审资源策略准入，初始Make4/Bazel1及后续调优须实测，不擅自突破门禁或同时启动多套真实内核构建。避免重复下载、重试风暴、无效重复测试及并发副作用。现有授权资源费用不作为主动缩减任务的理由，但新付费订阅、额外租赁、扩大账单权限等仍须用户明确授权；不得绕过API限流或安全机制。一次集中执行目标及此前迁移遗留最多三轮、Stage8/9各最多两轮的集中整改上限与阶段独立验收、发布/刷机门禁保持不变；并行子任务及普通内部修复不另计集中轮次。若外部硬阻塞，封存证据并继续其他独立任务。本次只更新任务指令与总账，未直接操作租机或启动并发任务。

### 16.23 长周期任务连续执行、会话生命周期管理与恢复专项（2026-11-28）

用户认可并要求将会话续接建议形成正式任务与任务要求，作为当前重建及后续KernelForge执行保障。用户截图中OpenCode报告压缩直接失败为星驰HTTP400 session_turn_limit_exceeded，提示100轮；本机客户端声明context1050000/input922000/output128000，非上游实测承诺。该截图为执行端报告，尚未取得原始脱敏响应日志，不独立确认服务端计数/适用范围；30% token buffer不能保证在轮次限制前触发，现有证据不支持归因为Max或上下文不足。截图亦报告认证字段进入工具输出及会话记录，必须优先界定受影响凭据、停止输出/传播、提示用户在可信设备轮换/撤销，审查会话、日志、备份和诊断文件的残留及访问范围；不得记录真实密钥或盲目删除原始证据，采用隔离权限及脱敏副本，轮换后验证合法接入。
- P0专项与当前重建并行，保持D:/Migration已验证工作区、openai/gpt-6.1-sol Max主任务、已工作Provider/HTTP、资源守卫和单真实构建锁；不擅自中断有效编译、下载或其他Agent。核实实际生效配置、官方支持的事件/会话/插件接口及服务商轮次规则；候选60轮预警、70轮安全交接、80轮前不再开启长工作包，根据实测提前调整，未知计数采用保守的本地估算与更频繁检查点而非冒称精确。仅在服务商许可及OpenCode支持范围内新建独立会话继续合法工作，不伪造标识、不规避账户或服务端限制；若不支持自动交接，提供人工新会话最短恢复指令并继续独立安全任务，不编造API/插件能力。400轮次限制不可在同一失败上下文无界重试；与401/403、429、503、1013、真实token超限区别处理。Summary/native及低强度摘要仅在独立会话验证且有证据支持时采用，不改变主任务Max。
- 建立本地持久化DAG/任务状态与原子检查点、版本化脱敏交接摘要、任务/会话/子Agent ID、源锁及Git身份、diff/文件哈希、命令退出码和日志引用、未完成项、授权需求、安全门禁、运行中进程PID/启动时间/命令与工作目录身份、资源及锁状态；绝对路径适配实际环境。进程恢复先核实身份、锁及真实状态，避免重复下载/编译/写入、错误接管或终止进程；不可安全接管时标记待人工确认，保持原任务证据。新会话先读总账和检查点，再核验状态、认领未完成任务，已完成且证据仍有效的不重跑；持久化状态不依赖模型记忆/单个会话；状态更新加锁、原子替换、版本化、校验与回滚，禁止并发写入冲突或私有信息入Git。
- 验收：隔离轻量夹具测试预警/轮次拒绝、正常交接、API断连、进程/服务异常、损坏检查点恢复、多Agent并行及冲突拒绝、重复执行防护、权限/凭据脱敏；模拟与真实服务调用分别报告，不为测试耗尽真实轮次，不中断正式构建；实际至少一次服务商允许的跨会话续接与真实工具调用，核对前后任务状态、证据和未完成项。交付可审查实现/配置、测试和原始脱敏日志、SHA256、中文恢复手册和检查点，PASS/PARTIAL/BLOCKED/NOT_RUN分列。不限人为时间、不以节省现有授权资源费用为目标、多进程资源感知调度；本专项不新增Stage编号或集中整改轮次，不解除既有三轮及Stage8/9各两轮上限、安全/独立验收、公开发布/刷机门禁。用户未授权新增付费、绕过服务限制、扩权或将凭据上传。此处仅任务合同及截图观察，ChatGPT未操作租机、未实施或验收自动续接，实际凭据轮换未确认。

### 16.24 原机20万上下文与自动压缩对照验证要求（2026-11-28）

用户补充：原电脑OpenCode实际显示上下文上限20万且自动压缩正常。与§16.19原机客户端回退预算200000/32000记录一致的上下文部分可作为候选对照；用户未确认原机实际输出上限或服务端真实容量。云机截图声明context1050000/input922000/output128000，曾报告HTTP400 session_turn_limit_exceeded、100轮。新增§16.23专项对照工作包：先核对两机相同OpenCode版本、实际合并配置、Provider ID/适配器/transport、同模型及合法授权分组、运行时上下文/输出预算、自动压缩模式及触发阈值、轮次/工具调用计数和原机实际压缩日志，区分配置声明、客户端回退及服务端真实限制；不得假设两机密钥/分组或协议完全相同。云机在隔离测试会话采用200000客户端context预算候选（output/input按原机实际证据及服务端支持核定，不机械套用32000或128000），保持auto开启，核对实际生效值、正常自动压缩及压缩前后任务续接；与现行配置做小规模同等负载对照，记录请求/轮次、Token、触发时机、摘要完整性、工具状态及错误码，不故意耗尽正式会话。105万配置可能使Token触发晚于100轮硬限制，仅为假设；摘要是否重置服务端计数、两机限制是否相同均未验证。若20万方案实测更可靠，再经备份和安全检查点应用于目标机相应模型或配置层级，不破坏当前openai+HTTP可用认证、不降低主任务Max或覆盖16模型和Skills；不得误称改变客户端预算能提高/解除服务端限制。持久化检查点与合法跨会话续接仍为独立保障，不因自动压缩恢复而取消；凭据轮换和脱敏要求继续有效。该追加任务与主线并行，不新增阶段或整改轮次；无时间上限、不以节省既有授权成本为目标、资源感知并发及既有安全门禁不变。此为用户观察及待验证方案，ChatGPT未直接操作两机或验收压缩机制。

### 16.25 云电脑首次综合整改证据包复审（2026-11-28）

用户上传 KernelForge-reports-evidence.zip。ChatGPT本轮独立读取归档，实际SHA256 53b88f431e215daef384d5a945a8c45e233ef12b83c0fb7094fbeccc4f0e1fa8；223个文件、无重复名、CRC通过；SHA256SUMS.json覆盖其余222文件，逐项大小与SHA256全部匹配，33个.py AST解析通过（未执行），常见sk十六进制/GitHub PAT/私钥头格式扫描无匹配（非完整秘密检测）。未收到包外最终发布回执与独立摘要，不能证明来源真实性、云机当前状态或所有引用的上游封存成员均实际入包。独立读取四份最终unittest日志，610唯一测试ID集合完全一致；Linux Python3.11/3.12各610运行、595通过、15跳过；Windows3.11/3.12各610运行、563通过、47跳过，均记录0失败0错误。合计2440测试实例、2316通过、124跳过，不是2440个独立用例；未在ChatGPT环境重跑。报告明确Windows/WSL仅112/113同字节（tests/test_validation_schema_gate.py四处路径断言），正式Windows树仍干净基线，修复在隔离副本；WSL有16 tracked修改+6新增，原机5 tracked/7 untracked独有成果未收到。SEC01–05、Windows夹具/长路径整改已有材料，真实跨帐号/UNC等未验，不得宣称安全全闭合。
- 报告记载 Ubuntu24.04/WSL2已部署、D盘VHDX、35/35锁定项目及工具链已核验；源码恢复实占14084542464字节。资源监督器为新机等价重建，33单元+5隔离夹具PASS，非实际Bazel/内核负载。75生成仓库为marker/顶层/链接范围核验、25固定资产、12 registry补丁；未证明真实目标闭包。
- 已知Context7/GitHub Readonly和9 Skills实调通过；102 builtin插件仅active/可发现，不等于全部功能通过。包含builtin opencode.websearch.firecrawl，非新增Firecrawl MCP验收；Firecrawl/Scrapling后发专项明确另行交付，当前包无T01–T20验收。避免重复安装或把内置搜索插件当远端MCP。用户补充Medium摘要偏好已有执行端对照及推广：200000/168000/32000、主Max、自动Summary Medium已读回；Low/Medium/High各n=1及High→独立Max root均60/60字段、74/74叶项、安全17/17、依赖6/6打平；无长期优势统计或实际供应商effort/cap/计轮重置证据。r2续接42合成测试、GET-only限定生产接纳；19会话98GET/远端写0，6 monitor/5 skip/13 hold，真实主继任因source active阻塞；server_count=null，WSL guest进程/两个Git unknown未核实，未真实接管/长期无人值守。认证事件仍PARTIAL_PASS，残留1条会话记录，轮换/新auth待用户确认；不要把打包脱敏当泄露闭环。
- 构建仍build_eligible=false，Stage7.5 NOT_ACCEPTED、Stage8/9 NOT_RUN。BA01官方wrapper symlink缺失，BA02精确recipe/独立preparation receipt未接纳，BA03新鲜资源窗口缺失，BA04五正式nofetch查询0/5及真实图未运行，BA05目标闭包/DFR/输出/实际工具链未验，BA06仅DISPATCH时间无实际compiler开始与生成环境证据；外部DFR原悬空链接保留。无真实Image/vmlinux。后续优先保护当前检查点和未提交成果，确认凭据轮换、统一113文件身份并精准补验证，串行关闭BA01–06，实际执行五查询及单锁定基线构建；并行MCP专项不得争抢资源或成为非必要构建门禁。复用有效报告和测试，不反复整理同一证据或盲目重放历史脚本。主入口D:/KernelForge-Rebuild/checkpoint.json及TASK_STATE_ZH.md，工作区D:/Migration。最新包内快照在ZIP生成前为NOT_RUN是时间边界，用户实际上传的ZIP存在且内部通过；包外最终发布验收待补。ChatGPT未操作租机、未运行工程测试/构建，未改变阶段状态或新增执行轮次。
