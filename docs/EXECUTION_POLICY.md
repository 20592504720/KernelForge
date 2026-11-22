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
