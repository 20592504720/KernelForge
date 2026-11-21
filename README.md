# KernelForge

KernelForge is a modular foundation for reproducible Android Linux kernel builds. It is being rebuilt in stages, with compatibility claims tied to real source inspection and build evidence.

## Goals and scope

The planned platform covers source pinning, distinct GKI and Vendor adapters, toolchains, KernelSU variants, reviewed patch manifests, Kconfig compatibility, device profiles, build reports, and validated artifacts. **Stage 1 provides configuration validation and CI scaffolding; it does not compile a kernel.**

## Kernel families and planned integrations

Configuration profiles exist for Linux 5.10, 5.15, 6.1, 6.6, and 6.12. Profiles are scaffolding, not evidence that a particular patch, feature, or toolchain works on that kernel.

GKI support is planned for Kleaf/Bazel and legacy build systems through separate adapters. Vendor builds will use device-specific source, defconfig, toolchain, commands, and artifact paths. KernelSU Official, KernelSU-Next, ReSukiSU, SUSFS, TCP congestion options, and ZRAM algorithms are future integrations and are not yet installed or compatibility-tested.

## Repository map

- `configs/`: global defaults and kernel-family inputs.
- `schemas/`: strict JSON Schema contracts.
- `patches/`: versioned manifests; enabled patch set is currently empty.
- `devices/`: device profile location; no unverified PJZ110 values are asserted.
- `kernelforge/`: local Python command line entry point and validation modules.
- `scripts/`: compatibility wrapper for the validator.
- `tests/`: unit and negative tests.
- `.github/workflows/`: validation CI, preflight-only manual build workflow, and guarded release placeholder.
- `docs/`: architecture, configuration, development, roadmap, and status.

## Configuration

JSON files are validated against Draft 2020-12 schemas. Intended precedence is global defaults → kernel profile → device profile, with the most specific value winning. Stage 1 validates references and schemas; it does not yet merge build configurations. Unknown keys fail validation to catch mistakes early.

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

`doctor` reports local Python and dependency availability. A configured build uses `python -m kernelforge build --config path/to/build.json`; the profile provides the repository/ref, required tools, adapter-specific argv, environment, and artifact globs. Commands execute as argv arrays without a shell. The resolved source commit, tool versions, elapsed time, logs, and hashes for files actually produced are written to the output directory. No toolchain is downloaded automatically.

## GitHub Actions

`validate.yml` runs structural checks and tests on pushes and pull requests. `build.yml` remains an explicit preflight-only manual workflow until a reviewed, checked-in build profile exists. Local configured builds are available through the CLI. `release.yml` is a disabled-by-default gate; it is not a kernel release pipeline.

## Status

- **IMPLEMENTED:** JSON/schema validation, patch-manifest structure/hash validation, local CLI, source ref checkout with resolved SHA recording, tool version checks, independent configurable GKI/Vendor plans, timeout/log/failure reports and real artifact hashing.
- **TESTED:** positive and negative configuration/manifest tests (see `docs/STATUS.md`).
- **PLACEHOLDER:** kernel build and release workflow entry points; no kernel build occurs.
- **NOT_IMPLEMENTED:** auto-downloaded/cached toolchains, verified upstream-specific GKI or vendor build profiles, KernelSU/SUSFS integration, patch application, device-ready configurations, Android kernel build verification.

See `docs/ROADMAP.md` for sequencing and evidence requirements.
