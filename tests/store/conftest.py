from pathlib import Path

import pytest

from stratum.store.connection import connect

FIXTURES = Path(__file__).parent / "fixtures" / "data" / "raw"


@pytest.fixture
def conn():
    connection = connect(":memory:")
    yield connection
    connection.close()
