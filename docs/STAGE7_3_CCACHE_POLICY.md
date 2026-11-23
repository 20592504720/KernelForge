# Stage 7.3: protected compiler-output caching (ccache)

Status: GITHUB_SCOPED_COMPLETE_WITH_LOCAL_CCACHE_RUNTIME_PENDING.

## Scope distinction

KernelForge ToolchainManager holds source archives and verified toolchain
installations. The new build_cache.py handles a DIFFERENT storage layer:
ccache COMPILER OUTPUTS. Bazel/Kleaf repository and output caches are not
configured here. No download, real ccache binary, kernel build or WSL2
source alteration is part of this stage.

## Immutable cache identity

The domain-separated versioned SHA256 namespace includes:

- device ID, kernel family, build mode and target architecture
- real kernel Git HEAD Commit and original repository
- locked Manifest digest, or explicitly separated generic NO_VENDOR_MANIFEST
  fingerprint (not a fake OnePlus 35-project proof)
- hash of actual selected CC executable bytes and checked compiler version
- Root provider/commit, SUSFS activation/commit
- patch-lock fingerprint, final .config file SHA256
- adapter command/target/build settings and effective non-CCACHE environment
  fingerprint

A different compiler, source, Root, SUSFS, patch, final config, build setting
or environment cannot silently acquire the previous namespace. Missing or
non-immutable values fail closed. Root and SUSFS identities must be consistent.

## Storage and failure safety

- Versioned ownership marker; refuse symlinked lock/lease/namespace paths,
  unknown nonempty roots, polluted metadata and source/output/toolchain overlap.
- Portable FileLock serializes namespace admission, with individual use
  leases; concurrent same-identity builds can have independent leases.
- Safe removal is EXPLICIT ONLY and dry_run by default. Active OR stale
  ambiguous lease blocks removal. No automatic cache clearing and no
  touching existing user-owned caches or WSL2 source.
- Failed/changed builds mark their namespace invalid; it cannot be reopened
  without a separate manual review and safely authorized cleanup.
- Build-scoped env sets CCACHE_DIR, CCACHE_MAXSIZE and
  CCACHE_COMPILERCHECK=content, strips ambient CCACHE_* overrides, never
  mutates the calling process environment.
- Max-size is a ccache application eviction TARGET, not a hard limit on
  physical disk. E: host actual free bytes and inode/resource checks must
  be implemented in the real build admission.
- Cache hits and time savings are UNTESTED. CCACHE_DIR alone does not wrap
  Clang, nor bypass Bazel sandboxing; compiler interception must be
  separately verified in Stage 7.4/7.5.

## Build integration

The schema adds optional build.ccache, omitted/disabled by default.
An enabled config requires exact pinned Git source SHA (no moving refs),
a completed managed toolchain with tested version and measured executable
SHA256, a preexisting final .config and immutable Root/SUSFS locks if
enabled. When the build finishes, compiler and .config bytes are rehashed.
A mismatch blocks acceptance and quarantines the namespace.

This stage currently BLOCKS all device-profile cache activation, including
OnePlus 13 PJZ110, pending Stage 7.4 source/OKI/Manifest admission. Generic
isolated GKI fixture builds may exercise the safe environment overlay but
do NOT prove real compiler caching. No GKI/OKI production build is launched.

## Stage 7.1/7.2 constraints retained

WSL2 audit previously found ccache absent on PATH; existing local Clang
r510928, LLD and other prebuilts are kept unchanged. Physical E: free was
about 184.4 GiB, WSL2 RAM about 3.77 GiB and swap 1 GiB at last sample.
Clang bundle redistribution remains BLOCKED_NO_VERIFIED_RELEASE. OnePlus13
DFR external include, full OKI, ABI/KMI, boot and runtime remain UNTESTED.

Stage 7.3 is software-only until Windows/Linux x Python 3.11/3.12 dedicated
offline fixture test and full Validate passes. Local WSL2 readiness is a
separate read-only Codex handoff in docs/STAGE7_3_LOCAL_CODEX_HANDOFF.md.
PR #1 remains open; main and 35 pinned project source files unchanged.

## Cloud CI acceptance — fixed Stage 7.3 source

Acceptance source Commit: 3b763168f4eb6d4ef4dc7b124a192e3c80b9f691.
The following tests all completed successfully:

| CI gate | Run | Result |
| --- | --- | --- |
| 7.3 dedicated Push | https://github.com/20592504720/KernelForge/actions/runs/45222983286 | 4/4, 29 tests per job |
| 7.3 dedicated PR | https://github.com/20592504720/KernelForge/actions/runs/45223004594 | 4/4, 29 tests per job |
| Full Validate Push | https://github.com/20592504720/KernelForge/actions/runs/45222983051 | 4/4, 367 tests per job |
| Full Validate PR | https://github.com/20592504720/KernelForge/actions/runs/45223004312 | 4/4, 367 tests per job |
| SM8750 Manifest | https://github.com/20592504720/KernelForge/actions/runs/45223004355 | Manifest audit success; locked-sync skipped by design |

TOTAL: 232 dedicated cache-test executions and 2,936 full-repository
test executions, zero failures/errors. All source-lock, ToolchainManager,
legacy and new fixtures are retained. Windows path/canonicalization
failure in intermediate CI was corrected; an internal test call was
updated to include its new effective-environment argument, with final
Windows and Linux matrices all green. Earlier failed runs do not count
toward the accepted evidence.

This scoped acceptance verifies software cache identity/namespace
safety and generic fixture build-engine integration. It DOES NOT prove
real ccache installed, compiler interception by Bazel/Kleaf, any cache
hit rate, physical disk quotas or OnePlus13 real OKI build success.

Required next action: docs/STAGE7_3_LOCAL_CODEX_HANDOFF.md. The local
report should be scoped read-only or disposable fixtures, and cannot
clear OnePlus device-cache, DFR, archive/license or boot blockers.

## Final test accounting and additional path-hardening

At final security commit 3b763168f4eb6d4ef4dc7b124a192e3c80b9f691,
the namespace inspector, lease invalidator and manual prune were tightened
to reject symlinks in ALL namespace-parent path components. A dedicated
negative test proves explicit prune never deletes through such a symlink.

The full 8-env suite reported 2,936 test cases across 8 runs. There were
148 normal Windows POSIX-only skips (37 in each of four Windows runs),
so 2,788 non-skipped test executions, zero errors/failures. Dedicated
Stage 7.3 suites reported 232 cases across 8 runs with zero failures.
These are CI/unit/fixture checks, not actual ccache throughput data.
