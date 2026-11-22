# Stage 5 evidence reconciliation (2026-11-23)

**Status: GitHub-side evidence reconciled; Stage 5 overall IN_PROGRESS, not accepted.** This is an audit of already available GitHub run/job/log records and the existing local-sync handoff. It creates no new build, download, source checkout, or device validation.

Repository: `20592504720/KernelForge`, development branch `stage1/initial-foundation`, reviewed HEAD `2192361c0be1b1f3e836e9b82d3c59cc398b72f1`. PR #1 remains open; main remains protected by project policy. Because the changes since executable-code HEAD `5d4ca11f0bfcf61fa71db9bba8a0e081b8cc14e3` are documentation only, earlier code-run evidence remains relevant to that code tree, **subject to matching exact workflow, toolchain, upstream refs and configs**.

## Evidence grades / no cross-claiming

- **OnePlus 13 locked source — TESTED (as recorded):** WSL2 verifier's successful `--resume` is documented in [STAGE5_HANDOFF.md](STAGE5_HANDOFF.md): exit 0, `source_sync=TESTED`, `matched_projects=35`, 0 mismatches, manifest SHA `f8e50677874c65b6da41057d2f39be7b4ef3c08a`, same persistent ext4 workspace. First attempt produced a recoverable CodeLinaro Rust `curl 56 GnuTLS` failure. This GitHub-only audit checked the **committed handoff text**, not the original local JSON and log bytes. Raw WSL verification remains a distinct local handoff task.
- **E: free-space delta — REPORTED, not per-repository size:** `338.13 - 185.41 = 152.72 GiB` available space decrease. This includes effects of the virtual disk and other host allocations; it is not a measured Git download byte count, extracted source size, or Bazel peak.
- **Generic GKI CI — mixed by exact run:** Four pinned full Image jobs passed in newest checked matrix; latest-branch matrix is **3/4 passing, 1 failing**. The overall latest real-source run is **7/8, failure**, not 8/8 TESTED.
- **OnePlus 13 full-build and device gates — UNTESTED:** full vendor/OKI `Image`, `vmlinux`, vendor modules, device tree/DTBO, KMI/ABI, firmware pairing, boot, BakaSU/Root runtime and actual SUSFS behavior. Generic GKI Image outputs do not prove PJZ110 boots.

## GitHub Actions ledger

| Run and URL | Tested Commit | Outcome and evidentiary limit |
| --- | --- | --- |
| [Validate 44997133507](https://github.com/20592504720/KernelForge/actions/runs/44997133507) | `da45033adb9e1976caf9419d08002af91b6a225c` | 4-platform pass, historical |
| [GKI 44997133564](https://github.com/20592504720/KernelForge/actions/runs/44997133564) | `da45033adb9e1976caf9419d08002af91b6a225c` | 8/8 success; prior handoff states 8 reports and pinned Image hashes independently inspected |
| [GKI 45000790179](https://github.com/20592504720/KernelForge/actions/runs/45000790179) | `d7c9d663dc2bcbb4510f7e12bad167dca0ec2eed` | 8/8 success; prior compatible run, not evidence that moving upstream remained compatible |
| [Validate 45020469994](https://github.com/20592504720/KernelForge/actions/runs/45020469994) | `5d4ca11f0bfcf61fa71db9bba8a0e081b8cc14e3` | **4/4 success**, Ubuntu/Windows × Python 3.11/3.12 |
| [SM8750 audit 45020469998](https://github.com/20592504720/KernelForge/actions/runs/45020469998) | `5d4ca11f0bfcf61fa71db9bba8a0e081b8cc14e3` | Manifest job passed; hosted-runner `locked-sync` **skipped**, not 35/35 evidence |
| [GKI 45020470109](https://github.com/20592504720/KernelForge/actions/runs/45020470109) | `5d4ca11f0bfcf61fa71db9bba8a0e081b8cc14e3` | **7/8**; 4 pinned success, 3 latest success, 1 latest incompatible |

### Precise newest failure

Run [45020470109](https://github.com/20592504720/KernelForge/actions/runs/45020470109), job [137201998796](https://github.com/20592504720/KernelForge/actions/runs/45020470109/job/137201998796), `sources (bakasu, true, latest)`, failed in **Validate real sources → KernelSU and SUSFS integration**. Full job log and its embedded `real-source-report.json`/`versions.lock.json` were inspected through GitHub:

- Kernel: exact GKI Commit `498f91c17b0822a09aede17d26a63bf8c6813725` (ACK 6.1 baseline, not OnePlus 13 6.6.118).
- BakaSU `main` resolved at `2734e0bc155759955880f5fb99be640fc5b92156`.
- SUSFS `gki-android14-6.1-dev` resolved at `756abbf2d81557e36664fc67dffaee26d3dfc57c`.
- Patch `kernel_patches/50_add_susfs_in_gki-android14-6.1.patch`, SHA256 `4c74f1862ad5a4851bd201e334c1149b9776e774274574ce58aa23a1da318364`.
- Git rejected hunks at `fs/exec.c:64` and `fs/namespace.c:32`; the report classified `INCOMPATIBLE: SUSFS patch conflict`. `kconfig`, `kbuild`, `kernel_compile` and `object_compilation` were `UNTESTED` in this failed job. This is **not** a CodeLinaro download or host disk issue.
- This latest-branch failure is narrower than a blanket BakaSU/SUSFS failure: `bakasu, true, pinned` **passed** in this same run. Do not reuse an older moving-branch success to override the latest failure.

No new GKI reruns were launched in this audit. Because both BakaSU and SUSFS were moving references, select the exact source/patch history and compare against the last known good run before attempting an audited compatibility adapter. Do not disable hardening, force fuzzy patch application, weaken the guards or auto-update the lock.

## Stage 5 gate matrix / next owners

| Gate | Status at review | Owner and next step |
| --- | --- | --- |
| Official OnePlus 13 Manifest 35 locked SHAs | **TESTED (documented local verifier)** | Local Codex may inspect exact successful `resume.json` bytes and export a safe evidence summary; no resync |
| Official 35-project materialized capacity / prebuilt inventory | **NOT_MEASURED** | Local Codex **read-only** disk / per-project size and toolchain inventory, respecting root `./` project overlaps |
| Lightweight regression | **TESTED 4/4** on executable HEAD `5d4ca11...` | GitHub evidence already available; don't rerun for docs-only changes |
| Pinned GKI full Image | **TESTED 4/4 jobs** in Run `45020470109` | Optionally independently hash newly archived artifact payloads; do not conflate GKI with vendor OnePlus Image |
| Latest-branch GKI source integration | **7/8 overall / 1 incompatibility** | GitHub-side targeted upstream review, compatibility decision; one failed configuration only if code fix is justified |
| Real generic feature patches on SM8750 / BBG / Unicode / Fengchi | **NOT_IMPLEMENTED / BLOCKED / UNTESTED**, depending on feature | Preserve prior constraints in Stage 5 handoff and [cloud-readiness plan](STAGE5_CLOUD_READINESS.md); no unreviewed script execution |
| OnePlus 13 full OKI compile / module ABI / firmware / device boot / Root | **UNTESTED** | Stage 8 work only after reviewed capacity and build inputs; do not declare flashable or Stage 5 wholly complete |
| Stage 6–9 cloud design preparation | **DESIGN_REVIEWED** | [STAGE5_CLOUD_READINESS.md](STAGE5_CLOUD_READINESS.md); implementation deliberately postponed |

**Acceptance decision required:** Stage 5 may close only once its exact policy-mandated evidence gates are satisfied, or an explicit documented decision scopes out the moving-`latest_branch` failure and deferred device/OKI work. At this checkpoint, mark **Stage 5 IN_PROGRESS**; `source_sync=TESTED` remains valid and is not revoked by the unrelated moving-patch failure.

## Local handoff

[STAGE5_LOCAL_CODEX_HANDOFF.md](STAGE5_LOCAL_CODEX_HANDOFF.md) provides the exact strictly read-only WSL2 tasks, outputs, ownership rules, and safety restrictions. The GitHub connector cannot inspect Windows E: virtual-disk contents or the raw WSL report at its local path; no assertions about those bytes beyond the handoff claim were made.
