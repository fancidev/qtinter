"""Test ways to import qtinter"""

import os
import unittest
from shim import run_test_script


class TestImport(unittest.TestCase):
    def test_no_package(self):
        # If no binding is imported and QTINTERBINDING is not defined,
        # raise import error.
        rc, out, err = run_test_script(
            "import2.py",
            QTINTERBINDING="")
        self.assertEqual(rc, 1)
        self.assertIn("ImportError: no Qt binding is imported "
                      "and QTINTERBINDING is not set", err)

    def test_unique_package(self):
        # When a unique binding is imported, that binding is used and
        # QTINTERBINDING is ignored.  It's also OK to import qtinter
        # before importing the binding (i.e. binding resolution is lazy).
        rc, out, err = run_test_script(
            "import1.py",
            os.getenv("TEST_QT_MODULE"),
            QTINTERBINDING="Whatever")
        self.assertEqual(rc, 0)
        self.assertEqual(out.rstrip(), f"{os.getenv('TEST_QT_MODULE')}.QtCore")

    def test_multiple_package(self):
        # When two or more bindings are imported, raise ImportError.
        rc, out, err = run_test_script(
            "import3.py",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 1)
        self.assertIn("ImportError: more than one Qt bindings are imported",
                      err)

    def test_good_env_variable(self):
        # When QTINTERBINDING is set to a good value, it should be used.
        rc, out, err = run_test_script(
            "import2.py",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 0)
        self.assertEqual(out.rstrip(), f"{os.getenv('TEST_QT_MODULE')}.QtCore")

    def test_bad_env_variable(self):
        # Invalid QTINTERBINDING should raise ImportError.
        rc, out, err = run_test_script(
            "import2.py",
            QTINTERBINDING="Whatever")
        self.assertEqual(rc, 1)
        self.assertIn(
            "ImportError: unsupported QTINTERBINDING value 'Whatever'", err)

    def test_wrong_platform_import(self):
        # Importing the submodule of wrong platform raises ImportError.
        rc, out, err = run_test_script(
            "import4.py",
            QTINTERBINDING=os.getenv("TEST_QT_MODULE"))
        self.assertEqual(rc, 1)
        self.assertIn("ImportError", err)


if __name__ == "__main__":
    unittest.main()
