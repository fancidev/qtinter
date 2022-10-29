"""Test ways to import qtinter"""

import os
import unittest
from test.support.script_helper import run_python_until_end


folder = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class TestImport(unittest.TestCase):
    def test_no_package(self):
        # If no binding is imported and QTINTERBINDING is not defined,
        # raise import error.
        result, cmd = run_python_until_end(
            os.path.join("tests", "import2.py"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc",
            QTINTERBINDING="")
        self.assertEqual(result.rc, 1)
        stderr = str(result.err, encoding="utf-8")
        self.assertIn("ImportError: no Qt binding is imported "
                      "and QTINTERBINDING is not set", stderr)

    def test_unique_package(self):
        # When a unique binding is imported, that binding is used and
        # QTINTERBINDING is ignored.  It's also OK to import qtinter
        # before importing the binding (i.e. binding resolution is lazy).
        result, cmd = run_python_until_end(
            os.path.join("tests", "import1.py"),
            os.getenv("QTINTERBINDING"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc",
            QTINTERBINDING="Whatever")
        try:
            self.assertEqual(result.rc, 0)
            self.assertEqual(str(result.out, encoding="utf-8"),
                             f"{os.getenv('QTINTERBINDING')}.QtCore\n")
        except BaseException:
            result.fail(cmd)
            raise

    def test_multiple_package(self):
        # When two or more bindings are imported, raise ImportError.
        result, cmd = run_python_until_end(
            os.path.join("tests", "import3.py"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc")
        self.assertEqual(result.rc, 1)
        stderr = str(result.err, encoding="utf-8")
        self.assertIn(
            "ImportError: more than one Qt bindings are imported", stderr)

    def test_good_env_variable(self):
        # When QTINTERBINDING is set to a good value, it should be used.
        result, cmd = run_python_until_end(
            os.path.join("tests", "import2.py"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc")
        self.assertEqual(result.rc, 0)
        stdout = str(result.out, encoding="utf-8")
        self.assertEqual(stdout, f"{os.getenv('QTINTERBINDING')}.QtCore\n")

    def test_bad_env_variable(self):
        # When QTINTERBINDING is set to a bad value, ImportError should be
        # raised.
        result, cmd = run_python_until_end(
            os.path.join("tests", "import2.py"),
            __cwd=folder,
            PYTHONPATH="src",
            COVERAGE_PROCESS_START=".coveragerc",
            QTINTERBINDING="Whatever")
        self.assertEqual(result.rc, 1)
        stderr = str(result.err, encoding="utf-8")
        self.assertIn(
            "ImportError: unsupported QTINTERBINDING value 'Whatever'", stderr)


if __name__ == "__main__":
    unittest.main()
