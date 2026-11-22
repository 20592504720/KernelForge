# KernelForge execution policy (Stages 5–8 and later)

This policy applies to local development and GitHub Actions. The protected
`main` branch, open PR #1 and the existing E-drive workspace remain intact.
Status words are IMPLEMENTED, TESTED, UNTESTED, NOT_IMPLEMENTED, BLOCKED,
IN_PROGRESS and PLACEHOLDER. Evidence, not a directory or switch, determines
the status.

## Resume and evidence

1. Read the latest handoff, run registry, build reports and source/patch locks;
   then inspect local branch, clean status, HEAD, Tree, remote HEAD and PR.
2. Inherit successful CI only after matching workflow, Run ID, Commit, Tree,
   source/provider/SUSFS commits, toolchain, config, matrix, logs and artifacts
   to the current acceptance claim. A matching Tree alone is insufficient for
   moving upstream versions.
3. For failures, read the original step and log before considering a rerun.
   Preserve canceled, queued and running Run IDs. A chat interruption does not
   stop GitHub Actions. Do not relaunch a valid existing run.
4. Register long jobs immediately with URL, Run ID, Commit, Tree, version locks,
   parameters, start time, resource expectations and diagnostic entry. Archive
   reports, `.config`, source/patch locks, relevant logs and SHA256 before
   artifacts expire. Never record tokens or signed temporary URLs as secrets.
5. Save incremental handoff notes after each important unit of work. If timed
   waiting is unavailable and nothing independent remains, record the state and
   end the session; resume from the same Run IDs.

## Low-frequency monitoring

- The normal interval between status checks of the same long-running batch is
  **at least 10 minutes**; 15–30 minutes is often appropriate. Batch all active
  runs into one check. Record last and next eligible check times. Stop polling
  completed jobs.
- An immediate extra check is allowed for a newly observed failure, possible
  data corruption, a required safety decision, a completion event or an artifact
  near expiry. State the reason. Never use repeated identical calls as a timer.

## Runner resources and disk failures

- Before a large sync or build, record `df -h`, `df -i`, capacity of workspace
  and temp mounts, and focused `du -sh` of relevant directories. Check again
  after dependencies, before/after sync, before/after compilation, before
  upload and on failure where possible. Avoid repeated full-tree scans.
- Set a minimum free-space requirement from the current runner, historical peak
  source/build sizes and a safety margin. If insufficient, report actual bytes,
  stage and estimate, then stop before a destructive failure. Do not invent a
  universal capacity threshold.
- Distinguish runner block exhaustion, inode exhaustion, memory, timeout,
  network/Git, missing source, toolchain, compilation, Actions cache and
  artifact quota. `No space left on device` in a Worker diagnostic path proves
  filesystem exhaustion; it does **not** identify the directory that first
  filled the disk or prove a kernel code defect.
- Do not infer usable capacity from a runner label or a generic published
  specification. The 2026-11-22 hosted Ubuntu 24.04 pilot actually measured
  92,656,624 KiB free before cleanup and 99,241,204 KiB after; a fresh job
  can differ. The provisional 35 GiB preflight is only a floor, not a measured
  source peak. Keep manifest-only PR/schedule jobs available and make full
  sync an explicit, one-attempt action. A skipped sync remains UNTESTED.
- On repeated disk failure, do not retry again under identical conditions.
  Preserve Run ID/log, locate the growth source and change the resource plan.
  Consider eliminating duplicate copies, safe shallow/partial sync only if
  pinned commits remain fetchable, lower sync concurrency, smaller verified
  outputs, then a larger authorized Linux runner if total requirements still
  exceed capacity. Lower `repo sync -j` alone does not reduce total source size.
- Clean only known disposable files on the current ephemeral runner after
  recording their size and confirming they are not needed for build or audit;
  recheck free space. Never apply this cleanup to E-drive sources/cache/builds,
  C-drive backups, other projects or runner system directories. Never disable
  CFI/KCFI, required modules or device trees to save space. Paid or self-hosted
  capacity requires a separate security and cost decision.
- For this SM8750 attempt only, `/usr/share/dotnet` is the sole tested cleanup
  candidate. Verify hosted Ubuntu 24.04, exact real path, non-symlink,
  non-mountpoint and recognizable root-owned .NET installation; use
  `--one-file-system`. Check direct tools and protected tool paths before and
  after. The pilot recovered 6,584,580 KiB; this proves only the checked tools
  survived, not full vendor build compatibility. Do not widen the allowlist.
- Monitor free blocks and inodes inside the sync job at low cost (30–60 s),
  recording stages, lowest observed capacity and exact failure. Use a measured
  safety reserve; a provisional 10 GiB is used for the first controlled sync.
  Terminate the sync process group before the reserve is exhausted and retain
  a small JSON/log report. Do not perform repeated full-tree `du` scans.
- A large sync should have a one-time explicit trigger, never an automatic PR
  or schedule trigger. Match its Run ID to a source lock and Commit before
  judging results. One failed attempt requires diagnosis before any retry.
  If hosted capacity is proven insufficient, first design a measured larger
  Linux option; E:/F: storage is only a later option with a Linux filesystem,
  no automatic migration or exposed public self-hosted runner.

## Efficient development and verification

- Pin third-party GitHub Actions to a verified full Commit SHA. Check the
  upstream `action.yml` runtime and runner minimum before upgrading. A Node
  runtime migration needs workflow syntax checks and a small representative
  CI run on the new Tree; it does not by itself justify another full GKI or
  SM8750 source build. If a small CI run cannot be started, record the new
  Action runtime as UNTESTED rather than treating syntax validation as proof.

1. Check existing evidence before searching, downloading, testing or querying.
   Reuse integrity-checked local caches and locks. Hosted runners are ephemeral;
   do not assume their previous local source survives.
2. Verify in levels: static syntax/Schema/Manifest/hash/diff; relevant focused
   tests; full software regression for shared code; real Linux GKI/kernel work
   for source, integration or build changes; later real-device validation.
   Lower levels cannot substitute for higher acceptance gates.
3. Before expensive CI, run lightweight gates, check source locks and disk,
   choose the smallest necessary matrix, then register the run. A single failed
   configuration calls for targeted diagnosis and retest, not an automatic
   complete-matrix retry. Documentation-only commits should not start a build.
4. Use a real Linux filesystem for kernel compilation. Windows may manage
   configuration and tests. Keep GKI and Vendor paths, artifacts and claims
   distinct. Do not equate source integration, Kconfig or object compilation
   with a complete Image, ABI match, boot or Root behavior.
5. Report briefly at start, important milestones, blockers and completion;
   keep detailed evidence in repository documents and artifacts. Do not repeat
   a full PR review at every step.

## Budget, Git and stage boundary

- Use user-provided or reliable remaining-budget data only. Around **20%**,
  stop low-priority research and update handoff. Around **10%**, finish the
  current unit and prepare submission. Around **5%**, stop new features, commit
  checked work, sync, record running runs and end development. Never skip
  safety or claim unverified success to save calls.
- Work only on `stage1/initial-foundation`; do not overwrite uncommitted work,
  reset history, force push, modify `main`, create a duplicate PR or merge PR #1.
  Keep C and E data, caches and backups. Do not execute unaudited remote scripts
  or release unverified flashable images.
- Stage 5 remains open until its real GKI, Patch Manager, capability and SM8750
  evidence is reviewed. A runner disk blocker is `BLOCKED:
  RUNNER_DISK_EXHAUSTED`, never TESTED. The user decides whether a documented
  exception is acceptable. Stage 6 begins only on a later instruction.

## Safe hosted-runner free-space pilot (2026-11-22)

- The completed [pilot run 44988567235](https://github.com/20592504720/KernelForge/actions/runs/44988567235)
  measured 92,656,624 KiB free before cleanup, 99,241,204 KiB after and
  6,584,580 KiB recovered. `.github/workflows/runner-disk-pilot.yml`
  tried only `/usr/share/dotnet` and `/opt/ghc`; the latter was absent. It
  guarded symlinks/mountpoints and was restricted to
  GitHub-hosted Ubuntu 24.04. It preserves Android SDK/NDK, all
  `RUNNER_TOOL_CACHE`, Java, Clang/LLVM, GCC, Git, Python, Node, Bazel,
  Docker, source locks and kernel files; verifies essential executable paths
  after the trial and uploads free-space/inode diagnostics.
- The pilot does **not** modify persistent E: or F: drives, perform `repo
  sync`, or prove complete kernel-build dependency safety. Newly synced
  vendor projects may introduce dependencies not visible in this repository;
  assess them before extending cleanup. Never apply third-party blanket
  free-disk actions or indiscriminate `apt autoremove` without auditing
  exactly what they delete.
- Hosted GitHub jobs start fresh images; a pilot's freed space cannot be used
  by a different job. Only after reviewing measured gain and dependencies
  should an approved allowlist be added to the *same* locked-sync job.
  Preinstalled components deleted in an isolated trial do not need to be
  re-downloaded in later jobs because each receives a fresh VM, but deleting
  a tool needed later *within the same job* can trigger unnecessary downloads.
  Never remove toolcache, build-essential, SDK/NDK, Java, LLVM/Clang or Bazel
  while their dependency status is unknown.
- The 35 GiB floor is provisional, not a measured source peak. If guarded
  cleanup cannot provide sufficient free bytes and inode capacity with
  safety margin, do not repeat the same sync on a standard hosted runner;
  evaluate authorized larger Linux capacity, with user-provided E:/F: space
  available as a later alternative. No paid resources or local-drive
  mutations without further coordination.
