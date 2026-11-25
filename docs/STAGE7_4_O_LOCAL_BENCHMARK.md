# Stage 7.4-O 本地性能交接

日期：2026-11-25（Asia/Shanghai）。开发分支远端 Commit `9690047eb4bec86959d5d9cbcc3e894e6326a9e7`；本地保留历史、逐项接入 27 个远端提交后 Commit `2d3b54f6b596fd4c1fe52bcef507d7b9b5e2f4ce`。两者 Tree 均为 `c8169ae684990f6e59bfa5f570e487c6143c79a5`，工作树采样前干净。源码锁 SHA256 实算为 `7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e`；它只证明本地锁文件字节，未在本轮重复审计 35 项源码。

## 本机只读采样

WSL2 Ubuntu 24.04，CPU 逻辑数与进程亲和性均为 8，`cpu.max=max 100000`，有效 CPU 集 `0-7`；`memory.max=max`，`memory.current=959,078,400` 字节。`/proc/meminfo`：MemTotal 3,950,236 KiB、MemAvailable 3,366,872 KiB；SwapTotal/SwapFree 均为 1,048,576 KiB。`max` 表示此 cgroup 未设置数值上限，不能推断宿主机有无限内存。真实编译峰值与 OOM 风险仍未测量。

Windows E: 物理盘总量 `371,516,764,160` 字节、实际可用 `196,092,567,552` 字节（约 182.62 GiB），满足 50 GiB 保留量。ext4 逻辑可用 `859,861,880,832` 字节，剩余 inode `66,821,107`，满足 20 GiB；该逻辑空闲不能替代宿主 E: 空间。

PATH 无 `clang`、`ld.lld`、`llvm-nm`、`bazel`、`bazelisk`、`ccache`、`sccache` 或 `make`。已锁定源码中可直接定位 Clang r510928、LLD、GNU Make 和 Bazel 包装脚本；分别记录其绝对路径和 SHA256 于 [机器报告](evidence/stage7_4_o_local_benchmark.json)。本轮只读取文件和哈希，未运行 Bazel 包装器。`CCACHE_*` 环境变量名为空。ccache 冷热命中率：BLOCKED_NO_CCACHE_BINARY。

## 性能证据与负优化判定

本地实测仅为资源快照和工具文件哈希，**无本地旧/新耗时或 RSS 对照**。交接文档已有的[云端隔离微基准](STAGE7_4_O_OPTIMIZATION.md)显示：36,293,120 字节 Image 的五次中位哈希耗时旧 34.52 ms、新 25.51 ms，Python tracemalloc 峰值 36,297,658/267,345 字节；16 MiB 模拟树初检旧/新读取 33,554,432/16,777,216 字节，耗时 27.64/13.71 ms。该容器样本不是本机进程 RSS，也不证明真实工具链整条缓存流程或内核构建加速。真实 GKI 主步骤历史值为 1018/989/1035/1754/1019 秒，包含获取、集成与构建，不能当纯编译基准。

在 `E:\内核构建\reports` 未发现适合受控复测的已审核完整工具链归档和独立安装树；完整归档 SHA256 与整包再分发许可也仍缺可验证依据。因此任务 B 的本地旧/新缓存算法对照为 BLOCKED_NO_VERIFIED_SAMPLE。没有准备副本或占用额外的大型临时空间。O5 线程对照和 O6 ccache 冷热对照依照交接属于后续单独批准的动态验证，本次没有样本，结论 INCONCLUSIVE；继续保留 `-j2` 和 ccache 默认关闭。

## 后续门禁

先解决 DFR 依赖、Stage 7.5 源码准入和真实构建目标，再给出隔离容量预算、固定源码/配置/时间戳与重复测量方案。O2 required checks 的分支保护 API 历史返回 403，需要管理员只读核对；O3 远端浅层获取由云端验证。任何优化必须保持安装树严格/legacy 摘要、独立解压复核、产物双哈希和安全配置，不以单次微基准作生产速度结论。

原始数据：`E:\内核构建\reports\stage7_4_o_passive_probe.json`，SHA256 `9b44f557970d897b96ab66abc667d1d271efe6278da920cecef3e1c22e3fd693`。本轮没有运行 Bazel、Repo、编译、下载、清理或修改源码。Stage 7.4-O 整体保持 IN_PROGRESS。
