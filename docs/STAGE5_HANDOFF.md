# KernelForge Stage 5 handoff — in progress

Status captured 2026-11-21. Stage 5 is **not complete**. Continue only on
`stage1/initial-foundation`; do not modify `main`, force push or merge PR #1.

## Git and review state

- At handoff authoring, local Commit `86a3a02b71d350c92a2ca9a70243dd1b4be83c06`,
  parent `a1113bf744aadf2a30869f80979454b7ff50abe9`, Tree
  `b495ca59c2af9f0952f441c41a660d122d3036eb`, clean working tree.
- Remote development Commit `830430da7eab27beebad86cd83ea86947625a344`,
  parent `22ccbcedcd108f9142d1c0870cb735ad7dffa995`, same Tree
  `b495ca59c2af9f0952f441c41a660d122d3036eb`.
- Local and remote Commit SHA differ because their pre-existing parent histories
  differ; connector-created blobs and full Tree were verified against local Git.
- [PR #1](https://github.com/20592504720/KernelForge/pull/1) was open and
  unmerged after sync; head was the remote Commit above, base `main` at
  `77af49c47acbfd384a4e22993797eebfa8d9eee6`. Its description was updated
  once for this continuation. This handoff document will be a subsequent Commit;
  check its final SHA in the delivery message or Git history. No second PR exists.

## Implemented and evidence

- **IMPLEMENTED; fixture TESTED:** `kernelforge/patch_manager.py` orders patch
  dependencies, detects explicit conflicts and duplicate features, checks exact
  kernel Commit and patch SHA256, applies text patches with reverse verification,
  and restores existing files on a failed series. It now resolves moving patch
  upstreams once with the existing version resolver, checks out the locked
  Commit, stages immutable patch bytes and writes `patches.lock.json`. Local
  fixture tests covered real Git application, repeat detection, branch movement
  after locking, checksum failure and rollback of an owned new file. Generic
  new-file operations inside `git apply` remain unsupported; SUSFS payload
  copies use the shared transaction boundary.
- **IMPLEMENTED; historical real GKI TESTED:** exact-baseline SUSFS integration
  retained its Stage 4.6 compatibility selection, SHA checks and BakaSU
  duplicate-hook guard. The new shared transaction boundary passed focused
  regression tests. No new generic patch was compiled against a real kernel.
- **IMPLEMENTED; fixture TESTED:** TCP/ZRAM inspection separates source,
  Kconfig, final `.config`, object compilation and runtime evidence. BBRv2/v3
  are not inferred from BBR; LZO-RLE uses `ZRAM_DEF_COMP_LZORLE`. Real GKI
  capability output for this new Commit is still UNTESTED.
- **IMPLEMENTED; manifest mapping TESTED:** isolated `oneplus13-pjz110` and
  `oneplus-ace6-plq110` Profiles, schema validation, official manifest parsing
  and flashable-release refusal when boot/ABI are unverified. The E-drive
  `reports/stage5-sm8750-audit.json` records a live manifest lookup.
- **TESTED static checks:** Python compileall, JSON/Schema/patch validation,
  YAML parsing and Git diff checks passed. A focused 43-test group using E-drive
  temporary paths passed. A local 150-test Windows full run had one `WinError 32`
  transient Git fixture cleanup error and is **not** a passing run.
- **TESTED CI on this code Tree:** [four-platform regression run
  44921504727](https://github.com/20592504720/KernelForge/actions/runs/44921504727)
  completed successfully on Ubuntu/Windows × Python 3.11/3.12. The preceding
  [regression run 44918112662](https://github.com/20592504720/KernelForge/actions/runs/44918112662)
  also completed 4/4.
- **Historical real-source evidence only:** [GKI run
  44918112639](https://github.com/20592504720/KernelForge/actions/runs/44918112639)
  on preceding Commit `22ccbcedcd108f9142d1c0870cb735ad7dffa995`
  completed 8/8 official/BakaSU × SUSFS on/off × pinned/latest jobs. This does
  not validate the new Stage 5 generic patch lock, TCP/ZRAM inspection or
  SM8750 build. No new real GKI run was triggered after splitting lightweight
  PR CI from scheduled/manual large builds.

## SM8750 audit

- **OnePlus 13 / PJZ110:** official `kernel_manifest` branch `oneplus/sm8750`
  at `f8e50677874c65b6da41057d2f39be7b4ef3c08a` has
  `oneplus_13_b.xml`, mapping common, msm-kernel and modules/devicetree to
  `oneplus/sm8750_b_16.0.0_oneplus_13`. Common Makefile reports **6.6.118**.
  At inspection, branch tips were common `e1b346b6b4f4096eb342ae3684838a942fd6f6c4`,
  msm-kernel `6028f47faddaa27700f8dd3a1d83906ea8f27170`, and
  modules/devicetree `d50b305f7da9e14715a25120a4ac7b1a4b8b97c3`.
  The latter contains `kernel_platform/qcom/opensource/devicetree` and
  `vendor/qcom`, `vendor/oplus` directories. **UNTESTED:** complete repo sync,
  exact firmware pairing, toolchain/build, module signing/load order, ABI/KMI,
  DTBO, boot layout and device boot. Directory presence is not completeness.
- **Ace 6 / PLQ110 reference:** community kernel `lineage-23.2` at
  `d19be24e86e114c06368e71400efe44f84187782` reports 6.6.142;
  modules default `lineage-24.0` at
  `8264400af7af2d91dff3dede2f98f2cb8714f155`. No matching 6.6.118
  source/firmware pair was identified. Requested
  `Ace6-Development/infinity_device_oneplus_ktm` returned 404. **UNTESTED:**
  firmware, device tree, ABI/KMI and ColorOS compatibility. No Ace 6 device
  components or image were reused for PJZ110.

## Third-party candidates and remaining work

- **BBG — NOT_IMPLEMENTED:** `vc-teahouse/Baseband-guard` `main` observed at
  `028ff7fd509e2104596da7cc1ef8e6ce2a0c9082`; GPL-2.0 LSM with
  Kconfig/Makefile/setup.sh. Do not execute its remote script. Exact target
  port, LSM/SELinux interaction and compile acceptance remain absent.
- **Unicode zero-width — NOT_IMPLEMENTED:** candidate
  `WildKernels/kernel_patches` `main` at
  `70c394f16d82b0f85a4f07617630d82dde6d203c` has a patch for
  `fs/unicode/utf8-norm.c`; a separate FuseFixer user-space module is also
  advertised. The intended problem, authoritative source and exact target
  baseline remain unresolved.
- **Fengchi — audited candidate; integration NOT_IMPLEMENTED:** user permits
  public unofficial candidates. `Numbersf/SCHED_PATCH` `sm8750` at
  `26e3774a9794e9728a3cc6840f01527de5536eca` contains
  `fengchi_oneplus_13_b.patch` (585,700 bytes), SHA256
  `0f835fea08a94e69409e9b4ffafd97af54c70c9871b25b788cb2eb5dafbbcc97`.
  Its README cites `cctv18/android_kernel_common_oneplus_sm8750` and says
  the patch derives from leaked code. No LICENSE file was found at the
  candidate Commit. Scheduler/GPU/sched_ext changes are extensive. Stage 6
  automatic adapter needs verified provenance, license/permission terms,
  exact 6.6.118 applicability, Kconfig, compile and device behavior. It is
  not currently enabled; unofficial status alone is not the blocker.
- **UNTESTED:** real Stage 5 generic patch on a locked GKI source; SM8750
  Image/vmlinux, vendor modules, ABI, device boot, Root and SUSFS behavior.
  No release or device-flashable artifact was created.

## E-drive workspace to retain

`KERNELFORGE_HOME=E:\内核构建`; project `E:\内核构建\project`;
`sources`, `toolchains`, `cache`, `builds`, `artifacts`, `logs`, `reports`,
`temp`, `manifests`, `backups` are present. `sources/susfs-stage45` and
historical Stage 4.5 validation directories are retained. `cache` and
`toolchains` have no top-level entries at this inspection; preserve them and
the Stage 4.6 manifests, version locks and reports anyway. The C-drive
originals remain untouched. Do not move or clean this workspace on resume.

## Next Codex entry points, in order

1. Confirm branch/clean status and PR head, and compare local/remote Trees;
   do not assume their Commit SHA will match. Read this file and
   `docs/STAGE5_REPORT.md` before editing.
2. Inspect the completed 4-job CI run above; investigate local `WinError 32`
   only if it reproduces. Do not rerun full suites without a concrete risk.
3. Perform one manually selected real GKI run for the new Commit if authorized
   environment permits; inspect capability report and SUSFS compile evidence.
4. Complete a locked official OnePlus 13 repo-manifest sync/build audit on a
   Linux filesystem, including modules, DTBO, KMI/ABI and firmware pairing.
   Keep Ace 6 as an isolated reference and find an actual 6.6.118 pair before
   considering common-code ports.
5. For Stage 5, complete generic patch new-file transaction support if needed,
   real-source patch compatibility checks, network/ZRAM object compile evidence,
   and an exact-baseline BBG/Unicode decision. Record failures as such.
6. Keep Fengchi automatic adapter work for Stage 6. Before integration, audit
   source permission, exact patch SHA/Commit, target baseline and conflicts.

No Stage 5 completion claim is made here.
