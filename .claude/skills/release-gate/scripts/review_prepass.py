#!/usr/bin/env python3
"""Deterministic pre-review pass over a diff.

Mechanical hygiene checks the reviewer should never have to re-derive by reading:
leftover debug scaffolding, hardcoded secrets and machine paths, suppressed
warnings, and this project's own documented UE 5.8 traps.

Only ADDED lines are inspected, so pre-existing code never generates noise.

Findings are INPUT to the reviewer, not a verdict — the reviewer weighs them
against the slice's acceptance criteria and decides. Nothing here blocks a gate
on its own.

Usage:
    python review_prepass.py [--repo PATH] [--base REF] [--head REF] [--json]

Exit codes: 0 = no findings, 1 = findings, 2 = error.
"""

import argparse
import json
import os
import re
import subprocess
import sys

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"

# Extensions whose *content* we scan, and which checks apply to them.
CODE_EXT = {".cpp", ".h", ".hpp", ".inl", ".cs"}
SCRIPT_EXT = {".py", ".ps1"}
TEXT_EXT = CODE_EXT | SCRIPT_EXT | {".ini", ".json", ".uproject", ".uplugin"}

# (id, severity, applies-to extensions or None for all text, compiled regex, message)
RULES = [
    ("secret", HIGH, None,
     re.compile(r'(?i)\b(api[_-]?key|apikey|secret|passwd|password|'
                r'auth[_-]?token|access[_-]?token|private[_-]?key)\b\s*[=:]\s*'
                r'["\'][^"\']{8,}["\']'),
     "Possible hardcoded credential assigned to a string literal."),

    ("secret-aws", HIGH, None,
     re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
     "Looks like an AWS access key id."),

    ("abs-path", HIGH, CODE_EXT | SCRIPT_EXT,
     re.compile(r'[A-Za-z]:\\{1,2}(Users|Program Files|Unreal)\b'),
     "Hardcoded machine path — breaks on a machine move. In the scaffold repo "
     "(skills, agents, docs) this is a hard rule: use LOCAL.md keys such as "
     "<UnrealProjectDir>. In tooling scripts, derive the path or read it from "
     "LOCAL.md rather than pasting it."),

    ("automation-flag-trap", HIGH, CODE_EXT,
     re.compile(r'EAutomationTestFlags::(ApplicationContextMask|FilterMask|'
                r'PriorityMask|FeatureMask)\b'),
     "Does not compile in UE 5.8 — composite masks are standalone constants "
     "spelled with an underscore, e.g. EAutomationTestFlags_ApplicationContextMask."),

    ("debug-draw", MEDIUM, CODE_EXT,
     re.compile(r'\b(DrawDebug[A-Za-z]+|FlushPersistentDebugLines)\s*\('),
     "Debug drawing call — confirm it is intended to ship, not left over from "
     "development."),

    ("log-temp", MEDIUM, CODE_EXT,
     re.compile(r'\bUE_LOG\s*\(\s*LogTemp\b'),
     "UE_LOG on LogTemp — scratch logging category; give it a real category or "
     "remove it."),

    ("warning-suppression", MEDIUM, CODE_EXT,
     re.compile(r'(#pragma\s+warning\s*\(\s*disable|\bNOLINT\b)'),
     "Suppressed compiler/lint warning — needs a stated reason."),

    ("vector-float-literal", MEDIUM, CODE_EXT,
     re.compile(r'TestEqual\s*\([^;]*\.[XYZ]\b[^;]*\d\.\d*f\b'),
     "UE5 vector components are double. A float literal here makes the "
     "float/double TestEqual overloads ambiguous (C2666) — write 0.5, not 0.5f."),

    ("anon-namespace", LOW, {".cpp"},
     re.compile(r'^\s*namespace\s*\{'),
     "Bare anonymous namespace in a .cpp. Unity builds merge translation units, "
     "so same-named constants in two files collide (hit twice on this project). "
     "Use `namespace <ClassName>Constants` instead."),

    ("blocking-sleep", LOW, {".py"},
     re.compile(r'\btime\.sleep\s*\('),
     "time.sleep in editor-facing Python blocks the game thread — sample across "
     "separate MCP calls instead (live-testing playbook)."),

    ("disabled-code", LOW, CODE_EXT,
     re.compile(r'^\s*#if\s+0\b'),
     "Disabled code block — delete it rather than shipping it commented out."),

    ("todo", LOW, None,
     re.compile(r'(?://|/\*|#)\s*(TODO|FIXME|HACK|XXX)\b'),
     "Unresolved marker left in the change."),
]

COMMENT_START = re.compile(r'^\s*(//|\*|#\s)')


def run_git(repo, args):
    result = subprocess.run(
        ["git", "-C", repo] + args,
        capture_output=True, text=True, errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def added_lines(repo, base, head):
    """Yield (path, line_number, text) for every line ADDED in the diff."""
    diff = run_git(repo, ["diff", f"{base}...{head}", "--unified=0",
                          "--no-color", "--diff-filter=d"])
    path, lineno = None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            path = raw[6:].strip()
        elif raw.startswith("@@"):
            m = re.search(r'\+(\d+)', raw)
            lineno = int(m.group(1)) if m else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            if path:
                yield path, lineno, raw[1:]
            lineno += 1


def scan_content(repo, base, head):
    findings = []
    for path, lineno, text in added_lines(repo, base, head):
        ext = os.path.splitext(path)[1].lower()
        if ext not in TEXT_EXT:
            continue
        stripped = text.strip()
        if not stripped:
            continue
        is_comment = bool(COMMENT_START.match(text))
        for rule_id, severity, exts, pattern, message in RULES:
            if exts is not None and ext not in exts:
                continue
            # Comment lines only matter for the marker rule.
            if is_comment and rule_id != "todo":
                continue
            if pattern.search(text):
                findings.append({
                    "rule": rule_id, "severity": severity, "file": path,
                    "line": lineno, "message": message,
                    "snippet": stripped[:160],
                })
    return findings


def load_asset_prefixes(scaffold_dir):
    """Parse the prefix column out of docs/NamingConventions.md."""
    doc = os.path.join(scaffold_dir, "docs", "NamingConventions.md")
    if not os.path.isfile(doc):
        return None
    prefixes = set()
    with open(doc, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            for match in re.findall(r'`([A-Za-z][A-Za-z0-9]{0,5}_)`', line):
                prefixes.add(match)
    return prefixes or None


def scan_asset_names(repo, base, head, prefixes):
    if not prefixes:
        return [], True
    findings = []
    out = run_git(repo, ["diff", f"{base}...{head}", "--name-status",
                         "--diff-filter=A"])
    for row in out.splitlines():
        parts = row.split("\t")
        if len(parts) < 2:
            continue
        path = parts[-1]
        if not path.lower().endswith(".uasset"):
            continue
        name = os.path.basename(path)[: -len(".uasset")]
        if not any(name.startswith(p) for p in prefixes):
            findings.append({
                "rule": "asset-prefix", "severity": MEDIUM, "file": path,
                "line": 0,
                "message": "New asset name carries no prefix from "
                           "docs/NamingConventions.md (hard project rule).",
                "snippet": name,
            })
    return findings, False


def render(findings, skipped_assets):
    if not findings:
        print("Pre-pass clean — no mechanical findings in added lines.")
    else:
        order = {HIGH: 0, MEDIUM: 1, LOW: 2}
        findings.sort(key=lambda f: (order[f["severity"]], f["file"], f["line"]))
        counts = {}
        for f in findings:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        summary = ", ".join(f"{counts[s]} {s}" for s in (HIGH, MEDIUM, LOW)
                            if s in counts)
        print(f"Pre-pass findings ({summary}):\n")
        for f in findings:
            where = f["file"] if f["line"] == 0 else f'{f["file"]}:{f["line"]}'
            print(f'  [{f["severity"]}] {where}  ({f["rule"]})')
            print(f'      {f["message"]}')
            print(f'      > {f["snippet"]}')
            print()
    if skipped_assets:
        print("note: docs/NamingConventions.md not found — asset-prefix check skipped.")
    print("These are mechanical signals, not a verdict. Judge each against the "
          "slice's acceptance criteria; an intentional debug draw or a documented "
          "suppression is a pass, not a finding.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository to inspect")
    parser.add_argument("--base", default="master", help="base ref (default master)")
    parser.add_argument("--head", default="HEAD", help="head ref (default HEAD)")
    parser.add_argument("--scaffold", default=".",
                        help="scaffold repo holding docs/NamingConventions.md")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    try:
        findings = scan_content(args.repo, args.base, args.head)
        prefixes = load_asset_prefixes(args.scaffold)
        asset_findings, skipped = scan_asset_names(args.repo, args.base,
                                                   args.head, prefixes)
        findings.extend(asset_findings)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        json.dump({"findings": findings,
                   "asset_check_skipped": skipped}, sys.stdout, indent=2)
        print()
    else:
        render(findings, skipped)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
