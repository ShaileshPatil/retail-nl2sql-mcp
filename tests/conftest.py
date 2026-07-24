import pytest
from data.create_retail_db import build_database
import tempfile, os


@pytest.fixture(scope="session")
def test_db_path():
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "test_retail.db")
    build_database(db_path=path, seed=99)
    return path
