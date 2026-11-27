# T09 云端验收记录（2026-11-27）

## 结论与适用范围

最终软件回归 PASS，9/9 云端 Job 成功。候选 Commit `451fb613f3fc0f4e7afbeb648742f60539ec07c4`，Tree `6d008af76a85926bbe8ec97edd508a251ed89a97`（259 个 tracked 文件）。验收分支工作流显式检出上述提交；验收分支自身的工作流 Tree 并非产品代码 Tree。本文档后置更新不改变已验收的程序、配置、测试或工作流。

原始本地封存提交 `df8ce3a0cc16e08c2ea38d5118571508563a6be1` 保留；原参考开发分支 `ccc8f1184d13a78a6d6a35ccae7c6d94cc51380f` 保留。相对参考版本共 113 个文件差异（81 修改、32 新增、0 删除）。原本地证据适用于其原 Tree，不挪用于后续修改。

## 最终云端矩阵

| 环境 | 执行方法 | 非跳过通过 | 跳过 | FAIL/ERROR | 退出码 |
| --- | ---: | ---: | ---: | --- | ---: |
| Ubuntu CPython 3.11 | 568 | 559 | 9 | 0/0 | 0 |
| Ubuntu CPython 3.12 | 568 | 559 | 9 | 0/0 | 0 |
| Windows CPython 3.11 | 568 | 521 | 47 | 0/0 | 0 |
| Windows CPython 3.12 | 568 | 521 | 47 | 0/0 | 0 |

合计 2272 项次，2160 非跳过通过，112 平台条件跳过。两套 Windows 测试均清理隔离目录，未遗留工作线程，实际退出码 0。四环境均核验完整检出及三种行尾配置。源锁 SHA256 为 `22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7`；历史混合 CRLF/LF 差异已经重建验证，不改变 35 项源码锁定身份。

- [Validate](https://github.com/20592504720/KernelForge/actions/runs/45948966996)：4/4。
- [CodeQL](https://github.com/20592504720/KernelForge/actions/runs/45948967060)：0 发现。
- [依赖及静态安全审计](https://github.com/20592504720/KernelForge/actions/runs/45948966997)：3/3，pip-audit 无已知漏洞，Bandit 高 0 / 中 1 / 低 53，扫描错误 0。
- [Gitleaks](https://github.com/20592504720/KernelForge/actions/runs/45948966987)：175 个可达提交，0 命中。

## 整改与残余限制

CI checkout 遗留配置仅在隔离工作区按审核值精确清理；不放宽 Git 配置白名单。CPython 3.11 采用可信解释器自带 pip wheel 的离线初始化，不引入 setuptools 的启动文件。Windows 真实原生 ACE 采用数字 SID 判定，拒绝其他主体写授权；长路径以实际规范化路径计算预算，Junction 按文件对象身份验证。Windows 原生 ACL 异主写授权拒绝、SID 同一性、长路径及离线初始化回归均通过。

Bandit B314 为 XML 解析启发式发现，已有 UTF-8、DTD/ENTITY 拒绝及资源预算防护；仍保留 Expat 残余风险。其余低风险主要为 subprocess 调用及可信 PATH/Git/SSH 边界，不作为零漏洞声明。完整 113 文件独立逐行语义审计尚未全部完成；扫描与回归不能替代人工审计。Windows 独立异主账户测试、历史 WinError 32 与并发锁超时根因仍未完全验证。

阶段 7.5 的实际 DFR external DDK / Bazel 图、资源及进程合同、OEM action 时间传递、真实性能、完整 OKI、ABI/KMI、真机运行均未验。软件门禁通过不授权真实内核构建、刷机或发布。Stage 8/9 尚未实施。原始历史证据保持不变。

## 执行方式

T09 内部集中整改，不新增 T10。后续 Stage 7.5、8、9 采用整阶段执行，必要时集中整改并统一验收；不将普通内部检查拆分为需要用户逐轮批准的子任务。重大风险操作仍须授权。
