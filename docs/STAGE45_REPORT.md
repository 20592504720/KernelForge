# Stage 4.5 delivery — 2026-11-21

## Result

Dynamic tracking, immutable locks, modern KernelSU source policies and narrow SUSFS transactions are implemented. Full Stage 4.5 acceptance is **not achieved**: the current SUSFS development patch conflicts with the current Android GKI source. No fallback or conflict suppression was used.

| Capability | State and evidence |
| --- | --- |
| pinned / latest_release / latest_prerelease / latest_branch | IMPLEMENTED; release selection/API failures fixture TESTED; actual main ref discovery TESTED |
| One resolution per build and locked Commit checkout | IMPLEMENTED / TESTED; recorded branch, SHA, time, method and patch hashes |
| Official modern Kbuild policy | IMPLEMENTED; actual source integration and final Kconfig TESTED; experimental built-in mode, not DDK/LKM delivery |
| BakaSU main policy | IMPLEMENTED; actual source integration and final Kconfig TESTED |
| SUSFS discovery by Android GKI identity | IMPLEMENTED / TESTED on real upstream android14-6.1-dev; other mapped branches discovered but not integration-tested |
| SUSFS patch/copy, duplicate protection, conflict checks and rollback | IMPLEMENTED; fixture TESTED; current real combination FAILS applicability |
| Real ARM64 GKI Kconfig / Kbuild | Without SUSFS: TESTED gki_defconfig, olddefconfig, final symbols, make prepare and Kbuild dry-run |
| Full kernel / KernelSU object compilation, boot and Root operation | UNTESTED |
| Official DDK/LKM packaging and complete general patch manager | NOT_IMPLEMENTED |

## Real locked upstreams

These are observed results, not permanent defaults. The development profiles resolve again on each new build.

- Official main: `2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4`.
- BakaSU main: `7b65bde0710b5e7c6f755545cb15a4abd417f3a8`.
- SUSFS gki-android14-6.1-dev: `756abbf2d81557e36664fc67dffaee26d3dfc57c`, SUSFS_VERSION v2.4.0.
- AOSP mirror android14-6.1: `498f91c17b0822a09aede17d26a63bf8c6813725`, Linux 6.1.155.

The real SUSFS check rejects hunks in `fs/exec.c` and `fs/namespace.c` on that kernel. This rejects the complete selected combination; it does not establish that BakaSU and SUSFS are universally incompatible. BakaSU's KSU-side SUSFS feature presence is recognized, and the official KSU patch is skipped for it. No partial real SUSFS integration is reported as supported.

The validation host is pinned to Ubuntu 22.04 because ubuntu-latest's newer libc/compiler exposed an ACK 6.1 host libbpf const-qualification error. Target sources remained the latest resolved revisions. No target kernel source warning or patch error was disabled. Windows local GKI checkout fails on the reserved path include/soc/arc/aux.h and cannot run final Kconfig/Kbuild here.

## Checks

- Full Ubuntu/Windows × Python 3.11/3.12 regression CI: 120 tests per matrix item, including all previous tests and 21 new development-source tests. [Regression run](https://github.com/20592504720/KernelForge/actions/runs/44892898333).
- [Real-source run with pinned compatible host](https://github.com/20592504720/KernelForge/actions/runs/44892768233): official and BakaSU without SUSFS passed; both SUSFS combinations failed before mutation on kernel patch conflicts.
- [Latest real-source run](https://github.com/20592504720/KernelForge/actions/runs/44892898391) repeats the matrix after the nested-directory patch regression fix; its per-job logs are the authoritative result.
- Python compilation, schema/config validation, YAML parsing and diff whitespace checks passed.

New tests cover branch discovery once, immutable freeze, pinned drift, missing branches, network/API failure, stable/prerelease separation, annotated tags, Android GKI mapping, failure lock writing, real fixture patch application, duplicate and partial integration, hashes, conflicts, mid-transaction rollback, BakaSU code presence, nested Git trees, changed official layouts and final-check failure blocking.

## Files

New modules: kernelforge/versions.py, development.py, providers.py and susfs.py. Existing build.py, kernelsu.py, source.py and build.schema.json are extended. New configs are bakasu-development.json and official-development.json. New validation script/workflow are scripts/validate_upstreams.py and .github/workflows/upstream-validation.yml. New tests live in tests/test_development.py; the existing KernelSU fixture now preserves exact committed bytes on Windows. README, STATUS and DEVELOPMENT_TRACKING document the changes.

## Reproduce and continue

Use the recorded versions.lock.json and configuration to select pinned Commit inputs explicitly. See DEVELOPMENT_TRACKING.md for replay instructions. Old stable and pinned configs remain available. Failed development combinations never select a previous successful build automatically.

The next required work is a reviewed adaptation of the SUSFS patch to this precise Android GKI base, followed by real final Kconfig/Kbuild/object compilation. That patch adaptation is not silently guessed or expanded into a general Stage 5 patch system here. Other Android GKI families, full DDK/LKM delivery and device validation still require separate evidence.
