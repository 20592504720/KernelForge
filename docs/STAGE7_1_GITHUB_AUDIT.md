# Stage 7.1 — GitHub and WSL2 read-only toolchain/fast-build preflight

**Stage 7.1 GitHub scope: TESTED; WSL2 local inventory PENDING.**
This document is a precise inventory, not permission to run Bazel, download
toolchains, sync Repo or compile OnePlus 13. Stage 1–6 scoped full acceptance
is separately supported by [Run 45184293290](https://github.com/20592504720/KernelForge/actions/runs/45184293290).

## What was audited

1. `ToolchainManager`: LLVM/GCC only; local/CACHE/download modes, SHA256
   mandatory for downloads, archive/tree integrity on cache reuse, atomic
   publication/rollback, version/architecture and cross-compile checks, locks
   and leases. These code paths have prior isolated-fixture tests. Stage 7.1
   statically verifies the reviewed methods and safety configuration were not
   removed; that is not a real upstream toolchain download.
2. The `llvm-release` and `gcc-release` source-type names currently
   resolve via generic `ArchiveSourceAdapter`. They are **not** yet a
   GitHub Release asset-identity/provenance contract: publisher/release asset,
   immutable digest binding, license and mirror fallback require 7.2.
3. Official PJZ110 profile: kernel family 6.6 / SoC SM8750 / fixed 35-project
   Manifest. Its `toolchain`, `firmware_build`, `abi_kmi` and
   `kernel_commit` fields still lack a complete fast-build admission record.
   A locked Repo source tree is not by itself a buildable OnePlus13 Image.
4. `.github/workflows/build.yml` is a **preflight-only placeholder**.
   `.github/workflows/release.yml` is disabled. The existing Stage 1–6
   one-shot workflow is historical verified ACK 6.1 evidence; it is not
   a OnePlus 13 Linux 6.6 fast-build workflow.
5. Toolchain archive cache is tested. Shared ccache build-output isolation by
   device, lock, exact compiler hash, KSU/SUSFS Commit, patch/config identity
   is **not yet implemented**; it belongs to 7.3. Do not confuse the valid
   toolchain-package cache identity with a safe shared compiler-output key.

## Read-only audit interface

```bash
python3 scripts/stage7_1_preflight.py
```

The program uses Python stdlib only, emits JSON to stdout, does **not**
execute Bazel/Bazelisk/Git/compiler/ccache or any downloader, and does not
write source, metadata, caches, config or artifacts. An optional existing
workspace enables OS filesystem and PATH-only inventory:

```bash
python3 scripts/stage7_1_preflight.py \
  --workspace /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750 \
  --host-path /mnt/e
```

It checks available disk bytes/inodes (via OS stat calls), physical memory
metadata and tool PATH entries. PATH presence **does not prove** a tool is
installed in the correct version, matches a pinned hash or runs successfully.
No Bazelisk `--version` is run: it may trigger a download. The report
explicitly records `source_identity=NOT_RECHECKED`.

## Deferrals / implementation gates

- **7.1 local WSL2 Codex evidence:** path and mount, actual tool locations,
  Clang/Bazel wrapper identity, ext4 and host E:/F: free physical bytes and
  inodes, RAM, existing cache and direct binary SHA256 (where reasonably
  bounded), without creating Bazel output, downloading or rewriting sources.
- **7.2** reviewed Release mirror origin/asset identity, checksum, license,
  fallback and real archive layout.
- **7.3** ccache keys and isolation across device/version/provider/SUSFS.
- **7.4** manual-only fast build Actions with resources and artifact controls.
- **7.5** actual pinned OnePlus13 6.6 Image/vmlinux fast build evidence.
- **Stage 8** full 35-project OKI modules/DTBO/ABI/KMI and device evidence.

GitHub-hosted runners have a **6-hour per-job execution limit** (GitHub
Actions limits as checked 2026-11-23), so 'no time limit' is not a
property of the hosted CI service. No paid runner may be used without
explicit approval.

## Safety boundary

Never mutate `main`, merge PR #1, change locked 35 Git SHAs, re-sync Repo,
add unverified third-party patched toolchains, execute remote shell scripts,
clear caches or publish flashable artifacts during Stage 7.1.

## Actual GitHub execution evidence — 2026-11-23

Commit `c277a2cafdc27392fd1c2b402d80f0796d34c269`, source tree `c3813eb3e4c7d3c13ff32c12d090f909882a57c4`:

| Check | Run | Evidence |
| --- | --- | --- |
| Preflight Push | [#45203492610](https://github.com/20592504720/KernelForge/actions/runs/45203492610) | successful, dedicated 12/12 negative/read-only tests |
| Preflight PR | [#45203510015](https://github.com/20592504720/KernelForge/actions/runs/45203510015) | successful, same 12/12 |
| Full Push Validate | [#45203492346](https://github.com/20592504720/KernelForge/actions/runs/45203492346) | 4/4 success; 316 tests per environment |
| Full PR Validate | [#45203509981](https://github.com/20592504720/KernelForge/actions/runs/45203509981) | 4/4 success; 316 tests per environment |
| SM8750 source audit | [#45203510069](https://github.com/20592504720/KernelForge/actions/runs/45203510069) | manifest audit passed; separate heavy locked-sync job **SKIPPED by design** |

Cloud inventory Artifact ID `14831289327` is valid JSON; result
`REPOSITORY_PREFLIGHT_TESTED_WITH_BLOCKERS`. Verified field values:
fixed source projects 35; OnePlus 13 toolchain and firmware pins missing,
fast-build workflow not implemented, GitHub Release provenance not implemented,
ccache isolation not implemented, stage-7 full OnePlus13 build untested.

**Scope decision:** GitHub-only Stage 7.1 is ACCEPTED. Stage 7.1 as a whole
awaits the explicit read-only WSL2 Codex report, not another cloud build or
a second full Repo sync. No Stage 7.2 work or toolchain downloads were started.
