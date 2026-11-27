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

下一步：以 §12.1 为当前状态，先审查离线仓库缺失及生成条件；读取最新本地执行报告。旧 WSL 运行时故障及无损恢复记录保留，不重复已经通过的准入。不得无条件重试同一故障、运行未经审核 repo sync、下载新二进制、修改 DFR 或源码锁。取得单独授权后才执行有界 nofetch 查询，核对结果及完整安全合同后才启动真实构建。用户规定 Stage 7.5 整阶段最多两轮；内部步骤非额外执行轮次，重大风险仍须批准。

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
| P0 | 审核 WSL 恢复证据与缺失离线仓库 @@local_config_platform 的安全准备条件 | BLOCKED_OFFLINE_REPOSITORY_NOT_PREPARED（§12.1）；本轮源码准入35/35通过 |
| P0 | 7.5 五项有界 nofetch Bazel 查询、实际 action graph、资源与时间传递 | 1项执行失败（exit 37），4项未执行；0项成功；不放宽门禁 |
| P0 | 7.5 一次获批准的真实 pinned Image/vmlinux、真实性能与独立产物验收 | 未执行 |
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

C. T09 已在 §3.1 记录；补充用户文件 KernelForge_T09_cloud_acceptance.json：候选259文件独立ZIP blob匹配；Python3.11 AST 102文件、YAML 14工作流、diff check PASS；81修改32新增、4208新增行/560删除行。完整patch SHA256 d7d6513fa2f7299b35b742fcda0feab2d212bdf75ce9adbe3ffb2e316eaca246，代码ZIP SHA256 8e15f4385c267ca45e3367222d44216e300007eb7d333ed3db748ef393ebb967。交付文档 Commit 14467ced92092c564a56d6b5936f7049eb56b62c、Tree a754947495d0e39992d3eb0a430bb2fbc601c9a4（仅 README/ROADMAP/STATUS/T09报告更新，不重跑程序）。结论 SOFTWARE_ACCEPTANCE_PASS; FULL_STAGE_CLOSURE_NOT_CLAIMED; BUILD_NOT_AUTHORIZED。T01–T08 精确任务名/逐字合同仍未恢复，不把 O1–O8 强行映射为 T01–T08。

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

恢复缺口保持 OPEN：Stage9 原始参数表及逐字用户确认、T01–T08 精确原始合同、早期阶段完整聊天逐字文本；本次没有足够证据将其标记已恢复。

### 12.5 持续维护授权与变更记录

2026-11-27 用户再次授权对固定文档长期增量维护，要求每次新会话恢复项目时先查此文件、在当次授权交互中追加新规划/调整/要求/证据/错误修正，历史记录保留；不另造替代总账。第二次补遗修正最新7.5阻塞、补齐O1–O8报告与早期安全证据、区分逐字可见引文与历史检索摘要、登记Stage9时间语义冲突及精确缺口。文档更新不触发真实构建、改变原代码分支、main、PR或发布。