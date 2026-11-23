# Stage 6.3 WSL2 source and layout audit

Status: **PARTIAL_TESTED_WITH_BLOCKERS**. This is an audit of the existing OnePlus 13 Repo workspace and three local archive fixtures. It is not a vendor archive certification, kernel build, ABI/KMI check, or device test.

## Identity and method

- Existing Ubuntu 24.04 WSL2 ext4 workspace: `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`.
- Existing manifest Git checkout: `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750/.repo/manifests`, HEAD `f8e50677874c65b6da41057d2f39be7b4ef3c08a`, matching the untouched 35-project lock. Pinned XML blob SHA256: `3c4f547f4926d449094023ab6bb33047fbdc9d1308464c4242b369cc6cf3290a`.
- The remote implementation Commit was `b23f6f60b4cdb01385cacbe9915978e47d7ef15f`. The local branch retains its previous independent history; after safe cherry-picks its code Tree is identical to that remote Commit's Tree, `3fe65d903fc3140853728cce247caf15e2579bb1`. No source lock or historical checkout was changed.
- At the initial environment check, the Windows E: host had 198,413,168,640 free bytes (about 184.8 GiB). WSL ext4 `df` showed about 802 GiB virtual free space; host capacity is the meaningful limit. No active `repo sync`, Git fetch, or Git clone process was found. No new 35-project sync or kernel build was started.

The exact read-only command was:

```sh
python3 -m kernelforge.repo_workspace_audit \
  --lock manifests/oneplus13-pjz110-sm8750-source.lock.json \
  --workspace /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750 \
  --manifest-checkout /home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750/.repo/manifests
```

It exited **0** and returned `PASS` for its stated scope. The [machine-readable acceptance record](evidence/stage6_3_wsl2_acceptance.json) contains all **35** actual Commit and Tree SHAs, source paths, link inventory and fixture proofs. The original stdout report is `E:\内核构建\reports\stage6.3-oneplus13-workspace-audit.json` (SHA256 `d929979e5976447d243bf90a6f350d27c4f8df849d4cce5472f92a5284649851`); its original stderr contains only the existing WSL localhost proxy warning. The acceptance record itself has SHA256 `fde72fdc5479f8883cd4bc1aacf61fff428cdc39d52daa705bfada7c3f679e88`.

## Actual source and Repo layout

| Check | Result |
| --- | --- |
| Manifest HEAD and authenticated `oneplus_13_b.xml` Git blob | **TESTED**, matches pinned Commit |
| All 35 project HEADs | **TESTED**, 35/35 equal to locked full SHAs; 35 actual Tree SHAs recorded |
| `./` root project | **TESTED** identity: `android_kernel_modules_and_devicetree_oneplus_sm8750`, Commit `d50b305f7da9e14715a25120a4ac7b1a4b8b97c3`, Tree `8cb71dcf592a530ffaafaf3c2b588f9094a0fd7e`; 20,684 tracked entries |
| Root versus 34 child mount paths | **TESTED** file-path inventory: zero root-tracked files under child mount prefixes; no non-root nested mounts |
| `src="."` linkfile | **TESTED**: `kernel_platform/.source_date_epoch_dir` is a symlink named `common` resolving to the existing `kernel_platform/common` **directory** |
| `src="build_with_bazel.py"` linkfile | **TESTED**: `kernel_platform/build_with_bazel.py` is a symlink named `msm-kernel/build_with_bazel.py` resolving to that existing **regular file** |
| Missing/uninitialized project checkout, wrong HEAD, linkfile diversion | **None found** by the auditor's checks |

The separate tracked-link inventory read all 35 Git Trees: **1,206** symlinks were present on disk and their link-target bytes matched Git blob identities; **0** gitlinks, **0** symlink escapes outside the workspace, and **0** missing symlink entries were found. However, **29 symlink targets are absent**. They include the root project's `mkdtboimg.py` and vendor paths, several Rust non-Linux-host convenience links, and `llvm-binutils-stable` references to `clang-r522817`. Exact paths and raw targets are in `E:\内核构建\reports\stage6.3-layout-diagnostics-final.json` (SHA256 `f2b6382c1ad4cfaa0e7460d008bdc1862715f0ae470eda845ac4bdc5254a1bd5`). These are **BLOCKED / requires upstream-layout or build-dependency investigation**, not automatically repaired or declared harmless. The two manifest Repo linkfiles above are valid and are not among the 29.

## Representative archive comparison

Only local `git archive --format=tar HEAD` fixtures were created in temporary WSL ext4 directories and compared with the existing locked Git checkouts using `verify_archive_git_tree`. No independent vendor archive was available. The three source projects contained no symlink or gitlink entries:

| Project | Files / bytes verified | Git Tree SHA | Result |
| --- | ---: | --- | --- |
| `kernel_platform/external/bazelbuild-platforms` | 25 / 36,799 | `52f475abdac0c030d9740f8a6d333456d693dd15` | **TEST_FIXTURE_ONLY** |
| `kernel_platform/external/bazelbuild-rules_license` | 98 / 267,851 | `39314478665e3c080e3df6fe4a97609182f089b5` | **TEST_FIXTURE_ONLY** |
| `kernel_platform/external/zopfli` | 50 / 718,672 | `e0025a0ae967935ec8c3f00af7f9bae5dab5b6c0` | **TEST_FIXTURE_ONLY** |

For the first fixture, modified bytes, one missing file and a changed executable bit were each rejected with the expected distinct error. The source files were untouched; only temporary extracted copies were changed, and the temporary directories were removed when the comparison finished. The complete results and local fixture archive SHA256 values are in `E:\内核构建\reports\stage6.3-archive-fixture-results.json` (SHA256 `139581fa91e2de5ca1a28e1cf0536adee8efef1de9723478aab7508d73772885`). The current archive preflight refuses symlinks: **14/35** real project Git Trees are `BLOCKED_UNSUPPORTED_LINKS` for that acquisition path. A local fixture cannot establish independent vendor archive provenance or eligibility for Build/Patch Manager.

## Remaining classification

- **TESTED:** pinned Manifest identity, 35/35 Commit matches and Tree recording, root project identity, two materialized Repo linkfiles, tracked-link byte identities, three local fixture comparisons and their negative checks.
- **UNTESTED:** full 35-project working-file byte equivalence, independently sourced vendor archive equivalence, complete OnePlus 13 OKI build, ABI/KMI, firmware match, device boot and Root/SUSFS runtime.
- **BLOCKED:** 29 unresolved tracked symlink targets need source-layout and build-impact diagnosis; 14 projects containing links cannot enter the current archive equivalence path. No link was fixed or ignored.

The original audit JSON, archive fixture JSON, detailed link inventory, generated scripts and stderr logs remain separately under `E:\内核构建\reports`. No source, `.repo`, cache, lock, patch, device image or PR was modified by this validation.
