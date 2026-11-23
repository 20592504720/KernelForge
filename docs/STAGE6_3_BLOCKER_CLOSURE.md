# Stage 6.3 blocker closure — bounded remote implementation

Stage 6.3 acceptance remains **PARTIAL_TESTED_WITH_BLOCKERS** until the WSL2 evidence is reconciled and reviewed. This change does not rewrite the source lock, checkout, archive acquisition or Patch/Build Manager.

## New read-only archive proof

`kernelforge.archive_link_proof.verify_archive_link_tree` compares TAR and ZIP entries directly to the *exact* pinned Git commit and Git Tree. It validates the declared digest against actual archive bytes, uses bounded streaming for file contents, enforces case-unique relative member names, compares regular-file Git blob SHA-1 plus executable modes, and compares each symlink as its Git `120000` blob (raw target bytes). It rejects unauthorized path additions, omissions, hard links, special nodes, altered target bytes, collisions and malformed modes.

**No archive member is extracted. No symlink is followed, materialized or repaired.** A Git symlink target may cross a project boundary: matching the Git blob does *not* certify the target is safe or exists in the full Repo workspace. All evidence explicitly says `archive_extraction_safe=UNTESTED`, `symlink_destinations_valid=UNTESTED`, `patch_manager_eligible=false`, `build_input_eligible=false`, `workspace_content_equivalence=UNTESTED`, `independent_vendor_archive_provenance=UNTESTED`.

The existing strict source acquisition mode (`kernelforge/source_acquisition.py` and `source_archive.py`) still rejects symbolic links. Thus 14/35 symlink-bearing projects can be *examined* by this standalone proof but cannot yet be promoted into the strict extraction pipeline or considered eligible for builds. Do not weaken that guard without a separately reviewed extraction threat model and tests.

`git archive` may honor `.gitattributes` `export-ignore` and `export-subst`. An export that omits or modifies Git-tracked content must fail content equivalence; the tests include `export-ignore`. The expected SHA256 must have independent trusted provenance. A locally generated fixture is marked `TEST_FIXTURE_ONLY`, not a vendor archive certification.

## WSL2 report reconciliation

The development branch includes `docs/STAGE6_3_WSL2_REPORT.md` and `docs/evidence/stage6_3_wsl2_acceptance.json` with 35/35 locked HEAD matches, 1,206 Git-tracked symlinks matching blob target bytes, two valid Manifest linkfiles, **29** symlinks whose targets do not exist, and **14** symlink-bearing projects. Existing source layout has not been proven completely byte-equivalent to all Git Trees.

From the committed JSON, the 29 missing targets break down by responsible area:

- **20** references in `kernel_platform/prebuilts/clang/host/linux-x86/llvm-binutils-stable` to `clang-r522817/bin/*`: priority **P0**, determine which pinned toolchain is actually selected and whether these are invoked by the relevant Linux Kleaf/OKI target.
- **6** Rust `stable` shortcuts in Darwin, Windows and Linux-musl host directories: investigate whether those non-default host variants are reachable from the actual Linux build path; do not assume harmlessness.
- **3** root-project references (`mkdtboimg.py`, `vendor/oplus/kernel/audio/bazel/mtk`, `vendor/oplus/kernel/dfr/soc/oplus/dfr/include`): determine exact build dependencies and availability without fixing links or changing locks.

All 29 have link target strings matching locked Git blobs and stay within the checked workspace. This is not proof that the targets exist or that the build will succeed. The two Repo Manifest `linkfile` directives are valid and are not among the 29.

## Required local Codex follow-up

1. **Read-only, no new sync**: use the existing `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`, preserve the clean KernelForge working tree, and confirm branch/source HEAD plus no active `repo sync`/git workers. Do not create or repair any symbolic links, fetch enormous toolchain trees or run a kernel build.
2. **Diagnose all 29 targets** using `docs/evidence/stage6_3_wsl2_acceptance.json` `tracked_link_inventory.broken_target_details` and `E:\\内核构建\\reports\\stage6.3-layout-diagnostics-final.json`. For each: identify tracked project, link path, raw target, resolved path, expected producer/project if identifiable, actual existence, source of missing target (e.g. absent prebuilt, branch layout, intentionally unsupported host), Linux build reachability with exact evidence. Grade P0 build-blocking / P1 uncertain / P2 proven out-of-scope, or `BLOCKED_UNDETERMINED`; do not automatically mark non-Linux shortcuts harmless. Report exact paths, file modes and evidence pointers.
3. **Full workspace working-file equivalence**, distinct from HEAD matches: using read-only bounded Git `ls-files -s -z`, `hash-object`/streaming SHA1, and `lstat/readlink` for all 35 projects, including the `./` root and overlay exclusions, compare file contents and modes against each pinned Git Tree. Avoid scanning `.git`/`.repo` object databases or silently ignoring nested mount files. Record every omission/collision, actual mismatch and performance cost; fail `TESTED` status if any tracked file cannot be checked. This is not an invitation to run a second 35-project sync.
4. **Link fixture of new verifier**: with the new `archive_link_proof.verify_archive_link_tree`, run on at least two small actual pinned projects containing tracked symlinks. Generate `git archive` into isolated temporary WSL ext4 only; verify linked target byte and executable-mode mismatches are rejected. Mark `TEST_FIXTURE_ONLY`. Do not use or modify vendor/archive cache; do not claim trusted vendor provenance.
5. **Deliver** `docs/STAGE6_3_WSL2_BLOCKER_DIAGNOSIS.md` and a compact machine-readable JSON report plus external raw logs under `E:\\内核构建\\reports`. Record report SHA256 and all `TESTED/UNTESTED/BLOCKED` statuses. Commit only documentation/evidence to `stage1/initial-foundation` after ensuring no remote-head conflict; never merge PR #1 or modify `main`.

## Acceptance rule

Stage 6.3 may be accepted for **bounded source identity and safety-comparison scope** only after: current-head software CI passes; 29 broken targets are classified with evidence and build impact; 35-project working-file/overlay comparisons are either `TESTED` or every missing proof is isolated as an explicitly deferred and approved blocker. Independent vendor archive and device/ABI/OKI build proof stay `UNTESTED` until separate stages, not secretly counted as passed.