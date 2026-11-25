# Stage 7.5-A — DFR static reachability addendum

Date: 2026-11-25 (Asia/Shanghai)  
Scope: exact pinned OnePlus 13 SM8750 source, read-only public source inspection.  
No Bazel query, cquery/aquery, build, source sync, local workspace mutation or symlink repair was performed.

## Verdict

- `CORE_SUN_KERNEL_BUILD_DFR_DEPENDENCY=STATICALLY_NOT_SELECTED`
- `CORE_SUN_DIST_DFR_DEPENDENCY=STATICALLY_NOT_SELECTED`
- `EXTERNAL_DFR_DDK_BUILD=BLOCKED_UNDETERMINED`
- `BAZEL_ACTION_GRAPH=NOT_RUN`
- `BUILD_ELIGIBLE=false`; no build authorization is implied.

This narrows the previous DFR blocker. The broken external DFR package is not in the statically declared core `sun_perf`/`sun_consolidate` kernel_build/dist dependency chain. It remains a blocker for separately building the OEM external DFR DDK modules and for full vendor-module acceptance. The result is source/macro-level only, not a Bazel action graph or runtime build result.

## Exact pinned inputs

1. `kernel_platform/msm-kernel`: Commit `6028f47faddaa27700f8dd3a1d83906ea8f27170` in [OnePlusOSS/android_kernel_oneplus_sm8750](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/tree/6028f47faddaa27700f8dd3a1d83906ea8f27170).
2. Root OEM modules/devicetree tree: Commit `d50b305f7da9e14715a25120a4ac7b1a4b8b97c3` in [OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/tree/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3).

These are the revisions already recorded in the 35-project source lock and previous pinned-source audit. Local byte identity and all 35 current project HEADs still require local revalidation.

## Core kernel target chain

1. The root [`BUILD.bazel`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/BUILD.bazel) calls `define_msm_platforms()` through [`msm_platforms.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/msm_platforms.bzl), which invokes `define_sun()`.
2. [`target_variants.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/target_variants.bzl) declares LA variants `consolidate` and `perf`. [`sun.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/sun.bzl) sets `target_name = "sun"`, iterates those variants and calls `define_msm_la()`.
3. [`msm_kernel_la.bzl`](https://github.com/OnePlusOSS/android_kernel_oneplus_sm8750/blob/6028f47faddaa27700f8dd3a1d83906ea8f27170/msm_kernel_la.bzl) derives `sun_perf` and `sun_consolidate` from the target/variant names, defines `kernel_build(name=target, module_outs=in_tree_module_list)`, and defines corresponding `<target>_dist` rules.
4. The `sun.bzl` module list is the in-tree `.ko` list. The core `kernel_build` uses that list; it does not append DFR external DDK labels. The core dist macro collects the base kernel, GKI artifacts where applicable, kernel target/images, system-DLKM image, headers, UAPI/config and related core outputs. It does not list `//vendor/oplus/kernel/dfr:oplus_bsp_dfr` or another DFR DDK target.
5. [`oplus_modules_define.bzl`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/bazel/oplus_modules_define.bzl) defines the DDK wrapper separately. It connects an external DDK module to a core `//msm-kernel:<target>_<variant>` kernel_build; that is a dependency from the external module build to the kernel build, not a reverse dependency that adds DFR modules into the core kernel_build.

**Macro-derived candidate labels (not Bazel-query verified):**
- `//msm-kernel:sun_perf`
- `//msm-kernel:sun_perf_dist`
- `//msm-kernel:sun_consolidate`
- `//msm-kernel:sun_consolidate_dist`

This proves naming and declared macro structure only. It does not prove that the checked-out root workspace loads the same files, that Bazel resolves these labels, which output groups contain Image/vmlinux, or that the build succeeds.

## Why the DFR external package is separate

- [`modules.ext.oplus`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/config/modules.ext.oplus) line 19 lists `../vendor/oplus/kernel/dfr`.
- [`oplus_build.sh`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/oplus/build/oplus_build.sh) treats `kernel` as `RECOMPILE_KERNEL=1`. It sets `RECOMPILE_EXT_MODULE=1` only when an explicit `../vendor/oplus...` module path is supplied and that path has a `BUILD.bazel`.
- [`prepare_vendor.sh`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/build/android/prepare_vendor.sh) compiles external DDK modules only inside `if [ "${RECOMPILE_EXT_MODULE}" != "0" ]`; if no explicit EXT_MODULES list is supplied, that separate phase reads the whole `modules.ext.oplus` list, which includes DFR.
- [`build_module.sh`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/kernel_platform/build/build_module.sh) then creates the external-module workspace link and queries/builds a matching DDK dist target.

Thus the core kernel-only path and the external DFR module path are distinct in the pinned source scripts. Do not infer full vendor-module readiness from a core Image build.

## Remaining DFR external-module defect/uncertainty

- [DFR `BUILD.bazel`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/vendor/oplus/kernel/dfr/BUILD.bazel) loads and calls `define_oplus_local_modules()`.
- [`oplus_local_modules.bzl`](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8750/blob/d50b305f7da9e14715a25120a4ac7b1a4b8b97c3/vendor/oplus/kernel/dfr/oplus_local_modules.bzl) declares multiple DDK modules, header globs, `ko_deps` and the aggregate `oplus_bsp_dfr` distribution target.
- The tree records `vendor/oplus/kernel/dfr/soc/oplus/dfr/include` as a symlink (mode `120000`) whose blob is `../../include/`. From the symlink's parent this resolves to `vendor/oplus/kernel/dfr/soc/include`, which is absent in the pinned tree. The separate `vendor/oplus/kernel/dfr/include` directory exists.
- DFR module definitions use `native.glob(["**/*.h", ...])` and `includes = ["."]`. Without a Bazel package-load/query or controlled DFR module build, it is not established whether the broken symlink is ignored, causes package loading failure, or affects a particular DFR header dependency.

Do not delete the DFR module, mask the include, rewrite the symlink or claim DFR compilation is safe. The DFR external package remains `BLOCKED_UNDETERMINED`.

## Build admission and next steps

1. Re-run the read-only Stage 7.4 source admission against the current local 35-project checkout. The latest passive resource report confirms the lock-file SHA only; it did not re-check all 35 live project HEADs and tracked cleanliness. A lock-file hash is not a substitute for live source admission.
2. Confirm local bytes for the two pinned source commits and relevant BUILD/.bzl/wrapper files; compare local HEAD/tree with remote without reset, force-push, source sync or history rewrite.
3. Resolve exact Bazel labels and Image/vmlinux output groups only through a separately authorized bounded no-fetch query. This audit did not run Bazel, even for queries.
4. Re-sample RAM/swap, physical E: reserve, ext4/inodes and toolchain identities. The reported ~3.37 GiB MemAvailable and 1 GiB swap do not establish safe build peak. Keep `-j2`; keep ccache OFF.
5. A real fast Image/vmlinux compile requires a separate explicit authorization and a reviewed process/resource/time/output envelope. No build was started or authorized by this addendum.

**Final classification:** core Image DFR dependency statically excluded; external DFR DDK unresolved; local source/action graph and real build pending.
