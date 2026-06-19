"""Route engine tests to committed offline fixtures on a fresh checkout."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from cli._fixture import use_fixture_cache


def pytest_sessionstart(session):
    use_fixture_cache()
