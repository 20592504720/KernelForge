# Development

Use Python 3.11+ and install `requirements-dev.txt`. Run `python -m kernelforge validate`, `validate-config`, `validate-patches`, or `doctor` from the repository root. Run tests using `python -m unittest discover -s tests -v`.

Keep adapters separate by build system and feature. Compatibility must be based on checked-out source/Kconfig and reported explicitly. UNKNOWN must never be promoted to PASS. Patches remain disabled until upstream, revision, hash, scope, and result are verified. Do not commit credentials or execute unreviewed remote scripts.

CI runs the local validator and tests. The manual build workflow is preflight only. Release is disabled until real build and artifact verification exist.
