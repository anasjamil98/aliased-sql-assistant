"""Treats the authored context file as something that can be tested.

context.md is written by hand. That's deliberate: you can point at the file and
say exactly what the model was told. The cost is that a hand-written file can
fall behind the schema, so these checks make that visible.
"""

import re
from pathlib import Path

from .aliasing import ALIAS_TOKEN, ROOT

CONTEXT_PATH = ROOT / "context" / "context.md"


def read(path=CONTEXT_PATH):
    return Path(path).read_text(encoding="utf-8")


def undocumented(alias_map, text=None):
    """Aliases that exist in the map but are never mentioned in the context."""
    mentioned = set(ALIAS_TOKEN.findall(text if text is not None else read()))
    return sorted(alias_map.aliases - mentioned)


def stale(alias_map, text=None):
    """Aliases the context mentions that no longer exist in the map."""
    mentioned = set(ALIAS_TOKEN.findall(text if text is not None else read()))
    return sorted(mentioned - alias_map.aliases)


def leaked_names(alias_map, text=None):
    """Real identifiers that appear in the context.

    Only names containing an underscore are checked. Real names like "status"
    or "city" are also ordinary English words the context needs to use, so
    they can't be told apart from prose. The underscore names can't be prose.
    """
    text = (text if text is not None else read()).lower()
    distinctive = {name for name in alias_map.real_names if "_" in name}
    return sorted(name for name in distinctive if re.search(rf"\b{re.escape(name)}\b", text))


def build_prompt(question, text=None):
    """The full prompt for any model: the context, then the question. No data, no real names."""
    body = text if text is not None else read()
    return f"{body.rstrip()}\n\n---\n\n## Question\n\n{question.strip()}\n"
