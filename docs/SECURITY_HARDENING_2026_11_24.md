# Security hardening following Stage 1–7.4 regression audit

Scope: existing development branch only; no source-lock mutation, actual kernel compilation, release, PR merge or device operation.

Prior audit baseline: `afe8fb7121680a089e5b11a1c505bdbcdffa7fad` (418 discovered tests across Linux/Windows and Python 3.11/3.12).

- F1: artifact files published exclusively with streamed SHA256 verification. Existing output files cause an early refusal; choose a fresh per-build output directory. Reject symlinked output directory components and reserved evidence names. Report staging is unique and atomic. These checks do not establish protection against a concurrently malicious process controlling the output directory.
- F2: portable patch-path syntax; invalid schema entries stop before path interpretation. Validate containment under the specific manifest directory and reject symbolic links and duplicate IDs.
- F3: hard download limit 8 GiB (or smaller caller-specified / exact expected size); archive maximum 32 GiB unpacked, 8 GiB single member, 250000 members; 64 MiB minimum free filesystem space, per-chunk enforcement. These are generic toolchain limits, NOT a WSL physical-host disk quota. Stage 7.4/7.5 physical host reserve and real build gate remain independently required. No archive should be executed merely because these checks passed; manager still requires trusted SHA256.
- F4: best-effort redaction of common URL credentials, authorization headers and recognized tokens in Git error, build argv, reports, and download diagnostics. Raw subprocess build output and arbitrary unknown secret formats are not exhaustively scrubbed; treat logs as sensitive. No claim of exhaustive redaction.
- F5: fail closed if the generic single-repo runner receives the oneplus13-pjz110 profile. Actual official 35-project Repo/Kleaf build remains BLOCKED until separately implemented and reviewed; no ABI/KMI, boot, Root, ccache interception or timestamp propagation claim.
- F6: add independent pip-audit workflow for development dependencies and disable persisted checkout credentials in Validate. Existing Actions remain SHA-pinned. Advisory scanning does not establish absence of vulnerabilities. Full cross-platform dependency artifact hash lock remains pending.
- New regression tests are offline synthetic fixtures, not real kernel compilation.

References: Python zipfile decompression pitfalls; OWASP File Upload and Logging Cheat Sheets; GitHub Actions Secure Use Reference; PyPA pip repeatable/secure installs and pip-audit. All previous acceptance evidence remains historical; new CI result must be inspected separately.
