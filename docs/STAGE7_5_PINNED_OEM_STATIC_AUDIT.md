# Stage 7.5 — independent GitHub audit of exact pinned OEM source (STATIC)

**Scope: read-only public GitHub source at the exact 35-project lock SHAs.**
No local WSL files, Bazel query/compile, source sync, cache, device or
host-specific build outputs were accessed. The conclusions below are **source
syntax and macro-definition evidence, not a resolved Bazel action graph**.
Antigravity must reconcile with the real WSL2 checkout before accepting any
target for a build. Do not modify 35 source SHAs.

## Immutable source references

- `kernel_platform/msm-kernel` pinned Git Commit
  `6028f47faddaa27700f8dd3a1d83906ea8f27170`:
  [OnePlusOSS android_kernel_oneplus_sm8750](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/tree/6028f47faddaa27700f8dd3a1d83906ea8f27170).
- Root OEM module tree `./` pinned Commit
  `d50b305f7da9e14715a25120a4ac7b1a4b8b97c3`:
  [OnePlusOSS modules and devicetree](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/tree/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3).
- `kernel_platform/common` pinned Commit
  `e1b346b6b4f4096eb342ae3684838a942fd6f6c4`.
- All three above identities come from the approved 35-project
  `manifests/oneplus13-pjz110-sm8750-source.lock.json`.
  Selected Manifest remains `f8e50677874c65b6da41057d2f39be7b4ef3c08a`.

## Kleaf target naming: defensible static leads, not approved labels

1. [`msm-kernel/target_variants.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/target_variants.bzl)
   lines 9–13 declares `la_variants = ["consolidate", "perf"]`.
2. [`msm-kernel/sun.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/sun.bzl)
   lines 8–10 sets `target_name = "sun"`, while lines 413–459
   iterate each LA variant and call `define_msm_la()` (also
   `define_msm_16k_la()`).
3. [`msm-kernel/msm_kernel_la.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/msm_kernel_la.bzl)
   lines 455–464 constructs the target name as
   `msm_target.replace("_", "-") + "_" + variant.replace("_", "-")`.
   Lines 162–174 define `kernel_build(name=target)`, and lines 320–415
   define an associated `<target>_dist` rule.
4. [`msm-kernel/msm_platforms.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/msm_platforms.bzl)
   lines 19–29 invokes `define_sun()` through the platform macro.

**Static candidate names:** `//msm-kernel:sun_perf`,
`//msm-kernel:sun_consolidate` and their `_dist` counterparts, IF the
reviewed build loads/calls these macros under its actual Bazel workspace.
This does not prove the macros are instantiated by the effective root
BUILD file, the labels are queryable, or the targets produce BOTH requested
Image and vmlinux in the intended configuration.

**Important nuance:** `msm_kernel_la.bzl` lines 156–174 lists `.config`,
`Module.symvers` (and DTB/DTBO) as the direct `kernel_build` outputs and
references a `base_kernel` `//common:kernel_aarch64` for non-consolidate
(or `kernel_aarch64_consolidate`). Whether Image/vmlinux are accessible
as direct outputs, output groups or dist artifacts is a question for the
resolved action graph. **Do not guess paths or claim a bare `sun_perf`
command automatically yields the desired bundle.**

An OEM shell wrapper
[`kernel_platform/oplus/build/oplus_build.sh`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/build/oplus_build.sh)
lines 165–171 selects `KERNEL_TARGET=\${OPLUS_KERNEL_PARAM:-sun}`,
`consolidate` for userdebug and another OEM-configured variant for other
build types. This wrapper is evidence of naming conventions, **not** an
approved standalone fast build; it also contains unrelated full-image and
OEM environment logic.

## DFR is present at the exact pinned OEM source revision

- [`kernel_platform/oplus/config/modules.ext.oplus`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/config/modules.ext.oplus)
  line 19 explicitly lists `../vendor/oplus/kernel/dfr`.
- The directory `vendor/oplus/kernel/dfr` **exists** at this exact pinned
  commit and contains `BUILD.bazel`, `Kconfig`, `Makefile` and
  `oplus_local_modules.bzl`.
  [`vendor/oplus/kernel/dfr/BUILD.bazel`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/vendor/oplus/kernel/dfr/BUILD.bazel)
  lines 7–9 loads and invokes `define_oplus_local_modules()`.
- [`vendor/oplus/kernel/dfr/oplus_local_modules.bzl`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/vendor/oplus/kernel/dfr/oplus_local_modules.bzl)
  lines 7–19, 21–50 etc define several DDK modules with explicit
  `ko_deps` on other DFR targets; lines 264–295 define an aggregate
  distribution rule `oplus_bsp_dfr`. This is not an unimportant optional
  text include to simply delete.
- [`kernel_platform/oplus/bazel/oplus_modules_define.bzl`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/bazel/oplus_modules_define.bzl)
  lines 121–137 connects DDK targets to
  `kernel_build = "//msm-kernel:{}_{}".format(target,variant)`.
  [`oplus_modules_variant.bzl`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/bazel/oplus_modules_variant.bzl)
  lines 1–4 selects `["sun", "parrot"]` and `["perf"]`.
- [`modules.vendor_boot.list.oplus`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/config/modules.vendor_boot.list.oplus)
  includes `oplus_bsp_dfr_reboot_speed.ko`, another explicit DFR trace.

**Classification: `DFR_SOURCE_PRESENT_STATIC`,
`FAST_IMAGE_DFR_REACHABILITY=UNDETERMINED`.**
DFR being present is not enough to establish whether the fast kernel
Image/vmlinux label needs DFR DDK modules. Resolving this requires the
actual OEM Bazel package load graph and usually a bounded no-fetch
`cquery/aquery`, which may create cache/output; it is NOT authorized by
this read-only review. The DFR include must not be removed or masked.

## Remaining physical-WSL verification

The first [Antigravity handoff](STAGE7_5_ANTIGRAVITY_HANDOFF.md) must check:
exact file byte identities and local BUILD macro load/call, fast Image/vmlinux
output groups, DFR reachability, actual `KBUILD_BUILD_TIMESTAMP` /
`SOURCE_DATE_EPOCH` propagation mechanism, safe Bazel/cache roots,
physical E: disk and WSL RAM/swap. Nothing in this document constitutes
a run of Bazel or an approved compile.


## 2026-11-25 addendum — core Image DFR reachability

The original static classification above is retained as the historical audit result. The subsequent pinned-source trace in [Stage 7.5 DFR static reachability addendum](STAGE7_5_DFR_STATIC_REACHABILITY_ADDENDUM.md) supersedes only the `FAST_IMAGE_DFR_REACHABILITY` question: the external DFR DDK package is not selected by the macro-defined core `sun_perf`/`sun_consolidate` kernel_build/dist path. It does **not** resolve the separate external DFR DDK build, repair its broken include symlink, validate Bazel action graphs, or authorize compilation.
