# KernelForge Stage 6.3 — remote implementation and exact local Codex handoff

**Scope:** read-only Git Tree/archive equivalence and manifest workspace planning. No new full 35-project sync, no kernel build, no patch/lock modifications, no PR merge or release.

## A. Implemented remotely

- `kernelforge/source_equivalence.py`: `verify_archive_git_tree` independently checks a local Git checkout HEAD against an existing locked 40-hex commit; obtains full Git Tree object SHA and zero-terminated `git ls-tree` blob entries, compares the complete extracted archive file set, exact Git blob hashes, and POSIX executable modes. Rejects symlinks, Git submodules/gitlinks, reserved metadata, casefold collisions, prefixes with extra files, wrong HEAD, missing/extra/tampered files and resource-budget overruns. Does not change either source tree. Windows cannot prove POSIX mode: fail closed; run actual proof in Linux/WSL2.
- `workspace_plan`: deterministic root-first mounting order for 35 locked projects; reports overlapping nested mounts and checks optional manifest-snapshot `copyfile`/`linkfile` declarations without applying them. Handles legitimate `linkfile src="."` as a directory source. Any XML supplied to the function is **UNAUTHENTICATED** unless caller independently proves it came from the pinned manifest commit. It never declares source sync, complete Repo overlay, or a bootable build.
- `kernelforge/repo_workspace_audit.py`: **read-only** local audit of all pinned project HEADs and Git Tree SHAs using the existing Android Repo source workspace; independently validates the pinned manifest checkout SHA and reads the XML directly from its Git object; checks every declared `linkfile`/`copyfile` on the filesystem, including the directory link `src="."`. Refuses missing projects, moved manifest/project HEADs, broken or diverted links. Reports complete workspace byte overlay and real vendor archive proof as `UNTESTED`; it never starts `repo sync`, builds a kernel, edits Git or rewrites symlinks. CLI provided for Codex to run.
- Offline tests create real local Git object fixtures, validate mode/content/HEAD, use real `git archive --format=tar` plus the Stage 6.2 acquisition module for an end-to-end quarantine-to-verifier test; confirm that `export-ignore`/`export-subst` and malicious/mismatched paths fail closed.
- Existing Build, Patch Manager, Stage 5 exact locks, source acquisition quarantine, and CI heavy-run gates remain unchanged. The Stage 6.3 comparison report **does not** set `build_input_eligible=true` or `patch_manager_eligible=true`.

## B. Independently checked against OnePlusOSS pinned manifest (GitHub immutable raw URL)

Manifest commit: `f8e50677874c65b6da41057d2f39be7b4ef3c08a`.

- `oneplus_13_b.xml` -> `manifests/oneplus13-pjz110-sm8750-source.lock.json`: **35/35 project name/path/revision declarations match**.
- `oneplus_ace_6.xml` -> `manifests/oneplus-ace6-plq110-sm8750-source.lock.json`: **35/35 match**.
- Each declares **2 linkfiles, 0 copyfiles**:
  - `kernel_platform/common`: `<linkfile src="." dest="kernel_platform/.source_date_epoch_dir"/>`.
  - `kernel_platform/msm-kernel`: `<linkfile src="build_with_bazel.py" dest="kernel_platform/build_with_bazel.py"/>`.
- This inspection proves *declaration alignment only*, not actual symlink targets, source files, byte-for-byte complete Repo workspace or physical device builds.

Official documentation: https://android.googlesource.com/tools/repo/+/HEAD/docs/manifest-format.md and https://git-scm.com/docs/git-archive.

## C. Codex tasks that REQUIRE the existing WSL2 OnePlus workspace

1. **Safety first**. Confirm current Git branch `stage1/initial-foundation` and its committed SHA, note any uncommitted changes, check available disk and any running `repo/git/index-pack` process. Never delete, clean/reset, resync, relocate or overwrite E: or `/home/kernelforge/...` workspaces. Never merge PR #1. Use existing *completed 35/35* report and locked workspace, not a fresh `repo sync`.
2. **Run the provided read-only audit first**. In the KernelForge repository checkout, use `python -m kernelforge.repo_workspace_audit --lock manifests/oneplus13-pjz110-sm8750-source.lock.json --workspace /absolute/existing/oneplus13/workspace --manifest-checkout /absolute/existing/oneplus13/workspace/.repo/manifests > /separate/report/folder/stage63-audit.json`. Verify `.repo/manifests` is the actual pinned Git checkout before running; if not, classify `BLOCKED_MANIFEST_CHECKOUT`, do not initialize or synchronize it. The command only reads existing Git objects, files and symlinks; redirect its report to a folder **outside** the existing source workspace.
3. **Authenticate the source identity**. For each of the 35 already synchronized project checkout paths, record exact `HEAD` and `HEAD^{tree}` and compare against the corresponding existing `source_lock.projects[].commit_sha` in the same pinned OnePlus 13 lock. Resolve Android Repo working-copy `.git` file handling; treat missing, dirty, replaced, uninitialized or inaccessible projects as explicit exceptions. Record original manifest repository/commit/path and current XML snapshot identity.
4. **Validate Repo root and linkfile semantics without writing**. Confirm the `./` root project and all project overlays under the real `repo` workspace. Inspect `kernel_platform/.source_date_epoch_dir` and `kernel_platform/build_with_bazel.py` using `readlink`, `realpath`, `stat` and source/destination comparisons. Record whether the two links point to the correct locations and whether the target is available. The first `src="."` is a directory link, not a path traversal attack. Confirm no unaccounted overlay/casefold collision. Do **not** create links merely to pass verification.
5. **Representative archive equivalence**. In isolated temporary space, try 2–3 small/medium projects first. Use an independently trusted external archive digest if there is a real vendor archive; otherwise label locally generated `git archive` as **TEST_FIXTURE_ONLY**, never production equivalence evidence. On Linux/WSL2 compare pinned Git blob identities, execute bits, symlink/gitlink handling, missing/exported files, and `export-ignore` / `export-subst`. The current Stage 6.2 quarantined Archive refuses links: classify any link-containing vendor project as `UNSUPPORTED_LINKS` / `BLOCKED` rather than silently dropping links or claiming success.
6. **Full-Repo layout evidence, not a full rebuild**. Provide a compact read-only JSON report containing: Git HEAD/tree for all 35 paths, success/mismatch counts, root overlay observations, linkfile source/target checks, archive fixture vs vendor-provenance status, exact commands and exit codes, relevant disk capacity and any blockers. Keep `source_sync` and `git_tree_equivalence` evidence distinct from `module_abi` and `device_boot`.
7. **Report review**. Commit only targeted tests/docs/compatibility fixes to the same branch after confirming head; request approval before any potentially destructive operation or large compilation. No new 35-project downloads, no kernel Image/OKI rebuild, no signing/flash or release in this handoff.

## D. Acceptance/evidence classification

- Stage 6.3 remote *framework*: PASS only after GitHub Linux/Windows CI and offline tests pass.
- Stage 6.3 actual OnePlus 13 overlay and linkfile behavior: `UNTESTED` until the read-only WSL2 evidence above is supplied.
- Stage 6.3 exact *real vendor archive* vs pinned Git Tree: `UNTESTED` until a trusted vendor archive is available and compared to independently pinned Git objects.
- Source archive remains quarantined and ineligible for Build/Patch Manager even if a single-project local fixture matches. Stage 8 owns complete vendor OKI and device validation.
