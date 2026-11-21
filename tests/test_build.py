import unittest

from kernelforge.build import BuildError, GkiAdapter, VendorAdapter


class BuildAdapterTests(unittest.TestCase):
    def setUp(self):
        self.context = {"source": "/src", "out": "/out", "jobs": "4", "defconfig": "board_defconfig"}

    def test_gki_uses_its_own_kleaf_command(self):
        cfg = {"build": {"gki": {"system": "kleaf", "argv": ["tools/bazel", "run", "//common:dist", "--jobs={jobs}"]}}}
        self.assertEqual(GkiAdapter().command(cfg, self.context), ["tools/bazel", "run", "//common:dist", "--jobs=4"])

    def test_vendor_adapter_uses_vendor_argv(self):
        cfg = {"build": {"vendor": {"argv": ["./build-kernel", "{defconfig}", "-j{jobs}"]}}}
        self.assertEqual(VendorAdapter().command(cfg, self.context), ["./build-kernel", "board_defconfig", "-j4"])

    def test_unsupported_gki_system_fails_closed(self):
        with self.assertRaises(BuildError):
            GkiAdapter().command({"build": {"gki": {"system": "magic", "argv": ["build"]}}}, self.context)

    def test_unknown_placeholder_fails_closed(self):
        with self.assertRaises(BuildError):
            VendorAdapter().command({"build": {"vendor": {"argv": ["make", "{untrusted_shell}"]}}}, self.context)


if __name__ == "__main__":
    unittest.main()
