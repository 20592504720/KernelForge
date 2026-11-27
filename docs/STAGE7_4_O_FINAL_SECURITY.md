# Stage 7.4-O-Final 安全边界与恢复约定

本轮继承 R2-E 项目规则、MCP 配置和九项技能，仅在原有工作树开发；正式工作区通过本地快进整合，不改变 main 或远端设置。

## Git 配置与仓库定位

普通仓库、裸仓库、worktree、子模块、独立 gitdir 均纳入布局识别。审计共同配置和单工作树配置；未知本地配置采用默认拒绝策略，拒绝 include、helpers、hooks、filter、凭据、代理、协议和 URL 重写等未经审核的能力。错误不回显配置键或值，防止 subsection 自身携带秘密。只允许明确审阅的被动字段和环境配置。

仅解释子命令之前的全局参数；不允许调用者覆盖 gitdir/worktree/config-env 或任意 `-c`。正常仓库操作显式定位到已审计 gitdir/worktree；clone/init/ls-remote 使用自己的仓库独立语义，不注入调用者仓库路径。环境隔离保留 TLS 和 SSH host-key 验证，清除继承的 Git 控制变量。

审计与执行仍是两个独立操作。具有同一用户写权限的进程可以并发改写配置、gitdir 指针或父目录；纯路径审计和调用前哈希无法消除这个安全域中的 TOCTOU。该边界标记为 `MITIGATED`，不得宣称对恶意同权限写入者隔离。要求源码、Git 元数据和父目录由受信用户独占维护。不同所有者的仓库沿用 Git 自身精确 ownership 检查，不自动加 wildcard safe.directory。PATH、OS 信任库、SSH 用户配置及 SSH agent 仍属于用户/管理员信任边界。

## Windows junction

继续使用 Win32 API，不调用 cmd.exe。创建期间持有目标和全部父目录句柄，禁止 rename/delete 共享，按句柄检查 reparse 属性；拒绝通过已有 junction/symlink 父目录创建。UTF-16 路径和 Win32 extended path 支持中文、空格、合法 shell 特殊字符及长路径。失败时通过已打开目录句柄设置删除 disposition，不关闭后按名称删除可能被替换的路径。

创建目录到打开句柄之间仍有很小窗口；同权限恶意写入者不在该 API 的隔离边界。无法安全打开时不按路径盲删，可能遗留空目录，应明确报告而非误删竞争者资源。

## 行尾、摘要与 UTF-8

源锁独立可信摘要固定为 `22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7`。与 HEAD 字节相同仅是附加检查。签名、证书、二进制、镜像和归档显式 `-text`；文本/补丁遵循 LF 并执行原有摘要检查，禁止对未知摘要输入重算摘要放行。

报告使用 UTF-8 bytes，避免中文脚本经 PowerShell 本地代码页变成 `?`；子进程原始 stdout/stderr 以二进制保存，解码仅用于展示。`kernelforge.evidence` 提供不可覆盖的 JSON 发布与 SHA256 校验，临时文件同目录写入并 fsync 后原子发布。中断遗留的 pending 文件不能当作完整证据；恢复先核对已发布文件 SHA256。

## 环境复用

`python scripts/environment_preflight.py` 检查锁定依赖、实际 Python 长路径能力、Git 可用性和工作区所有权。Python 成功不代表 Git/归档器等外部工具支持长路径。Windows 长路径注册表开关不修改；为外部工具采用短临时路径和明确预算。PowerShell 策略不修改、不绕过；以 Python 入口执行任务。

仅显式指定既有 wheelhouse 时允许创建依赖锁摘要命名的隔离 venv，并用 `--no-index --require-hashes` 初始化；相同锁和解释器复用同一目录。依赖版本相同不等于已证明安装字节来源。工具链/ccache 缺失时保留阻塞，不自动下载未经审核的二进制。线程仍为 -j2，ccache 默认关闭。
