# Stage 4: KernelSU providers

## Verified upstreams — 2026-11-21

The user confirmed that “BaksSU” means [Baka-SU/BakaSU](https://github.com/Baka-SU/BakaSU). Provider `bakasu` and alias `bakssu` select that project. Its [official site](https://bakasu.org/) identifies it as a KernelSU downstream through SukiSU Ultra. This is documented lineage, not a complete Git ancestry analysis.

| Provider | Reviewed revision | Integration | Status |
| --- | --- | --- | --- |
| official | [v0.9.5](https://github.com/tiann/KernelSU/tree/v0.9.5), `b766b98513b5a7eb33bc1c4a76b5702bf1288f07` | Legacy kernel/Makefile, OVERLAY_FS and kprobe prerequisites | IMPLEMENTED; fixture TESTED; compile/boot UNTESTED |
| bakasu / bakssu | [main Commit](https://github.com/Baka-SU/BakaSU/tree/7b65bde0710b5e7c6f755545cb15a4abd417f3a8) `7b65bde0710b5e7c6f755545cb15a4abd417f3a8` | Shared engine, kernel/Kbuild and tracepoint hook selection, preserved Git metadata | IMPLEMENTED; fixture TESTED; compile/boot UNTESTED |
| derived | User-reviewed repository, Commit and setup SHA256 | Shared legacy layout with review evidence | IMPLEMENTED; fixture TESTED; real providers UNTESTED |
| official current | [observed main](https://github.com/tiann/KernelSU/tree/2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4) | KPROBES && EXT4_FS Kconfig, module-oriented Makefile | NOT_IMPLEMENTED; rejected by legacy adapter |
| KernelSU-Next | [repository](https://github.com/KernelSU-Next/KernelSU-Next), default dev | README credits KernelSU as original base; broader compatibility is an upstream claim | UNTESTED; no selectable adapter |
| ReSukiSU | Insufficient investigation | No automatic substitution | NOT_IMPLEMENTED |

Official/BakaSU default branches are main. Their observed latest commits were dated 2026-11-21 / 2026-11-16. Latest Release API requests were rate-limited; no current latest stable release is claimed. The v0.9.5 profile explicitly selects a legacy stable release. The [official archived non-GKI guide](https://kernelsu.org/guide/how-to-integrate-for-non-gki.html) identifies it as the last officially supported non-GKI version. The five allowed kernel families represent preflight scope, not tested compatibility.

## Shared lifecycle and configuration

Source checkout → KernelSU preflight → pinned provider checkout → source layout verification → preserve full provider Git history → link driver → edit driver Makefile/Kconfig → postcheck → toolchain/build adapter → report.

The existing source checkout, workspace lock, toolchain manager and report writer are reused. No setup script is executed. The adapter implements the reviewed setup.sh link/Kconfig/Makefile changes, with strict failure handling instead of fallback to another branch. Linux uses a symlink; Windows uses a junction. Upstream build files may themselves invoke external commands during real compilation; they are not fully audited here.

KernelSU is off when the optional build-config `kernelsu` object is absent or has `enabled: false`. Copy one object from `configs/kernelsu/official-legacy.json` or `configs/kernelsu/bakasu.json` into your build config. The CLI validates it against the existing build schema. Global feature scaffolding does not automatically activate integration. Only one provider is allowed.

Commit, Tag, stable Tag or Branch selection requires `expected_commit`. Named refs are resolved and checked before checkout. `kernel_directory` defaults to `.` and can be `common`; `config_file` is relative to it. The adapter parses the actual kernel Makefile version and checks the requested ARM64 configuration. It does not run Kconfig or prove the final build retains the settings.

BakaSU currently requires GKI tracepoint hooks, KALLSYMS=y, KALLSYMS_ALL=y, TRACEPOINTS=y and KSU_TRACEPOINT_HOOK=y. Manual and SUSFS hooks are rejected. Vendor/manual hooks need separate source validation and are NOT_IMPLEMENTED. Other disabled upstream features are not enabled by the framework.

Derived providers require traceable `review.upstream_evidence` and `review.setup_sha256`. The hash pins the reviewed recipe; declarations do not prove upstream lineage, kernel compatibility or safety. Different source layouts need reviewed adapter changes rather than repository URL substitution.

Per-source transaction locks cover mutation and rollback. Existing root sources/integration and repeated execution fail without overwrite. On failure, driver files are restored and only owned provider/link paths are removed. Reports record provider/project/repository/upstream, ref/type/Commit, method, preflight checks, UNTESTED items, failure reason and kernelsu.log.

## Validation scope

18 new local Git fixture tests cover official/shared flow, BakaSU Kbuild/hook requirements, derived layout, Commit/Tag/Branch, bad source/ref, incompatible version, missing configs, hash failure, rollback, repetition, path safety, isolation, schema and failed build reports. Core source checkout/link/edit paths run for real; upstream identities are substituted only in explicit fixture tests. No Android kernel is downloaded or compiled by the tests.

Real official/BakaSU compilation, boot, ABI, hooks and full Kconfig resolution remain UNTESTED. SUSFS, networking, ZRAM and device-specific integrations remain outside Stage 4.
