"""Command line: python -m assistant {aliases,prompt,check,eval}"""

import argparse
import json
import sys
from pathlib import Path

from . import aliasing, context, evaluate, guardrails


def cmd_aliases(_args):
    existing = json.loads(aliasing.MAP_PATH.read_text(encoding="utf-8")) if aliasing.MAP_PATH.exists() else None
    mapping, added = aliasing.sync(aliasing.read_schema(), existing)
    aliasing.save(mapping)
    print(f"{len(mapping['tables'])} tables, {len(mapping['columns'])} columns aliased; {len(added)} new")
    missing = context.undocumented(aliasing.AliasMap(mapping))
    if missing:
        print("Not yet documented in context/context.md: " + ", ".join(missing))
    return 0


def cmd_prompt(args):
    sys.stdout.write(context.build_prompt(args.question))
    return 0


def cmd_check(args):
    alias_map = aliasing.load()
    sql = Path(args.file).read_text(encoding="utf-8")
    problems = guardrails.check(sql, alias_map)
    if problems:
        print("Blocked. This query will not run.")
        for rule, message in problems:
            print(f"  {rule}: {message}")
        return 1
    real_sql = alias_map.to_real(sql)
    print("Guardrails passed. Translated query:\n")
    print(real_sql.strip())
    if args.run:
        con = aliasing.connect_read_only()
        try:
            cursor = con.execute(real_sql)
            print("\n" + " | ".join(col[0] for col in cursor.description))
            for row in cursor.fetchmany(20):
                print(" | ".join(str(value) for value in row))
        finally:
            con.close()
    return 0


def cmd_eval(_args):
    results = evaluate.run_all(aliasing.load())
    print(evaluate.render(results))
    return 0 if all(evaluate.as_expected(r) for r in results) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m assistant")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("aliases", help="bring config/alias_map.json in line with the live schema")
    p_prompt = sub.add_parser("prompt", help="print the full prompt for a question")
    p_prompt.add_argument("question")
    p_check = sub.add_parser("check", help="run guardrails on a model's answer and translate it")
    p_check.add_argument("file", help="a .sql file written in aliases")
    p_check.add_argument("--run", action="store_true", help="also execute it, read-only")
    sub.add_parser("eval", help="run every candidate against its golden question")
    args = parser.parse_args(argv)

    if args.command != "prompt" and not aliasing.DEFAULT_DB.exists():
        print("No database. Run: python data/generate.py", file=sys.stderr)
        return 2
    return {"aliases": cmd_aliases, "prompt": cmd_prompt, "check": cmd_check, "eval": cmd_eval}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
