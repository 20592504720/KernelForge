# Codex handoff — Stage 7.1 WSL2 read-only physical environment audit

**Scope: strict READ-ONLY.** The GitHub-side Stage 7.1 inventory is implemented.
We need local WSL2 facts that the GitHub connector cannot inspect.

## Source of truth

- Windows project: `E:\\内核构建\\project`
- Persistent WSL2 ext4 Repo workspace:
  `/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750`
- Branch `stage1/initial-foundation`, PR #1 open. Match exact remote
  HEAD before collecting facts; do not reset or change the local branch.
- Preserve the existing 35-project lock and Stage 6.3 source evidence.
- Use `scripts/stage7_1_preflight.py` from the updated branch; it uses
  stdlib only and executes no external version commands.

## Step 1: read-only preflight, stdout JSON

Run in WSL2 at the local repo `E:\\内核构建\\project`:

```bash
cd /mnt/e/内核构建/project
SRC=/home/kernelforge/kernelforge/sources/oneplus13-pjz110-sm8750
mkdir -p /mnt/e/内核构建/reports
python3 -B scripts/stage7_1_preflight.py \
  --workspace "$SRC" --host-path /mnt/e \
  > /mnt/e/内核构建/reports/stage7_1_local_inventory.json
```

Creating the **report directory and JSON on E:\\内核构建\\reports** is
the only authorized write. If the reports directory already exists, reuse it.
No output in `SRC`, its `.repo`, the kernel checkout, or any cache.

## Step 2: corroborate passive host and build-tool inventory

Record stdout/text in `E:\\内核构建\\reports` only. Do not execute
Bazel/Bazelisk `--version` because Bazelisk may fetch binaries.

```bash
printf 'wsl release: '; uname -srmo
df -Pk "$SRC" /mnt/e
df -Pi "$SRC" /mnt/e
free -b
for t in bazel bazelisk clang ld.lld llvm-nm gcc ccache repo git java; do
  command -v "$t" || true
done
ls -ld -- "$SRC" "$SRC/.repo" "$SRC/.repo/manifests"
readlink -f -- "$SRC" || true
```

Report whether PATH names are symlinks/wrappers. If practical, hash known
local executable files (e.g. explicit executable paths from the inventory)
using `sha256sum -- <path>`, and note their architecture/size. **Do not**
hash directories recursively or silently execute Bazelisk. Existing PATH
entries do not prove correct version or operational compatibility.

If identification requires executing a tool or a Bazel query, mark version
`UNTESTED` and propose a separate controlled check.

## Step 3: pre-existing cache locations without cleanup

Report whether `~/.cache/bazel`, `~/.cache/ccache`, `~/.ccache`,
`/home/kernelforge/kernelforge/.cache/toolchains` and existing
build output directories exist, and their immediate metadata. Read-only
`du -sh` **only** if the directory is known and bounded in size; expensive
recursive size walks can be recorded as `UNTESTED_RESOURCE`.

Never execute `ccache -C`, `bazel clean`, `repo sync`, install, apt upgrade,
Git fetch, patch, build, delete, rename, move, or modify the 35-source tree.

## Step 4: acceptance evidence

Produce these two files on the existing branch:

- `docs/STAGE7_1_WSL2_ENV_AUDIT.md`
- `docs/evidence/stage7_1_wsl2_environment.json`

Include source path, run date/host category, filesystem free bytes/inodes for
ext4 **and physical E:**, RAM/CPU, tool PATH and actual binary digest where
checked, Bazel/Bazelisk ambiguity, cache presence, DFR unresolved dependency,
any missing build prerequisites and whether 7.2/7.3 can proceed independently.

Retain raw logs and SHA256 of logs in `E:\\内核构建\\reports`.
Assign each check `TESTED`, `UNTESTED` or `BLOCKED`; no invented values.
Document both remote and local Commit and Tree SHA. Git ancestry may differ;
the authoritative comparison is contents/Tree plus declared base.
Do not merge PR #1 or edit `main`. Stop before Stage 7.2, any Bazel query,
source sync or kernel build.

**Final question:** Is the current WSL2 environment usable for a *bounded*
Stage 7.2/7.5 study without touching existing sources, and which exact
dependencies/capacity limits require a separate decision?
