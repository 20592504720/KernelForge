# Round 2 security hardening

Baseline: ba67eeba267d0717219d25b11cc3bbc7831aa665. No real kernel builds, source lock changes, main updates, or PR merge.

* Toolchain reuse now compares the installed tree against a separate extraction of the pinned archive before version probes. Reject links, reparse points, hardlinks and mode/content mismatches. The proof costs temporary disk and extraction time. An extraction-resource failure blocks rather than authorizing use. Cache metadata alone remains only an inventory hint, not proof.
* Invalid cache with a live lease is not moved. Strict SHA256 cache keys and layout checks prevent malformed metadata from choosing arbitrary maintenance targets. No destructive fallback when quarantine fails. This is not a defense against simultaneous arbitrary writes by another process with the same permissions.
* Published generic build logs are filtered before writing, including failure and timeout output. Overlong lines are dropped, control characters normalized, published output capped at 128 MiB plus a marker. Private OS temporary spool is not a hard disk quota; arbitrary secret encodings and child processes are not completely contained. Never supply secrets to build scripts. Other evidence producers are not covered by this log policy.
* Run Bandit and pip-audit on relevant changes. Bandit inventory is report-only until findings are reviewed; scanner errors fail the job. A successful scanner run is not proof of zero findings.
* Seven exact development dependency versions and 13 distinct wheel SHA256 values are locked in requirements-dev.txt. Two independent Actions jobs each downloaded 28 wheel records for Linux/Windows x86-64 CPython 3.11/3.12 and produced identical hash lists. Pip hash-checking and wheel-only modes are mandatory. This does not lock the scanner tooling itself or prove the publisher is uncompromised. CodeQL is not yet active.
* OnePlus 13 remains blocked from the generic build entry point; the real Stage 7.5 gate is pending.

References: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html ; https://pip.pypa.io/en/stable/topics/secure-installs/ ; https://bandit.readthedocs.io/en/latest/start.html

## Evidence at pre-lock commit 5bbaa3b340896a69ab81f5f9ba789cd9eb2a7bea

- Validate run 45295571492: Linux 448/448 each; Windows 408 passed and 40 skipped each, no failures or errors.
- Candidate jobs 138114965397 and 138114994803: 28 wheel records each; identical 7 requirement lines and 13 distinct hashes.
- Bandit job 138114965643: 2 HIGH, 8 MEDIUM, 57 LOW; no scanner errors. Report-only, not a clean security verdict. Both HIGH findings (B324) are SHA-1 computations for Git blob identities, not cryptographic signatures. Git compatibility requires that hash; separate SHA256 archive integrity remains required. MEDIUM findings are network URL and XML parsing sites, requiring individual review.
- New lock must pass the fresh four-platform Validate matrix before claiming compatibility.
