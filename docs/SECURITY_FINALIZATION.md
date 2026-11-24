# Security finalization — targeted archive-path and CodeQL evidence review

Baseline: 64c1ae421dc0213a8b407a18b88f322d06a58bae. Latest prior scoped one-shot regression 45303277963: 12/12 jobs, 474 tests per OS/Python combination (40 Windows conditional skips per job), five real ACK6.1 Image jobs. Bandit inventory 0 HIGH / 1 MEDIUM / 56 LOW, pip-audit no known vulnerabilities, Gitleaks 146 reachable commits / zero findings. CodeQL uploaded analysis but connector could not list alerts.

- F-01: Stage 6 source archive member and project path checks now reject Windows reserved devices, alternate streams, trailing dot/space aliases and forbidden Windows filename characters in every component on all hosts. The explicit root project "./" remains supported. The shared member validator is used by preflight and source extraction. New offline ZIP/TAR, project-lock and no-promotion regression tests. Trusted archive digest and quarantine are unchanged; this is not proof of an exploitable RCE in the baseline.
- F-02: CodeQL uses its pinned action's supported output directory and emits rule IDs and security-severity counts, including unknown/nonsecurity results, without printing SARIF source snippets or changing the existing GitHub upload. An empty result inventory must not be inferred merely from a successful scan. This workflow change is a candidate until an actual run is reviewed.
- Pending: trusted host executable resolution and Git environment/config boundary, XML/Expat host-version evidence, CodeQL result review, local WSL2 lock digest reconciliation and final regression. No source locks changed; no main edit/merge, OEM build, release or heavy one-shot request authorized. Keep build_eligible=false.
- These changes require fresh cross-platform tests; no new test success is claimed here.

References: https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file ; https://learn.microsoft.com/en-us/windows/win32/fileio/file-streams ; https://docs.python.org/3/library/tarfile.html ; https://github.com/github/codeql-action/blob/1bd86f2fdb4b86187fa4059f16f31a3202acc9ea/analyze/action.yml

## F-03 — Git repository operand boundaries

The generic repository validator's SCP-style form previously admitted an option-prefixed repository string. The KernelSU tag/branch resolution also invoked ls-remote before the generic checkout validator. Reject option-prefixed repository strings before spawning Git; validate the provider repository before direct ref lookup, and delimit repository operands with -- for clone and ls-remote. Existing HTTPS/SSH/file fixtures remain supported. Two offline regression tests assert no Git process is launched for rejected operands. This closes a conditional command-option injection boundary, not a proven remote execution incident. The build profiles, Git runtime PATH and local Git/SSH configuration must still be trusted. No source-lock or request marker change. A local disposable Git fixture verified that clone and ls-remote accept the operand delimiter, but the project suite must pass separately.


## Final scoped acceptance (2026-11-24)

Completed run [45375493788](https://github.com/20592504720/KernelForge/actions/runs/45375493788) passed 12/12 jobs after F-01–F-03. Actual SARIF inventories zero at code baseline; all five downloaded Image SHA256 values and seven ZIP digests independently verified. See [最终安全验收报告](SECURITY_FINAL_ACCEPTANCE_2026_11_24.md) and [structured evidence](evidence/security_final_acceptance_2026_11_24.json). Historical pending statements above describe pre-acceptance state; host/runtime/local OEM limitations remain open.
