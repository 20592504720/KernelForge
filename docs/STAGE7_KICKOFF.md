# Stage 7 kickoff: fast real-build infrastructure and toolchain reproducibility

**Status: STARTED — 7.1 READ-ONLY PREFLIGHT ONLY.** Entry is authorized by Stage 1–6 scoped full acceptance [Run #45184293290](https://github.com/20592504720/KernelForge/actions/runs/45184293290) and independent artifact review.

Stage 7.1 (GitHub-side owner): inventory `ToolchainManager` pinned URLs/SHA256 and support for LLVM/GCC, isolate independent GKI/vendor workspaces and ccache keys, examine existing Actions fast-build triggers, enforce explicit approvals for resource-consuming builds, and prepare CI negative tests that reject untrusted archives, mutable releases and cross-device reuse. No toolchain download or build is automatically launched by this kickoff.

Stage 7.1 (local Codex if needed): only after a specific handoff, read-only report of existing WSL2 `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`, `bazel --version`, compiler path, ccache availability, free ext4/host bytes and inodes, and memory. Preserve original .repo, GKI, cached toolchains and E: evidence. Do not run Bazel queries with network fetching or write caches until review.

Stage 7.2: a controlled, configuration-aware investigation of the DFR include within the Linux `sun_perf_dist` / `sun_consolidate_dist` or OEM module dependency graph. Static evidence alone does not settle OEM module reachability; a bounded no-fetch cquery/aquery may still generate cache and requires a separate environment plan.

Stage 7.3: optional fast pinned generic GKI Image builds with recorded exact toolchain checksums and reproducibility. Stage 8 retains full OnePlus 13 35-project OKI/modules/DTBO/ABI/KMI and physical device gates.

Never auto-merge PR #1, touch `main`, rewrite 35 source locks or invoke device release.
