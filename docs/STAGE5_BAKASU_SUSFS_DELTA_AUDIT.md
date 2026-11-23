# Stage 5 BakaSU/SUSFS latest-branch compatibility audit — 2026-11-23

**Decision: STATIC_AUDITED; NOT FIXED; latest-branch integration BLOCKED.** This is an exact-commit comparison and failed-run review, **not** patch acceptance, kernel compilation, boot or Root evidence. No toolchain download, source sync, CI dispatch or local WSL modification was performed. The narrow fix must not be approved before source/API and compile evidence.

## Locked evidence and immediate mechanism

- Project development HEAD reviewed: `7c6dff5a52c7b1fb6db7f074e6e1d5c9101a0c3d`, branch `stage1/initial-foundation`.
- [GKI Run 45020470109](https://github.com/20592504720/KernelForge/actions/runs/45020470109), job [137201998796](https://github.com/20592504720/KernelForge/actions/runs/45020470109/job/137201998796), 2026-11-22: `sources (bakasu, true, latest)` failed at `Validate real sources` during `KernelSU and SUSFS integration`. **7/8 jobs passed overall; all four pinned jobs passed.**
- Exact failure inputs in job's preserved `real-source-report.json` and `versions.lock.json`: ACK 6.1 kernel `498f91c17b0822a09aede17d26a63bf8c6813725`; BakaSU `main` resolved to `2734e0bc155759955880f5fb99be640fc5b92156`; SUSFS `gki-android14-6.1-dev` resolved to `756abbf2d81557e36664fc67dffaee26d3dfc57c` (`SUSFS_VERSION=v2.4.0`). The input upstream `50_add_susfs_in_gki-android14-6.1.patch` SHA256 was `4c74f1862ad5a4851bd201e334c1149b9776e774274574ce58aa23a1da318364`.
- **Observed failure:** `git apply --check` could not match hunk context in GKI `fs/exec.c:64` and `fs/namespace.c:32`. The failed job's `kconfig`, `kbuild`, `kernel_compile` and `object_compilation` remained `UNTESTED`. It is not an ABI, link, compiler, OnePlus 13 source-sync, or disk-exhaustion failure.
- The repository's `kernelforge/compatibility.py::select()` requires **all three** exact kernel, provider and SUSFS Git HEADs and validates original/adapted patch hashes and unchanged upstream +/- lines. Its catalog `patches/compat/susfs/manifest.json` names only provider SHAs `2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4` (official) and `7b65bde0710b5e7c6f755545cb15a4abd417f3a8` (older BakaSU). New BakaSU `2734e0bc...` **does not match**; the selector must return the original patch. `kernelforge/susfs.py` then strictly checks applicability and refuses the conflicting raw patch. This is **correct fail-closed behavior**, not proof that a new adapter will compile.

## Exact BakaSU upstream comparison

[Compare old `7b65bde...` to new `2734e0bc...`](https://github.com/Baka-SU/BakaSU/compare/7b65bde0710b5e7c6f755545cb15a4abd417f3a8...2734e0bc155759955880f5fb99be640fc5b92156): GitHub reports **19 commits ahead, 0 behind, 76 affected files**. Both exact Git commit objects and trees were present. The old tree is `7ecd5dec65b97a690bf46e8218aa14f3ca177dc5`; the new tree is `5b3644e00413a98466dd34d504080b858b2dd296`. Representative exact file reads and compare patches:

| Area | Change in new BakaSU | Acceptance implication |
| --- | --- | --- |
| `kernel/Kbuild` | `feature/selinux_hide.o` → `feature/selinux_hide/selinux_hide.o` | Kbuild integration and actual new composite object coverage need fresh verification |
| `kernel/Kconfig` | New `KSU_SUSFS_PRIORITY_UID_FILTER` with `depends on KSU_SUSFS` and `default y` | Final Kconfig and SUSFS matching API need rechecking; a new default can affect compiled configuration |
| `kernel/tools/susfs_compat.mk` | Whitespace/indentation-only around existing `ksu_selinux_hide_running` detection and `KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE` | Detection conditional itself survives; not a build proof |
| `kernel/feature/selinux_hide.c` | Old monolithic file removed/split into `feature/selinux_hide/selinux_hide.c`, `selinux_hide_auto.c` and `selinux_hide_susfs.c` | Reworked SELinux hook implementations and include/Kbuild behavior must be audited, not assumed identical |
| `kernel/selinux/sepolicy.c` | New `CONFIG_KSU_SUSFS`-guarded calls to `susfs_add_sus_avd_allowed_by_type()` and `susfs_add_sus_type()`, plus RCU-based policy symbol handling | **Potential undefined-reference/link or semantic risk** unless definitions and compatible behavior exist in the exact locked SUSFS kernel payload |
| `kernel/tools/kernel_compat.mk` and `kernel/compat/kernel_compat.h` | Additional SELinux inode-prototype and audit/compatibility checks | Required header/ABI and Clang17 real-object tests; not guaranteed by old provider success |

Other changes affect manager/ksud, but the rows above are directly relevant to kernel acceptance. The existing successfully pinned BakaSU baseline proves only its own older provider commit.

**Important distinction:** the old adapter changes only kernel patch context, with identical upstream +/- code lines, and is limited to exact source identities. Although the new BakaSU might use the same kernel-side context patch, the **provider source has materially changed**. Adding `2734e0bc...` to `provider_commits` alone would bypass a review requirement and could reveal a later failure when the new BakaSU/SUSFS code is compiled or linked. Neither the API definitions in the exact GitLab SUSFS `756abbf...` checkout nor the new provider's ARM64 objects have been independently inspected in this GitHub-only session. Do not label either as TESTED.

A third-party [upstream-variant build failure example](https://github.com/WildKernels/Samsung_KernelSU_SUSFS/issues/87) reports undefined references to the same two `susfs_add_*` calls in a **different** KernelSU/SUSFS combination. It illustrates a concrete class of compatibility risk; it is **not evidence that this exact BakaSU/SUSFS pair fails to link**.

## Mandatory gates before any targeted adapter change

1. **Verify the exact SUSFS checkout:** using already available verified cache or a small, expressly authorized immutable fetch, inspect `kernel_patches/fs/susfs.c`, related `include/linux/susfs*.h`, full upstream kernel patch and any exported `susfs_add_sus_type`/`susfs_add_sus_avd_allowed_by_type` definitions under `756abbf...`. Record SHA256 and call-site/function-signature compatibility. A version string alone is insufficient.
2. **Verify new BakaSU kernel hooks:** inspect the exact `2734e0bc...` Git tree, `Kconfig`, `Kbuild`, `susfs_compat.mk`, `selinux_hide_susfs.c` and SELinux policy handlers; confirm expected symbols, include path and built-in/inline SUSFS behavior. Never apply official KernelSU-side SUSFS patch twice to BakaSU.
3. **Only if source/API review passes:** consider an **exact** new provider SHA in the current catalog. Keep fixed ACK 6.1 and SUSFS SHA, original/adapted patch digests and unchanged upstream +/- code checks intact. Review the actual selector return value and patch applicability in an isolated disposable GKI checkout.
4. **Negative tests mandatory:** old official and old BakaSU selection still pass; unknown/newer provider and wrong kernel/SUSFS HEAD return original rather than silent adapter selection; changed upstream patch hash, adapted patch hash or changed +/- lines abort; conflict/rollback and clean source protection remain intact.
5. **Real Linux source acceptance (separate):** pin and record the exact new BakaSU/SUSFS/kernel Commit triplet, final `.config`, CFI/KCFI/Shadow Call Stack, relevant ARM64 objects and relocatable link. Report new SELinux/SUSFS symbols and any compiler/link diagnostics. Only after success can the specific combo be `TESTED`; a unit test or `git apply --check` is not enough. Prefer **one targeted combination**, not automatic rerun of all 8 matrix jobs or a 35-project SM8750 sync.

Current `scripts/validate_upstreams.py` supports old `--pinned-baseline` or moving latest branch, **not arbitrary exact new provider SHA as a CLI argument**. A reproducible targeted test must add a safely reviewed explicit-Commit override or use a disposable exact-ref fixture without silently changing permanent defaults. Do not make a `latest` rerun pass/fail stand in for `2734e0bc...` if upstream has moved.

## Handoff and stage decision

**Completed here:** exact commit and file-diff audit, failure classification, safe selector diagnosis and a narrowly scoped verification plan. **Not completed:** current SUSFS API proof, new BakaSU compile/link/boot, new adapter approval or CI retest. Existing Stage 5 source sync 35/35 is still `TESTED`, and the prior Kleaf feasibility report is `STATIC_AUDITED`. Overall Stage 5 stays **IN_PROGRESS**.

**Local Codex parallel task (previously assigned):** inspect existing WSL/test/cache readiness and available exact source refs **read-only**, then supply the function/API, signature, headers and SHA report if those bytes are available; no source mutation or download without a separate resource decision. Once an adapter is approved and committed on `stage1/initial-foundation`, Codex performs the distinct lightweight local regression after matching new remote HEAD/Tree. Real generic GKI compilation is a separate explicitly controlled CI gate; full OnePlus 13 OKI build, ABI, firmware and boot remain deferred/unverified.

No modifications to `main`, PR merge, toolchain caches, lock files, WSL sources, runner jobs or device images were made by this audit.
