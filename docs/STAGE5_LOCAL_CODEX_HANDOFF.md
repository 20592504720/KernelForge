# KernelForge Stage 5 — local Codex handoff (read-only)

This task complements [STAGE5_EVIDENCE_RECONCILIATION.md](STAGE5_EVIDENCE_RECONCILIATION.md). Complete only the local WSL2 evidence and capacity measurements that a GitHub-only reviewer cannot access. **Do not perform another repo sync, download tools, compile, modify sources, or delete/compact the VHD.** Work within existing E: project and WSL. Keep `main` untouched, PR #1 open, no merge, reset, force-push or branch deletion.

## Entry and invariants

- GitHub development branch: `stage1/initial-foundation`. At handoff source-evidence Commit: `2192361c0be1b1f3e836e9b82d3c59cc398b72f1`. Before any subsequent Git documentation commit, compare local HEAD/Tree and remote HEAD/Tree; remote might have advanced. Reconcile by safe fast-forward/cherry-pick as appropriate without overwriting local changes. Do not assume different Commit SHA means different Tree.
- Windows project checkout: `E:\内核构建\project`; WSL distro: Ubuntu-24.04, ext4 VHD on E:; source workspace: `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`; local reports: `/home/kernelforge/kernelforge/reports/`.
- Preserve E: physical 50 GiB reserve and existing ext4 reserve. Avoid exhaustive scans while git/index-pack is active. Source lock: `manifests/oneplus13-pjz110-sm8750-source.lock.json`. Expected manifest SHA: `f8e50677874c65b6da41057d2f39be7b4ef3c08a`.

## Local tasks (no network/build required)

1. Verify that no `repo sync`, `git fetch`, `git index-pack` or verifier process is still writing. **Read only** the existing successful `oneplus13-pjz110-sm8750-resume.json` and `.log`, plus the initial `oneplus13-pjz110-sm8750-sync.json` and `.log`. Record `status/source_sync`, `matched_projects`, `unmatched_projects`, Manifest SHA, all 35 project identities + locked HEAD SHA matches, resume exit status, timestamps and original first-failure cause. Validate JSON parsing; do not modify report originals. Hash report/log files with SHA256, redacting any accidentally included proxy credentials/tokens from summaries.
2. Measure physical **E:** free space and WSL ext4 free bytes/inodes separately, plus `.repo` object/metadata size, materialized checkout size and relevant subdirectory sizes. Attribute exact per-project bytes where feasible. **Do not double-count** the Manifest root `path="./"` project and nested project paths; report exclusive ownership and overlap uncertainty. Distinguish virtual VHD capacity, physical VHD allocated bytes, and physical E: free-space delta (reported 338.13 GiB → 185.41 GiB, 152.72 GiB consumed). These are not network transfer bytes.
3. Identify the actual prebuilt `clang/host/linux-x86`, `prebuilts/rust`, `prebuilts/clang-tools`, `prebuilts/build-tools` and Bazel/Kleaf-related content from the lock. Report project path, Git Commit, on-disk bytes and verified version/host architecture if safely executable. Do not execute unknown third-party setup scripts. Search **read-only** for official Kleaf/Bazel `sun` targets and capture the exact build target/rule file paths; do not infer that their presence proves a successful build.
4. Save a concise **new** report in `E:\内核构建\reports` (or existing project reports path) with file sizes, disk samples, toolchain inventory, lock+report digests and unresolved items; do not overwrite original logs or JSON. If recording into GitHub handoff docs, safely synchronize the latest remote branch first and modify only newly dated sections. Retain raw diagnostic evidence locally.
5. The separate GKI CI issue (Run 45020470109, job 137201998796) has already been isolated on GitHub: `BakaSU + SUSFS + latest_branch` fails the `50_add_susfs_in_gki-android14-6.1.patch` applicability check at `fs/exec.c` and `fs/namespace.c`. **Do not** try to fix it by patching OnePlus 13 sources; this is a different ACK 6.1 baseline. Leave it documented as INCOMPATIBLE until a targeted upstream comparison and reviewed adapter are ready.

## Deliverable checklist

- Exact successful local JSON and first-failure summary, plus SHA256 of source lock/report/log (where available).
- 35 project verification total and any mismatch count, with clear statuses.
- Per-project size table (exclusive or accompanied by an explicit overlap caveat); `.repo` size; materialized worktree size; compiler/toolchain table.
- E: physical free and ext4 `df -h`/`df -i`, host VHD physical allocation if measurable without mutation, and confidence/limits.
- Bazel/Kleaf target inventory (file locations and target names), no compilation claims.
- List of missing information/remaining UNTESTED gates. Any failure is reported rather than concealed; do not launch another 35-project sync.

Stop and report if any prerequisite is missing or if permissions cannot access original local files. No destructive cleanups, expensive full kernel Actions runs, paid runners or flashable releases. Source checkout `35/35 TESTED` is a narrowly scoped gate; Stage 5 overall stays IN_PROGRESS.
