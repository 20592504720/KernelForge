# Stage 5 final bounded acceptance and exact GKI run request — 2026-11-23

Status at request: **IN_PROGRESS**. **A job request is not successful validation.** The workflow branch-push path and pre-download controls are documented in [STAGE5_BAKASU_SUSFS_DELTA_AUDIT.md](STAGE5_BAKASU_SUSFS_DELTA_AUDIT.md). The request below is a **single explicit, bounded GKI source/object/link test**, not a full Image compile or SM8750 source sync.

## Existing independently distinguishable evidence

| Requirement | Before this request | Qualification |
| --- | --- | --- |
| OnePlus 13 official source lock and 35/35 Git HEADs | TESTED | Locked WSL2 Ubuntu ext4 source sync; no SM8750 compile |
| OnePlus 13 Kleaf targets and inventory | STATIC_AUDITED | `sun_perf_dist` / `sun_consolidate_dist` only; no Bazel query/build |
| Real generic ACK 6.1 Patch Manager transaction | TESTED | A locked generated comment-patch/rollback probe, not all third-party feature patches |
| Pinned GKI official/BakaSU × SUSFS combinations | TESTED (4/4) | Prior Run 45020470109; distinct older BakaSU SHA |
| Source-level new BakaSU/SUSFS API | STATIC_AUDITED | Two `susfs_add_*` signatures match locked SUSFS commit; no ARM64 compilation |
| Local BakaSU compatibility safety and exact entry | Codex-reported 69/69 and 33/33 | GitHub report confirms latest 8/8 + 25/25 tests; E: logs are local; independent GH Actions runtime still needed |
| Moving latest-branch GKI | BLOCKED (7/8) | Run 45098970334 used `63ad1ea...`, one translation-only commit beyond reviewed `2734e0bc...`; exact Commit checks remain fail-closed |
| Full OnePlus 13 OKI, ABI/KMI, firmware, modules, flash/boot/Root | UNTESTED | Stage 8 / physical-device contract; not within this GKI request |

## One bounded run: exact target

The single trigger file `.github/stage5-exact-gki-request.json` must be changed on the existing `stage1/initial-foundation` branch. Its schema/version/commit/full_kernel values are compared to compiled-in expected constants by `scripts/stage5_exact_request.py` after checkout, **before dependency installation or upstream source fetch**; malformed SHA is rejected even earlier, before checkout.

- GKI: `498f91c17b0822a09aede17d26a63bf8c6813725`.
- BakaSU: `2734e0bc155759955880f5fb99be640fc5b92156`.
- SUSFS: `756abbf2d81557e36664fc67dffaee26d3dfc57c`.
- Run mode: exactly one `exact_bakasu` job, `--provider bakasu --susfs --pinned-baseline --bakasu-commit <SHA>`. The eight-job `sources` matrix explicitly excludes push events.
- Bound: hosted Ubuntu 24.04, job timeout 60 minutes, existing dependency installation; no `--full-kernel`, full Image, SM8750 `repo sync`, OnePlus 13 OKI, boot or Release.
- Preflight: Python 3 stdlib only, exact GH branch + Git HEAD changed-files check + duplicate-key rejecting marker JSON parser. CFI/KCFI and Shadow Call Stack remain enabled as required by pinned ACK baseline.
- Output: `real-source-report.json`, `versions.lock.json`, `source-check.log`, final `kernel.config`, `capabilities.json`, `undefined-symbols.txt`, object hash reports and uploaded `real-bakasu-susfs-true-exact` artifact if the source integration reaches those gates.

The preflight implementation was also reproduced in an isolated container fixture, where 13 positive and negative checks passed including an ephemeral Git HEAD fixture. This does **not** count as the repository's full Python suite, GitHub Actions job or kernel compile success; the separate Codex local suite must still validate the latest source Tree.

## Acceptance / failure decisions

1. Record the resulting workflow **Run ID, event, triggering Commit/Tree**, job name and verified `versions.lock.json` target SHAs. A skipped job, failed preflight, or unexpected eight-way matrix is a **failure**, not success.
2. Inspect the actual `git apply` record, final `.config` hardening flags, ELF/LLVM AArch64 objects, link return status, and unresolved KernelSU/SUSFS symbols. A `git apply --check` alone cannot pass Stage 5.
3. Require `real-source-report.json.status == success`, `kconfig == TESTED`, `object_compilation == TESTED`, and `acceptance.relocatable_link == TESTED`, together with the SHA-locked source and artifacts. Check `acceptance.full_vmlinux == UNTESTED` remains truthful. If any fail, preserve diagnostics and perform **one targeted fix**, not an automatic rerun of all eight.
4. Only after that GKI acceptance can Stage 5 be evaluated for scoped closure. A moving `latest_branch` failure cannot be silently called passed; explicitly choose `BLOCKED` dynamic-upstream monitoring with documented limitation or continue compatibility work. Official OKI/ABI/boot stays Stage 8, never mislabel as Stage 5 GKI evidence.
5. No `main` write, PR #1 merge, force push, source-lock rewrite, paid runner escalation or local E-drive deletion is authorized by this document.

Keep the workflow run evidence separate from the original OnePlus 13 35/35 source-sync evidence. Stage 5 **IN_PROGRESS** until checked.


## 2026-11-23 verified results — bounded GKI acceptance (supersedes request-only status)

**Generic ACK 6.1 exact BakaSU+SUSFS acceptance: TESTED for objects/relocatable link; NOT a complete Image/boot test.**

- [GitHub Run 45105067150](https://github.com/20592504720/KernelForge/actions/runs/45105067150), commit `5fb591438a12a7184d32cf496042baf289a7c0de`, tree `8d71f513cd922851a6cf18da502afff22a3bb28f`, status **success**. One `exact_bakasu` job `137464346250` passed; the `sources` eight-combination job was **SKIPPED**.
- Artifact [real-bakasu-susfs-true-exact](https://github.com/20592504720/KernelForge/actions/runs/45105067150/artifacts/14787570448), id `14787570448`, GitHub-reported archive SHA256 `b9c727b641faca1b268cd8fb24f2e3754646a3be60334194479a6e0ddb818518`. User/Codex reports an independently matching local copy at `E:\\内核构建\\reports\\stage5-final-45105067150`; those local bytes were not reopened during this GitHub-side audit.
- Independently parsed complete `real-source-report.json` from the job log: `status=success`, `version_policy=pinned`, `kconfig=TESTED`, `object_compilation=TESTED`, exactly **67 objects**, all `ELF64 ARM64 relocatable`, `status=TESTED`, with 67 SHA256 checksums. `integration-check.o` is a 24,121,824-byte ELF64 ARM64 relocatable object with SHA256 `9cf5c10656d5795f28d977468775efd9f476f0d12cbbc6885321e331674bfd63`. `unresolved_root_hooks=[]`, `acceptance.relocatable_link=TESTED`.
- `required_final_configs` explicitly records `KSU=y`, `KSU_SUSFS=y`, `CFI_CLANG=y`, `SHADOW_CALL_STACK=y`, `RANDOMIZE_BASE=y`, `HARDENED_USERCOPY=y`, `FORTIFY_SOURCE=y`. Version lock and adapted SUSFS patch match the exact ACK6.1 `498f91c...`, BakaSU `2734e0bc...`, SUSFS `756abbf...` Git SHA triplet. No compatibility whitelist was widened by this evidence reconciliation.
- `acceptance.full_vmlinux=UNTESTED`, `boot=UNTESTED`, `root=UNTESTED`; OnePlus 13 complete OKI, ABI/KMI and device evidence remain Stage 8, not this GKI result. The existing `latest_branch` failure is a separate moving-source policy issue and stays BLOCKED unless explicitly scoped out or a new exact source SHA is reviewed.

**Independent Windows blocker:** [Validate Run 45105067186](https://github.com/20592504720/KernelForge/actions/runs/45105067186) completed **3/4**: both Linux 3.11/3.12 and Windows 3.12 succeeded; Windows Python 3.11 job `137464346892` was interrupted with `KeyboardInterrupt` and Windows exit `-1073741510` during `test_toolchains.ToolchainVersionTests.test_host_mismatch_rejected`. Prior run `45098970262` showed the **same asynchronous abort in a different test**, not an assertion failure. Windows Python 3.12 ran **183 tests OK**. No confirmed Windows 3.11 test-code defect or external signal sender has been isolated.

**Follow-up CI diagnostic (not a demonstrated fix):** Change only Windows 3.11 test invocation from `cmd` to `pwsh` and log SIGINT/PID/in-progress test in `scripts/windows_test_runner.py`; keep full discovery and failures intact. The next CI run must be inspected; do not assert the 3.11 issue is repaired until it passes. No kernel source, patch bytes, source locks or full GKI workflow are changed. The lightweight `Validate` push workflow may execute automatically; do not rerun the costly real GKI job.

**Stage closure:** The exact-source GKI verification gate is **SATISFIED for the agreed object/link scope**, but Stage 5 overall remains **IN_PROGRESS** until Windows CI is accepted and the user approves a written Stage 5 scope decision for moving `latest_branch` monitoring and Stage 8 device/full-build deferrals. Do not silently change either to TESTED.

## 2026-11-23: Windows CI two-sided interruption analysis / full-suite isolation candidate

[Validate Run 45106947923](https://github.com/20592504720/KernelForge/actions/runs/45106947923) at Git Commit `4083903c4f96daa274632b539d916a541eb0435f` finished **2/4**. Both Linux jobs passed; **both Windows jobs BLOCKED**, for distinctly observed reasons:

- Windows Python **3.11** (`137470308177`): emitted `Ran 183 tests in 42.740s` and `OK`, but PowerShell job exited **1** without a printed SIGINT event or test assertion error. Full-suite verdict was positive; the source of the nonzero process/shell exit was not evidenced.
- Windows Python **3.12** (`137470308067`): at `test_toolchains.SourceAdapterTests.test_staging_path_is_bounded_under_long_cache_root`, `WINDOWS_TEST_INTERRUPT` observed `signal=2` (`SIGINT`), then `WINDOWS_TEST_ABORTED`, `KeyboardInterrupt`, Windows batch termination and exit **-1073741510**. Earlier interruptions occurred at different unit-test methods; therefore no specific assertion defect is established. The sender of the console signal is still **unknown**.
- The previous Run `45105067186` had 3/4 passing; neither result alters GKI Run `45105067150` **success** or proves device boot/runtime compatibility.

A **narrow isolation/diagnostic candidate** has been submitted: `scripts/windows_test_launcher.py` launches the existing full test runner as an isolated Windows process with `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`, consolidates child stdout/stderr for faithful logging and forwards its exact exit code. Windows 3.11/3.12 both use PowerShell to invoke this wrapper; the script explicitly outputs `WINDOWS_SHELL_CHILD_EXIT`. The original runner prints `WINDOWS_TEST_SUMMARY` (actual `wasSuccessful()`, 183 case count, failures/errors/remaining worker threads, chosen exit code), and its SIGINT handler cannot swallow a normally returning prior handler. Offline unit tests verify a successful child, failure, interrupted child and spawn failure. **No unit test is skipped, suppressed or converted into a success.** A real GitHub Windows runner result is necessary before claiming this is fixed; no kernel source, patch, provider list, GKI workflow or E-drive data is changed.

**Stage 5: IN_PROGRESS.** Scoped real GKI source/67-object/relocatable-link acceptance is TESTED; dynamic `latest_branch` stays BLOCKED; device/full OKI remains the Stage 8 UNTESTED track.
