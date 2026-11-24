# Stage 6.5 — scoped reconciliation and Stage 1–6 one-shot full acceptance

**At publication:** Stage 6.5 code and evidence reconciliation implemented; the
dedicated Stage 1–6 full run is **NOT YET TRIGGERED**. This page is a run contract,
not a claim that five real Image builds succeeded.

## Locked scope, stages 1 through 6

| Stage | Acceptance evidence | Limit retained |
| --- | --- | --- |
| 1 Foundation | JSON Schema, CLI validation, repository checks, all unit tests | No boot/release |
| 2 Build engine | Pinned Git, GKI/vendor plan/report and negative build fixtures | Vendor real build not proven |
| 3 Toolchains | Real local HTTP/ZIP/TAR integrity, cache, lock and rollback tests | Full upstream LLVM/GCC archives not proven |
| 4 Root/SUSFS | Official KernelSU/BakaSU source-identity/adapters, selected strict SUSFS | Only reviewed ACK6.1 combos; device Root untested |
| 5 Patch/OnePlus sources | Patch transactions, 35 fixed PJZ110 project HEAD/Tree evidence, exact generic GKI objects + Image | New 35-project sync not repeated; OEM Image/ABI/KMI not proven |
| 6.1 Software regression | Full Windows/Linux × Py3.11/3.12 | Not standalone real kernel proof |
| 6.2 Git/Archive | SHA256 cache, secure download, extraction, atomic rollback, negative tests | Archive remains quarantined from build |
| 6.3 Workspace | 35 HEAD/Tree matches, 35 clean-normalized matches, 34 raw-byte matches, symlinks and static Kleaf assessment | DFR include unresolved, independent vendor archive untested |
| 6.4 Compatibility | Exact ACK6.1 triple gate; unknown/new BakaSU SHA rejected | Moving latest branch not accepted |
| 6.5 Evidence gate | Cross-report, source-lock, 33 CRLF and 29-link reconciliation; fail-closed tests | Live full run is separate |

## Exactly one full acceptance request

The dedicated workflow `.github/workflows/stage1-6-full-acceptance.yml` runs
**only** on a push to the development branch changing the precise marker
`.github/stage6-full-acceptance-request.json`. It has no PR, schedule or
manual event. A request is valid only when that commit modifies **only** this
file, matches the approved 1–6 scope, and names its exact parent Stage 6.5
Commit. This is an explicit opt-in for heavyweight execution.

The workflow executes:

1. Exact branch/ref/commit preflight before any dependency installation.
2. Offline historical evidence reconciliation, both SM8750 profile audits, and
   schema/config checks. The existing pinned WSL2 35-project source sync is
   **not downloaded again**; committed summaries are audited, but local raw
   bytes are not independently re-read from the GitHub runner.
3. **All tests** on Windows/Linux × Python 3.11/3.12, with the same Windows
   isolated-process launcher used in the passing Validate workflow.
4. **Five real, fixed ACK 6.1 kernel source/image jobs**, with LLVM 17, GNU 11,
   CFI/KCFI and the verified exact source locks: official/BakaSU old ×
   SUSFS off/on, plus exact reviewed BakaSU `2734e0bc...` + SUSFS. Each
   validates actual Git HEAD, patch, final Kconfig, ARM64 objects, relocatable
   link, **complete generic GKI `vmlinux` and `Image`** and SHA256.
   `latest_branch` is intentionally not in the matrix, because unreviewed
   moving BakaSU may conflict and its failure would not be pinned regression.
5. A fail-closed aggregate job which records **all** job outcomes in GitHub
   Artifacts and Job Summary. Skipped or failed prerequisite/real GKI jobs
   cannot be counted as success.

Hosted GitHub Actions has hard runtime/resource limits; individual real GKI
jobs are bounded at 300 minutes, with Image command max 14,400 seconds. The
request to allow time is respected *within platform constraints*. A cancelled
job, runner capacity failure, timeout or missing artifact is **not success**.

## Evidence ledger before starting

- Stage 6.4 [Push Validate #45181004477](https://github.com/20592504720/KernelForge/actions/runs/45181004477)
  and [PR Validate #45181018825](https://github.com/20592504720/KernelForge/actions/runs/45181018825):
  both 4/4, 288 tests per job, zero errors.
- Earlier [exact BakaSU+SUSFS source/object job #45105067150](https://github.com/20592504720/KernelForge/actions/runs/45105067150):
  67 ARM64 objects, relocatable link, no full Image for that source triple.
- Stage 6.3 [final static dependency JSON](evidence/stage6_3_final_dependency_audit.json):
  28 links scoped-not-required, 1 DFR `BLOCKED_UNDETERMINED`. 33 `lz4`
  files clean-normalized, not raw-byte-identical.
- Stage 6.3 [WSL2 source evidence](evidence/stage6_3_wsl2_acceptance.json)
  and [byte audit](evidence/stage6_3_wsl2_blocker_diagnosis.json):
  35/35 Git commits/Trees, 34/35 raw-byte equality.
- Stage 6.4 unreviewed BakaSU `63ad1ea3a90455dee9d77163cdafb028d8a90416`
  remains rejected by exact-identity gate; later upstream versions need
  independent review before use.

## Final interpretation (do not overclaim)

A successful one-shot run permits `STAGE1_6_SCOPED_GATES_PASSED_WITH_DEFERRED_BLOCKERS`.
It **does not** imply full OnePlus 13 35-project OKI, external DFR module
dependency resolution, vendor module/DTBO correctness, firmware compatibility,
ABI/KMI, device boot, Root or SUSFS runtime. Independent vendor archives also
remain non-buildable. If any actual acceptance job fails, retain its failure
and artifacts; never silently scope it out or start Stage 7 automatically.

Do not modify `main`, merge PR #1, re-sync 35 projects, rewrite historical
source SHA locks or start a device release.

## First trigger preflight diagnosis (not a kernel failure)

[Run 45183774937](https://github.com/20592504720/KernelForge/actions/runs/45183774937)
was rejected before all software, evidence and real GKI jobs. The GitHub
checkout action used shallow `fetch-depth: 1`, so the exact-parent
`git rev-parse HEAD^` invariant could not inspect the parent commit. The
aggregate gate correctly FAILED and all downstream jobs SKIPPED. This is
**zero substantive Stage 1–6 test evidence**, not a failed kernel compile.
The one-shot preflight now fetches depth 2, with a regression assertion. A
new marker-only request is required for the actual first full attempt; do not
rerun the failed artifact as if its acceptance were complete.
