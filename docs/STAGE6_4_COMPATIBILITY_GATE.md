# Stage 6.4 — immutable KernelSU/BakaSU/SUSFS compatibility gate

Status: **SCOPED_IMPLEMENTED; first Windows/Linux CI successful; integration follow-up CI pending**.

## Exact reviewed matrix

The Stage 4.6 SUSFS context adapter catalog currently covers the immutable ACK
`android14-6.1` kernel Commit `498f91c17b0822a09aede17d26a63bf8c6813725`
and SUSFS Commit `756abbf2d81557e36664fc67dffaee26d3dfc57c`.

Provider identities reviewed for the same adapter:

| Provider | Exact Commit | Scope |
| --- | --- | --- |
| Official KernelSU | `2a60b2893b8d0d885d1ceff2287d8ad854f0e0f4` | Reviewed pinned adapter identity |
| BakaSU baseline | `7b65bde0710b5e7c6f755545cb15a4abd417f3a8` | Reviewed pinned adapter identity |
| BakaSU post-update | `2734e0bc155759955880f5fb99be640fc5b92156` | Reviewed pinned adapter; 67 ARM64 objects and relocatable link evidence: [Run 45105067150](https://github.com/20592504720/KernelForge/actions/runs/45105067150) |

At the Stage 6.4 audit, BakaSU `main` had moved to
`63ad1ea3a90455dee9d77163cdafb028d8a90416`. This is **not** on the
reviewed matrix and remains **BLOCKED** pending an independent source/API,
patch applicability and object/link verification. No SHA is automatically
admitted because it happens to be the latest branch tip. Official KernelSU
`main` at this audit matched the existing reviewed SHA, but an unpinned
latest policy is still ineligible for the immutable gate.

## What is implemented

`kernelforge.compatibility_gate.evaluate_reviewed` is a read-only admission
preflight on *declared* `versions.lock` records. It requires a pinned full
lowercase Commit for kernel, provider and SUSFS; exact repository identities;
an exact Android GKI; explicitly reviewed provider/family mapping; complete,
unchanged catalog matrix; and matching local adapter SHA256. Duplicate manifest
keys, untrusted additions, moving branches, unexpected refs and path traversal
fail closed. It does not mutate locks, checkouts or patches.

**Important boundary:** This is a declaration-level preflight only.
`kernelforge.compatibility.select` must still independently inspect the exact
real Git HEAD values, the original upstream patch digest, adapted patch digest
and unchanged upstream +/- lines before actual integration. Unit tests or a
manifest label never prove Git checkout integrity or compile success.
The gate always returns `release_eligible=false` and
`archive_build_input_eligible=false`. It does not replace the current
integrator or turn a quarantined archive into a Git checkout.

The opt-in real GKI source-validation entrypoint
`scripts/validate_upstreams.py` now calls `review_pinned_request()`
**before workspace creation or any download**. A pinned SUSFS request with a
new/unreviewed provider SHA is rejected, including explicit exact-SHA
overrides. This stops unchecked requests before paying for an upstream checkout.
Moving branch probes and no-SUSFS builds retain experimental functionality,
but their report records `NOT_ADMITTED_MOVING_OR_NO_SUSFS` and
`release_eligible=false`. The existing integration selector still performs
the independent actual-Git/patch-content checks.

Negative/regression tests run in ordinary Windows/Linux `Validate` CI.
Do not launch an 8-job GKI matrix, 35-project Repo sync, OnePlus OKI build,
release or PR merge for this stage without separate authorization.

## Acceptance boundaries

- Historical [Run 45105067150](https://github.com/20592504720/KernelForge/actions/runs/45105067150)
  is valid only for the stated BakaSU `2734e0bc...` + SUSFS `756abbf...`
  + ACK 6.1 `498f91c...` object/link scope; **no full vmlinux or Image**.
- The current BakaSU `63ad1ea...` tip is unreviewed and must not inherit
  the previous compilation claim.
- OnePlus 13 DFR include dynamic reachability remains
  `BLOCKED_UNDETERMINED`; complete OEM modules, ABI/KMI, device boot and
  Root/SUSFS runtime remain `UNTESTED`.
- PR #1 remains open and `main` unchanged; Stage 6.5 will reconcile
  Stage 6.1–6.4 evidence into an explicit scoped acceptance report.
