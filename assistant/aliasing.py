"""The alias layer: real table and column names on one side, opaque ones on the other.

The model only ever sees aliases (t_01, c_017). The map between the two stays
on this side, and SQL written in aliases is translated back before it runs.

Two properties matter:

* Column aliases are unique across the whole schema, not per table. That's
  what lets translation be a plain token swap with no SQL parser involved.
* Aliases are stable. When the schema grows, existing aliases keep their
  numbers and new columns take the next free one, so the context file and
  every saved query stay valid.
"""

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "zaffre.db"
MAP_PATH = ROOT / "config" / "alias_map.json"

# Allow-list. A table that isn't here has no alias, so it can't be queried.
EXPOSED_TABLES = ["customers", "merchants", "transactions"]

ALIAS_TOKEN = re.compile(r"\b(?:t_\d+|c_\d+)\b")
_STRING = re.compile(r"'(?:[^']|'')*'")
_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)


def connect_read_only(db_path=DEFAULT_DB):
    return sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)


def read_schema(db_path=DEFAULT_DB, tables=EXPOSED_TABLES):
    """{table: [column, ...]} for the exposed tables, in schema order."""
    con = connect_read_only(db_path)
    try:
        return {t: [row[1] for row in con.execute(f"PRAGMA table_info({t})")] for t in tables}
    finally:
        con.close()


def sync(schema, existing=None):
    """Returns (alias map, list of newly aliased names). Existing aliases never change."""
    existing = existing or {"tables": {}, "columns": {}}
    tables, columns = dict(existing["tables"]), dict(existing["columns"])
    added = []
    next_t = 1 + max([int(a[2:]) for a in tables.values()] or [0])
    next_c = 1 + max([int(a[2:]) for a in columns.values()] or [0])
    for table, cols in schema.items():
        if table not in tables:
            tables[table] = f"t_{next_t:02d}"
            next_t += 1
            added.append(table)
        for col in cols:
            key = f"{table}.{col}"
            if key not in columns:
                columns[key] = f"c_{next_c:03d}"
                next_c += 1
                added.append(key)
    return {"tables": tables, "columns": columns}, added


def load(path=MAP_PATH):
    return AliasMap(json.loads(Path(path).read_text(encoding="utf-8")))


def save(mapping, path=MAP_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(mapping, indent=2) + "\n")


def strip_literals(sql):
    """SQL with comments removed and string contents blanked, for inspection only."""
    return _STRING.sub("''", _COMMENT.sub(" ", sql))


def _outside_strings(sql, replace):
    """Applies replace(text) to everything except quoted strings and comments."""
    out, position = [], 0
    for match in re.finditer(f"{_STRING.pattern}|{_COMMENT.pattern}", sql, re.S):
        out.append(replace(sql[position:match.start()]))
        out.append(match.group(0))
        position = match.end()
    out.append(replace(sql[position:]))
    return "".join(out)


class AliasMap:
    def __init__(self, mapping):
        self.tables = mapping["tables"]      # real table -> alias
        self.columns = mapping["columns"]    # "table.column" -> alias
        self._to_real = {alias: real for real, alias in self.tables.items()}
        self._to_real.update({alias: key.split(".", 1)[1] for key, alias in self.columns.items()})

    @property
    def aliases(self):
        return set(self._to_real)

    @property
    def real_names(self):
        """Every real identifier, lower-cased. None of these should reach the model."""
        names = {t.lower() for t in self.tables}
        names.update(key.split(".", 1)[1].lower() for key in self.columns)
        return names

    def table(self, real_table):
        return self.tables[real_table]

    def column(self, qualified):
        return self.columns[qualified]

    def to_real(self, aliased_sql):
        """Translate SQL written in aliases into SQL that runs. Strings are left alone."""
        swap = lambda text: ALIAS_TOKEN.sub(lambda m: self._to_real.get(m.group(0), m.group(0)), text)
        return _outside_strings(aliased_sql, swap)

    def unknown_aliases(self, aliased_sql):
        return sorted(set(ALIAS_TOKEN.findall(strip_literals(aliased_sql))) - self.aliases)
