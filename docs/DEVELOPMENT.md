# Development

Use Python 3.11+ and install `requirements-dev.txt`. Run `python -m kernelforge validate`, `validate-config`, `validate-patches`, or `doctor` from the repository root. Run tests using `python -m unittest discover -s tests -v`.

Keep adapters separate by build system and feature. Compatibility must be based on checked-out source/Kconfig and reported explicitly. UNKNOWN must never be promoted to PASS. Patches remain disabled until upstream, revision, hash, scope, and result are verified. Do not commit credentials or execute unreviewed remote scripts.

CI runs the local validator and tests. The manual build workflow is preflight only. Release is disabled until real build and artifact verification exist.

Build profiles define an immutable source `ref` where possible; the checkout records the resolved full Commit SHA and runs Git connectivity checks before execution. GKI and Vendor each provide their own argv, build directory, environment, targets, artifact globs, and additional required tools. Shared tool requirements can specify an executable name or path, version arguments, and numeric minimum. Toolchain downloads/caches are implemented (Stage 3). Build runs serialize on a workspace lock; success and failure both write `build-report.json`, and configured artifact copies are SHA256 checked.

Stage 4 provider architecture and integration checks are documented in KERNELSU.md.
