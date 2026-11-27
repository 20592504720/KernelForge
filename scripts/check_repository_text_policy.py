"""Validate effective repository EOL attributes and byte-preserving lock policy."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = "manifests/oneplus13-pjz110-sm8750-source.lock.json"
TRUSTED_LOCK_SHA256 = "22cde7f21306497f47ffdd81b04da5661a24921a37cf8ae94203fd4c830e79a7"
sys.path.insert(0, str(ROOT))


def run(args, *, cwd=ROOT, env=None, check=True):
    from kernelforge.git_policy import git_command, git_environment
    safe_env = env or git_environment()
    command = git_command(args, cwd=cwd, env=safe_env)
    result = subprocess.run(command, cwd=cwd, env=safe_env, capture_output=True, check=False, timeout=30)
    if check and result.returncode:
        raise RuntimeError("Git text-policy probe failed: " + args[0])
    return result


def verify_repo(root=ROOT):
    rows = run(["ls-files", "--eol", "-z"], cwd=root).stdout.split(b"\0")
    checked = 0
    for row in rows:
        if not row:
            continue
        meta, sep, raw_path = row.partition(b"\t")
        if not sep:
            raise RuntimeError("malformed git ls-files --eol output")
        index, worktree, attributes = meta.decode("ascii").split(maxsplit=2)
        path = raw_path.decode("utf-8", "strict")
        if path == LOCK:
            if not attributes.startswith("attr/-text"):
                raise RuntimeError("hash-locked source manifest requires explicit -text transition")
            blob = run(["show", "HEAD:" + LOCK], cwd=root).stdout
            local = (root / Path(*path.split("/"))).read_bytes()
            if hashlib.sha256(local).hexdigest() != TRUSTED_LOCK_SHA256:
                raise RuntimeError('source manifest differs from independently reviewed trusted SHA256')
            if local != blob:
                raise RuntimeError("hash-locked source manifest differs byte-for-byte from HEAD")
            continue
        if attributes.startswith(("attr/text", "attr/text=auto")) and index != 'i/-text':
            if index not in ("i/lf", "i/none") or worktree not in ("w/lf", "w/none"):
                raise RuntimeError(f"tracked text file has non-LF bytes: {path} ({index}, {worktree})")
            checked += 1

    attr = run(["check-attr", "text", "eol", "--", ".gitattributes", LOCK], cwd=root).stdout.decode("utf-8")
    if ".gitattributes: eol: lf" not in attr or f"{LOCK}: text: unset" not in attr:
        raise RuntimeError("effective attributes do not protect the rules file and digest lock")
    return {"tracked_text_files_lf": checked,
            "locked_manifest_sha256": hashlib.sha256((root / Path(*LOCK.split("/"))).read_bytes()).hexdigest(),
            "locked_manifest_policy": "BYTE_IDENTICAL_TO_HEAD_NO_FILTER"}


def verify_checkout_matrix(root=ROOT):
    with tempfile.TemporaryDirectory(prefix="kernelforge-eol-") as temporary:
        repo = Path(temporary)
        lock_bytes = (root / Path(*LOCK.split("/"))).read_bytes()
        for relative, content in ((".gitattributes", (root / ".gitattributes").read_bytes()),
                                  ("kernelforge/sample.py", b"one\ntwo\n"),
                                  ('sample.bin', b'\x00\r\n\xff\n'),
                                  ('sample.sig', b'signed\r\nopaque\r\n'),
                                  ('sample.patch', b'--- a/test\n+++ b/test\n@@ -1 +1 @@\n-a\n+b\n'),
                                  (LOCK, lock_bytes)):
            target = repo / Path(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        run(["init", "-q"], cwd=repo)
        run(["config", "user.name", "KernelForge EOL probe"], cwd=repo)
        run(["config", "user.email", "eol-probe@example.invalid"], cwd=repo)
        run(["add", "--", ".gitattributes", "kernelforge/sample.py", 'sample.bin', 'sample.sig', 'sample.patch', LOCK], cwd=repo)
        run(["commit", "-qm", "EOL fixture"], cwd=repo)
        for autocrlf, eol in (("false", "lf"), ("true", "crlf"), ("input", "crlf")):
            for relative in ('sample.bin', 'sample.sig', 'sample.patch'):
                (repo / relative).unlink()
            for relative in (".gitattributes", "kernelforge/sample.py", LOCK):
                (repo / Path(*relative.split("/"))).write_bytes(b"tampered\r\n")
            result = run(["-c", f"core.autocrlf={autocrlf}", "-c", f"core.eol={eol}",
                          "checkout", "--force", "HEAD"], cwd=repo)
            if result.returncode:
                raise RuntimeError("cross-configuration checkout failed")
            if (repo / "kernelforge/sample.py").read_bytes() != b"one\ntwo\n":
                raise RuntimeError(f"text checkout did not preserve LF under autocrlf={autocrlf}")
            if (repo / Path(*LOCK.split("/"))).read_bytes() != lock_bytes:
                raise RuntimeError(f"digest lock bytes changed under autocrlf={autocrlf}")
            if (repo / 'sample.bin').read_bytes() != b'\x00\r\n\xff\n' or (repo / 'sample.sig').read_bytes() != b'signed\r\nopaque\r\n':
                raise RuntimeError('binary or signature bytes changed during checkout')
            if (repo / 'sample.patch').read_bytes() != b'--- a/test\n+++ b/test\n@@ -1 +1 @@\n-a\n+b\n':
                raise RuntimeError('patch bytes changed during checkout')
    return {"checkout_configurations": 3, "all_lf_text_and_lock_bytes_stable": True}


def main():
    try:
        result = {"schema_version": 1, "status": "PASS",
                  "repository": verify_repo(), "matrix": verify_checkout_matrix()}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        result = {"schema_version": 1, "status": "BLOCKED", "reason": str(exc)}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
