# Stage 6.2 — opt-in locked Git/archive source acquisition

Status: **IMPLEMENTED FOR SOFTWARE-LEVEL VALIDATION; real vendor equivalence deferred**. Branch: `stage1/initial-foundation`. No change to the existing BuildEngine, Patch Manager, OnePlus source locks, Stage 5 acceptance or main branch. This is an explicit Stage 6.2 component, not a flashable-source provider.

## Interfaces

- `kernelforge.source_acquisition.acquire_locked_source("repo-git-lock-v1", lock, name, destination)` dispatches to the preexisting verified Git checkout using the *exact* 40-character commit specified by an existing source lock. Git behavior remains unchanged.
- `acquire_locked_source("pinned-archive-v1", lock, name, destination, candidate=..., cache_dir=..., allowed_hosts={...})` is **opt-in**. It requires a trusted out-of-band expected SHA256 and exact repository/path/commit identity declared in the same lock. The caller supplies explicit HTTPS host allowlist, including any intended redirect hosts. No unpinned branch or archive can be selected.
- Archive candidate is a mapping with `project`, `repository`, `path`, `commit_sha`, `sha256`, `archive_format`, `archive_url`. Its `sha256` must be vetted outside the downloaded archive; a digest copied from an untrusted page provides no independent trust.
- `acquire_archive` supports bounded streaming HTTPS download, no HTTP downgrade or uncontrolled redirects, `Content-Length` consistency, SHA256 verification on download and cache hits, per-digest exclusive lock, atomic cache installation, metadata preflight, streaming TAR/ZIP payload verification, strict path, count and expanded-size budgets, restricted modes, no links/special entries, private staging, atomic directory promotion and rollback if publication fails. No existing destination may be overwritten.
- Optional `report_path` writes a separate JSON report; success reports `archive_checksum=TESTED`, `archive_metadata=TESTED`, `payload_integrity=TESTED`, but crucially `git_tree_equivalence=UNTESTED`, `source_sync=UNTESTED`, `patch_manager_eligible=false`, `build_input_eligible=false`, `phase=STAGE6_ARCHIVE_ACQUIRED_QUARANTINED`.

## Explicit limits and threat model

- No archive is treated as a valid Git checkout, Patch Manager input, or device build input. Exact Git Commit/Tree equivalence is **Stage 6.3**, and Android Repo multi-project semantics (root project `./`, copyfile, linkfile, nested mounts) are not silently represented by a flat archive.
- This strict no-links extractor intentionally rejects real-source archives containing legitimate symlinks until an independently verified signed/tree-validated safe-link policy is introduced. Archives requiring symlinks remain **BLOCKED_UNSUPPORTED**, not silently altered.
- The HTTPS host allowlist prevents arbitrary cross-host redirects but cannot guarantee safety against DNS rebinding or a hostile proxy. Deploy only with trusted, reviewed hosts and egress controls. Downloaded content is constrained by declared and actual byte budgets; storage limits must be selected for the target runner.
- A verified archive SHA256 proves equivalence to the separately trusted expected digest, not upstream Git tree equivalence. Git `archive` may omit files via `.gitattributes export-ignore` or rewrite them via `export-subst`.
- All tests are offline fixtures. No vendor 35-project sync, full OnePlus OKI, or real device flash/boot is authorized or claimed.

## Verification

Run focused checks with `python -m unittest discover -s tests -p 'test_stage6_source*.py' -v`, followed by regular `Validate` OS/Python matrix. Archive failure cases include truncated download, changed hash, corrupt cached bytes, invalid ZIP payload CRC, traversal, links, case/path collisions, over-budget metadata/expansion, HTTP/host redirects, existing destinations and wrong pinned identities. Preserve `source-acquisition-report.json` separately from `source_sync` evidence.

## Stage 6.3 handoff

Implement an independent trusted Commit→Tree binding (byte content, Git mode and symlinks), actual OnePlus subset plus Android Repo `copyfile`/`linkfile`/root layout tests, then decide whether any archive can safely be promoted to an eligible source. Do not auto-fallback or impersonate git with `git init`.
