# Stage 7.4-O 复审整改说明

本轮以 `03ed5571da39d498f9fdcfe8a94f5bf740aeed8b` 为基线。具体候选提交、命令、原始日志、逐项 Ruff 处置及分类验收见独立保存的 `reports/stage7_4_o_review_20261126` 交付目录。未变化的历史交付不重复验证，也不以历史测试替代本轮最终提交的复验。

## 安全边界

- 证据读取：逐层拒绝链接/reparse 父目录，打开后核验普通文件、单一链接及大小；有界读取后再次核验大小和时间，严格 UTF-8 并验证调用方提供的 SHA256。POSIX 使用目录描述符及 `O_NOFOLLOW/O_NONBLOCK`；Windows 固定祖先及文件句柄，禁止写入/删除共享。
- 证据发布：独占 pending 文件、文件 fsync、不可覆盖 hardlink 发布。POSIX 同步目录；Windows 仅承诺文件同步。进程中断下的原子可见性与断电持久性分别记录，断电结果仍依赖文件系统和存储硬件。
- Git：有界安全读取配置/指针，`git config --file - --no-includes` 解析受检字节，并固定执行的 Git 布局。实际 Git 子进程仍会重读仓库配置；持有相同权限的并发写入者能在审计后修改配置/代码，此风险为 **MITIGATED**。可信 PATH、解释器、Git 程序、仓库与祖先目录、OS 管理员均属于信任边界。
- Windows junction：`NtCreateFile(FILE_CREATE)` 原子创建并取得独占句柄，随后写入 reparse 数据；失败时按句柄标记删除，祖先与目标目录在操作期间固定。不能把该措施解释为隔离同权限恶意进程。
- 构建异常：常规异常在最外层生成失败报告；中断类异常原样传播。缓存隔离失败时保留 lease 供人工核对，不能无条件关闭后重新复用。

所有同权限或管理员修改可执行代码的风险保持 **MITIGATED**，并非完全消除的竞态。工作区、缓存及解释器目录需由调用用户控制，不能共享给不可信写入者。

## Python 环境初始化

`python scripts/environment_preflight.py` 检查现有解释器、依赖实际导入、版本及路径能力。使用可信的现有 CPython 3.11/3.12 执行：

```text
python scripts/environment_preflight.py --initialize-from-wheelhouse <受检本地wheel目录>
```

依赖锁内容决定环境名。验证 venv 配置、可信基础解释器/Windows launcher、实际 pip 与依赖导入路径和版本；合格环境直接复用。缓存检查 POSIX owner/mode 或 Windows SID、DACL，任意无关主体写权限均拒绝。环境锁防止并发初始化；pending 标记与失败环境保留。损坏环境只有在使用 `--repair-environment` 时才隔离旧目录并离线重建，失败也不删除旧内容。

pip 使用隔离解释器和清理后的环境，屏蔽配置、禁止 index/cache/源码包，wheel SHA256 必须在依赖锁中。离线 wheelhouse 及基础解释器是可信输入；相同权限下的检查后替换仍受上述信任边界约束。

Windows 外部工具路径采用保守的 240 UTF-16 单位预算，并在 build、checkout、下载、工具准备和 Python 初始化之前留出后代路径空间；解压成员与实际可执行文件另行检查。Python 文件操作支持长路径不能证明 Git/编译器支持。门禁拒绝时改用更短、受控的工作区或缓存路径；不自动修改系统设置。

## Python 3.11 隔离验证方案（尚未执行安装）

既有 Windows/WSL 常见安装目录未找到合格 3.11，当前运行测试使用既有 3.12。Pyright 3.11 目标仅证明静态兼容，不替代运行测试。新增 Python 安装需用户单独授权。

优先方案为官方 [CPython 3.11.18 源码](https://www.python.org/downloads/release/python-31118/)，发布于 2026-10-25；[XZ 源码](https://www.python.org/ftp/python/3.11.18/Python-3.11.18.tar.xz) 官方 SHA256 为 `9120e0a653868f6e3698d36cdd99e5a58903ec9469e448f21d98f7b16d8fa290`，另有同目录 `.sigstore` 签名。授权后先下载并校验哈希/发布者身份，在 WSL 独立目录配置 `--prefix=/home/kernelforge/.local/cpython-3.11.18`、`--with-ensurepip=install`，默认 `make -j2` 后 `make altinstall`。不使用 sudo、不写 `/usr/bin`、不变更 PATH、alternatives 或默认 Python；通过完整路径创建单独 venv，按现有锁离线安装并复验。本方案还需确认编译依赖和磁盘；缺失依赖的安装另行授权。

Windows 最后一个官方 3.11 安装器为 [3.11.9 amd64](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)，其官方 Sigstore bundle 的 SHA256 digest 为 `5ee42c4eee1e6b4464bb23722f90b45303f79442df63083f05322f1785f5fdde`。它已被后续源码安全版本替代，不能称为当前安全版本。只有明确接受该验证版本时，授权后核验安装器哈希、Sigstore 和 Authenticode，再按当前用户独立 TargetDir 安装，禁用 PATH、launcher、文件关联和全局注册；不得改变默认 Python。下载文件实物和签名验证尚未完成，不能据此计为安装包验收通过。

## Release、MCP 与真实构建

Release 仅声明 `workflow_dispatch`，job 要求不可由该触发器满足的 `github.event_name == 'kernelforge_release_disabled'`；整份禁用模板以 SHA256 固定审计。保持发布/上传禁用。Context7 与 GitHub MCP 为可选辅助工具；认证或额度失败均不构成无依据的构建硬依赖。

默认仍为 `-j2`、ccache 关闭，`build_eligible=false`。本轮只授权软件复验；没有真实大型内核构建、刷机、Stage 7.5/8 执行或发布。

## O4/O5/O6 性能后续清单

以下条目是待准入的真实实验，轻量文件/小程序计时不能计为内核收益：

| 项目 | 所需对照与身份 | 指标与准入 |
| --- | --- | --- |
| O4 工具链缓存 | 固定工具链包 SHA256、版本/目标、压缩包和安装目录身份；冷下载/校验/解压与同包热命中 | 分阶段 wall time、CPU、磁盘、网络字节及产物一致性；具备可信完整缓存才可执行 |
| O5 构建并发 | 同一源码 commit、配置、补丁、编译器、时间戳，先保留 `-j2` 基线；不同并发各至少三次并记录冷/热状态 | 中位数与离散度、峰值 RAM、CPU、I/O、交换区和磁盘余量；获得真实构建授权后才评估更高并发 |
| O6 ccache | 同一完整身份，关闭、首次填充、同输入热构建、单文件变化和输入不匹配拒绝 | ccache 命中/未命中/错误、缓存大小、lease/失效、构建耗时及产物一致性；先取得可信 ccache 与固定大型源树 |

每次实验必须保存原始命令、环境、退出码、资源采样、产物哈希和失败；默认设置只有在真实对照支持并获授权后才调整。当前 O4/O5/O6 均不声明真实内核性能提升。
