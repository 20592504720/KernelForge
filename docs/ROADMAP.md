# Roadmap


> **Evidence update (2026-11-23):** Fixed ACK 6.1 / BakaSU `2734e0bc...` / SUSFS `756abbf...` passed real 67-object ARM64 + relocatable-link verification ([Run 45105067150](https://github.com/20592504720/KernelForge/actions/runs/45105067150)); full Image/boot remain untested. After Windows test-runner isolation, both [Push Validate 45108869968](https://github.com/20592504720/KernelForge/actions/runs/45108869968) and [PR Validate 45108874520](https://github.com/20592504720/KernelForge/actions/runs/45108874520) passed all four OS/Python combinations, with 187 tests on each Windows job and exits 0. Stage 5 is **READY_FOR_SCOPED_ACCEPTANCE**, not formally completed until the user accepts treating dynamic `latest_branch` as ongoing maintenance (BLOCKED) and deferring OnePlus 13 full device/OKI compilation to Stage 8. See [final gate](STAGE5_FINAL_ACCEPTANCE_GATE.md).


> **Status clarification (2026-11-23):** OnePlus 13 official `source_sync=TESTED` (35/35) is documented in [Stage 5 handoff](STAGE5_HANDOFF.md). The latest checked real-source GKI matrix was 7/8, with BakaSU+SUSFS `latest_branch` patch conflict; Stage 5 overall is not yet accepted. See [evidence reconciliation](STAGE5_EVIDENCE_RECONCILIATION.md). Older "WSL source sync is running" lines below are historical and superseded for that single gate. Later Stages 6–9 remain planning only.


All stages follow the [execution policy](EXECUTION_POLICY.md). Stage 5 remains
open until current-Tree Linux and SM8750 evidence is assessed; do not infer
acceptance from configuration files or an earlier run.

1. **Foundation:** schemas, local validator, manifests, tests, and CI.
2. **Build engine:** pinned source checkout, separate GKI/Vendor plans, logging and reproducible reports.
3. **Toolchain manager — implemented:** profile-driven LLVM/GCC provisioning, mandatory SHA256 checks for downloads and cache reuse, safe installation, cache maintenance and isolated GKI/Vendor build environment integration. Real upstream toolchain layouts and Android kernel builds remain unverified.
4. **KernelSU:** individually researched adapters for Official, Next, and ReSukiSU.
5. **Patch manager:** ordering, conflict/check/apply/rollback, hashes, reports.
6. **Features:** source/Kconfig-based SUSFS, networking, ZRAM, optimization checks. Unidentified BBG/Unicode/Fengchi items remain unimplemented until their sources are confirmed.
7. **Devices and delivery:** verified profiles, real builds, artifact manifests, packaging, guarded releases.

Directories and configuration keys alone do not imply later-stage capability.


## Prospective Stages 6–9 (approved planning, NOT_IMPLEMENTED)

The historical Stage 6 feature and Stage 7 device/delivery bullets above are retained as context, **not discarded**. For new development, use the revised phase allocation below; see [Stage 5 cloud-readiness audit and acceptance contracts](STAGE5_CLOUD_READINESS.md). This is a plan only, not a Stage 5 completion or a release authorization.

- **Stage 6 — source acquisition and compatibility:** dual verified Git/archive strategies; preserve Git-backed patch targets and exact 35-project source lock. Carry forward old Stage 6 feature-source reviews and patch-conflict work. Gate: provenance/negative/security tests.
- **Stage 7 — toolchains, caching and fast real builds:** Release mirror through existing ToolchainManager, validated non-LLVM resources, ccache isolation and manual-only Actions fast Image builds. Carry forward permitted old Stage 6 feature build probes. Gate: real pinned Image/vmlinux plus toolchain, source and artifact hashes.
- **Stage 8 — scoped OnePlus 13 official OKI and 10 user-selected goals:** retain the pinned 35-project PJZ110 baseline and full vendor modules, DTB/DTBO, ABI/KMI and firmware/boot gates. Selected goals: BakaSU+SUSFS; native Fengchi HMBIRD; isolated safe ccache; BBR/Westwood and necessary network config; ZRAM with compatible compression; Droidspaces; Mountify; conditional ADIOS I/O; Re:Kernel/Freezer/NoActive. All other Stage 8 screenshot additions, other Root providers, device/kernel variants, public ccache-ECS preload, forced compression upgrades and experimental GKI are explicitly **DEFERRED**, not silently deleted. Follow the [10-item feature and deferral matrix](STAGE8_EXPANDED_FEATURE_MATRIX.md) and [scoped acceptance contract](STAGE8_SCOPED_ACCEPTANCE.md). Planning only; Stage 9 release gates unchanged.
- **Stage 9 — automated Actions delivery:** checked workflow configuration, repeatability, bounded caches, guarded Artifacts/Releases and device-flashing gates. Carry forward old Stage 7 guarded release obligations. Gate: negative configuration tests and verified artifact/provenance/release behavior.

**Stage 5 remains IN_PROGRESS** and the existing WSL2 35-project source sync continues independently. None of these phases authorizes rewriting its lock/verifier, a second sync, a heavy CI run or a local future-build dependency.
