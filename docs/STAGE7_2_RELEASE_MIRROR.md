# Stage 7.2 — reviewed Release mirror and pinned-byte fallback

Status: GITHUB_SCOPED_COMPLETE_WITH_REAL_ASSET_UNTESTED; local toolchain/license evidence PENDING.

## Scope

KernelForge now extends the original LLVM/GCC ToolchainManager without a
second installer, downloader, cache, extractor, lock or rollback implementation.
The old llvm-release / gcc-release aliases now require an exact release_lock;
unreviewed uses fail closed. archive/custom adapters retain existing behavior.

GitHub's Release and Asset APIs expose Release ID/tag/draft/immutable, Asset
ID/name/uploader/size/state/digest/download URL:
https://docs.github.com/en/rest/releases/assets
https://docs.github.com/en/rest/releases/releases

Crucially, this API is NOT an independently trusted digest source. The
toolchain spec and independently reviewed release_lock must pin the same
archive SHA256. Asset filename, release tag and GitHub's own digest are
insufficient independently.

## Verified-by-code procedure

1. Validate kind LLVM/GCC, exact canonical GitHub HTTPS asset URL, host/target
   configuration, nonempty numeric IDs/size, reviewed license declaration,
   identical independently pinned SHA256, strict field allowlists and optional
   locked fallback before fetching or creating a toolchain cache.
2. On a new download, query the Release and Asset APIs. Require exact
   Release ID/tag/draft, Asset membership/ID/name/uploader/size/state,
   published digest and URL. Optional require_immutable=true enforces
   GitHub-reported Release immutability. Revoked or replaced asset metadata
   fails closed and DOES NOT trigger upstream fallback.
3. Use existing ToolchainManager downloader, SHA256 check BEFORE extraction,
   safe extraction, executable layout/version/architecture checks,
   atomic install, tree hash, cache lock and rollback. The whole reviewed
   release_lock is included in the cache identity.
4. Optional fallback is only used after transient GitHub API/network failure
   or mirror transfer failure. It requires a different credential-free HTTPS
   URL, same exact archive SHA256, pinned full upstream Commit and repository.
   Any mirror or fallback content mismatch is fatal; fallback never hides
   failed provenance or digest validation. The actual source route is
   recorded in result audit and cache metadata.

All new CI tests use mock API responses and tiny generated ZIP archives;
no real GitHub asset, big compiler archive, kernel build, or Bazel query
is downloaded/executed by this stage.

## Unfinished production prerequisites

- No approved public GitHub Release Asset/Release IDs or trusted whole-archive
  digest has been selected. Existing Clang r510928 binary SHA256 is not the
  SHA256 of a redistributable source archive.
- Human approval of licensing/redistribution remains required; the
  license_reviewed flag is a recorded review assertion, not proof by itself.
- Real LLVM/GCC large-archive layout, runtime versions, mirror throughput
  and host/target usability are UNTESTED.
- Rust/JDK/Bazel/vendor tools are not reclassified as LLVM/GCC artifacts.
- Ccache isolation is Stage 7.3; OnePlus13 fast build is Stage 7.5.
  DFR include is still BLOCKED_UNDETERMINED; full OKI/ABI/KMI/boot UNTESTED.

Conditional success status: SCOPED_COMPLETE_WITH_REAL_ASSET_UNTESTED,
only after Windows/Linux × Python 3.11/3.12 offline regression,
whole repository Validate and SM8750 source audit pass.

No Release created, no large downloads, no source sync, no PR #1 merge.

## Completed CI evidence (2026-11-23)

Final reviewed source commit: e71946236d73332b7a8b0225eff677038fc6671b.

| Verification | GitHub Run | Result |
| --- | --- | --- |
| Release offline Push matrix | https://github.com/20592504720/KernelForge/actions/runs/45211041253 | 4/4 green; 22 tests each |
| Release offline PR matrix | https://github.com/20592504720/KernelForge/actions/runs/45211055295 | 4/4 green; 22 tests each |
| Full Push Validate | https://github.com/20592504720/KernelForge/actions/runs/45211041202 | 4/4 green; 338 tests each |
| Full PR Validate | https://github.com/20592504720/KernelForge/actions/runs/45211055338 | 4/4 green; 338 tests each |
| SM8750 Manifest audit | https://github.com/20592504720/KernelForge/actions/runs/45211055344 | successful; full Repo sync not rerun |

Totals: 176 dedicated offline Release test executions and 2,704 full repository
test executions, no errors/failures. The fixture tests exercise full
ToolchainManager SHA256, secure ZIP extraction, installed tree cache hash,
atomic replacement and fallback routing. The direct binary version runner
is intentionally mocked in these tests; legacy toolchain version tests
remain covered by the full repository Validate.

The reviewed release asset identity has no real approved values in this
repository yet. No new mirrors were downloaded or published and no OnePlus13
runtime/compiler integration has been independently verified. This is a
software-only, scoped Stage 7.2 acceptance, NOT a production mirror approval.
The remaining local handoff is docs/STAGE7_2_LOCAL_CODEX_HANDOFF.md.
