# KernelForge 功能状态与验证矩阵

更新日期：2026-11-25。当前有效验收基线：`0a6e702dda6d1851153490ac0aea22814bb06c49`。详见[最终安全验收报告](SECURITY_FINAL_ACCEPTANCE_2026_11_24.md)及[结构化证据](evidence/security_final_acceptance_2026_11_24.json)。本页替代早期阶段的状态概览；[旧版状态（历史快照）](https://github.com/20592504720/KernelForge/blob/4ac79893c19d95680bea4acc2374cc299fd6d2ab/docs/STATUS.md)仍可追溯。

## 状态说明

| 状态 | 含义 |
| --- | --- |
| 已实现并验证 | 指定范围有真实测试证据；必须注明软件、编译或真机层级 |
| 已实现待验证 | 已有代码或框架，但目标环境、真实资源或运行行为尚未验证 |
| 开发中 | 已启动的子任务，尚未满足验收门禁 |
| 待实现 | 已规划或未实现的功能 |
| 暂缓实现 | 明确暂缓或因前置条件不满足而阻塞；保留历史需求 |
| 不支持 | 现有实现明确拒绝的场景；不表示永远无法实现 |

原技术状态如 IMPLEMENTED、TESTED、UNTESTED、NOT_IMPLEMENTED、BLOCKED、IN_PROGRESS、PLACEHOLDER 保留于代码与证据，不作翻译替换。不能将测试夹具、配置存在、源代码检查、真实编译、真机运行混为一谈。

## 已实现并验证的基础功能

| 功能 | 状态 | 验证范围及限制 |
| --- | --- | --- |
| Stage 1：Schema、CLI、配置/补丁清单校验 | 已实现并验证 | 四环境软件回归，严格字段及负向测试 |
| Stage 2：Git 固定提交、独立 GKI/Vendor 构建适配器、日志、失败报告、产物哈希 | 已实现并验证 | 软件及通用 GKI 路径验证；Vendor 真实构建未验证 |
| Stage 3：LLVM/GCC 工具链管理、下载/哈希、解压、原子安装、锁、缓存、租约 | 已实现并验证 | 本地 HTTP/ZIP/TAR 与离线夹具；大型真实发行包另验 |
| Stage 4/4.5/4.6：官方 KernelSU、BakaSU、SUSFS | 已实现并验证 | 固定 ACK 6.1 五组合真实 Image；启动、Root、SUSFS 运行未验 |
| Stage 5：补丁事务、固定来源、顺序、冲突拒绝、回滚 | 已实现并验证 | 夹具及已审查 GKI 补丁；任意第三方补丁不保证兼容 |
| Stage 5：TCP/ZRAM 源码和 Kconfig 检查 | 已实现并验证 | 检查功能；不等于 BBR/Westwood 或压缩算法运行验证 |
| Stage 5/6：PJZ110 与 Ace 6 设备档案、Manifest 审计 | 已实现并验证 | Manifest 映射和历史 35 项源码证据；不是新同步或真机验证 |
| Stage 6.2：Git/Archive 来源、下载校验与隔离 | 已实现并验证 | 安全软件测试；独立 Vendor 归档不准入构建 |
| Stage 6.3–6.5：工作区证据、精确组合兼容门禁、全量回归 | 已实现并验证 | 云端证据重放；本地 WSL2 锁差异待核验 |
| Stage 7.1：环境预检 | 已实现并验证 | 只读预检；历史资源采样不代表当前容量 |
| Stage 7.2：Release 镜像与同 SHA256 回退 | 已实现并验证 | 离线身份及回退测试；无已批准生产镜像 |
| Stage 7.3：ccache 身份隔离、租约与失效保护 | 已实现并验证 | 软件级测试；真实 ccache 命中与加速未验 |
| Stage 7.4：构建准入、默认/自定义时间、报告防覆盖 | 已实现并验证 | 云端策略与夹具；`build_eligible=false`，OEM 实际编译未验；Stage 7.4-O 本地性能 INCONCLUSIVE，保留 `-j2`、ccache OFF |
| 安全加固 | 已实现并验证 | 四轮及收尾整改；479 项/环境、五组 GKI、7 ZIP/5 Image 独立哈希；详见最终报告 |

## 已实现待验证及开发中

| 功能 | 状态 | 下一项证据 |
| --- | --- | --- |
| Linux 5.10、5.15、6.6、6.12 配置档案 | 已实现待验证 | 各内核、工具链、补丁与设备组合独立编译；6.1 也仅限固定验证组合 |
| 真实 Vendor 适配器构建 | 已实现待验证 | 官方目标、完整源码、工具链与产物 |
| 真实 LLVM/GCC 大型发行包 | 已实现待验证 | 精确发行包及许可证、布局、版本、哈希 |
| 生产 Release 镜像 | 已实现待验证 | 许可、独立可信摘要、真实 Asset 和下载 |
| 真实 ccache | 已实现待验证 | 可信二进制、编译器拦截、冷热对照，默认关闭 |
| OEM 实际编译时间传递 | 已实现待验证 | Bazel/Kleaf 实际 action 环境，非仅外层 shell |
| Stage 7.5 Image/vmlinux 快速构建 | 开发中（受阻） | 静态宏链已确认 core sun_perf/sun_consolidate 路径不选 DFR external DDK；实际 Bazel action/output groups、本地 35 项源码复核、资源及时间传递仍待核验，未实际编译 |
| Actions 通用 build 入口 | 已实现待验证（PLACEHOLDER） | 当前仅预检；真实构建工作流另行验收 |
| Release 发布门禁 | 待实现（PLACEHOLDER） | Stage 9 审批与签名、打包、发布及设备证据 |

## Stage 8 已选十项目标（设备层全部未验收）

| ID | 目标 | 当前状态 |
| --- | --- | --- |
| S01 | 一加 13 完整官方 OKI 基线 | 待实现/验证；历史源码锁已存在 |
| S02 | BakaSU + SUSFS | 通用 ACK6.1 已验证；一加13 OKI 集成及运行待实现/验证 |
| S03 | 原生风驰 HMBIRD | 待实现/验证；优先保留 OEM 原生能力 |
| S04 | ccache 安全构建缓存 | 软件已验证；实际编译缓存待验证 |
| S05 | BBR + Westwood + 必需网络配置 | 待实现/验证；已有源码检查 |
| S06 | ZRAM + 适配过的压缩算法 | 待实现/验证；已有源码检查 |
| S07 | Droidspaces 支持 | 待实现/验证 |
| S08 | Mountify 兼容 | 待实现/验证 |
| S09 | ADIOS I/O 调度器 | 条件性待实现；不兼容则 BLOCKED |
| S10 | Re:Kernel / Freezer / NoActive | 待实现/验证；按应用分别验收 |

Stage 8 实施尚未开始；不得将软件基础能力计为设备交付。详细要求见[精简功能矩阵](STAGE8_EXPANDED_FEATURE_MATRIX.md)与[验收合同](STAGE8_SCOPED_ACCEPTANCE.md)。

## 暂缓与当前不支持

暂缓清单以 Stage 8 的 D01–D14 为准，包含跨设备通用 GKI/F2FS 免清数据实验、其他 SM8750/MT6991 设备与版本、其他 Root 分支或多 Hook、公共 ccache-ECS 和自动清理/固定速度承诺、额外 O2、强制 LZ4/zstd 版本、Brutal TCP/未界定 BBG、全量高级网络配置、Baseband Guard、NetHunter、kexec、Unicode 零宽补丁。官方 KernelSU 已有通用 GKI 验证，但不纳入 Stage 8 设备目标；KernelSU-Next、ReSukiSU 尚未实现。

当前不支持或拒绝：未经审核的移动 BakaSU/SUSFS 组合、独立归档直接进入 Git Patch Manager、未受审查的设备通用构建、缺失可信摘要的工具链下载、未满足准入的 OEM 构建、自动发布可刷写镜像。设备释放门禁保持 `device_release_eligible=false`。

## 安全与证据边界

[完整验收](https://github.com/20592504720/KernelForge/actions/runs/45375493788) 12/12 Job 通过；每环境 479 项，Windows 每环境 40 项条件跳过，合计 1836 次非跳过测试成功。五组真实 ACK6.1 Image 成功，7 份 ZIP、5 份 Image 独立 SHA256 通过。CodeQL 0、Bandit 高 0/中 1/低 56、锁定 Python 依赖无已知漏洞、Gitleaks 149 个提交无发现。扫描不保证零漏洞、不涵盖全部上游 CVE。

DFR external DDK 仍为 BLOCKED_UNDETERMINED（其 symlink/header glob 影响尚未由 Bazel 验证），但固定 OEM 源码的静态宏链显示该外部模块包不属于 core sun_perf/sun_consolidate kernel_build/_dist 依赖。当前 WSL2 报告确认锁文件 SHA256 未变，但本轮未复核 35 个项目 HEAD/cleanliness，不能据此宣告源码准入；须重新运行只读 source admission。独立 Vendor 归档、OnePlus13 OKI、ABI/KMI、真机 boot/Root/SUSFS、OEM 时间传递均未验证。XML/Expat 及可信 PATH/Git/SSH 边界保留；vmlinux 只有 runner 报告哈希。详见 Stage 7.5 DFR addendum 与最终验收报告。

## 文档维护

后续面向项目主页的介绍、功能状态、路线图及变更说明默认中文，保留代码、命令、路径、配置键、技术名称与机器状态原样。每次功能交付、阶段验收或证据变化同步 README、此矩阵和路线图；必须附实际证据及适用范围，不用规划替代交付，不改写历史验收记录。
