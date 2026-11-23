# Stage 7.2 本地工具链与镜像来源核验

## 范围与基线

- 开发分支：`stage1/initial-foundation`；核验时远端 Commit `b70f624b0814573efe91f0ea2f90ab879216c4e8`、Tree `8bafc063aa5be60313d1e91fa4d07fb2383faf41`。
- WSL2 ext4 源码：`/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`。
- 只执行现有 ELF 的版本查询、`ldd`、哈希与只读资源采样。没有执行 Bazel/Bazelisk、Repo 同步、编译、安装、下载或镜像创建。
- 机器可读结论见 [stage7_2_local_toolchain_review.json](evidence/stage7_2_local_toolchain_review.json)。原始 JSON 和采样脚本保存在 `E:\内核构建\reports`，不属于 Git 仓库。

## 直接运行结果

下表路径均相对于上述源码工作区。全部版本命令退出码为 0，ELF `e_machine=62`（Linux x86_64）。

| 工具 | 实际可执行路径 | 结果 | SHA256 | 状态 |
| --- | --- | --- | --- | --- |
| Clang | `kernel_platform/prebuilts/clang/host/linux-x86/clang-r510928/bin/clang` | Android r510928，Clang 18.0.0；`-print-target-triple` 为 `x86_64-unknown-linux-gnu` | `dc739fc44bb889146bd47732912cad457200af7de7c2fb5a7509b7a9974d6d67` | TESTED |
| LLD | `kernel_platform/prebuilts/clang/host/linux-x86/clang-r510928/bin/ld.lld` → `lld` | LLD 18.0.0 | 目标二进制 `27fdf99341929eab1f615a3172169b8dadd117b76a05b0abfa0a21873d1626a0` | TESTED |
| LLVM-NM | `kernel_platform/prebuilts/clang/host/linux-x86/clang-r510928/bin/llvm-nm` | LLVM 18.0.0 | `06e6634e0abe46ce464e09907955d5202451f7c545896e4c56162b721e74e3a6` | TESTED |
| GNU Make | `kernel_platform/prebuilts/build-tools/linux-x86/bin/make` | GNU Make 4.3 | `a9472ab2dc5ab512bd946ca73dc84e4d911df4ad028f48bdbfaf3a500a88ffee` | TESTED |

`ldd` 对 Clang 返回 `not a dynamic executable`，并非版本查询失败；LLD、LLVM-NM 和 Make 的动态库列表没有 `not found`。以上证明这些主机工具能在本机直接启动，不证明 ARM64 交叉编译、链接或完整内核构建成功。Clang 的默认 triple 是主机 triple。

## 原始来源、归档及许可

源码锁指定 CodeLinaro 仓库 `https://git.codelinaro.org/clo/la/kernelplatform/prebuilts-master/clang/host/linux-x86`，完整 Commit `b099698c583b8361ca771f3cc8d6af6f729f39b3`。现有 Git checkout 的 HEAD 与锁完全一致（TESTED）。`AndroidVersion.txt` 标记 18.0.0 / r510928；`clang_source_info.md` 记载 LLVM base revision `82e851a407c52d65ce65e7aa58453127e67d42a0`，运行时 `clang --version` 报告 Android llvm-project Commit `477610d4d0d988e69dbc3fae4fe86bff3f07f2b5`。这些分别是预编译仓库、LLVM 基线与运行时源码标识，不能互相替代。

[AOSP 的预编译仓库](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/)也列出 r510928，[AOSP 更新提交](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+/d604c47753dee3241981cc106cd139a2da5eb7aa)说明版本来源；尚未证实其文件字节与上述 CodeLinaro 锁定 Commit 一致。

**镜像结论：`BLOCKED_NO_VERIFIED_RELEASE`。** 本轮没有选定并验证可对应此工具链的完整公开发布归档，因此完整归档 SHA256、GitHub Release ID、Asset ID、上传者、Asset 大小和与原始上游归档的字节等价性均为 UNTESTED。单个 `clang` 的 SHA256 不能充当归档哈希。没有创建镜像或版本锁，可继续使用本地已锁定的工具链。

本地 `clang-r510928/NOTICE` 首行声明 LLVM Project 使用 Apache 2.0 with LLVM Exceptions；`Android.bp` 列出多个许可类别；**同一检出的 `METADATA` 将整个条目标记为 `license_type: RESTRICTED`，并记载捆绑 Python 内容的 LGPL 注意事项**。因此不能从 LLVM 主程序许可证推断整套归档的再分发权。整包许可清点、来源归属和镜像发布许可仍为 UNTESTED，公开镜像建立受到此项阻碍。精确文件哈希和完整证据字段见 JSON。

## 资源复核

2026-11-23 16:12 UTC 采样：WSL 可用内存 `3,482,624,000` 字节（总 `4,045,045,760`），Swap 可用 `1,073,741,824` 字节（总量相同）。Windows E: 总量 `371,516,764,160` 字节，实际剩余 `198,056,513,536` 字节，约 **184.4 GiB**，高于 50 GiB 安全余量。ext4 统计的空闲 `859,982,655,488` 字节属于虚拟磁盘视角，不可代替宿主 E: 的剩余容量。资源采样状态为 TESTED；未来构建时的峰值内存及磁盘占用为 UNTESTED。

## 可复核证据与剩余事项

- `E:\内核构建\reports\stage7_2_direct_tool_probe.json`：SHA256 `c63860c37ec774834294a42733cbb6c362309a8d6027e7b5510a6544ee5bb4a0`；含逐命令 stdout/stderr、退出码、ELF、链接库及二进制哈希。
- `E:\内核构建\reports\stage7_2_source_resource_probe.json`：SHA256 `f20589f9ec5a4ad010e09840449ccaab2e40f3540521d89390d0e315b20e4e6e`；含源码仓库 HEAD、远端、许可文件哈希及资源样本。
- TESTED：锁定的 CodeLinaro checkout、四种本机工具的直接执行与当前宿主容量。
- UNTESTED：完整公开归档字节等价、ARM64 交叉编译、完整构建以及整包再分发许可。
- BLOCKED：可信镜像发布缺少已核验的完整归档身份、哈希和再分发依据。

后续如需镜像，应先取得可追溯的发布资产和完整归档 SHA256，对照同一上游来源验证字节，并逐项审计归档许可；本轮不进入 Stage 7.3。
