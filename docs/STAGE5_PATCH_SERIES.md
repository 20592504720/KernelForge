# Stage 5 patch series

Build profiles can declare a patch_series array. The build schema requires a
unique patch ID and feature, a file relative to patches/, SHA256, an explicit
kernel commit allowlist, upstream HTTPS URL and commit, and a license.
depends_on, conflicts and order are optional. The lowest order and then the
ID break ties between ready entries. The build report records the result.

The manager accepts text edits, regular-file additions and deletions, and rejects shared targets,
even when individual hunks might be disjoint. Review and consolidate such
patches before applying them. Text applicability and reverse verification
do not establish semantic compatibility. Use the checked-out build-owned
repository and its pinned commit. The manager does not run upstream scripts.

SUSFS continues to use its existing provider-specific validation and patch
selection, with file snapshots and rollback shared with the generic manager.
An optional `source_spec` adds pinned, latest_release, latest_prerelease, or
latest_branch resolution through the existing version resolver. Before kernel
checkout, `lock_series` fetches that exact Commit, copies the selected patch
into a build-owned staging directory, computes SHA256 and writes
`patches.lock.json`. A lookup or checksum failure stops the build. A second
resolution during the same build is forbidden. Historical versions require
an explicit pinned selection. A moving patch can still be semantically
incompatible: every application report says `UNTESTED` for semantic and
runtime compatibility until separate compile/device evidence exists.

An entry can additionally limit kernel versions, Android GKI identities,
architectures, build modes and required final Kconfig symbols. Unknown target
identity and unavailable final Kconfig fail closed. Text conflict, feature
duplication and semantic compatibility are distinct checks. Existing source
files are restored byte for byte after a failed series; created files are removed
and deleted files restored. Symlinks, mode changes, renames, copies, binary
patches and executable-file creation are rejected. SUSFS uses this same
transaction boundary while retaining its precise baseline selection, payload
checks and BakaSU duplicate-hook protection.

Example dynamic entry (the Commit allowlist and upstream identity must be
replaced with verified values before use):

```json
{
  "id": "reviewed-patch", "feature": "reviewed-feature",
  "file": "path/in/upstream.patch",
  "kernel_commits": ["0123456789abcdef0123456789abcdef01234567"],
  "upstream": "https://github.com/OWNER/REPO",
  "license": "verified upstream license",
  "source_spec": {"repository": "https://github.com/OWNER/REPO",
                  "version_policy": "latest_branch", "branch": "main"},
  "kernel_versions": ["6.1"], "architectures": ["arm64"],
  "build_modes": ["gki"], "adaptation": "git-apply-text-v1",
  "verification": "UNTESTED"
}
```

This example is explanatory only; it is not enabled in a shipped profile.
BBG, Unicode and Fengchi have no enabled integration.
