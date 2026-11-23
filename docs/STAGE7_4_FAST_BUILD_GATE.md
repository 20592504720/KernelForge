# KernelForge Stage 7.4: manual fast-build admission

Status: PARTIAL_SOFTWARE_IMPLEMENTED, CLOUD_CI_PENDING, REAL_KERNEL_BUILD_NOT_IMPLEMENTED.
Development branch: stage1/initial-foundation. Keep PR #1 open; main unchanged.

## This stage's actual implementation

- scripts/stage7_4_fast_build_gate.py implements a fail-closed, offline OnePlus 13 PJZ110 policy gate, binding the user-reviewed SHA256 of the 35-project source-lock JSON to the fixed SM8750/arm64/6.6 device profile, immutable project commits, safe source paths and fixed manifest commit.
- Optional --source-workspace inspects an existing, untouched Repo source tree: selected Manifest and its HEAD, all 35 project HEADs, and tracked working-tree cleanliness. It does not run repo sync, create a source checkout or patch source. WSL2 requires --host-disk /mnt/e so the host physical 50 GiB reserve is checked, in addition to a 20 GiB ext4 reserve and inode checks.
- build_timestamp input inherits strict timezone-explicit parsing (blank = UTC at observation). The value in the Stage 7.4 report is a PREVIEW, not the actual build timestamp. Stage 7.5 must resolve it immediately before compilation and verify KBUILD_BUILD_TIMESTAMP and SOURCE_DATE_EPOCH inside the actual Kleaf/Bazel compiler environment.
- .github/workflows/stage7-4-fast-build.yml has only workflow_dispatch, contents:read, branch guard, 12-minute limit, bounded 7-day admission-report upload; it does not build Image, sync source, use ccache, or publish Releases. Existing .github/workflows/build.yml remains a preflight placeholder.
- tests/test_stage7_4_fast_build_gate.py covers policy and negative-security cases; only observed CI can upgrade them from IMPLEMENTED to TESTED.

A successful admission report deliberately has build_eligible=false. Stage 7.4 is NOT proof of a build, DFR compatibility, cache hit rate, ABI or boot.

## Offline commands (no kernel compilation)

First calculate the actual reviewed lock SHA256:

    sha256sum manifests/oneplus13-pjz110-sm8750-source.lock.json

Run offline tests:

    python3 -B -m unittest tests.test_stage7_4_fast_build_gate -v

Policy-only preview:

    python3 -B -m scripts.stage7_4_fast_build_gate --reviewed-lock-sha256 <64-lowercase-hex> --build-timestamp 2026-11-24T17:30:00+08:00

Optional local WSL2 read-only verification (report outside checked source):

    python3 -B -m scripts.stage7_4_fast_build_gate --reviewed-lock-sha256 <64-lowercase-hex> --source-workspace /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750 --host-disk /mnt/e --report /mnt/e/内核构建/reports/stage7-4-source-readonly.json

## Task list and explicit acceptance standard

| ID | Task | Current state | Objective completion criterion |
| --- | --- | --- | --- |
| 7.4-A | 35-project source/manifest/profile gate | CODE_IMPLEMENTED | Reviewed JSON SHA256 matches; local selected manifest and 35/35 Git HEADs match fixed lock, no tracked changes; report includes exact code Tree |
| 7.4-B | Immutable source and dangerous-input negative tests | CODE_IMPLEMENTED | Windows/Linux Python3.11/3.12 tests pass; wrong SHA, profile, path, commit, time, source, and disk guard all fail closed |
| 7.4-C | Manual-only workflow and branch isolation | CODE_IMPLEMENTED_NOT_REGISTERED | YAML passes static inspection; no push/PR build trigger, read-only permissions, bounded timeout, no Release, safe report-only artifacts; manual dispatch availability remains gated by default-branch registration |
| 7.4-D | Device build target/DFR dependency | BLOCKED_UNDETERMINED | Exact Kleaf target, required OEM module graph and DFR external include resolved from reviewed source without silently disabling modules |
| 7.4-E | Compiler/host and ccache | PARTIAL/BLOCKED | Exact Bazel, clang/LLD, versions and binary hashes proven; optional ccache has verified binary, interception and separately measured cold/warm hit rate (currently OFF) |
| 7.4-F | Resource/time and artifact envelope | CODE_POLICY_ONLY | Fresh physical host disk, inodes, RAM and peak estimate meet reserves, monitored build limit, evidence + SHA256; confirm with an authorized runner |
| 7.4-G | Actual timestamp through Kleaf sandbox | UNTESTED | Real compiler process sees KBUILD_BUILD_TIMESTAMP and SOURCE_DATE_EPOCH for default and explicit offset; final report records normalized UTC+epoch and config/cache inputs |
| 7.5-A | OnePlus fast Image/vmlinux build | DEFERRED_STAGE7_5 | Separate user-authorized pinned build, real Image and vmlinux hashes, Kconfig/source/toolchain/report and Run ID; no misleading success from static gate |
| 8-A | Full official OKI/DTBO/modules/ABI/KMI/device | DEFERRED_STAGE8 | Complete official PJZ110 vendor baseline and separate device recovery/boot/Root acceptance |

GitHub workflow_dispatch requires the workflow to be present on the default branch for the usual manual trigger. This new workflow is not on protected main; no merge/main edit, branch-only push workaround, paid runner, or real build is authorized here. Existing CI on development-branch commits tests software independently.

Current blockers: no ccache binary on the previously audited WSL2 PATH, 4 GiB-class WSL RAM needs real resource planning, DFR dependency and exact fast-build target remain undetermined, oneplus13 Image/vmlinux and module ABI/KMI untested. Refer to docs/STAGE7_4_LOCAL_CODEX_HANDOFF.md.
