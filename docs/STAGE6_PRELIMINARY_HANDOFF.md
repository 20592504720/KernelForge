# KernelForge Stage 6 — initial code and Codex handoff (2026-11-23)

## Baseline and scope

The project owner accepted bounded Stage 5 closure. Stage 6 work proceeds on `stage1/initial-foundation`, leaving `main`, PR #1, GKI pinned commits, SUSFS adapter, verified WSL2 source, 35-project source locks, and cached outputs unchanged. Dynamic `latest_branch` remains BLOCKED; a device-flashable OnePlus 13 OKI remains UNTESTED until Stage 8.

Stage 6 initial implementation: `kernelforge/source_archive.py` + `tests/test_stage6_source_archive.py`. The new module is intentionally opt-in, standard-library-only, side-effect-free on the existing build chain. It does **not** download, extract, impersonate Git checkout, or change `kernelforge/source.py`, `source_provider.py`, `patch_manager.py`, `build.py`, Repo verifier or ToolchainManager.

## Implemented and locally tested

- Validate schema-version-1 device source lock, exact 40-hex Manifest/project commits, HTTPS repository identities, case-insensitive unique paths and the single allowed `./` root path. Validate declared count and `all_refs_locked`.
- Bind an archive candidate to an exact existing project name/repository/path/Commit and a declared SHA256; check actual archive bytes against the expected checksum. Caller is responsible for establishing the independent *trust* of the expected SHA256.
- Fail closed on malformed/unsupported TAR/ZIP metadata, path traversal, absolute/drive/ambiguous paths, case-folding collisions, file-as-parent collisions, links and special files, setuid/setgid modes, encrypted ZIP, excessive member count and excessive declared unpacked size.
- Emit explicit separate evidence fields: `archive_checksum=TESTED`, `archive_metadata=TESTED`, `git_tree_equivalence=UNTESTED`, `source_sync=UNTESTED`, `patch_manager_eligible=false` and `payload_integrity=UNTESTED`.
- A guard rejects archive strategy inputs to existing Git-only patch operations.
- In an isolated environment, 11 new unit tests passed; Python source compiled. No real external ZIP/TAR, GKI kernel, OnePlus 13 Image, or GitHub Actions run has been validated for this module.
- Both checked-in locked profile manifests were independently inspected via GitHub: 35 projects each, one legitimate `./` root project, unique case-insensitive paths and exact 40-hex commit revisions. This is **static lock validation only**.

## Explicitly unimplemented / next local Codex work

1. Apply/cross-check these new files against the current local branch and working tree safely; preserve uncommitted work. Run new focused tests, then existing full Linux/Windows CI (not costly GKI/sync). Review zip/tar inspection under Python 3.11/3.12 on Windows and Linux.
2. Extend Stage 6 with an optional `pinned-archive-v1` acquisition worker using bounded, atomic downloads, HTTPS host/redirect controls, immutable content-addressed cache and reliable provenance. Never let a user-supplied SHA prove upstream-to-Git identity without an independent trusted binding.
3. Before any archive becomes a build input, prove extracted file contents **and modes** match the exact pinned Git tree, including symlinks and executable bits; support safe archive layout/link handling only after threat-model tests. The initial strict no-links policy is deliberate, not production completeness.
4. Handle Android Repo root `./` project, nested project mount order, copyfile/linkfile and all 35 source project mappings without rewriting existing Repo source locks or verifier. Keep patchable kernel trees as genuine Git checkouts; never simulate ancestry using `git init`.
5. Test truncated/corrupt payloads (not just header metadata), ZIP bombs and expansion limits, malicious links/metadata, case-insensitive filesystem aliases, source archive mirror drift, unavailable historical commits, unchanged source Git HEAD/Tree and explicit archive-versus-Git file/mode comparison.
6. Review schema versioning and adapters; maintain fail-closed fallback to locked Git only when identical commit identity is established. Keep a separate `source-acquisition-report.json` from `source_sync` and any device flashability declaration.
7. Run relevant CI after code integration. Do not launch a full 35-project sync, GKI Image build, complete OnePlus 13 OKI, paid runner, release, merge, or local E-drive migration as part of this handoff.

## Evidence boundaries

A digest of archive bytes alone does not establish that they are the exact contents of a pinned Git Commit. The new preflight scans metadata only; it does not read every compressed member to establish decompression integrity and does not extract files. Its passing result cannot be marked `SOURCE_CONTENT_VERIFIED`, full `source_sync=TESTED`, or `patch_manager_eligible=true`. Full Stage 6 acceptance is pending the integration and negative tests above.