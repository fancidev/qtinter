"""Run the examples"""

import os
import unittest
from test.support.script_helper import run_python_until_end


folder = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class TestExamples(unittest.TestCase):

    def test_where_am_i(self):
        result, cmd = run_python_until_end(
            os.path.join("examples", "where_am_i.py"),
            __cwd=folder,
            PYTHONPATH="src")
        if result.rc != 0:
            result.fail(cmd)
        else:
            print(str(result.out, encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
