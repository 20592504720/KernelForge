# Stage 7.4 local Codex handoff: read-only WSL2 evidence

Only do the current Stage 7.4 local audit after comparing remote and local development HEAD/Tree. Do not delete/reset uncommitted files or change main; PR #1 remains open.

1. In E:\内核构建\project, compare current branch stage1/initial-foundation, HEAD and Tree to GitHub and ensure the working tree is clean. Respect local commit ancestry; do not force reset. WSL project path is /mnt/e/内核构建/project.
2. Read scripts/stage7_4_fast_build_gate.py and docs/STAGE7_4_FAST_BUILD_GATE.md. Run only the offline unit test: PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_stage7_4_fast_build_gate -v. No pip, apt, Bazel, downloading or source sync.
3. Run sha256sum against manifests/oneplus13-pjz110-sm8750-source.lock.json; use the actual 64-hex value, not a copied placeholder. Verify on the already-existing ext4 source /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750 using --source-workspace and --host-disk /mnt/e. The gate does read-only Git queries for the locked 35 projects; fail without repair on any mismatch.
4. Record fresh host E: physical free bytes and 50 GiB reserve, ext4 free bytes/inodes and 20 GiB reserve. Do not trust virtual VHDX free bytes as physical host capacity. WSL memory at previous audit was approximately 3.77 GiB total, not a verified build budget.
5. Save raw logs only in E:\内核构建\reports. Add two evidence-only repo files docs/STAGE7_4_LOCAL_CODEX_AUDIT.md and docs/evidence/stage7_4_local_source_admission.json recording actual HEAD, Tree, lock SHA256, timestamp preview, test count, per-project 35/35 result, logs SHA256 and TESTED/UNTESTED/BLOCKED distinctions.
6. STOP. Real ccache, Kleaf cquery/aquery (which may create caches), bounded fast Image build, vendor module build, toolchain install or DFR patch require separately reviewed plans and approvals. No Git clean, cache prune, repo sync, real compiler invocation, release or flashable ZIP.

Success for this handoff is a local read-only admission/evidence audit, not a kernel build. If ccache remains absent, it stays OFF. Do not mark full Image, OKI, ABI/KMI, boot or Root TESTED.
