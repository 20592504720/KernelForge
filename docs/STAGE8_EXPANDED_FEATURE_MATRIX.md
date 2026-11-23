# Stage 8 expanded requirements and deduplication (2026-11-24)

STATUS: PLANNING_RECORDED_ONLY. Not an implementation or authorization for an OEM build, device flash, source sync or cache cleanup.

## Scope and provenance

Keep the established KernelForge targets: Linux families 5.10 through 6.12, independent GKI and vendor/OKI paths, official/third-party KernelSU (particularly BakaSU), SUSFS, Fengchi, TCP BBR/Westwood/BBG, enhanced compression, Unicode zero-width request, reproducible patches/toolchains and official OnePlus13 PJZ110 35-project OKI modules, DTBO, ABI/KMI, firmware and boot.

The screenshots match the feature checklist and Actions UI of the independently operated project https://github.com/cctv18/oppo_oplus_realme_sm8750 . Its statements of implementation, six-minute compilation and green workflow results are reference CLAIMS, not proof that KernelForge or a specific target device can build or boot those changes. The screenshot's legacy manual/kprobes/syscall entry is struck through; the four experimental features below were listed as PENDING. We do not silently promote any of those into existing supported functionality.

Prioritize the pinned OnePlus13 PJZ110 SM8750 official Linux 6.6 source and its matching firmware, compiler, Kleaf targets and vendor modules. OnePlus 13 variants 6.6.30/.66/.89, OnePlus 13T 6.6.56, OnePlus Pad2Pro 6.6.57, and 6.6.118 pictured Actions all require independent exact source/target/firmware evidence. MT6991 OnePlus Ace5 Supreme 6.6.50 is an additional independent SoC platform, not interchangeable with SM8750. A third-party mention of same kernel version does not prove device compatibility.

## Requested feature matrix (de-duplicated)

| ID | Priority | Feature | Scope and current gating |
| --- | --- | --- | --- |
| 01 | P0 | Official PJZ110 OKI and GKI | Full locked 35-project OKI modules, DTB/DTBO, ABI/KMI, firmware, Image, boot. GKI separate; not automatic no-wipe. |
| 02 | P2 | Additional SM8750 kernel variants | 6.6.30 OnePlus13, 6.6.56 OnePlus13T, 6.6.57 Pad2Pro, 6.6.66/6.6.89 OnePlus13, 6.6.118 shown in Actions. Each requires own source and device gate. |
| 03 | P2 | MT6991 OnePlus Ace5 Supreme | Separate MediaTek 6.6.50 source/toolchain/vendor target; not SM8750-compatible by assertion. |
| 04 | P1 | Root providers and SUSFS | Official KernelSU, BakaSU, ReSukiSU, SukiSU Ultra, KernelSU-Next. One pinned provider per build, exact hook/kernel/SUSFS compatibility. |
| 05 | P1 | Hooks | Kprobes, manual, syscall/tracepoint and SUSFS inline checked per upstream commit. Struck-through legacy screenshot item is NOT automatically supported. |
| 06 | P1 | Fengchi governor | Vendor original scx/HMBIRD and its sched modules/KABI; preserve stable OEM scheduling by default. |
| 07 | P2 | ccache-ECS | Stage 7.3 cache policy already exists. Shared preseed and ~6-min claims need trusted byte provenance and comparable cold/warm benchmarks; no automatic user-cache deletion. |
| 08 | P2 | Compiler O2 | Opt-in, measurable optimization with unchanged security flags CFI/KCFI and OEM ABI/KMI. |
| 09 | P1 | Compression and ZRAM | LZ4 1.10.0, zstd 1.5.7 kernel-compatible backports; built-in ZRAM versus zram.ko, actual runtime tests. |
| 10 | P1 | TCP algorithms | Existing BBR/Westwood/BBG plus Brutal; BBG source/meaning to be reviewed. Per-algorithm Kconfig and behavior. |
| 11 | P2 | Netfilter configuration | ipset, iptables, IPv4/IPv6 advanced networking capabilities conditional on vendor kernel and userspace. |
| 12 | P2 | ADIOS I/O | Optional Linux 6.6 block-mq and UFS/OEM driver compatibility tests. |
| 13 | P2 | Droidspaces | Namespaces, seccomp, cgroups, networking, OverlayFS and actual container runtime requirements. |
| 14 | P2 | Mountify | Root/module requirements, source pin and Android-version validation. |
| 15 | P2 | Re:Kernel/Freezer/NoActive | Userspace interfaces, measured power behavior, compatibility and rollback. |
| 16 | P2 | Baseband-guard | Audit partition protection source/license and safe OTA/recovery carve-outs; cannot promise total protection from wipes. |
| 17 | P3 | GKI F2FS data preservation | Experimental no-wipe compatibility study only. Backup and explicit device tests; no data-safety guarantee. |
| 18 | P3 | NetHunter monitor mode | Optional driver/firmware/USB wireless compatibility, not asserted on built-in WiFi. |
| 19 | P3 | kexec | Secure boot/signature, SELinux, rollback and physical-device impact study. |
| 20 | P2 | Unicode zero-width request | Preserved, not implemented until source and precise behavior are established. |
| 21 | P0 | Actions/build versions and delivery | Independent pinned Run IDs, source/patch lock, artifact sha, modules and ABI verification. Public release gated in Stage 9. |

Legend: P0 required to assess primary device baseline and safety; P1 important requested integration; P2 opt-in extension; P3 experimental feasibility research, NOT assumed deliverable. All entries are REQUESTED, not automatically IMPLEMENTED. A feature already scaffolded by Stages 1–7 is still unverified on the OnePlus 13 actual OEM build until new evidence exists.

BakaSU's current upstream documentation describes it as formerly ReSukiSU. Do not treat two names as distinct supported provider builds without repository identity, full immutable Commit, verified setup/hook ABI, and SUSFS compatibility. The currently available Official/BakaSU source adapters do not imply SukiSU Ultra or KernelSU-Next support.

The Stage 7.3 ccache output-cache isolation must not be overwritten by a public preseed cache. Public ccache-ECS presets require independently audited source/compiler/patch/config identity, provenance, poisoning controls and explicit authorization. Their advertised ~6 minutes cannot be used as a performance acceptance threshold until comparable cold/warm measurements exist; auto-deleting private caches after inactivity is not authorized.

A GKI F2FS transplant does not establish that encrypted /data can survive a kernel change. Any real trial needs an independently accepted backup/recovery path and physical-device authorization. Baseband/partition guard changes must preserve trusted OTA/recovery paths and must not claim perfect wipe protection.

## Proposed Stage 8 work breakdown

8.1 Device and immutable source/firmware matrix; diagnose DFR external module include in relevant Bazel/Kleaf targets, verify toolchain/build configs and keep SM8750/MT6991 separate.
8.2 Unmodified official OnePlus13 PJZ110 OKI reference build: selected vendor modules, DTB/DTBO, Image and vmlinux, exact compiler/config hashes and ABI/KMI logs. No optional patch additions.
8.3 One-at-a-time Root provider + SUSFS matrices: Official, BakaSU, KernelSU-Next, ReSukiSU and SukiSU Ultra; explicit per-version hook support, rollback and device Root evidence when approved.
8.4 OEM Fengchi scx/HMBIRD scheduling, CPU compiler O2 policy and optional ADIOS IO, with kernel-module/KABI/performance measurements.
8.5 LZ4/zstd/ZRAM and BBR/Westwood/Brutal/BBG + netfilter/ipset/iptables, each an opt-in reviewed patch source with Kconfig/compile/run checks.
8.6 Droidspaces, Mountify, Re:Kernel/Freezer/NoActive, Baseband-guard and the existing Unicode-zero-width request, separately audited for system safety and userland compatibility.
8.7 Experimental optional GKI/F2FS preservation study, NetHunter monitor driver support and kexec with explicit physical-device/security permissions and backup/rollback requirements.
8.8 Expand 6.6 kernel-version/SoC matrix only after the primary PJZ110 OKI baseline passes, including optional MT6991 6.6.50. Do not claim universal cross-device compatibility.
8.9 Full device/stage acceptance: report TESTED, UNTESTED or BLOCKED per feature; verify actual modules, DTBO, ABI/KMI, firmware/boot, Root/SUSFS, schedulers and artifacts where allowed. Stage 9 still controls guarded Release publication.

## Non-negotiable admission contract

Every optional change needs a traceable source URL, pinned Commit, license review, patch SHA256, applicability to an exact kernel/device/version, source/config diff, compilable patch sequence, build artifacts, rollback and device runtime evidence where required.

Do NOT disable CFI/KCFI, remove mandatory OEM modules, silently replace original patches, modify main/merge PR #1, alter previously verified 35-project source locks, auto-install external compilers, run unsafe download scripts, flash, or publish kernel packages based only on screenshot project claims. Full Image success alone does not prove ABI, boot, encrypted data survival or performance.

Acceptance is layered: PRIMARY_ONEPLUS13_OFFICIAL_OKI_VERIFIED requires its real build/modules/ABI evidence. ALL_REQUESTED_FEATURES_VERIFIED requires separate results for each selected optional and experimental item; blocked items remain visible instead of being silently removed. This documentation change does not start Stage 8.

Reference links:
- https://github.com/cctv18/oppo_oplus_realme_sm8750
- https://github.com/Baka-SU/BakaSU/blob/main/docs/zh/README.md
- https://www.droidspaces.org/docs/kernel-configuration.html
- docs/ROADMAP.md
- devices/profiles/oneplus13-pjz110.json
- docs/STAGE7_3_CCACHE_POLICY.md
