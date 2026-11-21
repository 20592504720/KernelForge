# Stage 4.6 exact-baseline SUSFS context adapter

The original android14-6.1 patch fails against the specified GKI baseline in
`fs/exec.c` and `fs/namespace.c`. In exec, its first hunk expects
`#ifndef __GENKSYMS__` and `linux/dma-buf.h`, where GKI has `linux/uaccess.h`
and `asm/mmu_context.h`. The namespace hunk expects `trace/hooks/blk.h`,
which is absent. The remaining upstream logic changes apply without alteration.

`patches/compat/susfs/manifest.json` pins the GKI, SUSFS and two provider commits,
original and adapted patch hashes, target Android identity and Linux version.
The complete adapted patch changes these two contexts and their hunk counts.
Every added/deleted code line remains identical to upstream. The upstream GPL
license is retained. Downloaded upstream patches are never rewritten.

Selection requires all three exact Git HEAD identities. Hash mismatch, altered
code changes or unsafe paths abort integration. A new upstream identity receives
the original upstream patch and normal strict applicability checking; it never
silently receives this old adapter or an old source checkout. The selected
adapter and hash are written into the build lock before application.

The original conflict was reproduced against 27 real GKI Git blobs. The adapted
patch passed `git apply --check`, actual application and reverse checking.
That evidence is **TESTED** for applicability only. It is not compilation or
boot evidence. The local conflict report is
`reports/stage46-conflict-reproduction.json` under the workspace root.

The independent Linux workflow runs official/BakaSU × SUSFS off/on, both with
the exact baseline and with `latest_branch`. Each job locks versions once,
checks real source SHA, integrates, resolves final Kconfig, runs `make prepare`
and `headers_install`, then actually compiles KernelSU and every kernel C file
changed by SUSFS, including `fs/susfs.o`. KSU objects are enumerated from its
actual Kbuild `built-in.a`, rather than assuming a composite `kernelsu.o` exists.
ELF64/ARM64 objects, or LLVM-validated ARM64 bitcode when LTO is enabled, and
their hashes are checked. A relocatable aggregate is linked separately; it does
not establish full vmlinux symbol resolution. No dry run counts as compilation.
Complete logs, configuration and locks are uploaded even on failure.

The current runner uses Ubuntu 24.04, Clang/LLVM 17 and GNU host compiler 11.
It first probes KCFI support and requires the hardening symbols explicitly
requested by the real GKI defconfig (including CFI_CLANG and SHADOW_CALL_STACK)
to survive final Kconfig resolution. Earlier Clang 14 smoke runs silently lost
CFI through Kconfig compiler capability detection; their Images/objects are
historical smoke evidence only and do not satisfy hardened GKI acceptance.

`python scripts/validate_upstreams.py --provider bakasu --susfs
--pinned-baseline --workspace <new-Linux-directory>` reproduces the fixed
combination. Omit `--pinned-baseline` to resolve latest branches; use
`--full-kernel` explicitly for an additional Image build (the fixed-baseline CI
jobs request this). Fresh workspaces are
required to avoid reusing partially integrated trees. BakaSU's existing KSU-side
SUSFS implementation is detected and not patched twice. Device boot and Root
remain **UNTESTED**. See the final stage report for actual CI outcomes.
