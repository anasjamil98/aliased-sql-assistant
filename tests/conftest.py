import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data"))

import generate  # noqa: E402
from assistant import aliasing  # noqa: E402


@pytest.fixture(scope="session")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "zaffre.db"
    generate.build(path, n_customers=600, seed=7)
    return path


@pytest.fixture(scope="session")
def alias_map():
    return aliasing.load()
