"""Download only pinned wheels; generate a review candidate, never auto-commit."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "requirements-dev-pins.txt"
TARGETS = (
    ("linux-x64-cp311", "manylinux2014_x86_64", "3.11", "cp311"),
    ("linux-x64-cp312", "manylinux2014_x86_64", "3.12", "cp312"),
    ("windows-x64-cp311", "win_amd64", "3.11", "cp311"),
    ("windows-x64-cp312", "win_amd64", "3.12", "cp312"),
)


def canonical(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: dependency_lock_candidate.py OUTPUT_DIR")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    pins = {}
    for line in PINS.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==")
        if canonical(name) in pins:
            raise ValueError("duplicate dependency pin")
        pins[canonical(name)] = version
    result = {name: set() for name in pins}
    records = []
    with tempfile.TemporaryDirectory(prefix="kf-wheel-proof-") as tmp:
        for target, platform, version, abi in TARGETS:
            folder = Path(tmp) / target
            folder.mkdir()
            subprocess.run([sys.executable, "-m", "pip", "--isolated", "download",
                            "--index-url", "https://pypi.org/simple", "--no-deps",
                            "--only-binary=:all:", "--no-cache-dir",
                            "--platform", platform, "--python-version", version,
                            "--implementation", "cp", "--abi", abi,
                            "-r", str(PINS), "--dest", str(folder)], check=True, timeout=240)
            seen = set()
            for wheel in sorted(folder.glob("*.whl")):
                name, wheel_version, _ = wheel.name.split("-", 2)
                name = canonical(name)
                if name not in pins or wheel_version != pins[name] or name in seen:
                    raise ValueError("unexpected wheel name/version or duplicate")
                seen.add(name)
                with wheel.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                result[name].add(digest)
                records.append({"target": target, "name": name, "version": wheel_version,
                                "wheel": wheel.name, "sha256": digest})
            if seen != set(pins):
                raise ValueError("missing pinned wheel")
    lock = "# REVIEW CANDIDATE: compare wheel hashes before enabling\n"
    for name, version in sorted(pins.items()):
        lock += name + "==" + version + " " + " ".join("--hash=sha256:" + h for h in sorted(result[name])) + "\n"
    (out / "requirements-dev.lock.candidate").write_text(lock, encoding="utf-8")
    (out / "wheel-evidence.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print("CANDIDATE_WHEEL_RECORDS", len(records))
    print(lock)


if __name__ == "__main__":
    main()
