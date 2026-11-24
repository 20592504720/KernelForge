# Stage 7.3 WSL2 本地 ccache 验收

## 范围与代码身份

本次只读盘点与隔离 Python 夹具测试基于远端 `stage1/initial-foundation` Commit `b86bc39996efd9f592b9bd8f600660bd0df82290`，Tree `8030ba2163095caac4e95cc4041449d2fd004e98`。本地保留原有历史后逐个接入远端 11 个提交，测试时本地 Commit `d408f93c1dde78a3a9b94c72bf960ea7ce230f3d`，Tree 相同，工作树干净。CI 已先通过：[Stage 7.3 专项 Run 45223495003](https://github.com/20592504720/KernelForge/actions/runs/45223495003)、[Validate Run 45223495085](https://github.com/20592504720/KernelForge/actions/runs/45223495085)。本地报告只补充 WSL2 证据，不把 CI 夹具当作真实缓存命中。

审查了 `kernelforge/build_cache.py`、`kernelforge/build.py`、`schemas/build.schema.json` 和 `docs/STAGE7_3_CCACHE_POLICY.md`。`build.ccache` 缺省未启用；启用时才进入隔离命名空间流程。设备 Profile（包括 PJZ110）在 Stage 7.4 真实 OKI/Manifest 准入前仍被明确拒绝。

## 被动环境盘点

| 项目 | 实测结果 | 状态 |
| --- | --- | --- |
| WSL2 | Ubuntu 24.04，Linux `6.18.58.1-microsoft-standard-WSL2`，x86_64；可用 CPU 8 | TESTED |
| ccache / sccache | PATH 均未发现；没有执行包装器，也未发现预设 `CCACHE_*` 环境变量名 | BLOCKED_NO_CCACHE_BINARY |
| Python / Git | `/usr/bin/python3` → `/usr/bin/python3.12`，`/usr/bin/git` 存在；未安装新依赖 | TESTED（存在性与测试可用性） |
| 源码 | ext4 的 `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750` 及 `.repo` 仍存在；未扫描或改动 35 项源码 | TESTED（存在性），内容本轮 UNTESTED |
| WSL 内存 | 总 `4,045,041,664` 字节；可用 `3,484,413,952` 字节；Swap 总/可用 `1,073,741,824` 字节 | TESTED |
| Windows E: | 总 `371,516,764,160` 字节，实际剩余 `198,018,408,448` 字节（约 184.4 GiB），高于 50 GiB 安全余量 | TESTED |
| ext4 | `df` 可用 `839,801,572` KiB、剩余 inode `66,821,538`；ext4 为虚拟磁盘视角，不代表 E: 的实际可用量 | TESTED |

WSL 启动时曾打印一次 systemd 用户会话启动警告，但只读脚本和测试均以退出码 0 完成。该警告的服务影响未进一步诊断（UNTESTED）。没有创建真实 ccache 根目录、修改 `CCACHE_CONFIGPATH`、清理缓存或运行 Bazel/Repo。

## 隔离测试与策略核验

在 `/mnt/e/内核构建/project` 以 `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_stage7_3_*.py' -v` 运行：**29 项通过、0 失败、0 错误、退出码 0**。测试使用临时夹具目录，不读取或写入 OnePlus 35 项源码。

测试覆盖：缺省关闭和设备 Profile 拒绝；源码/工具链/输出与缓存路径重叠拒绝；命名空间身份隔离、有效期与 symlink 安全；`prune` 缺省 dry-run；活动和残留 lease 阻止清理；损坏元数据拒绝重用；构建失败或 `.config` 变化后的命名空间隔离。测试中的显式清理仅针对其一次性临时夹具，没有清理实际用户缓存。缓存命中率、真实 ccache 二进制运行、Bazel/Kleaf 编译器拦截和物理磁盘硬配额均为 **UNTESTED**。

## 原始证据

原始日志只保存在 `E:\内核构建\reports`：

| 文件 | SHA256 |
| --- | --- |
| `stage7_3_wsl2_passive_inventory.log` | `04c947a7ccc746a8b46a23c872dd1a47eb31c55adbd2e6ea6d2c39d121ed3a73` |
| `stage7_3_passive_probe.json` | `dc01fd956440ac19d2e7d2a660c1c0646cedf3d5645e7abb46a1906af8b44bac` |
| `stage7_3_wsl2_fixture_tests.log` | `5eeb9c0f2c93caa04093eb4b7b381578ad9ef1ff8f7f6bf8a668bf05ca1f4a25` |

机器可读结论见 [stage7_3_wsl2_ccache_audit.json](evidence/stage7_3_wsl2_ccache_audit.json)。

## 判定

**Stage 7.4 软件开发可以在 `ccache` 继续关闭的条件下进行。** 本地真实 ccache 执行和命中率仍因缺少二进制而受阻；不得从本轮 29 项夹具通过推断缓存加速或 OnePlus 13 OKI 构建成功。本次未执行安装、下载、Bazel 查询、内核构建、源码同步或任何实际缓存修剪。
