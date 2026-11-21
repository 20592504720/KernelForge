# Configuration

JSON inputs use Draft 2020-12 schemas with unknown properties rejected. `configs/defaults.json` contains safe off-by-default feature defaults. Kernel family profiles describe only family-level intent; source URLs, defconfigs, compiler revisions, and compatibility claims are not invented.

Toolchain defaults require future profiles to pin versions before downloads can be enabled. Device profiles are validated against `schemas/device.schema.json`; PJZ110 is marked `unverified` with no guessed SoC, source, defconfig, or command.

Every `patches/<version>/manifest.json` is empty. Non-empty entries require a patch id, relative file, SHA256, traceable source URI, and enabled flag. Validation checks dependencies, file existence, and hashes. Stage 1 does not apply patches.

Planned merge priority is global defaults < kernel family < device. Merging and provenance reporting are not implemented.
