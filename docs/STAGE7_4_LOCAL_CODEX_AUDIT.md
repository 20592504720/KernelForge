# Stage 7.4 本地 WSL2 源码准入审计

## 代码与范围

远端开发分支核验基线：Commit `3603b1e72855cfbadeb1f9808e96df6abd154003`，Tree `7fbea2c60b4cd5be4d3e5d0bb26e0d76a2a74ece`。本地保留原有历史并逐个接入远端提交后，测试代码 Tree 与远端一致；本地提交身份不同。只执行离线单元测试和现有 WSL2 ext4 源码的只读准入检查，没有同步、修复或编译源码。

## 实际结果

| 检查 | 证据与结果 | 状态 |
| --- | --- | --- |
| 35 项源码锁 | `manifests/oneplus13-pjz110-sm8750-source.lock.json` 实算 SHA256 `7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e`；现有工作区 35/35 HEAD 匹配，受跟踪工作树干净 | TESTED |
| Manifest | 所选及锁定 Commit 均为 `f8e50677874c65b6da41057d2f39be7b4ef3c08a` | TESTED |
| 准入脚本 | 使用 `--source-workspace` 与 `--host-disk /mnt/e`，退出码 0；输出 `SOURCE_LOCK_TESTED_BUILD_BLOCKED`、`build_eligible=false`、`ccache_enabled=false` | TESTED（只读准入） |
| 宿主 E: | 实际可用 `197,966,118,912` 字节，满足 50 GiB 安全余量 | TESTED |
| ext4 | 虚拟盘可用 `859,964,493,824` 字节，剩余 inode `66,821,537`，满足 20 GiB 余量；不可代替宿主盘容量 | TESTED |
| 构建时间 | 仅预览 `2026-11-23T21:34:29Z` / epoch `1795469669`；未传入实际 Kleaf 编译环境 | TESTED（预览），实际传播 UNTESTED |
| 本地 WSL2 单元测试 | 21 项中 **18 通过、3 失败**，退出码 1。`test_dirty_tracked_source_blocks_even_if_all_commits_match`、`test_disk_reserve_stops_before_source_git_checks`、`test_project_mismatch_is_not_overridden_by_manifest_match` 均预期后续拒绝原因，却先收到 `WSL_PHYSICAL_HOST_DISK_REQUIRED`。保留原始日志，未改测试或绕过守卫 | BLOCKED（本地 WSL2 回归） |

GitHub 云端固定代码的 8 项 Validate Job 均成功，见 [Stage 7.4 云端验收](evidence/stage7_4_cloud_acceptance.json)；云端成功不覆盖本地 WSL2 的三项失败。

## 原始证据

原始文件留在 `E:\内核构建\reports`：

| 文件 | SHA256 |
| --- | --- |
| `stage7_4_local_source_gate.json` | `7072fbfbbf95d80c68946e78ffd102e5daad9e033ad06955f978dea994e2348f` |
| `stage7_4_local_source_gate.log` | `2a76aa327904e32a7895218e2f39b2c90a1dd9defa2af1f8f197c2a5cad3c313` |
| `stage7_4_local_unit.log` | `7505e8b24fae5bb25e4d3b381507770acd3dac2dca4f8e69e78c79d8f399845d` |

机器可读摘要见 [stage7_4_local_source_admission.json](evidence/stage7_4_local_source_admission.json)。

## 未满足的构建条件

Kleaf 目标及 DFR 依赖仍未确认；Bazel 动作环境中的时间戳传播、真实 Image/vmlinux、模块 ABI/KMI、设备启动和 Root 功能均为 UNTESTED。`ccache` 缺失，保持关闭。此报告仅证明锁定源码准入检查通过，**不授权或证明实际内核构建、刷机包或发布**。本地 WSL2 三项测试失败需要后续单独修复与复验；本轮按交接要求停止。
