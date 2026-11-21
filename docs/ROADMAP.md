# Roadmap

1. **Foundation:** schemas, local validator, manifests, tests, and CI.
2. **Build engine:** pinned source checkout, separate GKI/Vendor plans, logging and reproducible reports.
3. **Toolchain manager — implemented:** profile-driven LLVM/GCC provisioning, mandatory SHA256 checks for downloads and cache reuse, safe installation, cache maintenance and isolated GKI/Vendor build environment integration. Real upstream toolchain layouts and Android kernel builds remain unverified.
4. **KernelSU:** individually researched adapters for Official, Next, and ReSukiSU.
5. **Patch manager:** ordering, conflict/check/apply/rollback, hashes, reports.
6. **Features:** source/Kconfig-based SUSFS, networking, ZRAM, optimization checks. Unidentified BBG/Unicode/Fengchi items remain unimplemented until their sources are confirmed.
7. **Devices and delivery:** verified profiles, real builds, artifact manifests, packaging, guarded releases.

Directories and configuration keys alone do not imply later-stage capability.
