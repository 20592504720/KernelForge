# Stage 7.5 — pinned OnePlus 13 fast Image/vmlinux acceptance

**State: STARTED — GitHub-side offline evidence software only. The real-build gate is NOT yet met.**
Do not interpret Stage 7.4 `STAGE7_4_SOFTWARE_AND_SOURCE_ADMISSION_TESTED`
as `build_eligible=true`. The source admission report correctly remains
`SOURCE_LOCK_TESTED_BUILD_BLOCKED`.

## Exact entry baseline and boundaries

- Repository: `20592504720/KernelForge`; development branch
  `stage1/initial-foundation`. The starting Stage 7.4 accepted remote Commit
  was `5ca19c5843e127c218cf9aaa79eefbf12682448e`, Tree
  `3a32d3144eeee84a7d04b8bc34193ac79c37961a`.
- OnePlus 13 `PJZ110`, `SM8750`, arm64, official 6.6 source, Manifest
  `oneplus_13_b.xml` at
  `f8e50677874c65b6da41057d2f39be7b4ef3c08a`.
- Reviewed 35-project lock SHA256:
  `7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e`.
  **Recompute before use; any difference is a block, not an automatic re-pin.**
- Working repository: `E:\内核构建\project` / `/mnt/e/内核构建/project`.
  Existing ext4 source:
  `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`.
  Preserve the entire 35-project checkout, existing evidence, caches and
  independent local Git history. Do not run a second `repo sync`.
- Stage 7.4 WSL2: 21/21 passed; 35/35 HEAD, tracked clean, manifest and physical
  disk check passed. Cloud fix Run 45272620184 completed 4/4.
- Stage 7.2 WSL2 tested pinned Clang r510928/Clang18.0.0 binary SHA256
  `dc739fc44bb889146bd47732912cad457200af7de7c2fb5a7509b7a9974d6d67`.
  Bazel executable identity was inventoried but the exact build action and
  sandbox were not executed. `ccache` was not on PATH, and remains OFF.
- Previous WSL limit was about 3.77 GiB memory, 1 GiB swap; the E: physical
  host disk reserve is 50 GiB, ext4 reserve 20 GiB plus inodes. Ext4 VHDX
  advertised free space does **not** substitute for E: physical space.
  Resource samples are per-run and must be refreshed.
- Source profile lacks confirmed `firmware_build`, ABI/KMI, full device toolchain
  and resolved fast Kleaf target. OEM DFR external module/include dependency
  remains `BLOCKED_UNDETERMINED`.

## Definition of Stage 7.5 (NOT the full official OKI)

Deliver a **real, unmodified, pinned official OnePlus 13 fast Image and vmlinux
build**, with bounded, reproducible inputs, actual Bazel/Kleaf action evidence,
compiler/time provenance, checked artifacts and reported Git/toolchain hashes.

This phase does NOT accept: full vendor modules, DTB/DTBO, firmware identity,
ABI/KMI, BakaSU/SUSFS, Fengchi, network/ZRAM enhancements, boot, Root, flashing,
signing, OTA or Release. Those require the separate Stage 8/9 contracts.
Do not silently weaken CFI/KCFI, SELinux, module-signing or security options,
discard DFR dependencies, or relabel a generic GKI 6.1 Image as SM8750 OKI.

## Work packages and acceptance gates

| ID | Work package | Passing evidence | Current state |
| --- | --- | --- | --- |
| 7.5-A | Confirm actual Kleaf labels, Bazel wrapper/flags, DFR include and exact OEM dependency graph | Read-only citation to pinned BUILD/.bzl files, exact label and target files, whether Image/vmlinux action requires DFR/vendor modules; unresolved edges explicitly BLOCKED | LOCAL_AUDIT_REQUIRED |
| 7.5-B | Establish resource-protected local build contract | Fresh WSL RAM/swap, CPU, E: physical and ext4/inodes; bounded parallelism, no-fetch policy and output/cache roots, process-group kill-on-limit, log retention and rollback plan; review before costly execution | NOT_AUTHORIZED_TO_RUN_YET |
| 7.5-C | Verify compiler and timestamp action environment | Exact pinned Clang/LLD/Bazel wrapper bytes; blank timestamp sampled at actual build start, custom ISO8601+timezone normalized UTC; proof that KBUILD_BUILD_TIMESTAMP and SOURCE_DATE_EPOCH reach **actual compiler action** despite Bazel sandbox | UNTESTED |
| 7.5-D | Run one approved pinned fast Image/vmlinux build | Actual command, exit 0, full unredacted-safe diagnostic log, task time/peak disk/RAM, source HEAD/manifest, .config, build target, actions, output locations and no unexpected fetch/rewrite | NOT_RUN |
| 7.5-E | Hash/inspect artifacts and independent review | Image and ARM64 ELF64 little-endian vmlinux, nonempty final .config/log, SHA256/bytes, source/toolchain identity, timestamp; independent review of actual Bazel action and logs | SOFTWARE_IMPLEMENTED_NOT_REAL_TESTED |
| 7.5-F | Closure | Git HEAD and Tree, no source/lock mutation, CI regression, WSL real-build report, all acceptance gates explicit; no flashability assertions | PENDING |

No CI `workflow_dispatch` is assumed possible for a workflow absent on protected
`main`. Do not create a push-trigger workaround, trigger paid/heavy runner,
merge PR #1, or change main merely to expose a button.

## GitHub-side software: offline artifact receipt

`scripts/stage7_5_artifact_evidence.py` checks existing copied artifacts
read-only after a separately approved build. It requires exactly these files
under an existing, isolated bundle directory:

- `Image`: uncompressed, non-empty Image bytes (not an ELF copy)
- `vmlinux`: ELF64, little-endian, AArch64 executable or shared-object ELF
- `.config`: final kernel config with `CONFIG_ARM64=y`
- `build.log`: actual unmodified build process log, retained separately
- `build-time.json`: the actual resolved timestamp record; it must be
  internally consistent (format alone does not establish Bazel propagation)

The checker verifies the reviewed 35-project lock, all live source HEADs and
tracked cleanliness with `inspect_source()`, WSL host disk sampling, the
Stage 7.2 pinned Clang hash, required file shape and SHA256. It does **not**
execute Bazel, create compiler output, modify source or certify a logged
`--declared-build-exit-code 0`. `--target` must be the independently reviewed
real label, not the example placeholder from unit tests.

After a real authorized build, a sample *parameter shape* (replace TARGET with
the verified label, and choose an existing OUTSIDE-source bundle directory):

```sh
python3 -B -m scripts.stage7_5_artifact_evidence \
  --reviewed-lock-sha256 7c42e764c4e55a09f4b0c6a1f17661839e1d0c12a083ff399cca16eb4f124e1e \
  --source-workspace /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750 \
  --host-disk /mnt/e \
  --bundle /mnt/e/内核构建/reports/STAGE7_5_APPROVED_BUNDLE \
  --target TARGET \
  --declared-build-exit-code 0
```

**A successful receipt has status
`ARTIFACT_BYTES_CHECKED_BUILD_UNATTESTED`.** A synthetic fixture can pass
the receipt; the real build still requires separately reviewed terminal
logs, exact process exit and Bazel action/DFR evidence. Do not describe
this receipt as a successful compile or a device-ready kernel. Run receipts
on copies of artifacts, not inside pinned source or repository. Do not add
large binaries or sensitive build logs to Git.

## Guardrails and handoff

For the **first** Antigravity task, execute only
`docs/STAGE7_5_ANTIGRAVITY_HANDOFF.md`: read-only Kleaf/DFR and build-resource
investigation. Only after its findings are audited may a later separately
issued instruction authorize bounded Bazel graph query or real Image/vmlinux
compilation. If the DFR dependency cannot be resolved without disabling
vendor functionality, record BLOCKED; do not patch around it.

Current top-level verdict:
`STAGE7_5_CLOUD_SOFTWARE_IMPLEMENTED_LOCAL_TARGET_AND_REAL_BUILD_PENDING`.
