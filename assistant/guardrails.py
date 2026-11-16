"""Checks that run on model-written SQL before it is translated or executed.

These are token and pattern checks, not a SQL parser. They catch the mistakes
that matter most and are cheap to reason about, and they will miss things a
parser would catch. Anything that gets past them still runs on a read-only
connection.

The policy is written in real names because it lives on this side of the alias
layer. It's resolved to aliases when a query is checked.
"""

import re

from .aliasing import strip_literals

FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "attach", "detach", "pragma", "vacuum", "reindex", "truncate",
}

POLICY = {
    # table -> rules that apply whenever that table is referenced
    "transactions": {
        "bounded_on": "transactions.txn_ts",
        "must_reference": ["transactions.status", "customers.is_test_account"],
    },
    "customers": {
        "must_reference": ["customers.is_test_account"],
    },
}

# Every name in a query has to be accounted for: an alias from the map, a SQL
# word from these two lists, or a label the query defined itself. Anything else
# is a table or column the model was never given, such as an unlisted table.
KEYWORDS = {
    "select", "from", "where", "and", "or", "not", "in", "is", "null", "as", "on", "join", "left",
    "right", "inner", "outer", "cross", "full", "group", "by", "order", "having", "limit", "offset",
    "union", "all", "distinct", "case", "when", "then", "else", "end", "between", "like", "exists",
    "with", "asc", "desc", "over", "partition", "rows", "range", "unbounded", "preceding",
    "following", "current", "row", "cast", "integer", "real", "text", "numeric", "true", "false",
    "filter", "nulls", "first", "last", "except", "intersect",
}
FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "total", "round", "abs", "coalesce", "ifnull", "nullif",
    "iif", "substr", "length", "lower", "upper", "trim", "instr", "date", "time", "datetime",
    "julianday", "strftime", "row_number", "rank", "dense_rank", "lag", "lead",
}

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CTE_NAME = re.compile(r"\b([A-Za-z_]\w*)\s+as\s*\(", re.I)
_LABEL_AFTER_AS = re.compile(r"\bas\s+([A-Za-z_]\w*)", re.I)
_LABEL_AFTER_TABLE = re.compile(r"\bt_\d+\s+([A-Za-z_]\w*)", re.I)
_SELECT_STAR = re.compile(r"(?:\bselect\b|,)\s*(?:distinct\s+)?(?:\w+\s*\.\s*)?\*", re.I)
_COUNT_STAR = re.compile(r"\bcount\s*\(\s*\*\s*\)", re.I)


def check(aliased_sql, alias_map):
    """Returns a list of (rule, message). An empty list means the query may run."""
    problems = []
    bare = strip_literals(aliased_sql).strip()
    tokens = _IDENT.findall(bare)
    lowered = [t.lower() for t in tokens]

    # ---- shape of the statement -----------------------------------------
    if ";" in bare.rstrip(";"):
        problems.append(("single_statement", "more than one statement"))
    if not lowered or lowered[0] not in ("select", "with"):
        problems.append(("read_only", "must start with SELECT or WITH"))
    used_forbidden = sorted(FORBIDDEN.intersection(lowered))
    if used_forbidden:
        problems.append(("read_only", "contains " + ", ".join(w.upper() for w in used_forbidden)))
    if _SELECT_STAR.search(_COUNT_STAR.sub("count(1)", bare)):
        problems.append(("no_select_star", "name the columns, don't use *"))

    # ---- identifiers ----------------------------------------------------
    unknown = alias_map.unknown_aliases(aliased_sql)
    if unknown:
        problems.append(("known_identifiers", "not in the alias map: " + ", ".join(unknown)))
    else:
        defined = {name.lower() for pattern in (_CTE_NAME, _LABEL_AFTER_AS, _LABEL_AFTER_TABLE)
                   for name in pattern.findall(bare)}
        allowed = KEYWORDS | FUNCTIONS | FORBIDDEN | defined | {a.lower() for a in alias_map.aliases}
        strangers = sorted(set(lowered) - allowed)
        if strangers:
            problems.append(("known_identifiers", "not an alias, a SQL word or a label defined here: "
                             + ", ".join(strangers)))

    # A real name in model output means the model learned it from somewhere it
    # shouldn't have. A name straight after AS is an output label, which is fine.
    real = alias_map.real_names
    leaked = sorted(
        {tok for i, tok in enumerate(lowered) if tok in real and (i == 0 or lowered[i - 1] != "as")}
    )
    if leaked:
        problems.append(("no_real_names", "real identifiers used: " + ", ".join(leaked)))

    # ---- business rules, per table --------------------------------------
    used = set(tokens)
    for table, rules in POLICY.items():
        if alias_map.table(table) not in used:
            continue
        for qualified in rules.get("must_reference", []):
            alias = alias_map.column(qualified)
            if alias not in used:
                column = qualified.split(".", 1)[1]
                rule = "test_accounts" if column == "is_test_account" else f"{column}_filter"
                problems.append((rule, f"{alias_map.table(table)} is used but {alias} never is"))
        bounded = rules.get("bounded_on")
        if bounded:
            alias = alias_map.column(bounded)
            compared = re.search(rf"\b{alias}\b\s*(?:>=|<=|>|<|\bbetween\b)", bare, re.I)
            if not compared:
                problems.append(
                    ("date_bounded", f"compare {alias} directly so the index is used; don't wrap it in a function")
                )

    # one entry per rule, first message wins
    seen, unique = set(), []
    for rule, message in problems:
        if rule not in seen:
            seen.add(rule)
            unique.append((rule, message))
    return unique
