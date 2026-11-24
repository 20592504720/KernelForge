# KernelForge

面向 Android Linux 内核的模块化、可审计自动化构建框架。项目旨在统一源码版本锁定、GKI/Vendor 构建适配、LLVM/GCC 工具链、KernelSU 及其衍生版本、补丁事务、设备配置、缓存隔离、构建报告与产物完整性验证。

**当前状态（2026-11-24）：第一阶段至 7.4 的约定范围云端完整验收已通过，进入文档中文化与 Stage 7.5 后续准备。** 当前开发分支为 `stage1/initial-foundation`，[PR #1](https://github.com/20592504720/KernelForge/pull/1) 尚未合并。本项目仍处于开发阶段，不提供已验证的一加 13 可刷写内核。

## 最新验收

| 项目 | 结果 |
| --- | --- |
| [完整云端验收](https://github.com/20592504720/KernelForge/actions/runs/45375493788) | 12/12 Job 成功 |
| Linux / Windows × Python 3.11 / 3.12 | 每环境 479 项；合计 1836 次非跳过通过、80 次平台跳过、0 失败 |
| 固定 ACK 6.1 ARM64 通用 GKI | 五组完整 Image 编译成功 |
| 产物独立校验 | 7 份 ZIP、5 份 Image SHA256 全部匹配 |
| CodeQL / Bandit 高风险 | 0 / 0（Bandit 中风险 1、低风险 56） |
| pip-audit / Gitleaks | 已锁定 Python 开发依赖无已知漏洞；149 个可达提交无凭据发现 |

[最终安全验收报告](docs/SECURITY_FINAL_ACCEPTANCE_2026_11_24.md) · [机器可读证据](docs/evidence/security_final_acceptance_2026_11_24.json) · [完整功能状态](docs/STATUS.md)

上述结论只适用于审查过的代码、固定源码及测试范围。不能据此声称所有上游内核漏洞均已排除、设备可启动或可以刷机。

## 已实现功能

| 功能 | 当前状态 |
| --- | --- |
| 配置 Schema、CLI 校验、Git 固定版本、独立 GKI/Vendor 适配器 | 已实现并通过软件回归 |
| LLVM/GCC 工具链获取、SHA256、解压、原子安装、缓存锁与租约 | 已实现并通过软件测试；真实大型发行包待验 |
| 官方 KernelSU、BakaSU、SUSFS | 固定 ACK6.1 五组真实 Image 验证通过；设备运行未验 |
| 补丁清单、版本锁定、事务、冲突检查、回滚 | 已实现并验证已审查组合及夹具 |
| TCP/ZRAM 源码与 Kconfig 检查 | 已实现并验证检查功能，算法运行待验 |
| 一加 13 / Ace 6 独立设备档案、源码 Manifest 审计 | 已实现；设备实际构建待验 |
| Git/Archive 安全获取、源码证据及兼容门禁 | 已实现并通过软件/历史证据验证；归档不直接准入构建 |
| Release 镜像身份验证与同摘要回退 | 已实现并通过离线测试，生产镜像待验 |
| ccache 安全身份隔离、锁与失效保护 | 已实现并通过软件测试，真实命中率待验 |
| 默认/自定义构建时间、Stage 7.4 准入门禁 | 已实现并通过策略测试；实际 OEM Bazel 传递待验 |
| 安全防护、跨平台回归及产物 SHA256 | 已完成约定范围验收；保留已知风险 |

### 五组已验证的真实 GKI 组合

| 固定组合 | 完整 Image |
| --- | --- |
| 官方 KernelSU（SUSFS 关闭） | 通过 |
| 官方 KernelSU + SUSFS | 通过 |
| BakaSU（SUSFS 关闭） | 通过 |
| BakaSU + SUSFS | 通过 |
| 新版精确锁定 BakaSU + SUSFS | 通过 |

仅为通用 ACK 6.1 ARM64 固定组合，不等于 OnePlus 13 OKI、ABI/KMI、boot、Root 或 SUSFS 真机运行验证。

## 支持范围与开发计划

- Linux 5.10、5.15、6.1、6.6、6.12：已有配置档案，只有上述精确 ACK6.1 组合拥有完整编译证据，不代表每个版本均支持所有补丁。
- 构建模式：GKI 与 Vendor 分立；Vendor 真实编译未验证。
- 主设备目标：一加 13（PJZ110 / SM8750 / 官方 Linux 6.6 OKI），已有官方 35 项源码锁及历史证据。Ace 6 为独立社区参考档案，未获刷机许可。
- KernelSU-Next、ReSukiSU 尚未实现；未经审核的移动版本及任意 Hook 组合不受支持。

### 开发中与待实现功能

Stage 7.5 已开始离线产物检查与静态审计；实际一加 13 Image/vmlinux 快速构建仍受本地锁、DFR、Kleaf 目标和资源门禁限制。Stage 8 尚未开始实施。

| Stage 8 选定目标 | 当前设备层状态 |
| --- | --- |
| 一加 13 完整官方 OKI 基线 | 待实现/验证 |
| BakaSU + SUSFS | 通用 GKI 已验证；设备集成待验 |
| 原生风驰 HMBIRD | 待实现/验证 |
| ccache 安全构建缓存 | 软件已验证；实际使用待验 |
| BBR + Westwood + 必需网络配置 | 待实现/验证 |
| ZRAM + 适配过的压缩算法 | 待实现/验证 |
| Droidspaces | 待实现/验证 |
| Mountify | 待实现/验证 |
| ADIOS I/O 调度器 | 条件性待实现 |
| Re:Kernel / Freezer / NoActive | 待实现/验证 |

暂缓项目包括其他设备/内核变体、其他 Root 分支、多 Hook、BBG、Unicode 零宽补丁、Brutal TCP、强制压缩算法升级、公共 ccache-ECS 等；完整保留 D01–D14 及历史需求于[Stage 8 精简功能矩阵](docs/STAGE8_EXPANDED_FEATURE_MATRIX.md)。Stage 9 自动化发布、签名与刷机门禁待实现。

详见[完整状态矩阵](docs/STATUS.md)与[开发路线图](docs/ROADMAP.md)。状态严格区分已实现并验证、已实现待验证、开发中、待实现、暂缓和当前不支持。

## 使用方法

已审核的开发依赖锁适用于 x86-64 Linux/WSL2、Windows，CPython 3.11 或 3.12。其他平台须独立审核依赖及 Wheel 哈希。请从仓库根目录执行：

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m kernelforge validate
python3 -m kernelforge validate-config
python3 -m kernelforge validate-patches
python3 -m kernelforge doctor
python3 -m unittest discover -s tests -v
```

Windows 可使用相应 Python 解释器的 `python -m`。Windows 完整回归亦可使用 `python -u scripts/windows_test_launcher.py`。实际内核编译使用经过审核的 Linux 环境，Windows 主要用于配置及软件测试。

已审核构建配置的 CLI 入口（示例路径须替换，不代表设备构建授权）：

```sh
python -m kernelforge build --config path/to/build.json
python -m kernelforge inspect-features --source /path/to/kernel --config /path/to/.config
python -m kernelforge toolchain list --cache-dir .cache/toolchains
```

`doctor` 检查本地 Python 及依赖。构建报告记录 Git Commit、工具链完整性与来源、耗时、日志和实际产物哈希；可选补丁在修改源码前写入 `patches.lock.json`。配置采用 Draft 2020-12 JSON Schema，未知字段拒绝；工具链默认配置位于 `configs/toolchains/defaults.json`，GKI/Vendor 可指定独立 `toolchain_profile`。下载须提供可信 SHA256。

工具链模式：`AUTO`（显式本地工具链、有效缓存、下载验证）、`LOCAL_ONLY`（本地或已验证缓存，无网络）、`DOWNLOAD_ONLY`（仅指定下载来源或对应有效缓存）。缓存清理须明确授权，不清理活跃租约；参数参考 `python -m kernelforge toolchain clean --help`。

构建时间 `build_timestamp` 可选；留空默认实际构建开始时 UTC，自定义示例 `2026-11-24T17:30:00+08:00`。无时区或非法值拒绝；普通构建引擎记录并传递 `KBUILD_BUILD_TIMESTAMP`、`SOURCE_DATE_EPOCH`，实际 OEM sandbox 传递仍待验证。[构建时间说明](docs/BUILD_TIMESTAMP.md)

## GitHub Actions

`validate.yml` 执行结构、配置及跨平台测试；CodeQL、依赖安全审计和 Git 历史扫描各有独立工作流。真实上游 GKI 检查按已审核组合运行；重型完整验收仅通过专用一次性请求触发。SM8750 源码审计不等于新同步或完整 OEM 编译。通用 `build.yml` 当前仅预检，`release.yml` 仍禁用发布门禁。不要因工作流存在就推断可编译或可刷机。

## 仓库目录

| 路径 | 用途 |
| --- | --- |
| `configs/`、`schemas/` | 配置、内核档案及严格 Schema |
| `patches/`、`manifests/` | 补丁清单、版本与源码锁 |
| `devices/` | 设备隔离档案 |
| `kernelforge/` | CLI、构建、源码、补丁与工具链管理 |
| `scripts/`、`tests/` | 验证工具、单元/集成/负向测试 |
| `.github/workflows/` | CI、安全审计、受控验收入口 |
| `docs/` | 架构、文档、路线图、阶段证据及安全报告 |

## 已知限制与安全边界

本地 WSL2 源码锁摘要差异、DFR include（BLOCKED_UNDETERMINED）、真实 ccache、独立 Vendor 归档、实际 OnePlus13 完整 OKI、ABI/KMI、设备启动与 Root/SUSFS 运行、OEM 实际构建时间传递仍未解决或未验证。XML/Expat 与可信 PATH/Git/SSH 的残余风险详见安全报告；不将扫描零发现等同于零漏洞。禁止未经批准的设备编译、刷写、发布、源码锁变更或缓存删除；`build_eligible=false`、`device_release_eligible=false` 的设备门禁保持有效。

## 文档与维护

[功能状态](docs/STATUS.md) · [路线图](docs/ROADMAP.md) · [架构](docs/ARCHITECTURE.md) · [配置](docs/CONFIGURATION.md) · [开发指南](docs/DEVELOPMENT.md) · [KernelSU](docs/KERNELSU.md) · [SUSFS 兼容性](docs/SUSFS_COMPATIBILITY.md) · [执行政策](docs/EXECUTION_POLICY.md)

项目主页与后续项目介绍默认使用中文；命令、技术名词、路径、配置键与机器可读状态保留原样。历史证据不改写。新功能、阶段验收、已知限制变化须同步更新 README、状态矩阵和路线图，并注明验证层级。
