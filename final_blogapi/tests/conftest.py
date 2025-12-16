import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path):
    # Use temp SQLite file
    db_url = f"sqlite:///{tmp_path/'test.db'}"
    os.environ["DATABASE_URL"] = db_url
    os.environ["SECRET_KEY"] = "test-secret"

    # Reload modules that depend on env vars
    import database.session as session_mod
    importlib.reload(session_mod)

    import database.init_db as init_db_mod
    importlib.reload(init_db_mod)

    import main as main_mod
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as c:
        yield c
