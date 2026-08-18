#!/usr/bin/env python3
"""Mechanical checks for a skill directory. No dependencies beyond stdlib.

Usage: python skill_stats.py <skill-dir> [<skill-dir> ...]

For each skill dir, reports:
  - frontmatter parse status and top-level keys, flagging unknown ones
  - description (+ when_to_use) length vs the 1,536-char listing cap
  - SKILL.md body line count vs the ~500-line guidance
  - bundled files never mentioned in SKILL.md (possible dead weight)
  - files mentioned in SKILL.md that don't exist (broken pointers)
  - reference files over 300 lines (should carry a table of contents)

Exit code 1 if any skill has a hard defect (unparseable frontmatter,
unknown field, broken pointer, over-cap description); 0 otherwise.
"""
import re
import sys
from pathlib import Path

KNOWN_FIELDS = {
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools",
    "disallowed-tools", "model", "effort", "context", "agent", "background",
    "hooks", "paths", "shell", "metadata", "license", "compatibility",
}
DESCRIPTION_CAP = 1536
BODY_LINE_GUIDE = 500
REF_TOC_LINES = 300
SKIP_DIRS = {".git", "__pycache__", "node_modules", "evals"}  # evals/ is skill-creator tooling, not skill content


def parse_frontmatter(text):
    """Return (dict of top-level keys -> raw value, body). None if unparseable."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    fm_block = text[3:end]
    body = text[end + 4:]
    fields = {}
    current = None
    for line in fm_block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m and not line[0].isspace():
            current = m.group(1)
            fields[current] = m.group(2)
        elif current is not None:
            fields[current] += "\n" + line.strip()
    return fields, body


def audit_skill(skill_dir):
    problems = []
    notes = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"no SKILL.md in {skill_dir}"], []
    text = skill_md.read_text(encoding="utf-8", errors="replace")

    fields, body = parse_frontmatter(text)
    if fields is None:
        problems.append("frontmatter missing or unterminated (--- markers)")
        fields = {}
    else:
        unknown = sorted(set(fields) - KNOWN_FIELDS)
        if unknown:
            problems.append(f"unknown frontmatter field(s): {', '.join(unknown)} (silently ignored by Claude Code)")
        desc_len = len(fields.get("description", "")) + len(fields.get("when_to_use", ""))
        if desc_len > DESCRIPTION_CAP:
            problems.append(f"description+when_to_use is {desc_len} chars — over the {DESCRIPTION_CAP}-char listing cap, the tail is invisible")
        elif desc_len == 0:
            notes.append("no description — triggering falls back to the first body paragraph")
        else:
            notes.append(f"description+when_to_use: {desc_len}/{DESCRIPTION_CAP} chars")

    body_lines = len(body.splitlines())
    over = f" — over the ~{BODY_LINE_GUIDE}-line guidance" if body_lines > BODY_LINE_GUIDE else ""
    notes.append(f"body: {body_lines} lines{over}")

    bundled = [
        p for p in skill_dir.rglob("*")
        if p.is_file() and p.name != "SKILL.md"
        and not any(part in SKIP_DIRS for part in p.parts)
    ]
    for f in bundled:
        rel = f.relative_to(skill_dir).as_posix()
        if f.name not in text and rel not in text:
            notes.append(f"bundled file never mentioned in SKILL.md: {rel}")
        if f.suffix.lower() == ".md" and rel.startswith("references/"):
            ref_text = f.read_text(encoding="utf-8", errors="replace")
            n = len(ref_text.splitlines())
            if n > REF_TOC_LINES and "contents" not in ref_text.lower()[:2000]:
                notes.append(f"reference {rel} is {n} lines with no table of contents near the top")

    for m in re.finditer(r"(?:references|scripts|assets)/[\w./-]+", text):
        target = skill_dir / m.group(0)
        if not target.exists():
            problems.append(f"SKILL.md points at missing file: {m.group(0)}")

    return problems, notes


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    any_problem = False
    for arg in argv[1:]:
        d = Path(arg)
        print(f"\n=== {d} ===")
        problems, notes = audit_skill(d)
        for p in problems:
            any_problem = True
            print(f"  PROBLEM: {p}")
        for n in notes:
            print(f"  note:    {n}")
        if not problems:
            print("  no hard defects")
    return 1 if any_problem else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
