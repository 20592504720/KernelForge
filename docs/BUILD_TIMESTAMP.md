# Optional GitHub Actions kernel build timestamp

**Status: POLICY_AND_ENGINE_FIXTURE_IMPLEMENTED; REAL_ONEPLUS13_ACTIONS_BUILD_NOT_IMPLEMENTED.**

In Actions -> Kernel build (preflight-only) -> Run workflow, an optional
\`build_timestamp\` string is offered.

- **Leave blank (default)**: sample the UTC clock at the start of the actual
  build invocation. The current build.yml only demonstrates preflight
  resolution; it deliberately stops without starting any kernel compilation.
- **Custom timestamp**: \`YYYY-MM-DDTHH:MM:SSZ\` or a time with an explicit
  offset such as \`2026-11-24T17:30:00+08:00\` or
  \`2026-11-24T18:30:00+09:00\`.
- The same instant is canonicalized to UTC, and the build engine exports
  \`KBUILD_BUILD_TIMESTAMP=2026-11-24 09:30:00 UTC\` and the matching Unix
  \`SOURCE_DATE_EPOCH\` to the build subprocess. They are recorded in
  \`build-report.json\` as \`build.build_timestamp\`, separately from the
  actual process started_at/ended_at fields. User-defined times do not
  alter Git author/committer timestamps.
- Bad calendar dates, missing timezone, ambiguity, fractional seconds,
  excessively large timezone offsets, control characters and out-of-range
  years are rejected. Invalid custom input never silently becomes "now".
- The existing Stage 7.3 ccache identity includes the effective build
  environment, so changing the selected timestamp cannot invisibly reuse
  the previous compiler-output namespace.
- Time stamping alone does not prove bitwise reproducibility. Exact source,
  compiler, Kconfig, environment and artifact digests still control trust.

## Interface

Workflow input \`build_timestamp\` maps to an engine config:
\`\`\`json
{"build": {"build_timestamp": "2026-11-24T17:30:00+08:00"}}
\`\`\`
For the default behavior, omit the property or set an empty string.

Pure offline preflight:
\`\`\`bash
KERNELFORGE_BUILD_TIMESTAMP="2026-11-24T17:30:00+08:00" \
  python -B -m scripts.resolve_build_timestamp
\`\`\`

This emits a machine-readable UTC timestamp/epoch; only the actual
run_build path can set the kernel's environment. Stage 7.4 must use
\`--action_env\` or the equivalent Kleaf/Bazel-supported mechanism where
needed to propagate build-time variables through sandbox boundaries.
Neither this document nor the preflight job asserts such propagation
has been achieved for OnePlus 13.

Security boundaries: no source sync, no real build, no cache pruning,
no PR merge, no main modification, no Release publication.
