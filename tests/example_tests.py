"""Run the examples"""

import unittest
from test.support.script_helper import run_python_until_end


class TestExamples(unittest.TestCase):

    def test_where_am_i(self):
        result, cmd = run_python_until_end(
            "../examples/where_am_i.py",
            PYTHONPATH="../src")
        if result.rc != 0:
            result.fail(cmd)
        else:
            print(str(result.out, encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
