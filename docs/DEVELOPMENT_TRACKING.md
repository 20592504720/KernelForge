# Stage 4.5: development sources

## Implemented contracts

The optional `kernelsu.version_policy` accepts `pinned`, `latest_release`, `latest_prerelease`, and `latest_branch`. Existing Stage 4 configs remain pinned and retain expected-Commit checks. `configs/kernelsu/bakasu-development.json` tracks BakaSU main; `official-development.json` tracks official main. Both use the modern Kbuild adapter. They are opt-in examples, not device compatibility promises.

`latest_branch` performs one exact `git ls-remote refs/heads/...` lookup per upstream per build. GitHub release discovery selects the newest published non-draft stable or prerelease separately, then peels the real tag. API/network errors, empty results, absent refs, wrong checkout SHA and unsupported source layouts fail without fallback. The resolved SHA is used for all subsequent fetch/integration operations. Existing Stage 4 Branch inputs still check expected_commit and are not silently made dynamic.

`versions.lock.json` is written before kernel checkout. It records repository, policy, requested branch/tag, full Commit, resolution timestamp, method and SUSFS source-file/patch hashes. A failed resolution writes a failure lock as well as a build failure report. SHA256 values are hashes of files fetched from the pinned upstream Commit; they are not independent upstream-signed checksum attestations. Installed toolchain verification remains the Stage 3 subsystem.

The official modern adapter checks kernel/Kbuild separately from the module wrapper kernel/Makefile, including current source layout and Kconfig prerequisites. Upstream now recommends LKM and no longer officially supports GKI image mode: our current integration is an experimental built-in Kbuild source adapter, not a completed DDK/LKM release pipeline. Unsupported layout changes fail. The legacy v0.9.5 adapter and profiles remain available unchanged.

## SUSFS scope and upstream evidence

Verified upstream: https://gitlab.com/simonpunk/susfs4ksu.git . On 2026-11-21 a real checkout of `gki-android14-6.1-dev` resolved to `756abbf2d81557e36664fc67dffaee26d3dfc57c`, with SUSFS_VERSION v2.4.0. Git refs also expose development branches for android12-5.10, android13-5.15, android15-6.6 and android16-6.12. An Android GKI identity is mandatory; it is never inferred from Linux version alone.

The inspected layout contains kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch, kernel_patches/50_add_susfs_in_gki-android14-6.1.patch, fs/susfs.c and include/linux/{susfs.h,susfs_def.h}. Discovery validates these exact roles and hashes them. Different layouts fail rather than applying guessed files.

Example additional build configuration:

```json
{
  "susfs": {
    "enabled": true,
    "repository": "https://gitlab.com/simonpunk/susfs4ksu.git",
    "version_policy": "latest_branch",
    "android_gki": "android14-6.1",
    "allow_bakasu_inline": true
  }
}
```

This is a narrow reviewed-layout integration, not the general Stage 5 patch manager. Before any application, all applicable patches run git apply --check, target paths are checked, and payload overwrites are rejected. All touched files are restored on patch/copy failure. Fully reverse-applicable matching patches plus identical payloads are recognized as already integrated and skipped. Partial or different existing integration is a conflict.

BakaSU already contains KSU-side SUSFS code; the official KSU patch is skipped, never reapplied to BakaSU. This does not mean the Android kernel is patched. Kernel applicability, hook symbol agreement, compatibility source files and explicit inline-hook opt-in are required. Tracepoint/manual/inline combinations are rejected. Missing required KSU symbols or a patch conflict produces INCOMPATIBLE. A successful static preflight is not compile/link/boot compatibility evidence.

## Final validation and reproduction

Development builds require `validation.kconfig` and `validation.kbuild` argv arrays. These execute after source integration and toolchain preparation. Nonzero status blocks the build; final_config (default .config) is read and required_configs (default KSU) must remain enabled. Missing commands are reported UNTESTED and block formal development builds. Use real make/Kleaf commands appropriate to the selected source layout, not placeholder commands.

`scripts/validate_upstreams.py` and the Real development sources workflow fetch real Android GKI ARM64 android14-6.1 sources from the AOSP GitHub mirror, lock the kernel/provider/SUSFS SHAs, integrate, run gki_defconfig/olddefconfig, verify final symbols, run make prepare and a Kbuild dry run. A dry run is not object compilation. Kernel compilation, boot and Root operation remain UNTESTED. The workflow reports each provider/SUSFS combination separately, including strict compatibility failures; it does not substitute old revisions.

For reproduction, retain the build config, versions.lock.json, patches/hashes and toolchain metadata. Replace each moving strategy with pinned, ref_type=commit, ref=<recorded SHA> and expected_commit=<same SHA>, preserving the original integration method and Android GKI identity. This is also the explicit rollback mechanism: select a previously successful lock/config combination. A previous successful build is never automatically selected after a failure. Branch names and release labels may move; recorded Commits and matching file hashes are the reproducible inputs.

## Validation status

IMPLEMENTED: strategies, immutable build locks, source layout adapters, SUSFS discovery, narrow patch transactions, duplicate protection and final command gates.

TESTED with local fixtures: all four policies, annotated tags, missing refs/network/API failures, pinned drift, Android mapping, patch hashes, conflicts, rollback, duplicate/partial integration and final-check failures. Actual upstream CI results are recorded in the PR/delivery report rather than assumed here.

UNTESTED until actual runner evidence exists: each real provider/SUSFS/GKI combination, real Kconfig resolution and Kbuild preparation. Full kernel/KernelSU object compilation, boot and runtime Root remain UNTESTED even when source validation passes.

Local limitations: this Windows machine has no installed WSL distribution or kernel build toolchain. Initial GitHub/Android network attempts failed; a subsequent real run resolved all three upstreams but GKI checkout failed on the Windows-reserved include/soc/arc/aux.h path. Local real-source failure reports are retained under `$KERNELFORGE_HOME/builds/stage45-local-validation/report`. Network failures do not fall back to another version.

Observed real-source results and remaining blockers are recorded in [STAGE45_REPORT.md](STAGE45_REPORT.md).
