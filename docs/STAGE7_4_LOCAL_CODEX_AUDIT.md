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

## 修复后最终复验（2026-11-24，Asia/Shanghai）

本次结论：**STAGE7_4_SOFTWARE_AND_SOURCE_ADMISSION_TESTED**。此结论仅关闭软件安全回归与只读源码准入子任务；以上 18/21 失败记录及原始日志继续保留。

修复基线：远端 Commit `8fb34afd627b1c7d3423089b7d438683bd99d735`，Tree `737df8eedd83094049396063f132c99bcd39963b`。工作树干净后仅 cherry-pick 该测试修复，本地测试 Commit `5508d39ed64b69d285a6b439a41da02f9566ec86`，Tree 与远端一致。唯一接入的代码文件为 `tests/test_stage7_4_fast_build_gate.py`：三个夹具显式提供 host_disk，生产守卫未改，缺少宿主磁盘的负向测试保留。

WSL2 命令：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_stage7_4_fast_build_gate -v`。结果 **21/21 通过，0 failures，0 errors，0 skips，退出码 0**；三个历史失败项与 `test_wsl_requires_physical_host_sample` 全部通过。[云端 Validate Run 45272620184](https://github.com/20592504720/KernelForge/actions/runs/45272620184) 的 Windows/Linux × Python 3.11/3.12 四项均已核对为 success。

重新实算源码锁 SHA256 仍为 `7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e`。只读准入退出码 0，35/35 HEAD 匹配、受跟踪工作树干净；Manifest 保持 `f8e50677874c65b6da41057d2f39be7b4ef3c08a`。宿主 E: 实际空闲 `197,935,972,352` 字节，满足 50 GiB；ext4 空闲 `859,955,691,520` 字节、剩余 inode `66,821,538`，满足 20 GiB。时间戳只作预览：`2026-11-23T21:54:54Z` / epoch `1795470894`。

`build_eligible=false`、ccache 关闭。Kleaf 目标与 DFR 仍 BLOCKED_UNDETERMINED；实际时间戳传播、Image/vmlinux、OKI、模块、ABI/KMI、启动和 Root 仍 UNTESTED。本轮未执行 Stage 7.5 或编译、同步、源码修补。

新增原始证据位于 `E:\内核构建\reports`：

- `stage7_4_fixed_revalidation_tests.log` SHA256 `db3e502040eb3f2b1a2403bef7be2ff55064d3e7e2466973cdc774a8ff06121a`
- `stage7_4_fixed_source_gate.json` SHA256 `7d21340d6179410555d87d6d2a30d0ba70c4864f5bd98c5f762875eb907efaa3`
- `stage7_4_fixed_source_gate.log` SHA256 `e582d922f3a5e8461f01c2323eb56df8795d0f3b4a57e64f05090018ba06b578`
