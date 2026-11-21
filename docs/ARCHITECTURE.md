# Architecture

The repository is organized around separate responsibilities: `configs/` describes inputs, `schemas/` defines accepted structure, `scripts/` contains orchestration modules, `patches/` will own reviewed patch manifests, and `.github/workflows/` runs validation and later build jobs.

The current build engine separates source acquisition (`kernelforge/source.py`), tool inspection (`toolchain.py`), and GKI/Vendor command adapters (`build.py`). Adapters accept explicit argv arrays and never pass through a shell. They require a profile to define repository/ref, commands, tools, and artifact paths. Config presence is not compatibility evidence; compatibility must be established against checked-out source and recorded in build reports.
