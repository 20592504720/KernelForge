# Stage 6.3 WSL2 blocker diagnosis

Status: **PARTIAL_TESTED_WITH_BLOCKERS**. This is a read-only audit of the existing pinned OnePlus 13 `sun` Repo workspace. It did not run Bazel, modify a source link, sync a project, compile a kernel, or validate a vendor archive.

## Baseline and evidence

- Development branch: `stage1/initial-foundation`; remote input commit `eb098b3c0549a6ed834d3eccd1c8be3a304004aa` (source tree `09b8402e2cb4e4c36dd1a7d519533cf67b4568e7`). The local documentation commit is reported separately after publication.
- Workspace: `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750` on WSL2 ext4. Source lock and the 35 recorded HEADs were unchanged.
- Machine result: [stage6_3_wsl2_blocker_diagnosis.json](evidence/stage6_3_wsl2_blocker_diagnosis.json). It includes all **29** original link paths, literal target strings, resolved paths, risk grades, all **35** per-project file and mode counts, 35 Commit/Tree SHAs, both Repo linkfiles, and archive fixture outcomes.
- Raw read-only outputs are in `E:\内核构建\reports`: `stage6.3-layout-diagnostics-final.json`, `stage6.3-worktree-hash-audit.json` and `.stderr.log`, `stage6.3-lz4-clean-check.json`, `stage6.3-real-link-archive-fixture-results.json` and `.stderr.log`. Their SHA256 values are in the machine result. The hash audit took 310.936 seconds and returned code **2** because one project failed raw-byte equivalence; it did not silently treat that failure as success. The archive fixture returned **0**.

## A. Missing symlink targets

Every link itself has Git mode `120000` and target bytes matching the pinned Git blob. The missing destination is a separate issue. No missing destination has been repaired.

| Group | Links | Evidence and decision for Linux `sun` |
| --- | ---: | --- |
| `llvm-binutils-stable/*` → `../clang-r522817/bin/*` | 20 | `clang-r522817` is absent from the pinned Clang prebuilt checkout. `msm-kernel/build.config.constants:1` selects `r510928`; `build.config.common:8` uses that versioned directory; Kleaf `versions.bzl` lists `r510928`. The existing `r510928/bin/clang` reports Android Clang 18.0.0. **BLOCKED_UNDETERMINED** for the full build: these shortcuts do not block the statically identified direct compiler path, but Bazel dependency analysis has not proved none is called. |
| Root `build-tools/path/linux-x86/mkdtboimg.py` | 1 | Its `.py` destination is absent, while `prebuilts/kernel-build-tools/linux-x86/bin/mkdtboimg` is a Linux x86-64 ELF executable. `msm_kernel_la.bzl:467,499` enables DTBO for nonempty `sun` DTBO lists. The actual tool label remains unresolved. **BLOCKED_UNDETERMINED**; a DTBO build may need this path. |
| Root `vendor/oplus/kernel/audio/bazel/mtk` | 1 | Missing `../mtk/`; `oplus_modules_define.bzl:10` selects `qcom`, while `audio/bazel/oplus_local_modules.bzl:7` enters MTK dependencies only for `mtk`. **VERIFIED_NOT_REQUIRED** for the audited Linux `sun` qcom configuration; other platforms are outside scope. |
| Root `vendor/oplus/kernel/dfr/soc/oplus/dfr/include` | 1 | `../../include/` resolves to missing `dfr/soc/include`; `dfr/include` exists at a different path. DFR sources include `soc/oplus/dfr/...`, but target reachability and include resolution have not been analyzed by Bazel. **BLOCKED_UNDETERMINED**. |
| Rust Darwin and Windows `stable` shortcuts | 4 | Point to absent `1.77.1.p1/bin` host executables for Darwin/Windows. Current host is Ubuntu Linux x86-64 with glibc 2.39. **VERIFIED_NOT_REQUIRED** for this Linux host only. |
| Rust Linux-musl `stable` shortcuts | 2 | Point to absent `1.77.1.p1/bin/{rust-analyzer,rustfmt}`. The observed host uses glibc, but hermetic Bazel tool resolution is untested. **BLOCKED_UNDETERMINED**. |

Result: **5 VERIFIED_NOT_REQUIRED, 24 BLOCKED_UNDETERMINED, 0 proven BLOCKED_BUILD**. “No proven blocker” does **not** mean the full build is unblocked. Resolve the exact `sun` Bazel dependency graph, especially DTBO, DFR and LLVM tool labels, before changing source or claiming build readiness.

## B. Working-file equivalence

The audit compared pinned Git HEAD/Tree and index entries to each tracked working file with `lstat`, streamed Git-blob SHA-1, executable bits, and raw symlink target bytes. `.git`/`.repo` metadata and mounted child-project paths were excluded from root-project ownership; no root/child tracked-file collision was found. The two Repo linkfiles were checked separately: `kernel_platform/.source_date_epoch_dir` resolves to `common` (directory), and `kernel_platform/build_with_bazel.py` resolves to `msm-kernel/build_with_bazel.py` (regular file).

- **35/35 TESTED** for locked HEAD and Git Tree identity; **216,287** tracked entries examined (215,081 regular files and 1,206 symbolic links), about **10.60 billion** file/target bytes hashed. No tracked file was missing; no executable-bit, link-type, index, or root mount mismatch was observed.
- **34/35 TESTED** for *raw working-file byte* equality. The remaining project, `kernel_platform/external/lz4`, has **33** regular files whose raw bytes differ from their Git blobs. The files are Windows Visual Studio project/resource files. Git attributes include `text` and `eol=crlf`; all 33 match the expected Git blob after Git’s declared clean filter, and `git status --porcelain` is empty. The raw difference is preserved in the report rather than waived. Therefore **35/35 raw byte equivalence is BLOCKED**. No file was rewritten.
- Untracked files and the `.repo` object store were outside this tracked-file content proof. A future build should preserve the pinned checkout’s declared line-ending behavior; do not “fix” the 33 files by modifying the source tree without a separate review.

## C. Archive symlink verifier

Two real locked projects with tracked links were used: `kernel_platform/external/bazel-skylib` (1 link) and `kernel_platform/external/toybox` (6 links). For each, an isolated *local* `git archive` TAR was compared directly against the pinned Git Tree by `archive_link_proof.verify_archive_link_tree`. Both baseline comparisons passed. Altering a link target, regular-file bytes, or an executable bit was rejected in **6/6** negative cases. Archives were read as TAR members; no extraction or actual symlink creation occurred. Both source HEADs remained unchanged.

Status: **TEST_FIXTURE_ONLY**. Independent vendor archive provenance, safe extraction, full OKI build, ABI/KMI, Image generation and device boot are **UNTESTED**. The verifier test does not make these archives eligible build inputs.

## Remaining work

1. Analyze the exact `sun` Kleaf/Bazel graph to classify the 24 uncertain links as actual build blockers or proven unused. Do not alter the pinned source to force resolution.
2. Decide whether Git-clean-equivalent CRLF worktree files satisfy the intended workspace policy; the strict raw-byte result remains 34/35.
3. Keep Stage 6.3 acceptance limited to the proven source identity and read-only comparison scope until those blockers are reviewed. No Stage 7 work was started.
