"""Eval harness.

Each golden question has a reference query written in real names. Each
candidate is a query written in aliases, the way a model would return it, with
the verdict it ought to get. The harness runs every candidate through the same
path a live answer takes:

    guardrails -> translate aliases to real names -> run read-only -> compare with reference

Outcomes: pass, blocked:<rule>, error, wrong_result.

The candidates here are hand-written examples, not recorded model output. Some
are deliberately wrong, because the point is to show what each layer catches
and, more usefully, what the guardrails can't.
"""

import sqlite3
from collections import namedtuple
from pathlib import Path

from . import guardrails
from .aliasing import DEFAULT_DB, ROOT, connect_read_only

GOLDEN_DIR = ROOT / "evals" / "golden"
CANDIDATE_DIR = ROOT / "evals" / "candidates"

Case = namedtuple("Case", "name headers sql")
Result = namedtuple("Result", "name golden expected outcome detail note")


def read_case(path):
    """A .sql file whose leading '-- key: value' comment lines are its metadata."""
    headers, body = {}, []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not body and line.startswith("-- ") and ":" in line:
            key, value = line[3:].split(":", 1)
            headers[key.strip()] = value.strip()
        else:
            body.append(line)
    return Case(Path(path).stem, headers, "\n".join(body).strip())


def _normalise(rows, ordered):
    cleaned = [tuple(round(v, 4) if isinstance(v, float) else v for v in row) for row in rows]
    return cleaned if ordered else sorted(cleaned, key=repr)


def run_candidate(candidate, golden, alias_map, con):
    problems = guardrails.check(candidate.sql, alias_map)
    if problems:
        rules = "+".join(rule for rule, _ in problems)
        return f"blocked:{rules}", "; ".join(message for _, message in problems)

    real_sql = alias_map.to_real(candidate.sql)
    try:
        got = con.execute(real_sql).fetchall()
    except sqlite3.Error as error:
        return "error", str(error)

    ordered = golden.headers.get("ordered", "false") == "true"
    expected_rows = con.execute(golden.sql).fetchall()
    if _normalise(got, ordered) == _normalise(expected_rows, ordered):
        return "pass", f"{len(got)} row(s) match the reference"
    return "wrong_result", f"{len(got)} row(s) returned, reference has {len(expected_rows)}; values differ"


def run_all(alias_map, db_path=DEFAULT_DB):
    golden = {p.stem: read_case(p) for p in sorted(GOLDEN_DIR.glob("*.sql"))}
    con = connect_read_only(db_path)
    results = []
    try:
        for path in sorted(CANDIDATE_DIR.glob("*.sql")):
            candidate = read_case(path)
            reference = golden[candidate.headers["golden"]]
            outcome, detail = run_candidate(candidate, reference, alias_map, con)
            results.append(
                Result(
                    candidate.name,
                    reference.name,
                    candidate.headers["expect"],
                    outcome,
                    detail,
                    candidate.headers.get("note", ""),
                )
            )
    finally:
        con.close()
    return results


def as_expected(result):
    if result.expected.startswith("blocked:"):
        wanted = result.expected.split(":", 1)[1]
        return result.outcome.startswith("blocked:") and wanted in result.outcome.split(":", 1)[1].split("+")
    return result.outcome == result.expected


def render(results):
    width = max(len(r.name) for r in results)
    lines = []
    for r in results:
        mark = "ok " if as_expected(r) else "!! "
        lines.append(f"{mark}{r.name:<{width}}  {r.outcome}")
        lines.append(f"   {'':<{width}}  {r.note}")
    counts = {}
    for r in results:
        key = r.outcome.split(":", 1)[0]
        counts[key] = counts.get(key, 0) + 1
    unexpected = sum(not as_expected(r) for r in results)
    summary = ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items()))
    lines += ["", f"{len(results)} candidates: {summary}. {unexpected} verdict(s) differ from what was expected."]
    return "\n".join(lines)
