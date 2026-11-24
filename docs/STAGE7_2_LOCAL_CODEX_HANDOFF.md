# Codex local handoff — Stage 7.2 physical toolchain review

Begin ONLY after GitHub Stage 7.2 CI passes. This is read-only collection.
No Bazel/Bazelisk, Repo sync, source modifications, toolchain download,
installation, GitHub Release creation/upload or kernel compilation.

Workspace: E:\内核构建\project on Windows,
           /mnt/e/内核构建/project from WSL2.
Repo source: /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750
Logs destination: E:\内核构建\reports

Task steps:

1. Read updated branch Stage 7.2 report and release_mirror.py, safely
   reconcile HEAD/Tree without forced reset or altering 35-source lock.
2. Reuse Stage 7.1 realpath + hash evidence. In WSL2, directly execute
   only installed PINNED ELF binaries by absolute path: r510928 clang
   --version, clang -print-target-triple, ld.lld --version,
   llvm-nm --version, and GNU make --version. Optionally direct rustc/java
   versions for inventory. Do not run any Bazel wrapper/Bazelisk even with
   --version; those may download dependencies. Do not invoke builds,
   network scripts, repo sync or compile commands.
3. For each binary record absolute realpath, direct exit code, bounded
   stdout/stderr, SHA256 (reuse prior record if same), host arch, and
   version TESTED/UNTESTED/BLOCKED. Save raw logs only in E: reports.
4. Research whether the existing r510928 source corresponds to a legally
   redistributable, independently SHA256-pinned complete archive and exact
   GitHub Release Asset ID, Release ID and uploader. No large download.
   Separate individual binary SHA256 from whole archive SHA256.
   Without independent evidence set BLOCKED_NO_VERIFIED_RELEASE; recommend
   reusing locally pinned prebuilts instead of mirroring.
5. Recheck physical E: available bytes (50 GiB reserve), WSL RAM/swap
   and cache presence; do not treat virtual ext4 free space as host bytes.
6. Commit files to stage1/initial-foundation:
   docs/STAGE7_2_LOCAL_TOOLCHAIN_REVIEW.md
   docs/evidence/stage7_2_local_toolchain_review.json
   Include source/current Commit/Tree, direct tool results, license and
   archive provenance status, resource constraints and exact outstanding
   blockers. Keep raw log hashes in E: reports. No main changes or PR merge.

Stop at evidence delivery; do not begin Stage 7.3 or a kernel build.
