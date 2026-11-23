# Stage 1–6 full acceptance — independent evidence review

**Status: SCOPED_PASS_WITH_DEFERRED_BLOCKERS**. Run [#45184293290](https://github.com/20592504720/KernelForge/actions/runs/45184293290), trigger Commit `6c910dcbf9074c9d2030236013ce1b1ae5ddb735`, completed **success**. All **12/12 Actions jobs** succeeded, with no failed or skipped jobs. Preflight checked the one-shot source snapshot and exact marker-only commit.

- Full Windows/Ubuntu × Python 3.11/3.12 software suite: **304 tests per environment, 1,216 test executions total**, no errors or failures. The test runner may skip POSIX-only cases on Windows; this is not a skipped Actions job.
- Committed Stage 6.3 WSL2 evidence, 35 source projects, Manifest SHA/Tree, 33 Git-clean CRLF exceptions, 29 link risk classifications and locked adapter digest were reconciled; these are historic WSL2 records **not** a repeat live WSL2 filesystem scan.
- **Five exact-source ACK 6.1 generic GKI jobs** compiled real ARM64 objects, passed `ld.lld -r`, produced full `vmlinux` and `Image`, and uploaded five artifact ZIPs. Their `real-source-report.json` files all reported `status=success`, full Image `TESTED`, zero unresolved Root hooks. Each uploaded `Image` was independently rehashed from its artifact ZIP and matched the reported SHA256. The GKI full `vmlinux` digests are recorded by the build jobs but the binaries themselves were not included in these ZIPs; they were **not** independently rehashed outside the runner.

| Exact variant | ARM64 objects | Artifact ID | Verified Image SHA256 |
| --- | ---: | ---: | --- |
| `official-susfs-off` | 40 | 14823773446 | `0466a7f0125502157bd98b3ad11c2edf45bd60d1a0a7eea9f8dc66f900b82446` |
| `official-susfs-on` | 61 | 14826110019 | `d85b3d1285acd7645e7d4bcad2e6a1051cccd356ef34b7840a2820fb20a3888b` |
| `bakasu-susfs-off` | 44 | 14826761134 | `4569516ea675065abe62effc5848edaf3b1fbf48a3a5e3c4938c5af64d5e783a` |
| `bakasu-susfs-on` | 67 | 14826109526 | `0b984eb01ebe2da4aab19dd589362155f4e25904830f12e53da072486e9527ad` |
| `bakasu-reviewed-new-susfs-on` | 67 | 14828317031 | `11f668851907769d0e6db237f2bd9ce3bbc23ac6b8e212710a8ec82e76e19bdb` |

## One delivery defect in the otherwise passing run

The final workflow wrote `stage1-6-outcome.json` with a literal `\\n` after the closing `}`, making that one archived JSON file invalid under strict parsing. **Do not claim the original aggregate artifact is well-formed JSON.** The aggregate Actions job was successful because its status conditions were checked but the JSON itself was not parsed. The raw artifact is preserved as evidence of the defect. The workflow is now corrected to output one newline and to validate the JSON using `python3 -m json.tool`; the new repository-committed `docs/evidence/stage1_6_full_run_verified.json` provides a valid machine-readable independent review. That is a format/verification fix, not a retroactive change to the original run or a re-run of the five successful GKI Image builds.

## Acceptance boundary and Stage 7 entry

**Stage 1–6 scoped requirements are accepted** based on successful full software/GKI verification, verified artifact Image hashes and reconciled committed source evidence. Stage 7.1 may begin with read-only toolchain, ccache/cache-isolation and build-input inventories. This result does **not** authorize OnePlus 13 full OKI build, changes to the WSL2 35-project checkout, vendor module/DTBO packaging, ABI/KMI certification, firmware compatibility, device flashing, or a release.

Open: DFR include `BLOCKED_UNDETERMINED` for OEM external modules; independent supplier Archive `UNTESTED`; actual OnePlus 13 OKI/ABI/KMI/boot/Root `UNTESTED`; moving newer BakaSU branch `UNREVIEWED`. Stage 7/8 must retain these precise constraints.

PR #1 remains open; `main` is not modified. Historical source locks remain unchanged.
