# Configuration

JSON inputs use Draft 2020-12 schemas with unknown properties rejected. `configs/defaults.json` contains safe off-by-default feature defaults. Kernel family profiles describe only family-level intent; source URLs, defconfigs, compiler revisions, and compatibility claims are not invented.

Toolchain defaults (`configs/toolchains/defaults.json`) choose `AUTO`, a cache root and lock/download defaults. Build profiles can add `build.gki.toolchain_profile` or `build.vendor.toolchain_profile`; each profile names `kind` (`llvm` or `gcc`), `name`, target architecture, executable roles and either a local path or download source. Download profiles require URL, archive format and exactly 64 hexadecimal SHA256 characters. Optional fixed/minimum/maximum versions are checked after invoking the configured executable. GCC profiles query `-dumpmachine` by default. Local profiles may use `local_path` for a toolchain root or a compiler executable and should set `trust_source` to explain provenance.

Mode semantics: `AUTO` prefers explicit local paths, then a matching verified cache, then download; `LOCAL_ONLY` never downloads; `DOWNLOAD_ONLY` skips local paths and uses only a matching downloaded cache or configured source. A profile without a trusted SHA256 is rejected when downloaded. No real upstream URLs or hashes are supplied as examples because they must be verified before use. Device profiles are validated against `schemas/device.schema.json`; PJZ110 remains `unverified`.

The manager's built-in source adapter accepts declarative archive details for `archive`, `custom`, `llvm-release` and `gcc-release` profile types. Releases with different structure should provide a custom source adapter or configure `layout_root` and `executables`; the manager does not guess archive layout from a name.

Every `patches/<version>/manifest.json` is empty. Non-empty entries require a patch id, relative file, SHA256, traceable source URI, and enabled flag. Validation checks dependencies, file existence, and hashes. Stage 1 does not apply patches.

Planned merge priority is global defaults < kernel family < device. Merging and provenance reporting are not implemented.
