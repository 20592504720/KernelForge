"""Reviewed KernelSU providers sharing transactional source integration."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

from .source import checkout, remove_checkout, _run_git
from .toolchains.locking import FileLock

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = "https://github.com/tiann/KernelSU.git"
LEGACY = "b766b98513b5a7eb33bc1c4a76b5702bf1288f07"
BAKA = "7b65bde0710b5e7c6f755545cb15a4abd417f3a8"


class IntegrationError(RuntimeError):
    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


def _inside(root, relative):
    path = root / relative
    resolved = path.resolve()
    if resolved != root.resolve() and root.resolve() not in resolved.parents:
        raise ValueError(f"KernelSU path escapes kernel source: {relative}")
    return path


def _link(target, link):
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=False)
        if result.returncode:
            raise OSError("cannot create KernelSU directory junction")
    else:
        link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)


def _unlink(link):
    if os.name == "nt":
        os.rmdir(link)
    else:
        link.unlink()


def integrate(spec, source: Path, output: Path, *, mode: str, fetch=checkout):
    try:
        with FileLock(source / ".kernelforge-kernelsu-transaction.lock", timeout=1):
            return _integrate(spec, source, output, mode=mode, fetch=fetch)
    except IntegrationError:
        raise
    except Exception as exc:
        report = {"status": "failure", "implementation_status": "IMPLEMENTED", "provider": None,
                  "failure_reason": str(exc), "compatibility": [], "unverified": ["integration was not run"],
                  "log_file": "kernelsu.log"}
        output.mkdir(parents=True, exist_ok=True)
        (output / "kernelsu.log").write_text(f"Integration transaction failed: {exc}\n", encoding="utf-8")
        raise IntegrationError(str(exc), report) from exc


def _integrate(spec, source: Path, output: Path, *, mode: str, fetch=checkout):
    """Integrate one provider; abort and restore edited files on any failure.

    Source repositories are never executed by this module. Provider script hashes
    identify the reviewed integration recipe rather than authorizing script runs.
    """
    report = {"provider": None, "project": None, "repository": None, "upstream": OFFICIAL,
              "requested_ref": None, "ref_type": None, "commit_sha": None,
              "method": None, "status": "SKIP", "implementation_status": "IMPLEMENTED",
              "compatibility": [], "unverified": ["real kernel compilation and boot"],
              "failure_reason": None, "log_file": "kernelsu.log"}
    output.mkdir(parents=True, exist_ok=True)
    log = output / "kernelsu.log"
    log.write_text("KernelSU integration preflight\n", encoding="utf-8")
    def record(message):
        with log.open("a", encoding="utf-8") as stream:
            stream.write(message + "\n")
    original = {}
    owned_repo = False
    owned_link = False
    repo = source / "KernelSU"
    link = source / "drivers/kernelsu"
    try:
        schema = json.loads((ROOT / "schemas/build.schema.json").read_text(encoding="utf-8"))["$defs"]["kernelsu"]
        Draft202012Validator(schema).validate(spec)
        if not spec.get("enabled", False):
            return report
        report.update({key: spec.get(key) for key in ("provider", "project", "repository", "upstream", "method", "ref_type")})
        report["requested_ref"] = spec["ref"]
        baka = spec["provider"] in {"bakssu", "bakasu"}
        parsed = urlsplit(spec["repository"])
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            report["repository"] = "[REDACTED]"
            raise ValueError("KernelSU repository URL must not contain credentials or private parameters")
        official = spec["provider"] == "official"
        if official:
            if spec["repository"] != OFFICIAL or spec["expected_commit"] != LEGACY:
                raise ValueError("official built-in adapter is reviewed only for pinned v0.9.5; other revisions require a new review")
            if spec["ref_type"] == "stable" and spec["ref"] != "v0.9.5":
                raise ValueError("reviewed official stable release is v0.9.5")
        elif baka:
            if spec["repository"] != "https://github.com/Baka-SU/BakaSU.git" or spec["expected_commit"] != BAKA:
                raise ValueError("BakaSU provider requires the reviewed repository and pinned Commit")
            report["project"] = "BakaSU"
        elif not spec.get("review"):
            raise ValueError("derived provider requires reviewed upstream evidence and setup SHA256")
        if spec["ref_type"] == "commit" and spec["ref"].lower() != spec["expected_commit"].lower():
            raise ValueError("requested Commit must equal expected_commit")
        with FileLock(source / ".kernelforge-kernelsu.lock", timeout=1):
            kernel = _inside(source, spec.get("kernel_directory", "."))
            drivers = _inside(kernel, "drivers")
            link = drivers / "kernelsu"
            marker = source / ".kernelforge-kernelsu.json"
            if marker.exists() or repo.exists() or repo.is_symlink() or link.exists() or link.is_symlink():
                raise ValueError("existing KernelSU integration or source directory; refusing to overwrite or integrate twice")
            makefile, kconfig = drivers / "Makefile", drivers / "Kconfig"
            for path in (makefile, kconfig):
                if not path.is_file() or path.is_symlink():
                    raise ValueError(f"missing or unsafe kernel integration file: {path.name}")
                original[path] = path.read_bytes()
                if re.search(rb"kernelsu|CONFIG_KSU|[Rr]e[Ss]uki|BaksSU|SukiSU", original[path]):
                    raise ValueError("existing root integration conflicts with selected KernelSU provider")
            version_text = (kernel / "Makefile").read_text(encoding="utf-8")
            values = [re.search(rf"^{key}\s*=\s*(\d+)", version_text, re.M) for key in ("VERSION", "PATCHLEVEL", "SUBLEVEL")]
            if not all(values):
                raise ValueError("cannot identify actual kernel version from Makefile")
            version = tuple(int(v.group(1)) for v in values)
            report["kernel_version"] = ".".join(map(str, version))
            compat = spec["compatibility"]
            if spec["architecture"] != "arm64" or not (version[0] == 5 and version[1] in (10, 15) or version[0] == 6 and version[1] in (1, 6, 12)):
                raise ValueError("KernelSU source integration requires a configured ARM64 kernel family")
            family = f"{version[0]}.{version[1]}"
            if family not in compat["kernel_families"] or mode not in compat["build_modes"]:
                raise ValueError("kernel family or build mode excluded by provider compatibility requirements")
            config_path = _inside(kernel, spec["config_file"])
            actual_config = config_path.read_text(encoding="utf-8")
            required = set(compat["required_configs"]) | {"KSU", "SECURITY_SELINUX", "ARM64"}
            if baka:
                if mode != "gki":
                    raise ValueError("BakaSU adapter currently requires GKI tracepoint hooks; Vendor manual hooks are NOT_IMPLEMENTED")
                required |= {"KALLSYMS", "KALLSYMS_ALL", "TRACEPOINTS", "KSU_TRACEPOINT_HOOK"}
                if re.search(r"^CONFIG_KSU_(SUSFS|MANUAL_HOOK)=y$", actual_config, re.M):
                    raise ValueError("BakaSU SUSFS/manual hooks are outside this adapter")
            else:
                required |= {"KPROBES", "HAVE_KPROBES", "KPROBE_EVENTS", "OVERLAY_FS"}
            for symbol in sorted(required):
                if not re.search(rf"^CONFIG_{re.escape(symbol)}=y$", actual_config, re.M):
                    raise ValueError(f"required CONFIG_{symbol}=y missing from configured kernel file")
            report["compatibility"] = [{"check": "source version, mode and requested config", "status": "PASS"},
                                       {"check": "Kconfig resolution, compile, ABI and boot", "status": "UNTESTED"}]
            record(f"Preflight passed: {family}, {mode}, ARM64; requested configuration checked")
            ref = spec["ref"]
            if spec["ref_type"] in ("tag", "stable"):
                # Disambiguate tags from branches before using the existing fetcher.
                ref = spec["expected_commit"]
                resolved = _run_git(["ls-remote", spec["repository"], f"refs/tags/{spec['ref']}", f"refs/tags/{spec['ref']}^{{}}"], timeout=60)
                rows = resolved.splitlines()
                if not rows or rows[-1].split()[0].lower() != ref.lower():
                    raise ValueError("tag does not resolve to expected_commit")
            elif spec["ref_type"] == "branch":
                resolved = _run_git(["ls-remote", spec["repository"], f"refs/heads/{ref}"], timeout=60)
                if not resolved.strip() or resolved.split()[0].lower() != spec["expected_commit"].lower():
                    raise ValueError("branch does not resolve to expected_commit")
                ref = spec["expected_commit"]
            owned_repo = True
            sha = fetch(spec["repository"], ref, repo, timeout=spec.get("timeout_seconds", 300))
            report["commit_sha"] = sha
            record(f"Provider source checked out at {sha}")
            if sha.lower() != spec["expected_commit"].lower():
                raise ValueError("KernelSU checked out Commit does not match expected_commit")
            payload = _inside(repo, "kernel")
            for name in ("Kconfig", "Makefile", "setup.sh"):
                if not (payload / name).is_file():
                    raise ValueError(f"provider source missing kernel/{name}")
            if not re.search(r"^config KSU$", (payload / "Kconfig").read_text(), re.M):
                raise ValueError("provider Kconfig does not declare KSU")
            build_file = payload / ("Kbuild" if baka else "Makefile")
            if not build_file.is_file() or "CONFIG_KSU" not in build_file.read_text():
                raise ValueError("provider Makefile is not the reviewed built-in Kbuild layout")
            if not official and not baka:
                digest = hashlib.sha256((payload / "setup.sh").read_bytes()).hexdigest()
                if digest != spec["review"]["setup_sha256"]:
                    raise ValueError("reviewed provider setup SHA256 mismatch")
                report["upstream_evidence"] = spec["review"]["upstream_evidence"]
                report["unverified"].append("derived provider compatibility beyond fixture and declared review")
            if _run_git(["rev-parse", "--is-shallow-repository"], cwd=repo) == "true":
                _run_git(["fetch", "--unshallow", "origin"], cwd=repo, timeout=spec.get("timeout_seconds", 300))
            report["upstream_evidence"] = "https://bakasu.org/" if baka else report.get("upstream_evidence", OFFICIAL)
            _link(payload, link)
            owned_link = True
            record("Created KernelSU driver link; updating driver build files")
            makefile.write_bytes(original[makefile] + b"\nobj-$(CONFIG_KSU) += kernelsu/\n")
            text = original[kconfig].decode("utf-8")
            pos = text.rfind("endmenu")
            if pos < 0:
                raise ValueError("drivers/Kconfig has no endmenu insertion point")
            kconfig.write_text(text[:pos] + 'source "drivers/kernelsu/Kconfig"\n' + text[pos:], encoding="utf-8")
            if not (link / "Kconfig").is_file() or "CONFIG_KSU" not in makefile.read_text():
                raise ValueError("KernelSU integration postcheck failed")
            marker.write_text(json.dumps({"provider": spec["provider"], "commit_sha": sha}), encoding="utf-8")
            report["status"] = "success"
            report["integration_status"] = "IMPLEMENTED"
            record(f"Integrated {spec['provider']} at {sha}; compatibility remains UNTESTED for compilation/boot")
            return report
    except Exception as exc:
        # Restoration is restricted to files we changed and paths we created.
        if owned_link:
            _unlink(link)
        if owned_link:
            for path, content in original.items():
                path.write_bytes(content)
        if owned_repo and repo.exists():
            remove_checkout(repo)
        report.update(status="failure", failure_reason=str(exc))
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"Failed: {exc}\n")
        raise IntegrationError(str(exc), report) from exc
