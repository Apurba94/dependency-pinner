"""Requirement parsing (PEP 508 subset), pinning and version-drift reports."""
import re

try:
    from importlib import metadata
except ImportError:  # pragma: no cover
    metadata = None

_REQ = re.compile(r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?P<extras>\[[^\]]*\])?\s*(?P<spec>[^;#]*?)\s*"
                  r"(?P<marker>;[^#]*)?\s*(?P<comment>#.*)?$")


def canonical(name):
    """PEP 503 normalized project name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirement(line):
    """Return dict(name, extras, spec, marker, comment) or None for blanks/comments/options/URLs."""
    s = line.strip()
    if not s or s.startswith(("#", "-", "git+", "http://", "https://")) or "@" in s.split("#")[0] and "://" in s:
        return None
    m = _REQ.match(s)
    if not m:
        return None
    return {"name": m.group("name"), "extras": m.group("extras") or "", "spec": m.group("spec").replace(" ", ""),
            "marker": (m.group("marker") or "").strip(), "comment": (m.group("comment") or "").strip()}


def parse_requirements(text):
    return [(line, parse_requirement(line)) for line in text.splitlines()]


def installed_versions():
    if metadata is None:
        return {}
    out = {}
    for d in metadata.distributions():
        n = d.metadata.get("Name")
        if n:
            out[canonical(n)] = d.version
    return out


def _vtuple(v):
    parts = []
    for p in re.split(r"[.+-]", v):
        parts.append((0, int(p)) if p.isdigit() else (1, p))
    return tuple(parts)


def satisfies(version, spec):
    """Check a version against a comma-separated specifier set (==, !=, >=, <=, >, <, ~=, ===; wildcards for ==)."""
    if not spec:
        return True
    for clause in spec.split(","):
        m = re.match(r"(~=|===|==|!=|>=|<=|>|<)(.+)", clause.strip())
        if not m:
            continue
        op, target = m.groups()
        if op in ("==", "!=") and target.endswith(".*"):
            ok = (version + ".").startswith(target[:-1])
            ok = ok if op == "==" else not ok
        elif op == "~=":
            t = target.split(".")
            prefix = ".".join(t[:-1])
            ok = _vtuple(version) >= _vtuple(target) and (version + ".").startswith(prefix + ".")
        else:
            a, b = _vtuple(version), _vtuple(target)
            ok = {"==": a == b, "===": version == target, "!=": a != b, ">=": a >= b, "<=": a <= b, ">": a > b,
                  "<": a < b}[op]
        if not ok:
            return False
    return True


def pin(text, installed, mode="exact"):
    """Rewrite requirement lines with installed versions.

    mode 'exact' -> name==X.Y.Z; 'compatible' -> name~=X.Y (allows patch updates); 'minimum' -> name>=X.Y.Z.
    Returns (new_text, report) where report lists (name, old_spec, new_spec, status)."""
    out, report = [], []
    for line, req in parse_requirements(text):
        if not req:
            out.append(line)
            continue
        v = installed.get(canonical(req["name"]))
        if v is None:
            out.append(line)
            report.append((req["name"], req["spec"], req["spec"], "not installed"))
            continue
        if not satisfies(v, req["spec"]):
            report.append((req["name"], req["spec"], req["spec"], "installed %s violates spec" % v))
            out.append(line)
            continue
        if mode == "exact":
            new = "==" + v
        elif mode == "compatible":
            parts = v.split(".")
            new = "~=" + ".".join(parts[:2]) if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]) else "==" + v
        else:
            new = ">=" + v
        tail = ("" if not req["marker"] else " " + req["marker"]) + ("  " + req["comment"] if req["comment"] else "")
        out.append(req["name"] + req["extras"] + new + tail)
        report.append((req["name"], req["spec"], new, "pinned" if req["spec"] != new else "unchanged"))
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), report


def drift(text, installed):
    """Compare a pinned requirements file with the environment: (name, required, installed, status)."""
    rows = []
    for _, req in parse_requirements(text):
        if not req:
            continue
        v = installed.get(canonical(req["name"]))
        if v is None:
            rows.append((req["name"], req["spec"], None, "missing"))
        elif not satisfies(v, req["spec"]):
            rows.append((req["name"], req["spec"], v, "mismatch"))
        elif not req["spec"].startswith("=="):
            rows.append((req["name"], req["spec"] or "(any)", v, "unpinned"))
        else:
            rows.append((req["name"], req["spec"], v, "ok"))
    return rows
