# Round 2 security hardening

Baseline: ba67eeba267d0717219d25b11cc3bbc7831aa665. No real kernel builds, source lock changes, main updates, or PR merge.

* Toolchain reuse now compares the installed tree against a separate extraction of the pinned archive before version probes. Reject links, reparse points, hardlinks and mode/content mismatches. The proof costs temporary disk and extraction time. An extraction-resource failure blocks rather than authorizing use. Cache metadata alone remains only an inventory hint, not proof.
* Invalid cache with a live lease is not moved. Strict SHA256 cache keys and layout checks prevent malformed metadata from choosing arbitrary maintenance targets. No destructive fallback when quarantine fails. This is not a defense against simultaneous arbitrary writes by another process with the same permissions.
* Published generic build logs are filtered before writing, including failure and timeout output. Overlong lines are dropped, control characters normalized, published output capped at 128 MiB plus a marker. Private OS temporary spool is not a hard disk quota; arbitrary secret encodings and child processes are not completely contained. Never supply secrets to build scripts. Other evidence producers are not covered by this log policy.
* Run Bandit and pip-audit on relevant changes. Bandit inventory is report-only until findings are reviewed; scanner errors fail the job. A successful scanner run is not proof of zero findings.
* Reviewed dependency-wheel hash lock and CodeQL are not yet active. The candidate generation step is separately tracked.
* OnePlus 13 remains blocked from the generic build entry point; the real Stage 7.5 gate is pending.

References: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html ; https://pip.pypa.io/en/stable/topics/secure-installs/ ; https://bandit.readthedocs.io/en/latest/start.html
