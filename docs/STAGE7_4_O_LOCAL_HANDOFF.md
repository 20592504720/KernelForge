# Stage 7.4-O 本地性能专项交接（只读先行）

**目的：排除负优化，不直接执行 OEM 构建。** 云端第一批候选 `66a51aabbe749a2b40efa39ad467362f2a347c58` 已通过软件和安全回归；见 [优化专项](STAGE7_4_O_OPTIMIZATION.md)。应以实际远端 HEAD 为准，禁止回退历史、重写锁或覆盖本地未提交文件。

## 任务 A：环境与前置门禁（可立即只读执行）

原有 WSL2 设备源码、35 项锁与 E 盘项目保持原样。先检查 git status/HEAD/Tree、历史和当前源码锁的实际原始 SHA256，报告差异原因而不重写。检查 WSL CPU 配额/亲和性、cgroup memory.max、memory.current、MemAvailable、SwapFree、物理 Windows E: 可用空间、ext4 空间与 inode、现有编译器/Bazel/ccache 可执行路径及 SHA256。不得使用旧资源采样替代当前数据。历史锁差异、DFR 未解、Stage 7.5 源码准入仍为阻塞；本次不运行 Bazel（包括 cquery/aquery）、repo sync、真实内核编译。

可参考只读命令（按当前环境确认路径，缺失即记录，不安装）：

```sh
git status --short
git rev-parse HEAD
git rev-parse 'HEAD^{tree}'
sha256sum manifests/oneplus13-pjz110-sm8750-source.lock.json
nproc
grep -E 'MemAvailable|SwapFree|MemTotal' /proc/meminfo
df -h
df -i
command -v clang
command -v ccache
```

Windows 主机物理磁盘另用 `Get-Volume -DriveLetter E`，不能以 WSL ext4 逻辑空间替代。既定保留：E: 50 GiB、ext4 20 GiB；不删除已有数据。

## 任务 B：工具链缓存实测（有可信既有样本才执行）

不下载大型工具链、不运行现有 cache clean。仅在另行批准的隔离临时目录，对已审核的同一归档及安装树做旧/新算法对照，确保严格/legacy 摘要一致，独立解压再复核仍存在，记录每次总时间、峰值 RSS、逻辑读写字节与临时空间。先记录磁盘预算，再准备副本；空间不足或许可不明即 BLOCKED。不得直接在原始缓存试验。

## 任务 C：真实线程及 ccache 后续合同（不在此次只读任务执行）

- 固定源码/补丁/配置/编译器/构建时间；先完成准入、确认真实命令与运行限额，再在用户单独批准后，用通用已审查 GKI 或专用受控测试目标做 -j2 与候选线程（按实测 CPU、RAM 与链接峰值选择）的重复对照。至少记录 CPU wall time、峰值 RSS/cgroup、swap、物理磁盘/空间、失败、Image/vmlinux 哈希与配置/符号检查。不得将通用 GKI 当作一加13 OKI。
- ccache 缺失即 BLOCKED，不自动安装。只有受信二进制和真实编译器拦截证据具备时才提出冷热对照；先固定构建时间，确保身份一致，验证 cache hit/miss、输出字节、污染负向测试及回滚。默认关闭，不移除 timestamp、环境、设备、源码、补丁或工具链隔离。
- 整体速度或资源无实际改善、任何错误/安全退化均不保留。若样本不足，标 INCONCLUSIVE，不宣称加速。

## 任务 D：返回结果

将只读检查及后续经批准的实测分开记录，给出日期、机器环境、实际命令、输入身份、每次样本、日志位置、失败和无法执行原因。建议报告 `docs/STAGE7_4_O_LOCAL_BENCHMARK.md` 与对应 JSON；只在明确获准后提交开发分支。保持 main、PR #1、源码与历史证据不变。O2 required checks 需要仓库管理员只读查看分支保护及 Rulesets，不能更改设置。O3 远端浅层抓取兼容性由云端后续专项验证，不要求修改现有本地 Git 工作区。
