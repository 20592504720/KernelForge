# Stage 8 — 精简范围验收标准（10 项，规划文件）

**状态：PLANNED_NOT_IMPLEMENTED。** 本文与 [精简功能矩阵](STAGE8_EXPANDED_FEATURE_MATRIX.md) 一起替代旧版「全部 21 项功能均为必做」的理解。仅变更规划和准入条件，不表示任何新增功能已验证。

## 验收层级

1. **SOURCE_ADMITTED**：一加 13 PJZ110/SM8750 的官方 35 项 Git HEAD/Tree、设备固件/编译器精确身份、构建目标、补丁锁、DFR 依赖经过确认。此前的 WSL2 历史证据不能代替本轮构建输入验证。
2. **OFFICIAL_OKI_BUILT**：未经新增补丁的 OKI 完成真实 `Image`/`vmlinux`、厂商模块、DTB/DTBO、生成的配置、符号版本及 ABI/KMI 检查，有 GitHub Run ID/本地日志、SHA256、失败记录。通用 ACK 6.1 成功不能替代此项。
3. **DEVICE_BOOT_VERIFIED**：在用户明确授权、备份与恢复方案就绪时，进行固件一致性、实际设备启动与基础功能验证。未获硬件授权或未执行时只能标 `UNTESTED`。
4. **SELECTED_SCOPE_VERIFIED**：下表十项分别有独立测试证据，不能拿一项编译成功替代十项的运行验证。任何选定功能无法满足验收，应在专项记录中标 `BLOCKED` 或 `UNTESTED`；可发布有限范围报告，但不得称「十项全部完成」。
5. **STAGE9_READY**：安全发布、签名、打包、OTA/恢复及 Release 属于 Stage 9 单独审批。Stage 8 验收不自动合并 PR #1 或发布刷机包。

## 10 项逐项验收合同

| ID | 正式保留项 | 验收最低证据 | 当前状态 |
| --- | --- | --- | --- |
| S01 | 一加 13 完整官方 OKI 基线 | 必须建立未经增强的 OKI 参考构建与真实产物证据，设备启动验证须单独授权。 | UNTESTED（本次仅改规划） |
| S02 | BakaSU + SUSFS | 精确 SHA/补丁/Kconfig/编译/链接；实际设备 Root/SUSFS 行为另行验证。 | UNTESTED（本次仅改规划） |
| S03 | 原生风驰 HMBIRD | Kconfig/模块/KMI/启动/调度日志确认；禁止叠加冲突的第二套调度器。 | UNTESTED（本次仅改规划） |
| S04 | ccache 安全构建缓存 | 安全回归与缓存身份测试必须通过；真实命中率和加速效果只有在真实 ccache/cold-warm 实测后才算 TESTED。 | UNTESTED（本次仅改规划） |
| S05 | BBR + Westwood + 必需网络配置 | 以实际内核配置、模块加载/选择能力和网络回归验证；不默认切换全局拥塞算法。 | UNTESTED（本次仅改规划） |
| S06 | ZRAM + 适配过的压缩算法 | 核查解压路径/启动、内存及性能与稳定性；不强制 LZ4 1.10.0、zstd 1.5.7 或内置 ZRAM。 | UNTESTED（本次仅改规划） |
| S07 | Droidspaces 支持 | 兼容的 Kconfig、模块、实际容器启动/网络/文件系统验证。 | UNTESTED（本次仅改规划） |
| S08 | Mountify 兼容 | 真实 Mountify 操作、挂载/卸载、Root/SUSFS 交互、异常恢复与 Android 兼容性。 | UNTESTED（本次仅改规划） |
| S09 | ADIOS I/O 调度器 | 独立补丁/编译/模块/实际 I/O 指标与回滚；无法适配须标 BLOCKED 并保留记录。 | UNTESTED（本次仅改规划） |
| S10 | Re:Kernel / Freezer / NoActive | 每个应用独立安装/接口/冻结与唤醒/功耗及稳定性验证；无法复现不可宣称完成。 | UNTESTED（本次仅改规划） |

**S04 特别声明：** 已有 Stage 7.3 软件级缓存隔离证据，但 WSL2 上 ccache 二进制曾缺失。缓存命名空间安全通过测试不等于真实 ccache 被编译命令调用。只有实际可执行 ccache 和适配后的编译入口、同一精确源码/工具链/配置下冷/热构建对照，才能把加速率标为 `TESTED`。无效或污染缓存不得启用。

**S09 特别声明：** ADIOS 被保留为正式评估项，但属于高冲突风险的可选补丁。如果与 OEM UFS/blk-mq 或 KMI 不兼容，则以 `BLOCKED_INCOMPATIBLE` 结论保留，不为凑齐功能而强行启用，也不得冒充已交付。

**S02/S03 特别声明：** 只验收确定版本的 BakaSU+SUSFS 和设备原生风驰；不把其他 KernelSU 分支、旧 Hook 或第三方调度器一并纳入。

## 实施前置门禁

- Stage 7.4–7.6 的工具链/快速构建与后续阶段的任务状态必须分别确认；不以 Stage 8 规划提交为开工许可。
- 目前保留 DFR include `BLOCKED_UNDETERMINED`、一加 13 全套 OKI、ABI/KMI、启动与 Root 运行测试未完成等事实；不把未测试项改成通过。
- 每个新增补丁/配置至少应有固定上游仓库和 Commit、许可检查、补丁 SHA256、Kconfig/ABI 影响、冲突与回滚记录、构建及有条件的设备运行测试。
- 始终不自动改变官方 OEM 编译安全选项（CFI/KCFI、模块签名/SELinux 等），也不清理既有 WSL2 项目、缓存或源码，不能承诺「免清数据」。
- Droidspaces/Mountify/Re:Kernel/Freezer/NoActive 的内核配置通过不等于应用真实兼容；需分别提供应用版本及测试行为。
- GitHub Actions/Artifacts 必须可追溯，不能仅凭绿色运行或工作流名称宣称系统功能完成。所有真实内核编译、刷机和释放缓存应在对应阶段单独明确授权。

## 明确不计入 Stage 8 选定范围

未选择的功能在 [暂缓清单](STAGE8_EXPANDED_FEATURE_MATRIX.md#三明确暂缓清单) 中逐项列出。它们不算验收失败，也不允许通过默认脚本暗中引入。若今后重新启用，须用户批准、分配新任务/版本矩阵并增加独立验收。

**本次文档修改必须满足：** 恰好 10 项 selected、历史 21 条全可追溯、暂缓项目无误、Stage 9 发版门禁保留、Stage 8 状态仍 `PLANNED_NOT_IMPLEMENTED`。
