# Stage 5 continuation evidence and remaining gates

## Implemented and tested locally

- Generic patch series: deterministic dependency order, conflict/duplicate
  checks, exact kernel Commit, SHA256, text application, reverse check and
  rollback of existing files. A build-scoped lock now resolves moving upstream
  policies once and records immutable source Commit and patch bytes. This was
  exercised on small real Git repositories, not on a production device tree.
- SUSFS retains its exact GKI compatibility adapter and BakaSU Hook checks;
  provider and kernel patch operations now share the generic transaction
  boundary. Earlier real GKI acceptance remains historical evidence for the
  locked 6.1 baseline only. New Stage 5 generic patch combinations have not
  passed an Image build.
- TCP and ZRAM inspection reads source, Kconfig and final `.config` separately.
  BBRv2/BBRv3 are never inferred from BBR. `CONFIG_ZRAM_DEF_COMP_LZORLE`
  is recognized. Object compile and runtime availability remain UNTESTED.
- Separate PJZ110 official and PLQ110 community reference Profiles are schema
  checked. Both reject all optional patches until individually reviewed and
  refuse a flashable claim without boot and ABI evidence.

## Source audit, 2026-11-21

The [OnePlusOSS manifest](https://github.com/OnePlusOSS/kernel_manifest/blob/oneplus/sm8750/oneplus_13_b.xml)
at `f8e50677874c65b6da41057d2f39be7b4ef3c08a` maps the three official
SM8750 projects to `oneplus/sm8750_b_16.0.0_oneplus_13`. At inspection their
branch tips were common `e1b346b6b4f4096eb342ae3684838a942fd6f6c4`,
msm-kernel `6028f47faddaa27700f8dd3a1d83906ea8f27170`, modules/devicetree
`d50b305f7da9e14715a25120a4ac7b1a4b8b97c3`. These are observations,
not a firmware-matched lock. The common [Makefile](https://github.com/OnePlusOSS/android_kernel_common_oneplus_sm8750/blob/oneplus/sm8750_b_16.0.0_oneplus_13/Makefile)
reports Linux 6.6.118. The manifest includes many CodeLinaro projects and
toolchain/build dependencies; a three-repository checkout alone is incomplete.
The official modules/devicetree repository at its observed Commit contains
`kernel_platform/qcom/opensource/devicetree`, `vendor/qcom/opensource`,
`vendor/qcom/proprietary` and `vendor/oplus/kernel` trees. This verifies
publication of those directories, not that every firmware-specific DTS,
module, signing key, generated artifact or build dependency is present.
KMI, ABI, module signing, load order, DTBO, firmware build and boot layout are
UNTESTED. The local manifest parser checked the three project revisions and
paths and recorded its evidence outside Git in the E-drive reports directory.

The [Ace 6 community kernel](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750)
default branch was `lineage-23.2` at
`d19be24e86e114c06368e71400efe44f84187782`, while its
[modules repository](https://github.com/Ace6-Development/android_kernel_oneplus_sm8750-modules)
default branch was `lineage-24.0` at
`8264400af7af2d91dff3dede2f98f2cb8714f155`. The kernel Makefile
reports 6.6.142 on the inspected branch. The requested
`Ace6-Development/infinity_device_oneplus_ktm` returned 404; its current
location is UNKNOWN. The [community builder](https://github.com/GuLingguang/oneplus-sm8750-kernel-pro-build)
identifies Ace 6/ktm and Project Infinity X; this does not establish ColorOS
or PJZ110 compatibility. No community device tree, module or Image has been
reused for OnePlus 13. An Ace 6 **6.6.118** source/firmware pair was not
identified; the current default kernel branch is 6.6.142 and cannot be treated
as a drop-in reference for the official 6.6.118 target. Exact PLQ110
firmware/codename mapping remains UNTESTED.

## Third-party patch audit

- BBG: [vc-teahouse/Baseband-guard](https://github.com/vc-teahouse/Baseband-guard)
  is a real GPL-2.0 LSM project with Kconfig, Makefile, source and setup.sh.
  Its documentation requires `CONFIG_BBG` and `CONFIG_LSM` integration.
  We do not execute its remote setup script. No reviewed code port, exact
  kernel baseline, LSM interaction check or Image test exists: NOT_IMPLEMENTED.
- Unicode zero-width: [WildKernels candidate](https://github.com/WildKernels/kernel_patches/blob/main/common/unicode_bypass_fix_6.1-.patch)
  changes `fs/unicode/utf8-norm.c`. Separately, FuseFixer is described as a
  user-space/Xposed module by another project. The desired technical target,
  authoritative origin, security semantics and exact baseline are ambiguous;
  no patch is enabled: NOT_IMPLEMENTED.
- Fengchi: the user authorized evaluation of public unofficial candidates.
  [Numbersf/SCHED_PATCH](https://github.com/Numbersf/SCHED_PATCH) `sm8750`
  was at `26e3774a9794e9728a3cc6840f01527de5536eca` when inspected.
  `fengchi_oneplus_13_b.patch` was 585,700 bytes, SHA256
  `0f835fea08a94e69409e9b4ffafd97af54c70c9871b25b788cb2eb5dafbbcc97`.
  Its diff modifies scheduler and GPU code, removes sched_ext files and adds
  hmbird files. The repository README points to
  [cctv18's SM8750 kernel](https://github.com/cctv18/android_kernel_common_oneplus_sm8750)
  but describes its own patch as assembled from leaked code. No LICENSE file
  was found at that Commit; original provenance and redistribution terms are
  UNKNOWN. Patch target and OnePlus 13 6.6.118 compatibility were not tested.
  Automatic selection/download/application belongs to Stage 6; present state
  is audited candidate, NOT_IMPLEMENTED as an integration. Non-official status
  alone is not treated as a compatibility failure.

## Verification boundaries

Regression and source-audit workflows are separate. Ordinary PR validation
does not run full kernel builds. Scheduled real-source checks and manually
requested full Image checks run on Linux; their results must be inspected by
run/Commit. No Stage 5 SM8750 full Image, module ABI, device boot, Root or SUSFS
runtime acceptance has occurred. Profiles therefore cannot publish a
device-flashable artifact. E-drive migration was not repeated; prior files,
cache and C-drive originals remain in place.

Local checks on this continuation: `compileall`, JSON Schema/manifest CLI,
YAML parsing and `git diff --check` passed. The focused 43-test group with
E-drive temporary files passed. A 150-test Windows run had one environment
cleanup error (`WinError 32` deleting a transient Git fixture after its test);
it must not be reported as a passing full run. The earlier eight real GKI
jobs on the preceding patch-manager commit passed, but this continuation's
new code still needs its own CI result.

## Second continuation, 2026-11-22

**IMPLEMENTED; fixture TESTED:** generic text patches can now create and
delete regular files with transaction rollback. A test applies a create and
delete in a real Git repository, forces failure in a later patch, verifies
both paths and original bytes, then verifies successful and repeated application.
Executable creations, symlinks, renames, copies, binary patches and mode changes
remain rejected. The build checks Manifest/Lock/staged-byte consistency before
application. The focused patch, Stage 5 and SUSFS suite passed 29/29; Python
syntax, JSON Schema/Manifest validation and Git diff checks passed.
The [four-platform CI run for this code](https://github.com/20592504720/KernelForge/actions/runs/44961989086)
passed Ubuntu/Windows × Python 3.11/3.12 (4/4 jobs).

The official OnePlus 13 manifest/common refs and Fengchi candidate ref were
rechecked on 2026-11-22 and matched the pinned audit SHAs above. The local
Fengchi candidate patch SHA256 was recalculated and matched the audit record.
Official source directory publication still does not prove a complete,
firmware-matched repo sync or module ABI. Ace 6 6.6.118 remains unidentified.
BBG and Unicode are not enabled because exact-baseline patch/LSM/filesystem
behavior and compile evidence are absent. Fengchi automatic integration remains
Stage 6 work; no patch was redistributed or applied here.

**UNTESTED:** the present code Tree's Linux GKI integration and full Image build,
generic patch application on actual GKI, SM8750 full source sync/build, ABI,
device boot, Root and SUSFS runtime. These require separate CI/Linux/device
evidence and prevent declaring Stage 5 complete.

The local Windows host reports no installed WSL distribution (`wsl --list`);
there is no local Linux filesystem build environment. The GitHub connector
exposes workflow inspection but no workflow dispatch action, and the in-app
browser could not open the workflow page. A fresh real GKI run for this Tree
therefore remains BLOCKED in this session; the previous run must not be reused
as its acceptance result.

## Third continuation, 2026-11-22 (in progress)

The real-source workflow now has a same-repository PR trigger with read-only
permissions. A development-branch push trigger was used to establish that
GitHub would schedule the eight-job matrix, then removed to avoid duplicate
future runs. Each report must be matched to its actual Commit and Tree. The
real-source script now includes a build-owned GKI Patch Manager transaction
probe, records actual ARM64 object hashes for TCP/ZRAM, and requires both
nonempty `vmlinux` and `Image` for full-build success. Final-Tree CI evidence
is tracked in `docs/STAGE5_THIRD_ROUND.md` and the delivery report.

Official `oneplus_ace_6.xml` was found at the pinned OnePlusOSS Manifest
Commit. Its separate 6.6.118 common branch resolves to full Commit
`65b954a773b183a9999b06bb1b2f921f12eaaf11`; the old conclusion that
only a 6.6.142 community reference was identified is superseded. Both device
profiles now have independent 35-project source lock files. Reachability of
all CodeLinaro SHAs, complete sync/build, firmware and ABI are not thereby
verified. The Linux source-audit workflow attempts a locked sync and keeps
failure logs.

BBG upstream commit `028ff7fd509e2104596da7cc1ef8e6ce2a0c9082` references
`blk.h` and `objsec.h` that are absent at that exact commit: integration
BLOCKED before object compilation. The Unicode candidate patch at
`70c394f16d82b0f85a4f07617630d82dde6d203c` passes exact-file
`git apply --check` on locked ACK 6.1 and OnePlus 13 common 6.6.118, but
filesystem semantic and security behavior remain UNTESTED; integration is
NOT_IMPLEMENTED. Fengchi remains an audited Stage 6 candidate only.
