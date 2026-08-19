#!/usr/bin/env python3
"""
Extract the ANSM Thesaurus des interactions medicamenteuses (PDF) into a clean CSV.

Reproducible pipeline:
    1. `pdftotext -layout <pdf> <txt>` to get a two-column layout text dump.
    2. Parse the txt: substance headers (ALL CAPS at column 0), interactant
       entries ("+ XXX"), and description/niveau/conduite in the two-column
       layout (split on runs of >=3 spaces).

Usage:
    uv run --with pdfplumber extract_thesaurus.py  # pdfplumber not actually needed,
                                                     # kept optional; pdftotext (poppler)
                                                     # is required as a system binary.

    Simpler:
    uv run python extract_thesaurus.py \
        --pdf <thesaurus.pdf> \
        --out scenarios/ansm/truth/thesaurus_ansm.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

NIVEAU_MAP = {
    "CONTRE-INDICATION": "CI",
    "Association DECONSEILLEE": "AD",
    "Précaution d'emploi": "PE",
    "A prendre en compte": "APEC",
}
NIVEAU_LABELS = list(NIVEAU_MAP.keys())

# threshold (in spaces) used to split the two-column layout produced by
# `pdftotext -layout`. Empirically the gap between left/right columns is
# always >= 3 consecutive spaces, while intra-column text never has more
# than 1-2 consecutive spaces.
COL_SPLIT_RE = re.compile(r" {3,}")

# A header may contain parentheses ("ALUMINIUM (SELS)") and a plus sign, since
# the reference files fixed combinations under one heading ("GLECAPREVIR +
# PIBRENTASVIR"). Excluding either character makes the header fall through into
# the body, and every row of the block that follows is then filed under the
# previous substance. An interactant line is matched earlier in the loop, so
# allowing "+" here cannot capture one: those start with it.
SUBSTANCE_RE = re.compile(r"^[A-ZÀ-ÖØ-Þ0-9(][A-ZÀ-ÖØ-Þ0-9 '/\-,.()+]*$")
INTERACTANT_RE = re.compile(r"^\+\s*(.+)$")
PAGE_NUM_RE = re.compile(r"^\s*\d+\s*$")
PAGE_BREAK_RE = re.compile(r"\x0c")


def normalize_text(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("é", "e") if False else s  # keep accents, just normalize apostrophes
    s = re.sub(r"\s+", " ", s).strip()
    return s


def find_niveau(right_text: str) -> tuple[str | None, str]:
    """Return (niveau_label, remainder) if right_text starts with a niveau label."""
    right_text = right_text.strip()
    for label in NIVEAU_LABELS:
        if right_text.startswith(label):
            remainder = right_text[len(label):].strip()
            return label, remainder
    return None, right_text


def split_columns(line: str) -> tuple[str, str]:
    """Split a body line into (left, right) using the >=3-space gap heuristic."""
    parts = [p.strip() for p in COL_SPLIT_RE.split(line.rstrip("\n"))]
    parts = [p for p in parts if p]  # drop empty fragments (e.g. leading indent)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    # left = first non-empty chunk; right = remaining chunks joined (there can
    # be multiple >=3-space runs inside the right column itself, but that's
    # fine to rejoin with a single space).
    left = parts[0]
    right = " ".join(parts[1:])
    return left, right


def is_substance_header(line: str, *, continuation: bool = False) -> bool:
    """A header line. `continuation` allows the second line of a header the
    reference wraps, which starts inside an open parenthesis."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("+"):
        return False
    if PAGE_NUM_RE.match(stripped):
        return False
    if stripped.lower().startswith("voir aussi"):
        return False
    if stripped.startswith("(") and not continuation:
        return False
    # must be all uppercase (allow accented uppercase, digits, spaces, punctuation)
    if stripped != stripped.upper():
        return False
    if not SUBSTANCE_RE.match(stripped):
        return False
    # must contain at least one letter
    if not re.search(r"[A-ZÀ-Ü]", stripped):
        return False
    return True


def parse(txt_path: Path):
    """Parse the pdftotext -layout dump into a list of dict rows.

    Returns (rows, ambiguous_count).
    """
    lines = txt_path.read_text(encoding="utf-8", errors="replace").split("\n")

    rows = []
    ambiguous = 0

    substance = None
    pending: str | None = None      # a header whose parentheses are still open
    interactant = None
    desc_parts: list[str] = []
    conduite_parts: list[str] = []
    niveau_label: str | None = None
    in_entry = False

    def flush():
        nonlocal ambiguous, interactant, desc_parts, conduite_parts, niveau_label, in_entry
        if interactant is None:
            return
        desc = normalize_text(" ".join(desc_parts))
        conduite = normalize_text(" ".join(conduite_parts))
        niveau_code = NIVEAU_MAP.get(niveau_label) if niveau_label else None
        if not substance or not interactant or niveau_code is None:
            ambiguous += 1
        else:
            rows.append(
                {
                    "substance": substance,
                    "interactant": interactant,
                    "niveau": niveau_code,
                    "description": desc,
                    "conduite": conduite,
                }
            )
        interactant = None
        desc_parts = []
        conduite_parts = []
        niveau_label = None
        in_entry = False

    for raw_line in lines:
        line = raw_line.replace("\x0c", "")
        stripped = line.strip()

        if PAGE_BREAK_RE.search(raw_line):
            continue
        if PAGE_NUM_RE.match(stripped) and stripped != "":
            continue
        if stripped == "":
            continue

        m_inter = INTERACTANT_RE.match(stripped)
        if m_inter:
            flush()
            # the "+ XXX" line may itself carry two columns if interactant
            # name is short and a niveau/desc starts same line (rare); handle
            # generically via split_columns.
            left, right = split_columns(line)
            left = INTERACTANT_RE.match(left.strip()).group(1) if INTERACTANT_RE.match(left.strip()) else left.strip().lstrip("+").strip()
            interactant = normalize_text(left)
            in_entry = True
            if right:
                lvl, rem = find_niveau(right)
                if lvl:
                    niveau_label = lvl
                    if rem:
                        conduite_parts.append(rem)
                else:
                    conduite_parts.append(right)
            continue

        # real substance headers sit flush at column 0 of the original
        # (unstripped) line; deeply-indented all-caps fragments (e.g. a
        # wrapped "CYP3A4." on the right column) must not be mistaken for
        # a new substance.
        at_col0 = len(line) - len(line.lstrip(" ")) == 0
        if at_col0 and is_substance_header(stripped, continuation=pending is not None):
            pending = f"{pending} {stripped}" if pending else stripped
            if pending.count("(") == pending.count(")"):
                flush()
                substance = normalize_text(pending)
                pending = None
                in_entry = False
            continue
        pending = None      # an unbalanced candidate was an annotation after all

        if stripped.lower().startswith("voir aussi") or (stripped.startswith("(") and stripped.endswith(")")):
            # substance alias / list-of-actives annotation, not a data row
            continue

        if in_entry:
            left, right = split_columns(line)
            # a lone fragment deeply indented (right-column width) is a
            # wrapped continuation of the conduite text, not description.
            if left and not right:
                indent = len(line) - len(line.lstrip(" "))
                if indent > 40:
                    right, left = left, ""
            if left:
                desc_parts.append(left)
            if right:
                if niveau_label is None:
                    lvl, rem = find_niveau(right)
                    if lvl:
                        niveau_label = lvl
                        if rem:
                            conduite_parts.append(rem)
                    else:
                        # right-side text before niveau found: shouldn't
                        # normally happen, but keep it defensively
                        conduite_parts.append(right)
                else:
                    conduite_parts.append(right)
        # else: stray line outside any entry (e.g. front matter) -> ignore

    flush()
    return rows, ambiguous


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(Path.home() / "Downloads" / "20230915-thesaurus-interactions-medicamenteuses-septembre-2023.pdf"))
    ap.add_argument("--out", default=str(Path(__file__).parent / "thesaurus_ansm.csv"))
    ap.add_argument("--txt-cache", default=None, help="optional path to reuse/save the pdftotext -layout dump")
    args = ap.parse_args()

    pdf_path = Path(args.pdf).expanduser()
    out_path = Path(args.out).expanduser()

    if args.txt_cache:
        txt_path = Path(args.txt_cache).expanduser()
        if not txt_path.exists():
            subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True)
    else:
        txt_path = out_path.parent / (pdf_path.stem + ".layout.txt")
        subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_path)], check=True)

    rows, ambiguous = parse(txt_path)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["substance", "interactant", "niveau", "description", "conduite"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    from collections import Counter

    counts = Counter(r["niveau"] for r in rows)
    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Ambiguous/skipped entries: {ambiguous}")
    for lvl in ["CI", "AD", "PE", "APEC"]:
        print(f"  {lvl}: {counts.get(lvl, 0)}")

    bad_niveau = [r for r in rows if r["niveau"] not in {"CI", "AD", "PE", "APEC"}]
    empty_fields = [r for r in rows if not r["substance"] or not r["interactant"]]
    print(f"Sanity: bad niveau values = {len(bad_niveau)}, empty substance/interactant = {len(empty_fields)}")

    known_cases = [
        ("AGOMELATINE", "FLUVOXAMINE", "CI"),
        ("AGOMELATINE", "CIPROFLOXACINE", "AD"),
        ("AFATINIB", "ITRACONAZOLE", "PE"),
    ]
    for sub, inter, expected in known_cases:
        match = [r for r in rows if r["substance"] == sub and r["interactant"] == inter]
        got = match[0]["niveau"] if match else "NOT FOUND"
        status = "OK" if got == expected else "MISMATCH"
        print(f"  known case {sub}+{inter}: expected {expected}, got {got} [{status}]")

    ci_rows = [r for r in rows if r["niveau"] == "CI"]
    import random

    random.seed(42)
    sample = random.sample(ci_rows, min(5, len(ci_rows)))
    print("Sample CI rows:")
    for r in sample:
        print(f"  {r['substance']} + {r['interactant']}: {r['description'][:80]}")


if __name__ == "__main__":
    main()
