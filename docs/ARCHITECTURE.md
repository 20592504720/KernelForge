# Architecture

The repository is organized around separate responsibilities: `configs/` describes inputs, `schemas/` defines accepted structure, `scripts/` contains orchestration modules, `patches/` will own reviewed patch manifests, and `.github/workflows/` runs validation and later build jobs.

Stage 1 deliberately ships only configuration validation. Later stages should add distinct GKI and Vendor adapters, toolchain resolution, KernelSU adapters, a transactional patch manager, feature/Kconfig inspection, and artifact packaging as separate modules. Config presence is not compatibility evidence; compatibility must be established against checked-out source and recorded in build reports.
