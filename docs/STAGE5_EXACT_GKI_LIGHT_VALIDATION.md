# Stage 5 exact BakaSU GKI entry — local lightweight validation (2026-11-23)

Scope: no Actions dispatch, `repo sync`, toolchain download or kernel compilation. The remote development baseline before this check was Commit `22cf51531cd43627175967a88b9539ea6a80b83e`, Tree `7d142426ed4a0c38d3b8e2d22fcc54b9fe1d8ed3`. The local history has different parents; cherry-picking that one remote commit produced the same Tree. The **tested code Tree** after the two-file preflight fix, before this documentation file, is `9219c86fd1a38e8f7399144f21bcdffbae3452c7`. The final documentation Commit/Tree should be taken from Git after submission.

## Finding and narrow fix

The incoming `exact_bakasu` job validated `exact_bakasu_commit` only after `actions/checkout`, `actions/setup-python` and `pip install`. A malformed nonempty input therefore selected the single job and could download dependencies before being rejected. This did **not** meet the requested pre-download admission rule.

The job now starts with a no-network Bash step that accepts only `^[0-9a-fA-F]{40}$` and exits 2 otherwise. It passes the expression through an environment variable rather than embedding the value in shell source. Checkout, Python setup and package installation follow that first step. The existing Python parser still validates and normalizes the Commit, and `choose_pinned_provider_commit` still requires `--provider bakasu --susfs --pinned-baseline` before creating a report/workspace. No GKI, SUSFS or BakaSU source lock or patch allowlist changed.

The two job conditions were read from parsed YAML. For manual dispatch with a nonempty exact input, `sources` is skipped and `exact_bakasu` is selected; for blank input, the original `sources` 2×2×2 matrix remains selected and the exact job is skipped. PR/schedule use the existing matrix path, with the same-repository PR guard. This is a **static expression/step-order audit**, not GitHub Actions runtime acceptance.

## Executed checks

All commands ran from the local Windows project on the tested code Tree. Full output is retained locally in `E:\内核构建\reports\stage5-exact-gki-entry-final.log`, SHA256 `6e15b2d330aaf79aadb5630422976da9f1b77b9c9ad40e9b4aaf82da220088c5`.

| Check | Result |
| --- | --- |
| `python -m compileall -q kernelforge scripts tests` | exit 0 |
| `python -m unittest discover -s tests -p test_exact_gki_validation.py -v` | **8/8**, exit 0 |
| `python -m unittest discover -s tests -p test_stage46.py -v` | **25/25**, exit 0 |
| PyYAML `BaseLoader` parse plus expected event, job and first-step assertions | exit 0; `pull_request`, `schedule`, `workflow_dispatch`; jobs `sources`, `exact_bakasu` |
| WSL Bash `-n` on the first step | exit 0 |
| WSL Bash first step with `main`, a 12-character SHA, and the full `2734e0bc155759955880f5fb99be640fc5b92156` | exits **2, 2, 0** respectively; no checkout/download in this local probe |

The new tests cover a full 40-hex SHA, case normalization, branch/tag/short/nonhex rejection, required option combination, malformed CLI failure before a workspace exists, and workflow step order. Existing Stage 4.6 tests continue to cover exact old/new adapter selection, mismatched identities, patch hashes, changed upstream code lines, path safety and patch-context reversal. **33/33 targeted unit tests passed; 0 failed.** The original six exact-entry tests passed before the fix, but their result did not establish pre-download validation; the final eight-test run above is the acceptance evidence for this local change.

## Limits and remaining work

- **UNTESTED:** GitHub Actions expression evaluation/runtime behavior and the actual manual dispatch; PyYAML syntax and static conditions cannot prove those. No workflow was triggered here.
- **UNTESTED:** exact new BakaSU + SUSFS on real ACK 6.1 ARM64 objects, relocatable link, Image, boot or Root behavior. The old [7/8 GKI failure](https://github.com/20592504720/KernelForge/actions/runs/45020470109/job/137201998796) remains historical evidence of the original-patch conflict, not evidence of this new entry succeeding.
- `[skip ci]` on the documentation/fix submission avoids a large automatic push/PR matrix. Per [GitHub's skip-workflow documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs), skipped required checks may remain pending; this is not a passing CI result. Stage 5 remains **IN_PROGRESS** pending a separately authorized targeted real-source run.
