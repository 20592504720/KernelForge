# KernelForge Stage 5 handoff — in progress

Resume under the [all-stage execution policy](EXECUTION_POLICY.md), including
the minimum 10-minute routine CI check interval and disk-failure classification.

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

## 2026-11-22 post-run evidence and Node 24 maintenance

The previous handoff Commit is local `190626985e7bcdeeb14f1602b4f1359273bce648`,
remote `417dbbad37022ee89042d6b6d2fe079042a92443`, with equal Tree
`0a38f3d999e4b2bafbc190d60fbf64ddf5d91bbb`. This section is a later
documentation/workflow change; verify its own Commit and Tree on resume.

- Current-code [GKI run 44971781385](https://github.com/20592504720/KernelForge/actions/runs/44971781385)
  completed **success, 8/8 jobs**. The four `latest_branch` jobs completed
  integration/Kconfig/object/link checks; the four pinned jobs completed real
  ARM64 Image builds. The final official/pinned/SUSFS-off job includes the
  modular ZRAM object check. Inspect its archived machine report for exact
  object and image hashes before quoting them; do not infer boot or Root.
- Current-code [four-platform run 44971781400](https://github.com/20592504720/KernelForge/actions/runs/44971781400)
  ended success after one targeted Windows/Python 3.12 job retry. Initial
  WinError 2/KeyboardInterrupt failure remains recorded above.
- [SM8750 run 44970091559](https://github.com/20592504720/KernelForge/actions/runs/44970091559)
  and [current-code run 44971781359](https://github.com/20592504720/KernelForge/actions/runs/44971781359)
  both ended **failure** in locked-sync; their manifest jobs succeeded. The
  user supplied runner diagnostic `_diag/Worker_20261122-013037-utc.log` with
  `System.IO.IOException: No space left on device`. Classify the sync gate as
  **BLOCKED: RUNNER_DISK_EXHAUSTED**. GitHub's archived locked-sync job logs
  returned 404/BlobNotFound and no locked-sync artifact was present, so the
  first growth directory and exact failing sync step remain UNKNOWN. Do not
  retry identical runner conditions. OnePlus full build, modules, ABI,
  firmware pairing, DTBO and boot remain UNTESTED.
- All used checkout/setup-python/upload-artifact Action references were
  updated to verified upstream Node 24 release SHAs. The SM8750 workflow
  now records block/inode capacity and has a provisional 35 GiB free-space
  preflight. This workflow revision has static checks only at handoff; its
  actual GitHub runtime is **UNTESTED**. Run only a lightweight validation
  on the new Tree when available, and separately design a measured disk
  mitigation before any new 35-project sync.

Do not accept Stage 5 or enter Stage 6 from the eight GKI successes alone.
Read `docs/EXECUTION_POLICY.md` before the next long run.

## Third-round continuation

See `docs/STAGE5_THIRD_ROUND.md` and the later sections of
`docs/STAGE5_REPORT.md` for current evidence. The earlier statement that no
official Ace 6 6.6.118 source was found has been corrected: the official
Manifest contains `oneplus_ace_6.xml` and an independent source lock was
created. The current-Tree real GKI matrix and Linux OnePlus 13 locked sync
must be judged by their actual GitHub run reports, not by this older handoff.

## Emergency third-round handoff, 2026-11-22 (Stage 5 remains open)

At this handoff the working tree was clean on `stage1/initial-foundation`.
Local Commit `ac921b5ec004fe15348f6c02b2e5779fbf91d16f` and remote
Commit `78aec63fcdd5d9f74857b47c51d3d4b473a31c85` had the same Tree
`938b1a8371b87c8937d9f7aac451cf23749d2958`. The Commit SHAs differ
because local and connector-maintained remote histories have different parents.
This documentation-only handoff will create a later Commit; inspect its final
SHA and Tree before resuming. PR #1 was open and unmerged; `main` remained
`77af49c47acbfd384a4e22993797eebfa8d9eee6`.

**IMPLEMENTED; fixture TESTED:** the real-source GKI job now runs a locked,
build-local Patch Manager apply/repeat/rollback probe on official/pinned/SUSFS
off. The preceding-code [GKI run 44970091372](https://github.com/20592504720/KernelForge/actions/runs/44970091372)
finished 8/8; its official/off job produced a nonempty Image and vmlinux,
reported `APPLIED`, `ALREADY_APPLIED`, rollback `TESTED`, and a clean source.
The independently downloaded Image matched SHA256
`d4be9d084676242be5698bb984f6fb28af157ecba871950c2a3625fce0113a2c`.
That run preceded the final ZRAM object-check change and is not the final Tree's
complete acceptance result. Local focused tests passed 12/12 before that
change and 9/9 after it; Python compile and configuration validation passed.

**TESTED for current Tree:** [four-platform CI 44971781400](https://github.com/20592504720/KernelForge/actions/runs/44971781400)
has a successful Ubuntu/Windows × Python 3.11/3.12 result (155 tests on each
completed suite). The initial Windows/Python 3.12 attempt failed with WinError
2 during temporary cache path resolution followed by `KeyboardInterrupt`;
the single failed job was retried once and passed. Keep the first failure in
the record. Current-Tree [GKI run 44971781385](https://github.com/20592504720/KernelForge/actions/runs/44971781385)
had 4/4 `latest_branch` jobs successful at last inspection. Official/BakaSU ×
SUSFS off/on resolved the same locked commits as the pinned baseline on this
occasion; no version drift occurred. Three of four pinned Image jobs had
completed successfully; official/pinned/SUSFS-off, which additionally compiles
the modular ZRAM object, was **IN_PROGRESS**. Do not infer its outcome.

**IN_PROGRESS:** [SM8750 source audit 44971781359](https://github.com/20592504720/KernelForge/actions/runs/44971781359)
on remote Commit `78aec63fcdd5d9f74857b47c51d3d4b473a31c85` had the
manifest job successful and the locked 35-project Linux `repo sync` still
running. [Earlier sync 44970091559](https://github.com/20592504720/KernelForge/actions/runs/44970091559)
on Commit `e357a089ec7c3d986ec1c6bd6f0a4901e53bfe97` was also running.
Neither sync nor any OnePlus 13 full Bazel build, module ABI, firmware match,
DTBO, boot or Root test has passed. Both jobs were left running; do not cancel
or relaunch them merely for this handoff.

**IMPLEMENTED; source mapping TESTED:** separate OnePlus 13/PJZ110 and Ace 6/
PLQ110 official 6.6.118 profiles and 35-project source locks exist in
`manifests/`. The Ace 6 official `oneplus_ace_6.xml` finding corrects the
earlier community-only conclusion. CodeLinaro commit reachability and complete
sync remain UNTESTED until the Linux jobs finish. BBG is **BLOCKED** by missing
`blk.h` and `objsec.h` at the audited upstream Commit. Unicode patch textual
applicability passed on two exact source files, while semantic and compile
validation remain UNTESTED; integration is NOT_IMPLEMENTED. Fengchi candidate
Commit and SHA256 were rechecked; automatic integration remains Stage 6 work.

**Resume in order:** inspect the final attempt of GKI run 44971781385,
especially official/pinned/off `zcomp.o`, `capabilities.json`, Image and
vmlinux hashes; inspect both SM8750 sync reports and exact errors; reconcile
CI with the code Tree above; update PR #1 once with final Stage 5 evidence.
If sync succeeds, audit the official `sun` Bazel target and attempt a separate
Linux build with the locked source. If it fails, record the specific missing
repo, disk, network or tool error. Do not claim Stage 5 acceptance, flashable
PJZ110 output, ABI, boot or Root until evidence exists. Keep E-drive sources,
cache, toolchains, builds, artifacts, logs, reports and backups; C-drive
originals remain untouched. Do not enter Stage 6 without a new instruction.


## Post-handoff CI capacity and Node 24 smoke plan (2026-11-22)

- This was the pre-pilot capacity assumption. The later measured hosted
  Runner had 92,656,624 KiB free before a safe cleanup and 99,241,204 KiB
  after; the blanket 14 GB claim must not govern the next attempt. The
  previous `SM8750_LARGE_RUNNER` gate skipped source sync, **not TESTED**.
  Recheck actual capacity on every fresh Runner and keep paid resources
  subject to a separate decision.
- The lightweight Validate workflow now uploads one small Node 24 smoke
  artifact on Ubuntu/Python 3.12, exercising the pinned checkout,
  setup-python and upload-artifact Actions together. Check the new run
  and its artifact before marking these upgraded Actions TESTED.
- Historical GKI 8/8 evidence remains valid for its recorded code and
  workflow inputs. No new GKI or full SM8750 builds are required merely
  because of this workflow-only revision.
- The local E-drive checkout is not updated by a GitHub connector
  commit. At next Codex resume, compare remote HEAD/Tree with local
  history and reconcile safely; do not reset local work or force push.

## Free hosted-runner disk pilot (2026-11-22; original plan)

The user prefers free, dependency-safe Runner cleanup over an immediate
switch to local E:/F: storage. A one-run disk experiment was added in
`.github/workflows/runner-disk-pilot.yml`; it is scoped to the
`stage1/initial-foundation` push of that workflow or manual dispatch.
It removes only the optional preinstalled .NET and GHC directories on an
isolated GitHub-hosted Ubuntu 24.04 Runner, records actual free-space and
inode gain, checks essential build tools and uploads one small report.
The real SM8750 locked-sync remains gated on an explicitly authorized
large Runner; the pilot does not sync kernel source. At resume, read the
pilot's existing Run ID/results rather than relaunching it and decide
whether and how the verified safe cleanup can be reused inside the
actual sync job. Actual full-source and build safety is still UNTESTED.
Do not touch E: or F: drives or clean SDK/NDK, Java, Python/Node,
Clang/GCC, Bazel or toolcache to obtain a green check.

## Controlled OnePlus 13 sync continuation (2026-11-22)

The prior remote branch head was `7b6fe3129effd6c0c883e67adb9c46d3e194c387`
with Tree `6d153fe52f9d2ee7527f529dab8c453b03f37d07`. Its two changes
were safely cherry-picked onto the divergent but Tree-equal local branch;
no reset or force push occurred. The completed [disk pilot 44988567235](https://github.com/20592504720/KernelForge/actions/runs/44988567235)
removed only `/usr/share/dotnet`, skipped absent `/opt/ghc`, recovered
6,584,580 KiB, and passed its direct tool checks. The completed
[four-platform validation 44988571659](https://github.com/20592504720/KernelForge/actions/runs/44988571659)
passed 4/4; [GKI 44988571592](https://github.com/20592504720/KernelForge/actions/runs/44988571592)
passed 8/8; [SM8750 audit 44988571636](https://github.com/20592504720/KernelForge/actions/runs/44988571636)
passed manifest audit while locked sync was skipped by the old large-runner
gate. These are prior-Tree evidence, not proof of the new sync monitor.

The new workflow confines the verified .NET cleanup to its locked-sync job,
then checks current free blocks/inodes and applies a provisional 35 GiB
preflight. `verify_sm8750_sync.py` records 30-second resource samples,
minimum free bytes/inodes, repo stage, partial project HEADs and failure
reason; it reserves a provisional 10 GiB and stops the sync process group
if that reserve is crossed. Ordinary PRs and schedules remain manifest-only.
A single named development-branch push (`[run-sm8750-once]`) or explicit
manual `full_sync` input can authorize the complete sync. This is not a
commit-reachability or complete-source result until the actual Run and its
35/35 HEAD report are inspected. No device build, firmware ABI, boot or Root
claim follows from a successful sync.

The one-time trigger commit temporarily skipped the already validated GKI
matrix for this same-repository development PR; it changed no GKI build step.
The prior PR gate was restored immediately after registering the sync Run,
using a `[skip ci]` follow-up commit.

### One-time Run registry

- [SM8750 source audit Run 44991299785](https://github.com/20592504720/KernelForge/actions/runs/44991299785),
  push event at **2026-11-22 05:53 UTC** (13:53 China time), source Commit
  `0a14ade2b68f1376606a312f745a5ed86004019f`, Tree
  `e7dbd8cad22eb7765d758c0bae91705d24850529`.
- Target: OnePlus 13 PJZ110 official 6.6.118, 35-project lock
  `manifests/oneplus13-pjz110-sm8750-source.lock.json`, Manifest Commit
  `f8e50677874c65b6da41057d2f39be7b4ef3c08a`; configured hosted
  `ubuntu-24.04`, 35 GiB provisional admission floor, 10 GiB monitored
  reserve, 30-second in-job resource sampling. The Manifest audit produced
  its small Artifact; locked sync was **IN_PROGRESS** at registration.
- Initial free capacity, reclaimed bytes, minimum during sync, 35/35 HEAD
  count, CodeLinaro reachability, Bazel entry and final outcome are **UNKNOWN**
  until this Run's log and JSON Artifact are inspected. Do not start a second
  attempt. Routine status inspection of this Run is next eligible after
  **2026-11-22 06:03 UTC** (14:03 China time); batch it with other runs.

At the permitted **06:03 UTC** check, Manifest job `137112719805` had
completed successfully; locked-sync job `137112720089` was still
**IN_PROGRESS**. No final sync report or minimum-space measurement was
available yet. The next routine status check is **no earlier than 06:13 UTC**
(14:13 China time). If the job completes or fails unexpectedly, an immediate
completion/failure check is allowed under the execution policy. Keep this
same Run; do not launch another sync.

### Windows CI failure on the trigger Tree

[Validate Run 44991303165](https://github.com/20592504720/KernelForge/actions/runs/44991303165),
Windows/Python 3.11 job `137112730067`, failed in
`test_custom_source_adapter_can_resolve_archive_and_layout`: the long
toolchain staging path produced `WinError 3` during archive extraction,
followed by `KeyboardInterrupt` and exit `-1073741510`. This is a real
failure, not a passing four-platform result. The follow-up local fix shortens
the transient stage, backup and metadata names while retaining the full
identity in the cache lock/metadata. A long-root regression and interrupted
backup recovery test passed locally (9 targeted checks). A full local Windows
run reported 162 unittest assertions OK but its wrapper exited 1. That
wrapper also checks for residual worker threads, and the final diagnostic
line was not retained; it is **not** counted as a passing full run. GitHub
CI for the follow-up fix is **UNTESTED**; do not rerun the 35-project sync
to test this independent Windows change.

## 2026-11-22: SM8750 locked sync diagnosis and local continuation

- [Run 44991299785](https://github.com/20592504720/KernelForge/actions/runs/44991299785),
  Commit `0a14ade2b68f1376606a312f745a5ed86004019f`, is now **FAILED**.
  Its `sm8750-locked-sync` Artifact `14742927455` was downloaded and its ZIP
  SHA256 matched `b28f33c4dc85df34c8d2c783d630d888b61244d0775135374aad62aca51fc3d1`.
  The report records Manifest HEAD exactly `f8e50677874c65b6da41057d2f39be7b4ef3c08a`,
  31/35 project HEADs matched, and `repo sync` timed out after 2700 seconds.
  Free space fell from 101,619,314,688 to 15,283,589,120 bytes (86,335,725,568
  bytes consumed); the 10 GiB safety reserve was not crossed. These are
  runner measurements, not persistent local disk usage.
- The official pinned `oneplus_13_b.xml` declares the OnePlus modules and
  device tree project at `path="./"`. The old inspector falsely reported
  `UNSAFE_PATH`. The inspector now accepts only that exact project identity,
  checks its Git top-level, origin and locked HEAD, while still rejecting
  traversal and paths outside the worktree.
- `kernel_platform/prebuilts/rust`, `kernel_platform/tools/mkbootimg`, and
  `kernel_platform/prebuilts/tradefed` returned Git exit 128 after the timeout.
  The saved Artifact lacks per-path directory and `.repo` object details, and
  the hosted runner's filesystem has expired. Their precise states are
  **UNTESTED**: one cannot conclude network failure, missing download or Git
  corruption from exit 128 alone. The new inspector records directory, `.git`,
  Repo project metadata, target-object presence and a distinct diagnosis on
  the next persistent run. Repo 2.36 printed an update notice for 2.71, not a
  compatibility error; its causal role is **UNTESTED**.
- This Windows host has WSL available as a command but `wsl -l -q` exits 1
  with no installed distribution. E: has 340.19 GiB free, F: 281.30 GiB;
  the host has 8 logical CPUs and about 7.88 GiB RAM. No WSL installation,
  ext4 VHD, local 35-project sync or migration has been performed. The
  persistent source workspace is **BLOCKED** until a Linux distribution is
  installed/imported on E: or F: with an ext4 VHD. Keep the existing
  `E:\内核构建\project`, caches, sources and all backups intact.
- After a distro exists, place the VHD on E: if its free space still exceeds
  120 GiB; use an ext4 path such as
  `~/kernelforge/sources/oneplus13-pjz110-sm8750`. Keep `.repo` and run the
  verifier with `--resume`, `--reserve-gib 20` and a locally suitable
  `--sync-timeout-seconds`. The verifier uses `--no-manifest-update` so a
  resume cannot silently advance the Manifest during sync. First validate the exact Manifest Commit and
  three incomplete projects. Do not copy the vanished hosted-runner worktree
  or start another GitHub-hosted 45-minute sync as a substitute.
- Repo's current generated `.repo/manifest.xml` include and older symlink
  form are both accepted after verifying the selected file against the pinned
  Manifest checkout. Repo-owned `.git` links within the workspace are allowed;
  links escaping the workspace remain rejected. This behavior has fixture
  tests but is **UNTESTED** on the unavailable 35-project ext4 checkout.
## 2026-11-22: independent audit of 8 real-source artifacts (Run 44997133564)

On the development-branch commit \`da45033adb9e1976caf9419d08002af91b6a225c\`, the CI state was confirmed
without triggering new runs:
- [four-platform regression 44997133507](https://github.com/20592504720/KernelForge/actions/runs/44997133507):
  **TESTED 4/4**, Ubuntu and Windows on Python 3.11/3.12.
- [SM8750 audit 44997133509](https://github.com/20592504720/KernelForge/actions/runs/44997133509):
  Manifest job **TESTED**, 35-project \`locked-sync\` **SKIPPED/UNTESTED**.
- [real-source matrix 44997133564](https://github.com/20592504720/KernelForge/actions/runs/44997133564):
  **8/8 jobs successful**. All eight downloadable Artifact ZIPs were opened and
  their \`real-source-report.json\` records inspected, including independently
  hashing each packaged \`Image\` against its report's size and SHA256.

| Provider | SUSFS | Policy | Image bytes | Verified Image SHA256 | Full vmlinux |
| --- | --- | --- | ---: | --- | --- |
| official | off | pinned | 36,223,488 | \`2c8dabac80719c9046c09b3f923655859684f631bc574e5b2e7ba86c5bfbd637\` | TESTED |
| official | on | pinned | 36,293,120 | \`bc451c27ab5faf48bf9de11b42e2ab6d39999ee85fed4db86d3578d2845bfa3a\` | TESTED |
| BakaSU | off | pinned | 36,289,024 | \`87b625567a4311276634dbc4d63a6f39aea8ecce6a57b27e12b07d7dc9902572\` | TESTED |
| BakaSU | on | pinned | 36,293,120 | \`4ab7ccd62a6ce4a4262c5157c542cedbf6266719a22223cc51a508be3090c19d\` | TESTED |

All four \`latest_branch\` artifacts have \`status=success\`, \`object_compilation=TESTED\`,
and \`acceptance.relocatable_link=TESTED\`, but **contain no Image** by design;
\`kernel_compile=UNTESTED\` and \`acceptance.full_vmlinux=UNTESTED\`.
All eight report \`boot=UNTESTED\` and \`root=UNTESTED\`.
The verified Images are **generic GKI validation output**, not official OnePlus 13
SM8750 vendor-source Images, firmware/ABI validation, or device boot evidence.
The Stage 5 35/35 locked SM8750 sync remains **UNTESTED/BLOCKED**.
This audit added evidence only; no new CI, sync, build, or Windows E:/F: disk
operation was performed.


## Cloud-first preparation while the persistent 35-project sync runs (2026-11-22)

The requested five independent preparatory tasks—module compatibility review, Git/archive dual-source design, GitHub Releases toolchain mirror design, GitHub Actions caching/resource plan, and Stage 6–9 acceptance contracts—are captured in [STAGE5_CLOUD_READINESS.md](STAGE5_CLOUD_READINESS.md) and referenced in [ROADMAP.md](ROADMAP.md). They are **DESIGN_REVIEWED / STATIC_AUDIT_ONLY**; no new source provider, Release mirror, full OKI build workflow or stage-acceptance implementation exists from this documentation change. The previous numbered Stage 6 features / Stage 7 devices-and-delivery commitments are explicitly remapped, not waived.

Key blocker: patch_manager.apply_series() requires true Git top-level and locked HEAD; a TAR-only kernel cannot be substituted without a reviewed equivalent. build.py currently obtains a single source checkout, not a complete official multi-project OKI workspace. ToolchainManager already has SHA256/cache/source-adapter contracts that mirror support must reuse. The existing Windows-backed ext4 sync and its report/log remain unchanged. Read the actual final JSON before calling 35/35 TESTED or doing volume analysis. Preserve the existing branch, PR #1, main, locks, caches, WSL directories and user backups.

## Persistent OnePlus 13 source sync result (2026-11-22)

**TESTED for source checkout only:** Ubuntu 24.04 WSL2 ext4 workspace
`/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750` is backed by
`E:\内核构建\wsl\Ubuntu-24.04\ext4.vhdx`. The first `repo sync -c -j2`
attempt stopped with a CodeLinaro Rust fetch error, `curl 56 GnuTLS recv
error (-9): Error decoding the received TLS packet`. Its JSON recorded
34/35 at exit; the original `.repo`, objects and checkout were preserved.
An independent post-exit HEAD check then found 35/35 pinned commits. A
same-workspace `--resume` with `--no-manifest-update` exited zero and its
final JSON records `source_sync=TESTED`, `matched_projects=35`, no unmatched
projects, and Manifest HEAD
`f8e50677874c65b6da41057d2f39be7b4ef3c08a`.

Evidence is retained inside WSL at
`/home/kernelforge/kernelforge/reports/oneplus13-pjz110-sm8750-sync.json`
and `.log` (failed first attempt), plus
`/home/kernelforge/kernelforge/reports/oneplus13-pjz110-sm8750-resume.json`
and `.log` (successful resume). Windows E: had 338.13 GiB free before the
first sync and 185.41 GiB after successful resume; the 50 GiB host reserve
was not crossed. The successful resume report retains ext4 and host samples.
No OnePlus 13 kernel compilation, module ABI, firmware match, flashability,
device boot, Root or runtime behavior was verified; these remain UNTESTED.


## Stage 5 evidence reconciliation following successful WSL source sync (2026-11-23)

The GitHub-side evidence review and local-only task split are now in [STAGE5_EVIDENCE_RECONCILIATION.md](STAGE5_EVIDENCE_RECONCILIATION.md) and [STAGE5_LOCAL_CODEX_HANDOFF.md](STAGE5_LOCAL_CODEX_HANDOFF.md). This later entry supersedes the earlier **in-progress** statements *only for source sync*: the prior local WSL `35/35`, `source_sync=TESTED` evidence remains recorded in the section above.

The newest inspected GKI job matrix, [Run 45020470109](https://github.com/20592504720/KernelForge/actions/runs/45020470109), was **7/8**, not 8/8. The sole failed configuration was `BakaSU + SUSFS + latest_branch` (job `137201998796`): the locked SUSFS patch `50_add_susfs_in_gki-android14-6.1.patch` failed against ACK 6.1 `fs/exec.c` and `fs/namespace.c`. Four pinned GKI jobs passed; the complete OnePlus 13 Vendor/OKI Image, modules, ABI, firmware, device boot and Root runtime remain UNTESTED. This failure must not be conflated with the successfully resumed OnePlus 13 35-project source sync. The subsequent local WSL inspection is recorded below. Stage 5 as a whole is IN_PROGRESS.

## 2026-11-23: local WSL evidence and capacity audit

**TESTED, limited to source sync and read-only inventory.** The original successful resume JSON and log were parsed and hashed without modification. The original first-attempt JSON recorded 34/35 and exit 1 after a CodeLinaro Rust fetch `curl 56 GnuTLS recv error (-9)`; the retained ext4 workspace then resumed with `--no-manifest-update`, exited zero and recorded `source_sync=TESTED`, 35/35 locked project HEADs, and Manifest `f8e50677874c65b6da41057d2f39be7b4ef3c08a`. Lock SHA256: `22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7`. Successful JSON/log SHA256: `6ff051451fd141adc0586f026934be3142f978dd2934e89709eddafe1053aed3` / `55ba9ded814d79f1590a9c27b5c92815a5a0b7bd18b2cefa353c993928c48eed`. Failed JSON/log SHA256: `83ebd94074c7e40f6ad205faf844bf76ce5ef01bf2e8ab3d81b365d0268c22e0` / `0507571c73b775ed0e3af9e7730dc5c14962da25be8ab60691fe7832c7e73052`.

The existing ext4 source workspace contains 152,422,501,795 apparent bytes of `.repo` data and 10,603,950,454 apparent bytes of checked-out files, totaling 163,026,452,249 B (151.83 GiB). The root `path="./"` project's exclusive checkout estimate is 549,537,974 B after subtracting the 34 nonoverlapping nested paths; it is not added again to the total. At measurement Windows E: had 198,991,945,728 B (185.33 GiB) free, above the 50 GiB reserve; ext4 reported 860,784,242,688 B virtual free and 66,822,088 free inodes. The E-backed VHD file's logical length was about 165.95 GB, not a measured NTFS physical allocation.

The locked checkout includes Android Clang 18.0.0 (`r510928`), Rust 1.73.0-dev, Bazel 7.1.1, GNU Make 4.3 and Android OpenJDK 11.0.15. `msm-kernel/sun.bzl`, `msm_platforms.bzl`, `BUILD.bazel` and `msm_kernel_la.bzl` define the source-derived `sun_perf` / `sun_consolidate` dist variants; their labels and complete dependencies have not been verified by Bazel query or build. The GCC host prebuilt lacks an observed GCC executable; system `gcc` and `make` were absent from WSL `PATH`, while a locked prebuilt Make is present. The full per-project size/Commit table, input paths, evidence hashes and remaining gates are in local-only `E:\内核构建\reports\stage5-oneplus13-local-resource.json` and `.md`.

**UNTESTED:** OnePlus 13 compilation, module ABI/KMI, firmware matching, Image/DTB/DTBO, boot and Root/SUSFS runtime. The separate ACK 6.1 GKI 7/8 failure remains unresolved. Stage 5 overall remains **IN_PROGRESS**. No sync, download, build, large CI, source-lock edit or cleanup occurred during this audit.
