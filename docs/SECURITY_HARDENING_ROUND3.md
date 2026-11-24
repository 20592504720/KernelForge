# Round 3 — targeted Bandit follow-up

Baseline: 4c3a3220df88dac6b9a37ec0c188ec4c726005d6. No main, PR merge, source lock, real kernel build or device modifications.

- B324: retain Git blob SHA-1 identity compatibility; explicitly mark non-security use, do not change Git object format. Separate archive SHA256 checks remain mandatory. This is not a claim of collision resistance.
- B314: shared bounded UTF-8 XML parser (2 MiB, depth 32, 20,000 elements), forbid DTD/entity declarations before parsing, reject duplicate official project names. Applied to the four prior parse sites. This does not authenticate the manifest.
- B310: exact HTTPS origin and standard port, no URL credentials, fragments, or unapproved queries; validate each redirect BEFORE connecting; bound responses and release rows. Apply to four previous metadata fetch sites. Custom toolchain archive downloads are distinct and retain pinned SHA256 checks; no claim of general SSRF protection.
- Low severity findings: predominantly subprocess imports/argv execution and PATH-based Git binaries. They are not automatically safe; trusted runtime PATH and trusted build configuration remain required. No blanket nosec or suppressed rules.
- CodeQL Python analysis added with the official verified v4 action commit 1bd86f2fdb4b86187fa4059f16f31a3202acc9ea (v4.39.4 release branch). Actual run and alert results must be inspected; no clean verdict assumed.
- History secret scanning and concurrent cache/log resource protection are pending separately; no credential values should be printed.
- Existing build_eligible=false policy retained.

Reference: https://docs.python.org/3/library/xml.html ; https://github.com/github/codeql-action/commit/1bd86f2fdb4b86187fa4059f16f31a3202acc9ea
