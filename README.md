# aliased-sql-assistant

A text-to-SQL assistant that never sees a real table name, a real column name or a single row of data, with the checks that decide whether what it writes is allowed to run.

## The problem

Pointing a language model at a warehouse takes an afternoon. Getting that past a security review in a regulated company doesn't, and the objections are fair. The schema is internal, the data is customer data, and "we told it to be careful" isn't a control.

So the work that matters isn't the prompt. It's 4 questions about the architecture around it:

1. What does the model get to see?
2. Who decides what it's told about the data, and can you prove what that was?
3. What stops a wrong or expensive query from running?
4. How do you know the answers are right?

At work I own the query assistant our data team runs on. It sits on an aliased warehouse layer, so the model never sees real table names or customer data. This repo isn't that system and shares no code, schema or data with it. It's the same pattern, rebuilt small on invented data, so you can read it end to end in one sitting.

## How it works

```
 question
    |
    v
 context.md  ------------------>  MODEL            sees: aliases, rules, definitions
 (authored, in aliases)             |              never sees: real names, any rows
                                    v
                         SQL written in aliases
                                    |
                                    v
                              guardrails          8 rules; a failure stops here
                                    |
                                    v
                         alias map (stays here)    t_03.c_017 -> transactions.amount_minor
                                    |
                                    v
                         read-only connection      results go to the analyst, not the model
```

The demo schema has 3 tables and 20 columns. To the model they're `t_01` to `t_03` and `c_001` to `c_020`, and that's all it ever gets.

| | The model sees | The model never sees |
|---|---|---|
| Schema | `t_03`, `c_017` and a plain-words description of each | Real table and column names |
| Data | Nothing | Any row, any result, any customer |
| Rules | The authored context file, in full | The alias map |

## The context file is the product

I wrote [`context/context.md`](context/context.md) by hand, and that's deliberate. It holds what an experienced analyst carries in their head: which of the 3 tables answers which question, the 6 filters people forget when they're in a hurry, what "active" and "TPV" mean here, and why you never wrap the timestamp in a function.

An authored file is auditable. You can point at it and say exactly what the model was told on 14 March or any other date, because it's in version control. A system that builds up its own memory can't offer you that.

The cost is that a hand-written file can fall behind the schema. So I test it like code, with 3 checks:

| Test | What it proves |
|---|---|
| Every alias in the map is documented in the context | Nothing queryable is undescribed |
| Every alias the context mentions exists | The context isn't describing columns that are gone |
| No real identifier appears in the context or the prompt | The alias layer isn't leaking through the documentation |

When the schema grows, the first 20 aliases keep their numbers and the new column becomes `c_021`. Until somebody documents it, the build says so:

```
3 tables, 21 columns aliased; 1 new
Not yet documented in context/context.md: c_021
```

That turns "keep the context current as tables change" from a good intention into a failing test.

## What the guardrails catch, and what they can't

There are 6 golden questions, each with a reference query I wrote in real names. Against them sit 18 candidate answers written in aliases, the way a model would return them. Every candidate takes the same path a live answer would.

```
ok G1_a_correct                 pass
ok G1_b_no_outcome_filter       blocked:status_filter
ok G1_c_test_accounts_left_in   blocked:test_accounts
ok G1_d_counts_receivers        wrong_result
ok G2_a_correct                 pass
ok G2_b_utc_month               wrong_result
ok G2_c_funding_counted_as_tpv  wrong_result
ok G2_d_minor_units             wrong_result
ok G3_a_correct                 pass
ok G3_b_real_names              blocked:no_real_names
ok G3_c_select_star             blocked:no_select_star
ok G4_a_correct                 pass
ok G4_b_invented_column         blocked:known_identifiers
ok G5_a_correct                 pass
ok G5_b_two_statements          blocked:single_statement+read_only
ok G5_c_write                   blocked:read_only+test_accounts
ok G6_a_correct                 pass
ok G6_b_function_on_timestamp   blocked:date_bounded

18 candidates: 8 blocked, 6 pass, 4 wrong_result. 0 verdict(s) differ from what was expected.
```

Of the 18, 6 pass and 8 are stopped by one of the 8 rules. The other 4 are the ones to look at. Each of them passes every guardrail:

| Candidate | What's wrong with it |
|---|---|
| `G1_d` | Counts people who only received a transfer as active |
| `G2_b` | Uses UTC month boundaries, so 3 hours at each end of September land in the wrong month |
| `G2_c` | Counts cash in and cash out as payment value |
| `G2_d` | Forgets the amounts are in minor units, so every figure is 100 times too big |

All 4 are well-formed, read-only, properly filtered SQL that returns a confident, wrong number. No pattern check will ever catch them, because they aren't mistakes of form. They're mistakes of meaning. Only 2 things help: a context file that states the definition clearly enough to prevent them, and golden answers to catch them when it doesn't.

One more row deserves a mention. `G6_b` returns the right answer for December 2025 and is still blocked, because it wraps the timestamp in a function and would scan all 194,707 rows. Some rules are about cost, not correctness.

## Run it

You need Python 3.9 or later.

```bash
pip install -r requirements.txt
```

```bash
python data/generate.py
```

```bash
python -m assistant eval
```

```bash
python -m assistant check evals/example_answer.sql --run
```

```bash
python -m pytest
```

That last command runs 40 tests in about 2 seconds.

## Using it with a model

The repo makes no network calls and holds no API keys. I did that on purpose: it works with whichever model you use, and there's nothing here to leak.

```bash
python -m assistant prompt "Which three cities had the most active customers in November 2025?"
```

That prints the full prompt: the context file, then your question. Give it to your model, save the SQL it returns, and check it:

```bash
python -m assistant check answer.sql --run
```

If all 8 rules pass, the query is translated to real names and run read-only. For the example answer in this repo you get Port Azure with 903 active customers, Saffron Bay with 590 and Highmere with 462. Those results print for you. They don't go back to the model.

## Decisions worth explaining

**Column aliases are unique across the whole schema.** `c_012` means 1 column in 1 table. That's what lets translation be a plain token swap with no SQL parser in the path, and it keeps the security-relevant step short enough to read in a minute.

**The allow-list is the alias map.** Every name in a query has to be an alias from the map, a SQL word, or a label the query defined itself. Anything else is blocked. The demo database has a 4th table that isn't in the map, and 5 tests try to reach it or the database's own catalogue: by name, by comma join, by schema prefix. All 5 are stopped. The first version only checked names shaped like aliases, so a query that named the unlisted table outright would have run.

**Guardrails run before translation.** The check I care most about, "did the model use a real name it should never have seen", only makes sense on the aliased text.

**The connection is read-only anyway.** The guardrails block writes, and I've a test showing the connection refuses a `DELETE` even with the guardrails switched off. That's 2 layers, because the first one is pattern matching.

**Results never go back to the model.** It can't correct itself from the output. That's a real cost, and I accept it in exchange for the data never leaving.

## The messy part

- **My guardrails are pattern checks, not a parser.** They'll miss things a parser would catch, and they err towards blocking. The list of SQL words they accept is short, about 90, so a query using a function that isn't on it (`group_concat`, say) is stopped until somebody adds it. `REPLACE()` is blocked outright because `REPLACE INTO` is a write. That's the safe way to be wrong, and a parser is the next step.
- **I wrote the 18 candidates by hand. They aren't recorded model output.** This repo shows what each layer catches. It doesn't measure how often any particular model gets things right. For that you'd point the same harness at real answers, over a few hundred questions and not 6.
- **Descriptions carry meaning.** The model isn't told a column is called `amount_minor`, but it is told the column holds an amount in minor units. Aliasing hides identifiers, not concepts. Code values such as `'success'` are visible too, and in a stricter setting I'd alias those as well.
- **Sequential aliases are guessable.** `t_01`, `t_02`, `t_03` tells you there are 3 tables. The map sits in this repo only because the data is fake. In real use it lives where the model and its users can't read it.

## About the data

Every row is generated by [`data/generate.py`](data/generate.py) from a fixed seed: 4,000 customers and 194,707 transactions across 2025. Zaffre Wallet, its customers, merchants and currency are invented. None of the code, schema, rules or context in this repo comes from an employer's systems.

## Licence

MIT
