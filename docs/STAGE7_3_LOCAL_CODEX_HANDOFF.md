# Codex task: Stage 7.3 local WSL2 ccache readiness and fixture validation

Only begin after GitHub Stage 7.3 CI passes. This is READ-ONLY inventory plus
small isolated Python tests in disposable temporary directories if existing
dependencies are already present. Do not build an Android kernel.

Locations:
Windows Git repo: E:\内核构建\project
WSL Git repo: /mnt/e/内核构建/project
Immutable 35-project source:
  /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750
Raw logs only: E:\内核构建\reports
Branch stage1/initial-foundation, protect main, leave PR #1 open.

Task steps:

1. Safely reconcile Git HEAD/Tree with remote Stage 7.3 code and review
   kernelforge/build_cache.py, kernelforge/build.py, schemas/build.schema.json,
   docs/STAGE7_3_CCACHE_POLICY.md. Never reset/discard local work or alter
   the 35-project source lock.
2. Passive WSL2 discovery only: command -v ccache and sccache, absolute
   path metadata if installed, free -b, nproc, df -Pk /mnt/e and
   df -Pi on ext4 source. Inspect preexisting CCACHE_* environment
   variable NAMES, without printing secrets. Do not create a real cache
   root or change CCACHE_CONFIGPATH. Retain a 50 GiB E: physical reserve.
3. If ccache is still absent, mark BLOCKED_NO_CCACHE_BINARY. Do NOT install
   software, download a compiler, or falsely claim hit-rate measurements.
   If an existing standalone ccache binary is discovered, an OPTIONAL
   direct absolute-path --version query is allowed (no wrappers that
   can download dependencies); record version, exit code and file SHA256.
4. If Python dependencies already exist, run in the Windows Git repo
   from WSL2 with PYTHONDONTWRITEBYTECODE=1 and python3 -B:
   python3 -B -m unittest discover -s tests -p 'test_stage7_3_*.py' -v
   These tests use isolated temporary fixture directories, not actual
   ccache, Bazel or OnePlus source. If dependencies are missing, mark
   BLOCKED_DEPENDENCY. Do not pip install.
5. Confirm build.ccache is OFF by default and device-profile cache is
   blocked until Stage 7.4. Verify source/cache directory separation,
   safe dry-run prune, active/stale lease blocking and corrupt namespace
   quarantine. Do not perform real pruning, ccache -C, bazel clean,
   Git clean, repo sync, apt, build, or cache deletion.
6. Create and submit ONLY:
   docs/STAGE7_3_WSL2_CCACHE_AUDIT.md
   docs/evidence/stage7_3_wsl2_ccache_audit.json
   Keep raw logs and hashes under E:\内核构建\reports. Report TESTED,
   UNTESTED, BLOCKED distinctly; record exact remote/local Commit and
   Git Tree, SHA256 for report and JSON, and resource readings. Conclude
   whether Stage 7.4 software work can proceed with ccache OFF.

Stop. No package installation, Bazel queries, fast kernel build, DFR patch,
RAM configuration changes or Stage 7.4 code changes. No main modification
or PR merge.
