# Stage 5 patch series

Build profiles can declare a patch_series array. The build schema requires a
unique patch ID and feature, a file relative to patches/, SHA256, an explicit
kernel commit allowlist, upstream HTTPS URL and commit, and a license.
depends_on, conflicts and order are optional. The lowest order and then the
ID break ties between ready entries. The build report records the result.

The manager accepts text edits to existing files and rejects shared targets,
even when individual hunks might be disjoint. Review and consolidate such
patches before applying them. Text applicability and reverse verification
do not establish semantic compatibility. Use the checked-out build-owned
repository and its pinned commit. The manager does not run upstream scripts.

SUSFS continues to use its existing provider-specific validation and patch
selection, with file snapshots and rollback shared with the generic manager.
Dynamic generic patch discovery, device profiles, and compile acceptance
are pending. BBG, Unicode and Fengchi have no enabled integration.
