# Stage 5 third-round evidence (in progress)

This document records exact checks and their limits. It is not a Stage 5
completion declaration. No device-flashable image or Release is produced.

## Linux verification entry

`.github/workflows/upstream-validation.yml` now runs on the same-repository PR
for changes to the real-source validator, Patch Manager probe, capability
inspector or workflow. The workflow uses `contents: read` and no Secrets. The
four pinned jobs request a full `Image`; the four `latest` jobs verify source,
Kconfig, objects and a relocatable link only. Each run must be matched to its
actual Git commit and Tree before it counts as current-code evidence.

The official/pinned/SUSFS-off job runs `kernelforge.real_patch_probe` on its
fresh, build-owned ACK checkout. A build-local comment patch is generated from
the exact locked Makefile, SHA256-locked and applied; duplicate detection is
checked; then the edit is reversed. A second series creates a temporary file
and deliberately conflicts in Makefile, proving that the new file is removed.
The source must be clean before and after. The probe does not claim that a
third-party feature patch compiled. Its lock and result are uploaded with the
real-source report.

The capability report now checks actual ARM64 ELF/LLVM object bytes and records
their SHA256. Source presence, Kconfig, final `.config`, object compilation and
runtime remain separate. An enabled algorithm without a compiled object is
UNTESTED. `vmlinux` and `Image` must both be nonempty after a full build and
their hashes are recorded. Runtime TCP and ZRAM availability remains UNTESTED.

## SM8750 source locks

The pinned [OnePlus 13 source lock](../manifests/oneplus13-pjz110-sm8750-source.lock.json)
uses `oneplus_13_b.xml` at Manifest commit
`f8e50677874c65b6da41057d2f39be7b4ef3c08a`. Its 35 projects include
three OnePlus repositories at full Commit SHA and 32 CodeLinaro projects with
SHA revisions in the official XML. The OnePlus common commit is
`e1b346b6b4f4096eb342ae3684838a942fd6f6c4` and its Makefile says
6.6.118. The exact MSM and modules/devicetree commits are in the lock.

The previously recorded absence of an official Ace 6 6.6.118 source pair was
incorrect. The same official Manifest commit contains `oneplus_ace_6.xml`.
The [independent Ace 6 lock](../manifests/oneplus-ace6-plq110-sm8750-source.lock.json)
maps its three OnePlus projects to the separate
`oneplus/sm8750_b_16.0.0_ace_6` branch. The common commit
`65b954a773b183a9999b06bb1b2f921f12eaaf11` has a 6.6.118 Makefile.
The Ace 6 MSM and modules/devicetree commits differ from OnePlus 13 and are
recorded separately. The older community `lineage-23.2` 6.6.142 observation
remains a separate candidate, not the official source.

The lock records reference resolution, not commit reachability for every
CodeLinaro project, complete repo sync, a working Bazel target, module ABI,
firmware pairing, DTBO layout or device boot. The Linux source-audit workflow
attempts a 35-project `repo sync` with controlled concurrency and checks each
HEAD against the lock. It fails if the Manifest branch moved or any project
differs. It retains the report and log on failure. Native Windows source
directories do not count as a Linux build environment.

## BBG, Unicode and Fengchi

At BBG commit `028ff7fd509e2104596da7cc1ef8e6ce2a0c9082`,
`kernel_compat.h` includes `objsec.h` and `blk.h`, while both raw paths return
404 at that commit. This is a concrete upstream source completeness blocker
before Kconfig, LSM/SELinux and object compilation can be accepted. The remote
`setup.sh` is not executed. BBG integration: **BLOCKED**; object, boot and
security behavior: **UNTESTED**.

The WildKernels Unicode candidate at
`70c394f16d82b0f85a4f07617630d82dde6d203c` has patch SHA256
`3d1abd5e9666d15e415acb058ba260b007bc94f777539bbcb284e9cca41fccb9`.
An exact-file `git apply --check` succeeds against both locked ACK 6.1 and
OnePlus 13 common 6.6.118 `fs/unicode/utf8-norm.c`. This is **TESTED** only
for textual applicability. The patch changes empty-decomposition cursor state
and canonical combining behavior; no filesystem semantic tests, object build,
runtime security review or clear standalone license were found. Automatic
integration: **NOT_IMPLEMENTED**. The audit JSON is saved outside Git under
`E:\内核构建\reports\stage5-third-candidate-audit.json`.

Fengchi remains a Stage 6 candidate. The `Numbersf/SCHED_PATCH` `sm8750`
commit `26e3774a9794e9728a3cc6840f01527de5536eca` and candidate patch
SHA256 `0f835fea08a94e69409e9b4ffafd97af54c70c9871b25b788cb2eb5dafbbcc97`
were previously checked. The source describes leaked-code provenance and has
no clear repository license. Exact 6.6.118 applicability and redistribution
permission remain unresolved. No automatic download/application is enabled.

## Acceptance boundary

### Controlled sync preparation, 2026-11-22

The hosted Runner pilot actually recovered 6,584,580 KiB by removing only
the checked `/usr/share/dotnet` preinstall; capacity must be measured on the
fresh sync Runner. The source-audit workflow now separates manifest-only
PR/schedule activity from a named one-time full-sync trigger, keeps the
35-project exact lock and adds low-space process-group termination and
periodic JSON/log evidence. The 35 GiB admission floor and 10 GiB reserve
are provisional. Until a new Run yields 35 matching HEADs, complete locked
source sync remains **UNTESTED**. Full image, modules, ABI, firmware match,
boot and Root remain **UNTESTED** even if that sync succeeds.

Until the current-Tree Linux jobs finish, real GKI Patch Manager, final
network/ZRAM object evidence, full Images and any SM8750 source sync/build are
UNTESTED. Even successful source sync will not establish firmware-matched ABI,
boot, Root or SUSFS runtime behavior. A Stage 5 framework acceptance request
requires inspection of the exact CI reports and unresolved blockers.
