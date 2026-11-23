# Stage 7.5-A — Antigravity single-model first handoff

**Executor / single model: Claude Opus 4.6.** Do not switch models mid-task.
This handoff is the first LOCAL task for Stage 7.5. It is a READ-ONLY
technical/build-admission audit, **not** authorization for an actual build.
See `docs/STAGE7_5_FAST_IMAGE_PLAN.md` for the acceptance contract.

## Mandatory context — do not reconstruct the project from scratch

Repository: https://github.com/20592504720/KernelForge
Development branch: `stage1/initial-foundation`
Pull request: https://github.com/20592504720/KernelForge/pull/1 (OPEN)
Protected main reference: `77af49c47acbfd384a4e22993797eebfa8d9eee6`
Stage 7.4 accepted remote HEAD *before Stage 7.5 began*:
`5ca19c5843e127c218cf9aaa79eefbf12682448e`, Tree
`3a32d3144eeee84a7d04b8bc34193ac79c37961a`.
The remote Stage 7.5 development branch will advance during handoff
implementation: ALWAYS fetch and inspect the **actual current** remote HEAD,
and reconcile it with local state. Local commits may have different ancestors
but equivalent Trees. No reset, force push or history rewrite.

Windows project: `E:\内核构建\project`.
WSL project: `/mnt/e/内核构建/project`.
Pinned ext4 source: `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`.
Device: official OnePlus 13, `PJZ110`, `SM8750`, Linux 6.6, arm64.
35-project lock file: `manifests/oneplus13-pjz110-sm8750-source.lock.json`;
previous reviewed SHA256:
`7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e`.
Selected Manifest `oneplus_13_b.xml` Commit
`f8e50677874c65b6da41057d2f39be7b4ef3c08a`.
Stage 7.4 SOURCE_ADMISSION = TESTED: WSL2 21/21, 35/35 HEAD,
worktrees clean, physical host disk reserve passed;
cloud Run https://github.com/20592504720/KernelForge/actions/runs/45272620184
4/4. **Still `build_eligible=false`.**
Historical local failure logs and corrected evidence both MUST remain available.
Do not repeat source download/sync and do not re-pin anything.

Already identified local tools:
`kernel_platform/tools/bazel` Kleaf wrapper, Android Clang18 r510928
at `kernel_platform/prebuilts/clang/host/linux-x86/clang-r510928/bin/clang`,
Clang SHA256 `dc739fc44bb889146bd47732912cad457200af7de7c2fb5a7509b7a9974d6d67`,
Bazel backing binary 7.1.1 (identity inventoried, runtime graph UNTESTED).
`ccache` previously absent on PATH: keep OFF.
WSL memory approximately 3.77 GiB RAM plus 1 GiB swap as previously sampled.
Physical E: disk and ext4 capacity must be re-sampled.
Kleaf candidates `sun_perf_dist` and `sun_consolidate_dist` are **UNVERIFIED
HYPOTHESES**; do not assume these strings are real target labels.

## Required tasks in order

**A. Safe Git context admission**
Read `README.md`, `docs/ROADMAP.md`, `docs/STAGE7_4_LOCAL_CODEX_AUDIT.md`,
`docs/evidence/stage7_4_local_source_admission.json`,
`docs/STAGE7_5_FAST_IMAGE_PLAN.md`,
`scripts/stage7_5_artifact_evidence.py`,
`docs/STAGE7_5_PINNED_OEM_STATIC_AUDIT.md`, and
`docs/STAGE8_SCOPED_ACCEPTANCE.md`. The pinned OEM static audit already
identifies candidate `sun_perf`/`sun_consolidate` macro labels and
actual DFR DDK source files, but **not** a verified runtime Bazel action graph.
Verify local/remote Git branch,
HEAD, Tree, status and source-lock hash. If a safe cherry-pick is needed,
record the exact commits and compare Trees; do not force-reset.
For this first audit, do not modify the actual 35-project source or caches.

**B. Read-only Kleaf exact target discovery**
Inspect *existing* pinned `BUILD`, `BUILD.bazel`, `.bzl`, `.bazelrc`,
`MODULE.bazel` and wrapper scripts in relevant `kernel_platform`
directories. Identify the exact official Bazel label(s) producing BOTH
`Image` and `vmlinux`, their target definitions, `outs`/`dist` paths,
minimum dependencies, effective defconfig and toolchain rules. Cite the
file paths and exact lines in your report; distinguish an actual target label
from a guessed name. Detect whether a fast Image-only target can avoid
building all vendor modules without mutating OEM targets or silently
dropping required dependencies.

**C. Read-only DFR dependency trace**
Find the recorded DFR external module/include reference in the locked
BUILD/.bzl files, track the enclosing rules, exact label, location and all
known in-tree references. Classify its reachability from the proposed fast
Image/vmlinux target as PROVEN_REQUIRED, PROVEN_NOT_REQUIRED or
UNDETERMINED. If static inspection cannot prove reachability, preserve
UNDETERMINED; provide a proposed bounded `bazel cquery` / `aquery`
command with flags, output/cache roots and no-fetch controls for a later
separately approved run. **Do not execute Bazel, even for queries, in this
first task** because it may generate cache/output or contact the network.

**D. Capacity and execution-envelope proposal**
Using passive OS queries, record current RAM, swap, CPU, WSL version,
physical Windows E: free bytes, ext4 free bytes and free inodes, and existing
Bazel/cache paths (without creating or clearing anything). Proposed future
parallelism, time/output budget and process-group safe termination must
preserve 50 GiB physical host reserve and 20 GiB ext4 reserve. Do not
pretend ext4 reported free bytes are real E: physical capacity.
Inspect the pre-existing compiler executable's SHA256 only as needed; do
not download compilers, install dependencies or run `repo sync`.

**E. Timestamp, ccache and security plan**
Document how future `KBUILD_BUILD_TIMESTAMP` and `SOURCE_DATE_EPOCH`
will be sampled immediately before the real compiler call, injected through
the *actual* Kleaf/Bazel sandbox, and independently demonstrated (not merely
inherited by the outer shell). Optional custom ISO 8601+timezone must remain
strict; default blank is actual UTC. ccache must remain disabled until
real binary, compiler interception and isolation can be demonstrated.
Do not modify Root/SUSFS, Kconfig security settings or make a flashable ZIP.

## Required deliverables

Save raw audit logs in `E:\内核构建\reports` without overwriting historical
files. Produce:

1. `docs/STAGE7_5_LOCAL_TARGET_AUDIT.md`: exact target/Bazel wrapper/DFR
   source references, verified vs uncertain labels, build envelope,
   timestamp and toolchain plan, risk register, and next gated commands.
2. `docs/evidence/stage7_5_local_target_audit.json`: machine-readable
   Commit/Tree, lock/manifest identity, sampled resources, target provenance,
   DFR classification, current blockers, raw-log paths and SHA256.
3. Final concise summary with `STAGE7_5_TARGET_DISCOVERY_TESTED` only if
   actual labels/dependency edges are statically evidenced, otherwise
   `STAGE7_5_TARGET_AND_DFR_BLOCKED`. A statically discovered label does
   not authorize compile. Include local/remote Git identity and whether
   repository worktree remains clean.

Update only these new evidence files if authorized by the repo's current
state. Never destroy or overwrite existing evidence. If a conflict or
unknown target arises, document it rather than guessing.

## Explicit STOP / forbidden operations in this handoff

Do not run: Bazel build, Bazel cquery/aquery, repo sync, any full/partial kernel
compile, kernel config update, patch application, source mutation, package
install, large download, cache prune, Git clean/reset/force push, Release,
flashing, main-branch changes, PR merge, or any paid GitHub runner.

This task ends with an independent report. Stage 7.5-B bounded graph query
and Stage 7.5-C actual Image/vmlinux compilation require separately issued
instructions following review. Stage 8 and Stage 9 are out of scope.
