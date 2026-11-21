# Workspace migration and platform boundaries

Set `KERNELFORGE_HOME` to your existing workspace root, then run
`python -m kernelforge workspace --init`. Machine-specific paths and migration
manifests remain outside this repository. With this variable unset, existing
CLI defaults continue to work. Explicit build and cache paths take precedence.

The root contains `project`, `sources`, `toolchains`, `cache`, `builds`,
`artifacts`, `logs`, `reports`, `temp`, `manifests`, and `backups`.
`project` contains this Git checkout. Configurations in Git use relative paths;
the local `manifests/workspace.json` records absolute paths for this computer.

## Safe migration procedure

1. Inventory attributable project files, sizes, source/destination paths and
   available disk capacity before copying. Exclude global applications and
   unrelated projects. Refuse destination collisions.
2. Copy, retaining the original. Compare SHA256 for every copied file, including
   Git objects, untracked files and reports. Record the verified inventory.
3. Compare branch, HEAD, tree, complete revision list and dirty status. Preserve
   uncommitted changes; do not reset or replace history.
4. Run configuration validation and all tests from the destination. Use its
   temporary directory for test data. Preserve full logs and exit codes.
5. Set the per-user environment variable and initialize the local manifest.
   A fresh terminal picks up the persisted variable.
6. Produce a cleanup candidate list, with sizes and checksums. Deletion requires
   explicit user approval. A successful copy does not authorize deletion.

Stage 4.6 copied 1,333 files (294,460,194 bytes) across the project and identified
research directories, checking every file hash. The attributable C-drive
checkout is 874,233 bytes. Its original remains intact. The local audit records
are `manifests/stage46-migration-plan.json`,
`manifests/stage46-migration-verified.json`, and
`reports/c-drive-cleanup-candidates.json`. Original research directories also
remain intact. This scan covers known KernelForge task paths, not unrelated
system directories.

## Windows and Linux isolation

Windows is suitable for repository development, configuration and downloads.
Native Windows cannot check out all GKI paths (for example `aux.h`). An NTFS
workspace is **UNTESTED** for real Linux kernel builds, even when accessible
through WSL. No local WSL distribution was available during migration.

Use a Linux runner or a WSL2 ext4 filesystem for real source/build trees. If
deploying WSL later, place its virtual disk on the data drive after separately
checking capacity and backing up distributions. This migration does not move
Windows applications or install/move WSL. Cloud compilation evidence and local
disk migration evidence are separate acceptance results.
