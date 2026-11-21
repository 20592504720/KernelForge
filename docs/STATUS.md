# KernelForge implementation status

## Stage 3: Toolchain Manager

- **IMPLEMENTED:** profile-driven LLVM/GCC toolchain preparation; version constraints; host and target checks; local root/executable handling; HTTP(S) download retries, timeouts, size checks and atomic temporary-file publication; mandatory SHA256 validation; zip/tar extraction with traversal/link rejection; atomic install; cache metadata and integrity checks; cache list/cleanup; cross-platform directory locks; build leases; AUTO/LOCAL_ONLY/DOWNLOAD_ONLY; isolated environment overlays; build report integration.
- **TESTED:** local HTTP server downloads, timeout/incomplete response cleanup, expected and actual SHA256 comparisons, safe zip/tar extraction, invalid archive cleanup, cache reuse/tampering/quarantine/reacquisition, cache clean and active lease protection, lock timeout/recovery, concurrent preparation, version and architecture checks, local executable mode, and GKI/Vendor environment/report integration.
- **UNTESTED:** real upstream LLVM/GCC distributions, vendor-specific archive layouts, and a real Android kernel compile. Fixture tests exercise the real download, checksum, extraction and installation path using small local HTTP payloads; compiler version queries are mocked where fixtures are not executable on all CI hosts.
- **NOT_IMPLEMENTED:** KernelSU, patch application, SUSFS, networking/ZRAM integration, device-specific profiles, and real Android kernel build support.
- **PLACEHOLDER:** GitHub build workflow remains preflight-only; release workflow remains disabled; PJZ110 remains explicitly unverified.

## Verification commands

Run `python -m compileall -q kernelforge scripts tests`, `python -m kernelforge validate`, YAML parsing, and `python -m unittest discover -s tests -v`. CI runs Ubuntu/Windows with Python 3.11 and 3.12.

## Limitations

Toolchain profiles must provide trusted source URLs and SHA256 values. Built-in archive handling is generic; upstream distribution-specific layouts require a checked profile or registered source adapter. A detected compiler version and target triple do not prove that the compiler can build or boot a particular Android kernel.
