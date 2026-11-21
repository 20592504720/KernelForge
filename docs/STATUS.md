# Stage 1 report

## Completed

- **IMPLEMENTED:** modular repository structure, strict schemas, five kernel profiles, CLI validation/doctor commands, versioned empty patch manifests, and GitHub Actions workflows.
- **TESTED:** JSON/schema checks, Python compilation, workflow YAML parsing, profile coverage, invalid configuration, missing manifest, and hash failure cases.

## Not implemented

- **IMPLEMENTED:** configured source checkout, tool version checks, separate GKI and Vendor command adapters, build logging, duration and SHA256 reports for real produced artifacts.
- **TESTED:** adapter selection and build failure paths are covered by stage-two tests.
- **NOT_IMPLEMENTED:** automatic toolchain download/cache, project-specific validated GKI/Vendor profiles, KernelSU integration, patch application, SUSFS, TCP/ZRAM detection, verified device builds.
- **PLACEHOLDER:** GitHub build workflow remains preflight-only pending reviewed build profiles; release workflow is disabled; PJZ110 profile explicitly unverified.

## Tests

Run `python scripts/validate.py` and `python -m unittest discover -s tests -v`. Results from the current authoring environment are recorded in the delivery report, not assumed from this file.

## Blockers and next stage

This stage has no known implementation blocker. Stage 2 should implement source pinning, toolchain inspection, and genuinely separate GKI and Vendor adapters with explicit missing-input and build-failure handling.
