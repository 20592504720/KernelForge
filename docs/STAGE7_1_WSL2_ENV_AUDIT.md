# Stage 7.1 WSL2 local environment audit

**Status:** local environment inventory **TESTED**; toolchain execution and OnePlus 13 build **UNTESTED/BLOCKED**. This audit used only passive file, process-environment and resource inspection. It did not run Bazel/Bazelisk, Repo sync, compilers, installers, downloads, or a kernel build. Source and caches were not changed.

## Baseline and raw evidence

- Branch: `stage1/initial-foundation`. Remote input commit `e17229705bfa220597439eb60b2463eee1bbfe0e`; local input commit after safe cherry-pick `c1ca40dc038b6760924a59f8d01802ea7fdfef8c`; both input Trees `27db8d5c158650e5b0b9485b4fd7c830e200cb95`. The different commit hashes reflect the connector-maintained remote history; no reset was used.
- Windows project: `E:\内核构建\project`; ext4 workspace: `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`. The workspace, `.repo`, `.repo/manifests` and selected manifest entry are present (**TESTED presence**). The previous 35-project identity/content proof was not rerun here (**UNTESTED in this audit**).
- Ran `python3 -B scripts/stage7_1_preflight.py --workspace /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750 --host-path /mnt/e` from the project directory. Exit code **0**. Its result is `REPOSITORY_PREFLIGHT_TESTED_WITH_BLOCKERS`; its local portion explicitly says inventory, not build validation.
- Raw files: `E:\内核构建\reports\stage7_1_local_inventory.json` (SHA256 `442790b4b32d6ba3525e7a962c135a2ca07ec47d3eb62f7f5fe14500c8b96e30`), `stage7_1_passive_probe.json` (`93caa77f8cc68624813e47081a7772c02efe472af083533ea4d2e9d0cb6e250a`), `stage7_1_system_snapshot.txt` (`516b901f2cfe8097623b34451d0c5a8376c41d50e15c90403874820ad42eba2a`). Full paths, digests and item statuses are in [the machine-readable result](evidence/stage7_1_wsl2_environment.json).

## Resources

| Check | Observation | Status |
| --- | --- | --- |
| Host | Ubuntu WSL2, Linux `6.18.58.1-microsoft-standard-WSL2`, x86_64, 8 logical CPUs, Python 3.12.3 | **TESTED** |
| RAM and swap | 3.77 GiB WSL RAM; about 3.25 GiB available at sampling; 1.00 GiB swap | **TESTED** snapshot; sustained-build adequacy **UNTESTED** |
| ext4 virtual filesystem | 1,081,101,176,832 bytes total; 860,100,542,464 bytes free; 66,821,557 free inodes | **TESTED** filesystem report |
| Physical Windows E: | 371,516,764,160 bytes total; 198,101,848,064 bytes free (184.50 GiB) on the final Windows sample | **TESTED**; the 50 GiB reserve is currently met |
| `/mnt/e` inodes | WSL reports inconsistent NTFS inode totals; this is **not** a meaningful capacity measure | **UNTESTED** inode interpretation |

The ext4 virtual filesystem advertises about 801 GiB free, but its VHDX grows on E:. **The physical E: free space is the binding limit.** Only about 134.5 GiB could be consumed before the required 50 GiB safety reserve, and future Bazel output size has not been measured. WSL's roughly 4 GiB RAM is also a material risk for a real OKI build.

## Tools and versions

Let `W=/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750/kernel_platform`. File type, resolved target, size and SHA256 for every checked executable are recorded in the machine result. SHA256 verifies the bytes observed locally; it does not certify upstream provenance or runtime compatibility.

| Tool | Observed location and type | Version evidence | Status |
| --- | --- | --- | --- |
| Bazel/Kleaf | `$W/tools/bazel` symlink → `$W/build/kernel/kleaf/bazel.sh` wrapper → `bazel.origin.sh`/`bazel.py` → `$W/prebuilts/kernel-build-tools/bazel/linux-x86_64/bazel`, itself a symlink to an x86-64 ELF | Target filename says `bazel-7.1.1-linux-x86_64`; binary SHA256 `d93508529d41136065c7b1e5ff555fbfb9d18fd00e768886f2fc7dfb53b05b43` | File/path **TESTED**; executed version **UNTESTED**. Neither `bazel` nor `bazelisk` is on `PATH`. |
| LLVM Clang | `$W/prebuilts/clang/host/linux-x86/clang-r510928/bin/clang`, x86-64 ELF | `r510928` directory pin; SHA256 `dc739fc44bb889146bd47732912cad457200af7de7c2fb5a7509b7a9974d6d67` | File/path **TESTED**; executed version **UNTESTED**. |
| LLD and LLVM NM | Same `clang-r510928/bin`; `ld.lld` symlink → `lld`; `llvm-nm` ELF | SHA256 `27fdf99341929eab1f615a3172169b8dadd117b76a05b0abfa0a21873d1626a0` and `06e6634e0abe46ce464e09907955d5202451f7c545896e4c56162b721e74e3a6` | File/path **TESTED**; runtime **UNTESTED**. |
| GNU Make | `$W/prebuilts/build-tools/linux-x86/bin/make`, x86-64 ELF | SHA256 `a9472ab2dc5ab512bd946ca73dc84e4d911df4ad028f48bdbfaf3a500a88ffee` | File/path **TESTED**; runtime version **UNTESTED**. |
| Rust | `$W/prebuilts/rust/linux-x86/1.73.0b/bin/rustc`, x86-64 ELF | Directory says `1.73.0b`; SHA256 `0b0909f6a20e94ab2ae38d7875629ed0b4d334906cb6e3c23d01c57994c1b763` | File/path **TESTED**; runtime version **UNTESTED**. |
| Java | `$W/prebuilts/jdk/jdk11/linux-x86/bin/java`, x86-64 ELF | Static `release` file declares `JAVA_VERSION="11.0.15"`; executable SHA256 `fda7b89fcfe8f0ddecc4607731061df717fc5d47b7d94e855fcb4967a7d3a65b` | File/path and declared version **TESTED**; runtime **UNTESTED**. |
| Git, Repo, Python | `/usr/bin/git` ELF, `/usr/bin/repo` script, `/usr/bin/python3` ELF | Path and SHA256 in JSON; Python interpreter reports 3.12.3 | Paths **TESTED**; Git/Repo runtime versions **UNTESTED**. |
| GCC and ccache | No `gcc`, `gcc-11` or `ccache` on `PATH`; no GCC compiler executable found at the previously checked host-prebuilt path | Absence on `PATH` does not prove the target needs GCC | Availability for the chosen build **UNTESTED**; ccache acceleration **BLOCKED_MISSING**. |

The Kleaf Bazel entry is a wrapper and may select remote-cache behavior from environment variables; it was **not executed**. Bazel/Bazelisk `--version` was intentionally not invoked, so no auto-download or cache creation occurred.

## Existing caches and outputs

- WSL `~/.cache/bazel`, `~/.cache/ccache`, `~/.ccache`, `~/kernelforge/.cache/toolchains`, `~/kernelforge/builds` and source `kernel_platform/out` / `bazel-out` are absent (**TESTED presence**).
- Existing `E:\内核构建\cache` and `toolchains` directories are empty at their top level. `E:\内核构建\builds\stage45-local-validation` and `artifacts\stage46-bakasu-config.zip` remain present. No cleanup was performed.
- `.repo` and `.repo/manifests` remain present. Recursive cache/source sizes were **UNTESTED_RESOURCE**; the prior Stage 6.3 source measurement was not repeated.

## Readiness answer and blockers

**Stage 7.2 toolchain mirror development: conditionally ready.** WSL2 ext4, the existing source layout, Python/Git, identifiable pinned prebuilts and current E: free capacity are enough to design and test a mirror manager in an isolated project/report area. Mirror provenance, SHA256 policy, version pinning and cache isolation still need implementation and review. This audit does not authorize a download.

**Bounded OnePlus 13 build validation: not yet ready (`BLOCKED`).** The device profile still lacks an explicit toolchain pin and firmware build identity; ABI/KMI is untested; DFR external module dependency remains `BLOCKED_UNDETERMINED`. The WSL memory limit, physical E: reserve and output/cache growth need a separately bounded plan. Existing prebuilt files do not prove they run together successfully. No Stage 7.2 development or build was started in this task.
