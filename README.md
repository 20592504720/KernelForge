# KernelForge

KernelForge is a modular framework for reproducible Android Linux kernel builds. Toolchain acquisition is profile-driven and verifies archives before installation; kernel compatibility claims still require source inspection and build evidence.

## Goals and scope

The platform covers source pinning, distinct GKI and Vendor adapters, managed toolchains, reviewed patch manifests, Kconfig compatibility, device profiles, build reports, and validated artifacts. The current build engine can prepare local or configured LLVM/GCC toolchains and pass their environment to either adapter. It does not claim a real Android kernel build has succeeded.

## Kernel families and planned integrations

Configuration profiles exist for Linux 5.10, 5.15, 6.1, 6.6, and 6.12. Profiles are scaffolding, not evidence that a particular patch, feature, or toolchain works on that kernel.

GKI support is planned for Kleaf/Bazel and legacy build systems through separate adapters. Vendor builds will use device-specific source, defconfig, toolchain, commands, and artifact paths. Pinned official legacy KernelSU and BakaSU source integration is available. KernelSU-Next, ReSukiSU, SUSFS, TCP congestion options and ZRAM remain future integrations.

## Repository map

- `configs/`: global defaults and kernel-family inputs.
- `schemas/`: strict JSON Schema contracts.
- `patches/`: versioned manifests; enabled patch set is currently empty.
- `devices/`: device profile location; no unverified PJZ110 values are asserted.
- `kernelforge/`: CLI, build and source modules, plus the standalone `toolchains/` manager, downloader, safe archive extraction, and portable locks.
- `scripts/`: compatibility wrapper for the validator.
- `tests/`: unit and negative tests.
- `.github/workflows/`: validation CI, preflight-only manual build workflow, and guarded release placeholder.
- `docs/`: architecture, configuration, development, roadmap, and status.

## Configuration

JSON files are validated against Draft 2020-12 schemas. Toolchain defaults are in `configs/toolchains/defaults.json`; each GKI or Vendor adapter may provide its own `toolchain_profile` in a build config. Profiles specify the executable layout, version constraints, target architecture, and either a local path or a URL plus a trusted SHA256 and archive format. Unknown keys fail validation to catch mistakes early.

## Local requirements and commands

Python 3.11 or newer. Install development dependencies and run commands from the repository root:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m kernelforge validate
python3 -m kernelforge validate-config
python3 -m kernelforge validate-patches
python3 -m kernelforge doctor
python3 -m unittest discover -s tests -v
```

`doctor` reports local Python and dependency availability. A configured build uses `python -m kernelforge build --config path/to/build.json`; each adapter can supply its own toolchain profile. Commands execute as argv arrays without a shell. Source commit, toolchain integrity and provenance, elapsed time, logs, and hashes for files actually produced are written to the output directory. Downloads require a configured SHA256; absent checksums fail before network access.

Toolchain manager modes are:

- `AUTO`: use an explicitly configured local toolchain first, then a valid cache, then download and verify when needed.
- `LOCAL_ONLY`: use an explicitly configured local toolchain or verified cache; never access the network.
- `DOWNLOAD_ONLY`: ignore local/system-discovered tools and resolve only from a profile-defined download source or its matching verified cache.

Use `python -m kernelforge toolchain list --cache-dir .cache/toolchains` to inspect cached versions and validity. Use `python -m kernelforge toolchain clean --cache-dir .cache/toolchains [--kind llvm|gcc] [--name NAME] [--version VERSION] [--damaged-only]` to remove selected cache entries. Active build leases are retained.

## GitHub Actions

`validate.yml` runs structural checks and tests on pushes and pull requests. `build.yml` remains an explicit preflight-only manual workflow until a reviewed, checked-in build profile exists. Local configured builds are available through the CLI. `release.yml` is a disabled-by-default gate; it is not a kernel release pipeline.

## Status

- **IMPLEMENTED:** JSON/schema validation, patch-manifest structure/hash validation, source ref checkout with resolved SHA recording, independent GKI/Vendor plans, local and managed LLVM/GCC profile preparation, secure downloads, mandatory archive SHA256 verification, safe extraction, atomic cache installation, cache metadata/maintenance, portable locks, isolated toolchain environments, timeout/log/failure reports and real artifact hashing.
- **TESTED:** local HTTP download and interruption handling, SHA256 success/failure, zip/tar extraction and traversal rejection, cache corruption and reuse, concurrent requests, mode behavior, GKI/Vendor environment delivery, failure reports, plus existing regression suite (see `docs/STATUS.md`).
- **PLACEHOLDER:** kernel build and release workflow entry points; no kernel build occurs.
- **NOT_IMPLEMENTED:** verified upstream-specific GKI/vendor source profiles, SUSFS integration, patch application, device-ready configurations, Android kernel build verification. No real large Clang/GCC distribution was downloaded during automated tests; those tests exercise actual local HTTP and archive handling with fixture payloads.

See `docs/ROADMAP.md` for sequencing and evidence requirements.

Stage 4 adds opt-in shared KernelSU integration with pinned official v0.9.5 and BakaSU providers. Source integration is IMPLEMENTED and fixture TESTED; kernel compilation/boot remain UNTESTED. See [KernelSU providers](docs/KERNELSU.md).

Stage 4.5 adds opt-in development tracking, immutable build locks, modern Kbuild policies and narrow SUSFS transactions. See [development tracking](docs/DEVELOPMENT_TRACKING.md) for configuration, real-source validation and limits.
