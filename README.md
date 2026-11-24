# KernelForge

KernelForge is a modular framework for reproducible Android Linux kernel builds. Toolchain acquisition is profile-driven and verifies archives before installation; kernel compatibility claims still require source inspection and build evidence.

## Goals and scope

The platform covers source pinning, distinct GKI and Vendor adapters, managed toolchains, reviewed patch manifests, Kconfig compatibility, device profiles, build reports, and validated artifacts. The current build engine can prepare local or configured LLVM/GCC toolchains and pass their environment to either adapter. The exact Android GKI 6.1 baseline completed historical Image builds; no SM8750 device kernel or boot has been validated.

## Kernel families and planned integrations

Configuration profiles exist for Linux 5.10, 5.15, 6.1, 6.6, and 6.12. Profiles are scaffolding, not evidence that a particular patch, feature, or toolchain works on that kernel.

GKI and Vendor have separate build adapters; actual build success depends on a reviewed source/config/toolchain combination. Official KernelSU and BakaSU have source integration paths. SUSFS has an exact-baseline GKI adapter with historical real-source and Image evidence. KernelSU-Next and ReSukiSU remain unimplemented. TCP and ZRAM source/config inspection is available; algorithm compilation and runtime behavior are not inferred from inspection.

## Repository map

- `configs/`: global defaults and kernel-family inputs.
- `schemas/`: strict JSON Schema contracts.
- `patches/`: versioned manifests and a narrowly scoped SUSFS compatibility patch; optional generic patch series are disabled by default.
- `devices/`: separate OnePlus 13 official-source and Ace 6 community-reference Profiles; neither is cleared for flashing.
- `kernelforge/`: CLI, build and source modules, plus the standalone `toolchains/` manager, downloader, safe archive extraction, and portable locks.
- `scripts/`: compatibility wrapper for the validator.
- `tests/`: unit and negative tests.
- `.github/workflows/`: lightweight validation CI, scheduled/manual real-source checks, scheduled/manual SM8750 manifest audit, preflight build entry and guarded release placeholder.
- `docs/`: architecture, configuration, development, roadmap, and status.

## Configuration

JSON files are validated against Draft 2020-12 schemas. Toolchain defaults are in `configs/toolchains/defaults.json`; each GKI or Vendor adapter may provide its own `toolchain_profile` in a build config. Profiles specify the executable layout, version constraints, target architecture, and either a local path or a URL plus a trusted SHA256 and archive format. Unknown keys fail validation to catch mistakes early.

## Local requirements and commands

The reviewed development dependency lock supports x86-64 Linux/WSL2 and Windows with CPython 3.11 or 3.12. Other Python/host combinations require a separately reviewed wheel hash lock. Install development dependencies and run commands from the repository root:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m kernelforge validate
python3 -m kernelforge validate-config
python3 -m kernelforge validate-patches
python3 -m kernelforge doctor
python3 -m unittest discover -s tests -v
```

`doctor` reports local Python and dependency availability. A configured build uses `python -m kernelforge build --config path/to/build.json`; each adapter can supply its own toolchain profile. Commands execute as argv arrays without a shell. Source commit, toolchain integrity and provenance, elapsed time, logs, and hashes for files actually produced are written to the output directory. Downloads require a configured SHA256; absent checksums fail before network access.

Use `python -m kernelforge inspect-features --source /path/to/kernel --config /path/to/.config` to obtain source, Kconfig and final-config evidence for TCP and ZRAM. Compilation and runtime remain separate checks. Optional generic patches may use pinned or moving upstream references; each build writes `patches.lock.json` with the resolved Commit and SHA256 before touching kernel source. See [Stage 5 patch series](docs/STAGE5_PATCH_SERIES.md) and [Stage 5 evidence](docs/STAGE5_REPORT.md).

Toolchain manager modes are:

- `AUTO`: use an explicitly configured local toolchain first, then a valid cache, then download and verify when needed.
- `LOCAL_ONLY`: use an explicitly configured local toolchain or verified cache; never access the network.
- `DOWNLOAD_ONLY`: ignore local/system-discovered tools and resolve only from a profile-defined download source or its matching verified cache.

Use `python -m kernelforge toolchain list --cache-dir .cache/toolchains` to inspect cached versions and validity. Use `python -m kernelforge toolchain clean --cache-dir .cache/toolchains [--kind llvm|gcc] [--name NAME] [--version VERSION] [--damaged-only]` to remove selected cache entries. Active build leases are retained.

## GitHub Actions

`validate.yml` runs structural checks and tests on pushes and pull requests. Real-source checks run on a schedule or by manual dispatch; full Image compilation requires an explicit manual option. `build.yml` remains a preflight-only manual workflow until a reviewed build profile exists. Local configured builds are available through the CLI. `release.yml` is a disabled gate.

## Status

- **IMPLEMENTED:** JSON/schema validation, patch-manifest structure/hash validation, source ref checkout with resolved SHA recording, independent GKI/Vendor plans, local and managed LLVM/GCC profile preparation, secure downloads, mandatory archive SHA256 verification, safe extraction, atomic cache installation, cache metadata/maintenance, portable locks, isolated toolchain environments, timeout/log/failure reports and real artifact hashing.
- **TESTED:** local HTTP download and interruption handling, SHA256 success/failure, zip/tar extraction and traversal rejection, cache corruption and reuse, concurrent requests, mode behavior, GKI/Vendor environment delivery, failure reports, plus existing regression suite (see `docs/STATUS.md`).
- **IMPLEMENTED:** generic patch locking and transactional text application; SUSFS exact-baseline integration; TCP/ZRAM source inspection; device Profile isolation and official manifest mapping audit.
- **TESTED:** patch transactions on fixture Git repositories, historical GKI 6.1 SUSFS object/Image builds, official OnePlus 13 manifest mapping, and local feature-inspection fixtures. See `docs/STAGE5_REPORT.md` for limits.
- **UNTESTED:** current Stage 5 generic patches on a real GKI tree, SM8750 Image/module ABI, device boot, Root and SUSFS runtime.
- **PLACEHOLDER:** preflight-only build and disabled Release workflow.
- **NOT_IMPLEMENTED:** BBG, Unicode and Fengchi integration, OnePlus 13/Ace 6 flashable kernels, KernelSU-Next and ReSukiSU.

See `docs/ROADMAP.md` for sequencing and evidence requirements.

Stage 4 adds opt-in shared KernelSU integration with pinned official v0.9.5 and BakaSU providers. Source integration is IMPLEMENTED and fixture TESTED; kernel compilation/boot remain UNTESTED. See [KernelSU providers](docs/KERNELSU.md).

Stage 4.5 adds opt-in development tracking, immutable build locks, modern Kbuild policies and narrow SUSFS transactions. See [development tracking](docs/DEVELOPMENT_TRACKING.md) for configuration, real-source validation and limits.


Stage 4.6 adds portable workspace paths and an exact-baseline SUSFS context adapter. See [workspace migration](docs/WORKSPACE_MIGRATION.md) and [SUSFS compatibility](docs/SUSFS_COMPATIBILITY.md). Real object compilation is validated separately by the Linux upstream workflow; source integration alone is not compilation, boot or Root acceptance.
