# Stage 7.4-O 接管与安全准入交接（2026-11-25）

## 结论

隔离工作树中的定向安全审计、根因修复和双平台软件回归已完成；本地软件检查通过。Stage 7.4-O **整体仍未结项**：性能证据不足，O5/O6 阻塞，正式完整回归未运行，真实 OEM/GKI 编译及设备验收未执行。不得把本报告解释为构建准入或性能 PASS。

## 工作区与边界

| 项目 | 核验结果 |
| --- | --- |
| 隔离工作树 | `E:\内核构建\worktrees\kernelforge-stage74o-resume`，分支 `codex/stage7-4-o-resume` |
| 修改前基线 | HEAD `da2ed84a185b88ffd782e564c740de893bb173f8`；Tree `39a1d9173ff4fc885173667dfdc56da9527c9d0d` |
| 正式工作区 | `E:\内核构建\project`；分支 `stage1/initial-foundation`；HEAD/Tree 与基线一致；`git status --short` 为空 |
| 源锁摘要 | 隔离 LF 文件 `22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7`；正式工作区混合行尾文件 `7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e` |
| 改动范围 | 仅隔离分支的安全实现、调用点、行尾策略和回归测试；R2 本地检查点提交到隔离分支。正式工作区、main、远端、依赖锁及既有历史证据均未改动 |
| 禁止项 | 未 Push、未合并 PR #1；未运行 repo sync、Bazel、真实内核编译、设备刷写或 Stage 7.5/8 |

## 审计发现与最小修复

| 发现 | 修改 | 原因/边界 |
| --- | --- | --- |
| Git 子进程会继承大部分调用环境，残留的 `GIT_*` 可改变仓库定位、配置、对象解析或辅助命令行为 | `kernelforge/source.py` 新增进程级 `git_environment()`；在源码获取、来源等价检查、SM8750 同步和 Stage 7.4 准入调用中复用 | 丢弃继承的 `GIT_*`，禁用 system/global Git config、替换对象、可选锁及交互提示；不修改用户全局配置。仓库本地配置仍按 Git 默认规则适用 |
| Git 来源 URL userinfo 可携带凭据并进入外部 Git 请求链路 | `validate_repository()` 拒绝 URL 中的 username/password；新增 HTTPS/SSH 负向测试 | 不影响无 userinfo 的锁定 HTTPS URL；SCP 风格 SSH 仍允许，SSH agent/SSH 配置未被本次隔离 |
| Windows junction 通过 `cmd /c mklink`，路径元字符可能被命令解释器当作语法 | `kernelforge/kernelsu.py::_link()` 在启动命令解释器前拒绝元字符路径；加入离线负向测试 | 对含 `&|<>^()%!`、引号及换行的路径安全失败关闭；不改变 POSIX symlink 逻辑 |
| 一项同步测试用主机全局 Git 配置创建临时仓库，却用隔离 Git 环境检查，导致行尾配置不一致的假失败 | 测试夹具创建/提交 Git 仓库时改用同一 `git_environment()` | 让夹具与受测生产调用使用相同 Git 配置边界，不触碰主机全局设置 |

## 静态审计摘要

- `kernelforge` 包内未发现 `shell=True` 或 `os.system()` 调用；唯一明确的 Windows `cmd /c` junction 路径已增加命令解释器元字符拒绝检查。
- 复核 Git 来源获取、来源归档路径/成员校验、缓存摘要验证、工具链解压边界和 Stage 7.4 准入中的路径/锁调用。现有实现包含路径规范化、链接拒绝、归档成员/字节预算和 SHA256 检查；这属于静态与定向测试证据，不构成对所有文件系统竞态或 TOCTOU 的形式化证明。
- 解析了 14 个 GitHub Actions workflow：未发现 `pull_request_target`、`workflow_run` 或 `secrets.*` 插值；顶层权限为 `contents: read`，CodeQL 另需 `security-events: write`；第三方 action 使用固定 commit SHA。未触发云端 workflow，也未测试仓库端规则集。
- HTTP/SSH URL userinfo 拒绝已验证；SSH agent、SSH 配置、操作系统凭据存储及恶意远端行为未作为隔离承诺。

## 定向验证

在 Windows 隔离工作树运行：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:PYTHONPATH='tests'
python -B -m unittest tests.test_kernelsu tests.test_build tests.test_security_hardening tests.test_stage6_source_equivalence tests.test_stage7_4_fast_build_gate tests.test_sm8750_sync -v
```

- **137 项运行：116 项通过、21 项条件跳过、0 失败。** 跳过项因 Windows 无法证明 POSIX 文件模式，或当前环境不保证符号链接权限。
- 新增 `test_repository_text_policy`，覆盖有效 `.gitattributes`、摘要锁字节稳定性及三种 `autocrlf/core.eol` checkout 配置。
- WSL2 ext4 验证副本同步到最新隔离工作树后运行同一 7 个模块：**137 项运行、136 项通过、1 项条件跳过、0 失败**；源文件 322 个，目标文件 322 个，逐文件 SHA256 不匹配 0 个。
- `python -B -m compileall -q kernelforge scripts tests`：通过。
- `git diff --check`：通过。
- Windows 日志：`reports/stage7_4_o_r2_20261125/windows-r2-cross-platform-tests-final.log`，SHA256 `8364c535cc1650297a98fcedd11c173544d08feda8fdc5c1f16160a55be3534e`。
- WSL 日志：`reports/stage7_4_o_r2_20261125/wsl-r2-current-tests-final.log`，SHA256 `d210419235e2e88f1bc7a0aceaed3b1fdaf4ba3d97b1af0c48645e45bd24f321`。
- 这是定向跨平台回归，不是完整正式回归；也没有真实构建样本。

## O1–O8 恢复矩阵

| 项目 | 当前结论 | 后续准入条件 |
| --- | --- | --- |
| O1 | 已有实现及先前软件/云端证据；本轮未重跑云端 | 保持原验收范围，不推导整体编译提速 |
| O2 | 待评估 | 管理员只读核验 required checks/Rulesets；不得通过跳过正式门禁来优化触发 |
| O3 | 仅有一次隔离本地对照；未修改生产 checkout，结论 INCONCLUSIVE | 真实远端、兼容性及拒绝任意 SHA 的边界对照 |
| O4 | 已有缓存校验实现与先前证据；本轮未下载或重测大型工具链 | 仅在可信既有样本与隔离目录具备时测量完整流程 |
| O5 | BLOCKED / 无可靠当前资源和吞吐样本 | 保持 `-j2`；另行批准后采样 CPU/RAM/swap/峰值/物理磁盘并做重复对照 |
| O6 | BLOCKED / 无 ccache 二进制及真实编译器拦截证据 | 默认关闭；先固定输入身份，再做冷/热编译及产物一致性验证 |
| O7 | 部分完成 / 长期独立证据保管策略待定 | 审核外部持久存储、访问与到期策略 |
| O8 | 本轮仅定向回归；正式完整回归未执行 | 最终改动集合经授权后跑正式跨平台回归；跳过项不得计 PASS |

## 阻塞与下一步

1. R2 差异已在隔离分支保存本地检查点；后续交由独立审核，不自动推送或合并。
2. 正式工作区混合行尾锁与隔离 LF 锁的摘要不同；本轮保持原状，须独立批准后再解决，不能将隔离测试结果替代该整改。
3. Windows `longPathsEnabled=0`、O5/O6 证据缺失、DFR/Stage 7.5 源码和 Bazel action/output 验证未完成，仍是准入阻塞。
4. 不运行真实 OEM/GKI 编译、正式全量回归、repo sync、Bazel、Push、PR 合并或 Stage 7.5/8，除非之后得到明确授权。

结构化记录：[`docs/evidence/stage7_4_o_resume_checkpoint_2026-11-25.json`](evidence/stage7_4_o_resume_checkpoint_2026-11-25.json)。
