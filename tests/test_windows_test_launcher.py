"""Offline checks for Windows CI test process isolation and exit reporting."""
from __future__ import annotations

import io
import unittest
from unittest.mock import MagicMock

from scripts.windows_test_launcher import run_suite


class WindowsTestLauncherTests(unittest.TestCase):
    @staticmethod
    def process(lines: str, code: int):
        child = MagicMock()
        child.stdout = io.StringIO(lines)
        child.wait.return_value = code
        manager = MagicMock()
        manager.__enter__.return_value = child
        manager.__exit__.return_value = False
        return manager

    def test_all_output_and_success_are_preserved(self):
        process = self.process("Ran 183 tests\\nOK\\n", 0)
        factory = MagicMock(return_value=process)
        output = io.StringIO()
        code = run_suite(creationflags=0x208, popen=factory, stream=output,
                         python="python-fixture", runner="runner-fixture.py")
        self.assertEqual(code, 0)
        self.assertIn("Ran 183 tests", output.getvalue())
        self.assertIn("WINDOWS_LAUNCH_EXIT child_exit=0", output.getvalue())
        args, kwargs = factory.call_args
        self.assertEqual(args[0], ["python-fixture", "-u", "runner-fixture.py"])
        self.assertEqual(kwargs["creationflags"], 0x208)
        self.assertEqual(kwargs["stderr"], __import__("subprocess").STDOUT)
        self.assertEqual(kwargs["stdin"], __import__("subprocess").DEVNULL)

    def test_child_nonzero_exit_remains_failure(self):
        process = self.process("FAILED (failures=1)\\n", 1)
        out = io.StringIO()
        self.assertEqual(run_suite(creationflags=0x208,
                                   popen=MagicMock(return_value=process), stream=out), 1)
        self.assertIn("WINDOWS_LAUNCH_EXIT child_exit=1", out.getvalue())

    def test_child_keyboard_interrupt_exit_not_swallowed(self):
        process = self.process("WINDOWS_TEST_INTERRUPT signal=2\\n", -1073741510)
        out = io.StringIO()
        self.assertEqual(run_suite(creationflags=0x208,
                                   popen=MagicMock(return_value=process), stream=out), -1073741510)
        self.assertIn("WINDOWS_TEST_INTERRUPT", out.getvalue())

    def test_test_process_spawn_errors_propagate(self):
        def fail(*_args, **_kwargs):
            raise OSError("injected process failure")
        with self.assertRaisesRegex(OSError, "injected"):
            run_suite(creationflags=0x208, popen=fail, stream=io.StringIO())


if __name__ == "__main__":
    unittest.main()
