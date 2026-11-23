# Stage 5 final bounded acceptance and exact GKI run request — 2026-11-23

Status at request: **IN_PROGRESS**. **A job request is not successful validation.** The workflow branch-push path and pre-download controls are documented in [STAGE5_BAKASU_SUSFS_DELTA_AUDIT.md](STAGE5_BAKASU_SUSFS_DELTA_AUDIT.md). The request below is a **single explicit, bounded GKI source/object/link test**, not a full Image compile or SM8750 source sync.

## Existing independently distinguishable evidence

| Requirement | Before this request | Qualification |
| --- | --- | --- |
| OnePlus 13 official source lock and 35/35 Git HEADs | TESTED | Locked WSL2 Ubuntu ext4 source sync; no SM8750 compile |
| OnePlus 13 Kleaf targets and inventory | STATIC_AUDITED | `sun_perf_dist` / `sun_consolidate_dist` only; no Bazel query/build |
| Real generic ACK 6.1 Patch Manager transaction | TESTED | A locked generated comment-patch/rollback probe, not all third-party feature patches |
| Pinned GKI official/BakaSU × SUSFS combinations | TESTED (4/4) | Prior Run 45020470109; distinct older BakaSU SHA |
| Source-level new BakaSU/SUSFS API | STATIC_AUDITED | Two `susfs_add_*` signatures match locked SUSFS commit; no ARM64 compilation |
| Local BakaSU compatibility safety and exact entry | Codex-reported 69/69 and 33/33 | GitHub report confirms latest 8/8 + 25/25 tests; E: logs are local; independent GH Actions runtime still needed |
| Moving latest-branch GKI | BLOCKED (7/8) | Run 45098970334 used `63ad1ea...`, one translation-only commit beyond reviewed `2734e0bc...`; exact Commit checks remain fail-closed |
| Full OnePlus 13 OKI, ABI/KMI, firmware, modules, flash/boot/Root | UNTESTED | Stage 8 / physical-device contract; not within this GKI request |

## One bounded run: exact target

The single trigger file `.github/stage5-exact-gki-request.json` must be changed on the existing `stage1/initial-foundation` branch. Its schema/version/commit/full_kernel values are compared to compiled-in expected constants by `scripts/stage5_exact_request.py` after checkout, **before dependency installation or upstream source fetch**; malformed SHA is rejected even earlier, before checkout.

- GKI: `498f91c17b0822a09aede17d26a63bf8c6813725`.
- BakaSU: `2734e0bc155759955880f5fb99be640fc5b92156`.
- SUSFS: `756abbf2d81557e36664fc67dffaee26d3dfc57c`.
- Run mode: exactly one `exact_bakasu` job, `--provider bakasu --susfs --pinned-baseline --bakasu-commit <SHA>`. The eight-job `sources` matrix explicitly excludes push events.
- Bound: hosted Ubuntu 24.04, job timeout 60 minutes, existing dependency installation; no `--full-kernel`, full Image, SM8750 `repo sync`, OnePlus 13 OKI, boot or Release.
- Preflight: Python 3 stdlib only, exact GH branch + Git HEAD changed-files check + duplicate-key rejecting marker JSON parser. CFI/KCFI and Shadow Call Stack remain enabled as required by pinned ACK baseline.
- Output: `real-source-report.json`, `versions.lock.json`, `source-check.log`, final `kernel.config`, `capabilities.json`, `undefined-symbols.txt`, object hash reports and uploaded `real-bakasu-susfs-true-exact` artifact if the source integration reaches those gates.

The preflight implementation was also reproduced in an isolated container fixture, where 13 positive and negative checks passed including an ephemeral Git HEAD fixture. This does **not** count as the repository's full Python suite, GitHub Actions job or kernel compile success; the separate Codex local suite must still validate the latest source Tree.

## Acceptance / failure decisions

1. Record the resulting workflow **Run ID, event, triggering Commit/Tree**, job name and verified `versions.lock.json` target SHAs. A skipped job, failed preflight, or unexpected eight-way matrix is a **failure**, not success.
2. Inspect the actual `git apply` record, final `.config` hardening flags, ELF/LLVM AArch64 objects, link return status, and unresolved KernelSU/SUSFS symbols. A `git apply --check` alone cannot pass Stage 5.
3. Require `real-source-report.json.status == success`, `kconfig == TESTED`, `object_compilation == TESTED`, and `acceptance.relocatable_link == TESTED`, together with the SHA-locked source and artifacts. Check `acceptance.full_vmlinux == UNTESTED` remains truthful. If any fail, preserve diagnostics and perform **one targeted fix**, not an automatic rerun of all eight.
4. Only after that GKI acceptance can Stage 5 be evaluated for scoped closure. A moving `latest_branch` failure cannot be silently called passed; explicitly choose `BLOCKED` dynamic-upstream monitoring with documented limitation or continue compatibility work. Official OKI/ABI/boot stays Stage 8, never mislabel as Stage 5 GKI evidence.
5. No `main` write, PR #1 merge, force push, source-lock rewrite, paid runner escalation or local E-drive deletion is authorized by this document.

Keep the workflow run evidence separate from the original OnePlus 13 35/35 source-sync evidence. Stage 5 **IN_PROGRESS** until checked.
