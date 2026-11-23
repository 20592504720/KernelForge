"""Stage 7.5 offline artifacts: synthetic fixture tests only, NEVER a kernel build."""
import hashlib
import json
import os
import shutil
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernelforge.build_timestamp import resolve_build_timestamp
from scripts.stage7_4_fast_build_gate import ROOT, LOCK, PROFILE, AdmissionBlocked
from scripts.stage7_5_artifact_evidence import inspect_bundle, main


class Stage75ArtifactEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = []
        self.root = self.directory()
        self.source = self.directory()
        self.bundle = self.directory()
        for rel in (LOCK, PROFILE):
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dest)
        self.digest = hashlib.sha256((self.root / LOCK).read_bytes()).hexdigest()
        self.compiler = (self.source / "kernel_platform/prebuilts/clang/host/"
                         "linux-x86/clang-r510928/bin/clang")
        self.compiler.parent.mkdir(parents=True)
        self.compiler.write_bytes(b"reviewed synthetic clang fixture")
        self.compiler_digest = hashlib.sha256(self.compiler.read_bytes()).hexdigest()
        elf = bytearray(4096)
        elf[:7] = b"\x7fELF\x02\x01\x01"
        struct.pack_into("<HHI", elf, 16, 2, 183, 1)
        (self.bundle / "vmlinux").write_bytes(elf)
        (self.bundle / "Image").write_bytes(b"ARM64 IMAGE" + b"\0" * 4096)
        (self.bundle / ".config").write_text("CONFIG_ARM64=y\n", encoding="utf-8")
        (self.bundle / "build.log").write_text("fixture only, not a build\n", encoding="utf-8")
        self.timestamp = resolve_build_timestamp("2026-11-24T17:30:00+08:00")
        (self.bundle / "build-time.json").write_text(json.dumps(self.timestamp), encoding="utf-8")

    def directory(self):
        temp = tempfile.TemporaryDirectory()
        self.temporary.append(temp)
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def inspect(self, **changes):
        args = dict(repo_root=self.root, expected_lock_sha=self.digest,
                    source=self.source, host_disk=None, bundle=self.bundle,
                    target="//msm-kernel:sun_perf_dist", declared_exit_code=0)
        args.update(changes)
        evidence = dict(all_project_heads_match=True, tracked_worktrees_clean=True,
                        capacity={"host": {"reserve_gib": 50}, "source": {"reserve_gib": 20}})
        with patch("scripts.stage7_5_artifact_evidence.inspect_source", return_value=evidence):
            with patch("scripts.stage7_5_artifact_evidence.CLANG_SHA256",
                       self.compiler_digest):
                return inspect_bundle(**args)

    def test_synthetic_artifacts_only_prove_file_integrity(self):
        report = self.inspect()
        self.assertEqual(report["status"], "ARTIFACT_BYTES_CHECKED_BUILD_UNATTESTED")
        self.assertFalse(report["real_build_independently_verified"])
        self.assertFalse(report["device_flashable"])
        self.assertEqual(report["declared_build_exit_code"], 0)
        self.assertEqual(report["artifacts"]["Image"]["sha256"],
                         hashlib.sha256((self.bundle / "Image").read_bytes()).hexdigest())
        self.assertEqual(report["timestamp_record"]["utc_iso8601"],
                         "2026-11-24T09:30:00Z")

    def test_incorrect_lock_digest_fails(self):
        with self.assertRaisesRegex(AdmissionBlocked, "SOURCE_LOCK_SHA256_CHANGED"):
            self.inspect(expected_lock_sha="a" * 64)

    def test_missing_artifact_blocks(self):
        (self.bundle / "Image").unlink()
        with self.assertRaisesRegex(AdmissionBlocked, "MISSING_OR_SYMLINK_ARTIFACT:Image"):
            self.inspect()

    def test_empty_image_blocks(self):
        (self.bundle / "Image").write_bytes(b"")
        with self.assertRaisesRegex(AdmissionBlocked, "ARTIFACT_TOO_SMALL:Image"):
            self.inspect()

    def test_vmlinux_architecture_must_be_aarch64(self):
        path = self.bundle / "vmlinux"
        data = bytearray(path.read_bytes())
        struct.pack_into("<H", data, 18, 62)
        path.write_bytes(data)
        with self.assertRaisesRegex(AdmissionBlocked, "VMLINUX_NOT_AARCH64"):
            self.inspect()

    def test_vmlinux_must_have_elf_magic(self):
        (self.bundle / "vmlinux").write_bytes(b"?" * 4096)
        with self.assertRaisesRegex(AdmissionBlocked, "VMLINUX_NOT_ELF64"):
            self.inspect()

    def test_image_must_not_be_vmlinux_elf(self):
        (self.bundle / "Image").write_bytes((self.bundle / "vmlinux").read_bytes())
        with self.assertRaisesRegex(AdmissionBlocked, "IMAGE_IS_VMLINUX_ELF"):
            self.inspect()

    def test_required_arm64_kconfig(self):
        (self.bundle / ".config").write_text("CONFIG_ARM64=n\n")
        with self.assertRaisesRegex(AdmissionBlocked, "CONFIG_ARM64_NOT_ENABLED"):
            self.inspect()

    def test_timestamp_epoch_must_match(self):
        data = json.loads((self.bundle / "build-time.json").read_text())
        data["source_date_epoch"] += 1
        (self.bundle / "build-time.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(AdmissionBlocked, "BUILD_TIMESTAMP_INCONSISTENT"):
            self.inspect()

    def test_timestamp_request_must_match_utc(self):
        data = json.loads((self.bundle / "build-time.json").read_text())
        data["requested"] = "2026-11-25T17:30:00+08:00"
        (self.bundle / "build-time.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(AdmissionBlocked, "CUSTOM_TIMESTAMP_DIFFERENT"):
            self.inspect()

    def test_timestamp_default_cannot_claim_custom_request(self):
        data = json.loads((self.bundle / "build-time.json").read_text())
        data["mode"] = "current_utc"
        with self.assertRaisesRegex(AdmissionBlocked, "DEFAULT_TIMESTAMP_HAS_REQUEST"):
            (self.bundle / "build-time.json").write_text(json.dumps(data))
            self.inspect()

    def test_untrusted_label_rejected(self):
        with self.assertRaisesRegex(AdmissionBlocked, "EXACT_KLEAF_TARGET_REQUIRED"):
            self.inspect(target="; rm -rf /")

    def test_failure_exit_code_rejected(self):
        with self.assertRaisesRegex(AdmissionBlocked, "BUILD_EXIT_NOT_DECLARED_SUCCESS"):
            self.inspect(declared_exit_code=1)

    def test_compiler_digest_mismatch_rejected(self):
        self.compiler.write_bytes(b"unknown compiler bytes")
        with self.assertRaisesRegex(AdmissionBlocked, "LOCKED_CLANG_SHA256_MISMATCH"):
            self.inspect()

    def test_bundle_cannot_overlap_source_or_repo(self):
        with self.assertRaisesRegex(AdmissionBlocked, "BUNDLE_OVERLAPS"):
            self.inspect(bundle=self.source)

    @unittest.skipIf(os.name == "nt", "Windows cannot reliably create symlinks without privilege")
    def test_symlinked_artifact_rejected(self):
        image = self.bundle / "Image"
        image.unlink()
        image.symlink_to(self.bundle / "vmlinux")
        with self.assertRaisesRegex(AdmissionBlocked, "MISSING_OR_SYMLINK_ARTIFACT"):
            self.inspect()

    def test_wsl_host_guard_cannot_be_bypassed(self):
        with patch("scripts.stage7_5_artifact_evidence.inspect_source",
                   side_effect=AdmissionBlocked("WSL_PHYSICAL_HOST_DISK_REQUIRED")):
            with self.assertRaisesRegex(AdmissionBlocked, "WSL_PHYSICAL_HOST_DISK_REQUIRED"):
                inspect_bundle(self.root, self.digest, self.source, None, self.bundle,
                               "//msm-kernel:sun_perf_dist", 0)

    def test_cli_no_report_if_invalid_input(self):
        outside = self.directory()
        report = outside / "report.json"
        result = main(["--repo-root", str(self.root),
                       "--reviewed-lock-sha256", "not-a-digest",
                       "--source-workspace", str(self.source),
                       "--bundle", str(self.bundle),
                       "--target", "//msm-kernel:sun_perf_dist",
                       "--declared-build-exit-code", "0",
                       "--report", str(report)])
        self.assertEqual(result, 2)
        self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
