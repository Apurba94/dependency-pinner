import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from dependency_pinner.cli import main
from dependency_pinner.core import canonical, drift, parse_requirement, pin, satisfies

INSTALLED = {"numpy": "1.26.4", "pandas": "2.2.2", "scikit-learn": "1.5.0", "requests": "2.32.3"}
REQS = """# analysis deps
numpy
pandas>=2.0  # dataframes
scikit_learn[alldeps]>=1.0; python_version >= "3.9"
-r extra.txt
git+https://github.com/x/y.git
missingpkg==1.0
requests<2.0
"""


class ParseTests(unittest.TestCase):
    def test_parse(self):
        r = parse_requirement('scikit_learn[alldeps]>=1.0; python_version >= "3.9"  # ml')
        self.assertEqual((r["name"], r["extras"], r["spec"], r["comment"]), ("scikit_learn", "[alldeps]", ">=1.0", "# ml"))
        self.assertTrue(r["marker"].startswith("; python_version"))
        self.assertIsNone(parse_requirement("-e ."))
        self.assertIsNone(parse_requirement("pkg @ https://x.org/pkg.whl"))
        self.assertEqual(canonical("Scikit_Learn"), "scikit-learn")

    def test_satisfies(self):
        self.assertTrue(satisfies("1.26.4", ">=1.20,<2"))
        self.assertFalse(satisfies("2.0.0", "<2"))
        self.assertTrue(satisfies("1.4.2", "~=1.4"))
        self.assertFalse(satisfies("2.0", "~=1.4"))
        self.assertTrue(satisfies("1.4.9", "==1.4.*"))
        self.assertTrue(satisfies("1.10.0", ">1.9.0"))        # numeric, not lexical


class PinTests(unittest.TestCase):
    def test_pin_exact(self):
        new, report = pin(REQS, INSTALLED)
        lines = new.splitlines()
        self.assertIn("numpy==1.26.4", lines)
        self.assertIn("pandas==2.2.2  # dataframes", lines)
        self.assertIn('scikit_learn[alldeps]==1.5.0 ; python_version >= "3.9"', lines)
        self.assertIn("-r extra.txt", lines)
        status = {r[0]: r[3] for r in report}
        self.assertEqual(status["missingpkg"], "not installed")
        self.assertIn("violates", status["requests"])

    def test_modes(self):
        self.assertEqual(pin("numpy\n", INSTALLED, "compatible")[0], "numpy~=1.26\n")
        self.assertEqual(pin("numpy\n", INSTALLED, "minimum")[0], "numpy>=1.26.4\n")

    def test_drift(self):
        rows = {r[0]: r[3] for r in drift("numpy==1.26.4\npandas==2.1.0\nscipy==1.0\nrequests\n", INSTALLED)}
        self.assertEqual(rows, {"numpy": "ok", "pandas": "mismatch", "scipy": "missing", "requests": "unpinned"})

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            p, out = os.path.join(d, "requirements.txt"), os.path.join(d, "pinned.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("numpy\npandas\n")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["pin", p, "-o", out], installed=INSTALLED), 0)
            with redirect_stdout(io.StringIO()) as buf:
                self.assertEqual(main(["check", out], installed=INSTALLED), 0)
                self.assertEqual(main(["check", p, "--strict"], installed=INSTALLED), 1)
            self.assertIn("UNPINNED", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
