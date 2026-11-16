import json
import shutil
import sqlite3

import pytest

from assistant import aliasing, context, evaluate, guardrails

GOOD = (
    "SELECT COUNT(DISTINCT t.c_012) AS active_customers FROM t_03 AS t "
    "JOIN t_01 AS c ON c.c_001 = t.c_012 "
    "WHERE t.c_011 >= '2025-05-31 21:00:00' AND t.c_011 < '2025-06-30 21:00:00' "
    "AND t.c_020 = 'success' AND c.c_005 = 0"
)


def rules(sql, alias_map):
    return {rule for rule, _ in guardrails.check(sql, alias_map)}


# ---- the alias map ---------------------------------------------------------

def test_committed_map_matches_the_live_schema(db):
    committed = json.loads(aliasing.MAP_PATH.read_text(encoding="utf-8"))
    synced, added = aliasing.sync(aliasing.read_schema(db), committed)
    assert added == []
    assert synced == committed


def test_aliases_are_unique_across_the_schema(alias_map):
    every = list(alias_map.tables.values()) + list(alias_map.columns.values())
    assert len(every) == len(set(every))


def test_only_allow_listed_tables_get_an_alias(alias_map):
    assert set(alias_map.tables) == set(aliasing.EXPOSED_TABLES)
    assert "meta" not in alias_map.tables


def test_new_column_takes_the_next_alias_and_nothing_else_moves(db, tmp_path):
    changed = tmp_path / "changed.db"
    shutil.copy(str(db), str(changed))
    con = sqlite3.connect(str(changed))
    con.execute("ALTER TABLE transactions ADD COLUMN device_os TEXT")
    con.commit()
    con.close()

    before = json.loads(aliasing.MAP_PATH.read_text(encoding="utf-8"))
    after, added = aliasing.sync(aliasing.read_schema(changed), before)

    assert added == ["transactions.device_os"]
    assert after["columns"]["transactions.device_os"] == "c_021"
    assert {k: v for k, v in after["columns"].items() if k != "transactions.device_os"} == before["columns"]
    # ...and the context is now visibly behind until someone documents it.
    assert context.undocumented(aliasing.AliasMap(after)) == ["c_021"]


# ---- translation -----------------------------------------------------------

def test_translation_swaps_every_alias(alias_map):
    real = alias_map.to_real(GOOD)
    assert "t_0" not in real and "c_0" not in real
    assert "FROM transactions AS t" in real
    assert "t.status = 'success'" in real


def test_translation_leaves_strings_and_comments_alone(alias_map):
    sql = "SELECT 't_01 and c_005' AS label, c.c_003 -- c_003 is the city\nFROM t_01 AS c WHERE c.c_005 = 0"
    real = alias_map.to_real(sql)
    assert "'t_01 and c_005'" in real
    assert "-- c_003 is the city" in real
    assert "c.city" in real and "FROM customers AS c" in real


def test_translated_query_runs(db, alias_map):
    con = aliasing.connect_read_only(db)
    try:
        (count,) = con.execute(alias_map.to_real(GOOD)).fetchone()
    finally:
        con.close()
    assert count > 0


# ---- guardrails ------------------------------------------------------------

def test_a_query_that_follows_the_rules_passes(alias_map):
    assert guardrails.check(GOOD, alias_map) == []


@pytest.mark.parametrize(
    "sql, rule",
    [
        ("DELETE FROM t_03 WHERE c_011 < '2025-01-01'", "read_only"),
        ("WITH x AS (SELECT c_001 FROM t_01 WHERE c_005 = 0) INSERT INTO t_01 SELECT c_001 FROM x", "read_only"),
        (GOOD + "; DROP TABLE t_01", "single_statement"),
        (GOOD.replace("COUNT(DISTINCT t.c_012) AS active_customers", "*"), "no_select_star"),
        (GOOD.replace("COUNT(DISTINCT t.c_012) AS active_customers", "t.*"), "no_select_star"),
        (GOOD.replace("c.c_005", "c.c_099"), "known_identifiers"),
        (GOOD.replace("t_03", "transactions"), "no_real_names"),
        (GOOD.replace(" AND t.c_020 = 'success'", ""), "status_filter"),
        (GOOD.replace(" AND c.c_005 = 0", ""), "test_accounts"),
        ("SELECT COUNT(*) AS customers FROM t_01 AS c WHERE c.c_002 >= '2025-01-01'", "test_accounts"),
        (
            "SELECT COUNT(*) AS n FROM t_03 AS t JOIN t_01 AS c ON c.c_001 = t.c_012 "
            "WHERE date(t.c_011, '+3 hours') = '2025-06-01' AND t.c_020 = 'success' AND c.c_005 = 0",
            "date_bounded",
        ),
    ],
)
def test_each_rule_catches_its_mistake(sql, rule, alias_map):
    assert rule in rules(sql, alias_map)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT value AS setting FROM meta",                       # a real table that has no alias
        "SELECT name AS found FROM sqlite_master",                 # the database's own catalogue
        "SELECT c.c_003 AS home_city FROM t_01 AS c, meta WHERE c.c_005 = 0",   # slipped in by comma join
        "SELECT c.c_003 AS home_city FROM t_01 AS c JOIN main.meta ON 1 = 1 WHERE c.c_005 = 0",
        "SELECT c.c_003 AS home_city, secret_column FROM t_01 AS c WHERE c.c_005 = 0",
    ],
)
def test_a_name_the_model_was_never_given_is_blocked(sql, alias_map):
    assert "known_identifiers" in rules(sql, alias_map)


def test_unlisted_table_really_exists_and_really_is_unreachable(db, alias_map):
    con = aliasing.connect_read_only(db)
    try:
        assert con.execute("SELECT COUNT(*) FROM meta").fetchone()[0] > 0   # it's there
    finally:
        con.close()
    assert guardrails.check("SELECT COUNT(*) AS settings FROM meta", alias_map) != []


def test_table_label_without_as_is_accepted(alias_map):
    sql = "SELECT c.c_003 AS home_city, COUNT(*) AS customers FROM t_01 c WHERE c.c_005 = 0 GROUP BY c.c_003"
    assert guardrails.check(sql, alias_map) == []


def test_count_star_is_allowed(alias_map):
    sql = "SELECT COUNT(*) AS customers FROM t_01 AS c WHERE c.c_005 = 0"
    assert guardrails.check(sql, alias_map) == []


def test_multiplication_is_not_mistaken_for_select_star(alias_map):
    sql = "SELECT c.c_003 AS home_city, 2 * COUNT(*) AS doubled FROM t_01 AS c WHERE c.c_005 = 0 GROUP BY c.c_003"
    assert guardrails.check(sql, alias_map) == []


def test_output_labels_may_use_ordinary_words(alias_map):
    sql = "SELECT c.c_003 AS city, COUNT(*) AS customers FROM t_01 AS c WHERE c.c_005 = 0 GROUP BY c.c_003"
    assert guardrails.check(sql, alias_map) == []


def test_keywords_inside_strings_are_ignored(alias_map):
    sql = "SELECT COUNT(*) AS n FROM t_02 AS m WHERE m.c_007 = 'Drop; Delete Cafe'"
    assert guardrails.check(sql, alias_map) == []


def test_merchant_only_query_needs_no_customer_rules(alias_map):
    sql = "SELECT m.c_008 AS merchant_category, COUNT(*) AS merchants FROM t_02 AS m GROUP BY m.c_008"
    assert guardrails.check(sql, alias_map) == []


def test_the_connection_refuses_writes_even_without_guardrails(db):
    con = aliasing.connect_read_only(db)
    try:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM customers")
    finally:
        con.close()


# ---- the context file ------------------------------------------------------

def test_context_documents_every_alias(alias_map):
    assert context.undocumented(alias_map) == []


def test_context_mentions_no_alias_that_does_not_exist(alias_map):
    assert context.stale(alias_map) == []


def test_context_contains_no_real_identifiers(alias_map):
    assert context.leaked_names(alias_map) == []


def test_prompt_is_the_context_plus_the_question(alias_map):
    prompt = context.build_prompt("How many customers signed up in May 2025?")
    assert prompt.startswith("# Context for the query assistant")
    assert prompt.rstrip().endswith("How many customers signed up in May 2025?")
    assert context.leaked_names(alias_map, prompt) == []


# ---- the eval set ----------------------------------------------------------

def test_every_candidate_gets_the_verdict_it_should(db, alias_map):
    results = evaluate.run_all(alias_map, db)
    wrong = [(r.name, r.expected, r.outcome) for r in results if not evaluate.as_expected(r)]
    assert wrong == []


def test_eval_set_covers_all_three_layers(db, alias_map):
    outcomes = {r.outcome.split(":", 1)[0] for r in evaluate.run_all(alias_map, db)}
    assert outcomes == {"pass", "blocked", "wrong_result"}


def test_every_golden_question_has_a_passing_candidate(db, alias_map):
    passed = {r.golden for r in evaluate.run_all(alias_map, db) if r.outcome == "pass"}
    assert passed == {p.stem for p in evaluate.GOLDEN_DIR.glob("*.sql")}


def test_every_guardrail_rule_is_exercised_by_the_eval_set(db, alias_map):
    blocked = set()
    for r in evaluate.run_all(alias_map, db):
        if r.outcome.startswith("blocked:"):
            blocked.update(r.outcome.split(":", 1)[1].split("+"))
    assert blocked >= {
        "read_only", "single_statement", "no_select_star", "known_identifiers",
        "no_real_names", "status_filter", "test_accounts", "date_bounded",
    }
