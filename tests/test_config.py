import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kernelforge.validation import validate_configs, validate_manifests

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def test_all_kernel_configs_validate(self):
        schema = json.loads((ROOT / "schemas/kernel.schema.json").read_text())
        validator = Draft202012Validator(schema)
        paths = sorted((ROOT / "configs/kernels").glob("*/kernel.json"))
        self.assertEqual({p.parent.name for p in paths}, {"5.10", "5.15", "6.1", "6.6", "6.12"})
        for path in paths:
            with self.subTest(kernel=path.parent.name):
                validator.validate(json.loads(path.read_text()))

    def test_unknown_field_and_wrong_kernel_rejected(self):
        schema = json.loads((ROOT / "schemas/kernel.schema.json").read_text())
        data = json.loads((ROOT / "configs/kernels/5.10/kernel.json").read_text())
        data["unexpected"] = True
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(data)))
        data.pop("unexpected")
        data["kernel"] = "9.99"
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(data)))

    def test_missing_required_field_rejected(self):
        schema = json.loads((ROOT / "schemas/kernel.schema.json").read_text())
        data = json.loads((ROOT / "configs/kernels/5.10/kernel.json").read_text())
        del data["toolchain"]
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(data)))

    def test_invalid_json_has_clear_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "schemas").mkdir()
            (root / "configs/kernels").mkdir(parents=True)
            (root / "schemas/kernel.schema.json").write_text("{")
            self.assertIn("invalid or unreadable JSON", validate_configs(root)[0])

    def test_all_patch_manifests_validate(self):
        self.assertEqual(validate_manifests(ROOT), [])

    def test_patch_missing_file_and_bad_hash_are_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "schemas").mkdir()
            (root / "patches/5.10").mkdir(parents=True)
            (root / "schemas/patch-manifest.schema.json").write_bytes((ROOT / "schemas/patch-manifest.schema.json").read_bytes())
            patch_content = "diff --git a/x b/x\n"
            (root / "patches/5.10/test.patch").write_text(patch_content)
            manifest = {"schema_version": 1, "kernel": "5.10", "patches": [
                {"id": "one", "file": "test.patch", "sha256": "0" * 64, "source": "https://example.org/upstream/commit/abc", "enabled": False},
                {"id": "missing", "file": "missing.patch", "sha256": hashlib.sha256(b"x").hexdigest(), "source": "https://example.org/commit/def", "enabled": False}
            ]}
            (root / "patches/5.10/manifest.json").write_text(json.dumps(manifest))
            issues = "\n".join(validate_manifests(root))
            self.assertIn("SHA256 mismatch", issues)
            self.assertIn("missing patch file", issues)

    def test_invalid_device_config_rejected(self):
        schema = json.loads((ROOT / "schemas/device.schema.json").read_text())
        device = json.loads((ROOT / "devices/oneplus/pjz110/device.json").read_text())
        device["kernel"] = "made-up"
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(device)))


if __name__ == "__main__":
    unittest.main()
