"""Command-line interface for dependency-pinner."""
import argparse
import sys

from .core import drift, installed_versions, pin


def main(argv=None, installed=None):
    ap = argparse.ArgumentParser(prog="dependency-pinner", description="Pin requirements and check environment drift.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pin", help="pin requirements to the installed versions")
    p.add_argument("requirements", nargs="?", default="requirements.txt")
    p.add_argument("-m", "--mode", choices=["exact", "compatible", "minimum"], default="exact")
    p.add_argument("-o", "--output", help="output file (default: print; use the input name to overwrite)")
    c = sub.add_parser("check", help="report drift between requirements and the environment")
    c.add_argument("requirements", nargs="?", default="requirements.txt")
    c.add_argument("--strict", action="store_true", help="also fail on unpinned requirements")
    args = ap.parse_args(argv)
    installed = installed if installed is not None else installed_versions()
    with open(args.requirements, encoding="utf-8") as fh:
        text = fh.read()
    if args.cmd == "pin":
        new, report = pin(text, installed, args.mode)
        for name, old, newspec, status in report:
            print("%-25s %-15s -> %-15s %s" % (name, old or "(any)", newspec, status), file=sys.stderr)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(new)
        else:
            sys.stdout.write(new)
        return 1 if any("violates" in r[3] or r[3] == "not installed" for r in report) else 0
    rows = drift(text, installed)
    for name, req, inst, status in rows:
        if status != "ok":
            print("%-9s %-25s required %-15s installed %s" % (status.upper(), name, req, inst or "-"))
    bad = [r for r in rows if r[3] in ("missing", "mismatch") or (args.strict and r[3] == "unpinned")]
    print("%d requirement(s): %d ok, %d problem(s)" % (len(rows), sum(r[3] == "ok" for r in rows), len(bad)))
    return 1 if bad else 0
