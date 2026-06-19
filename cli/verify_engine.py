#!/usr/bin/env python3
"""Claim: the backtest is deterministic, lookahead-free, and the sizing ladder is correct.

Runs offline against the committed synthetic fixture (no data download needed): determinism +
no-lookahead guard + feature-shift (tests/test_engine.py) and the sizing ladder
(tests/test_sizing.py).

Run: python cli/verify_engine.py   (or: make verify-engine)
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _run(pyfile):
    spec = importlib.util.spec_from_file_location(Path(pyfile).stem, REPO / pyfile)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main()


def main():
    from cli._fixture import use_fixture_cache
    use_fixture_cache()                      # route engine at the synthetic fixture
    rc1 = _run("tests/test_engine.py")
    rc2 = _run("tests/test_sizing.py")
    rc3 = _run("tests/test_engine_compat.py")
    return 0 if all(rc in (0, None) for rc in (rc1, rc2, rc3)) else 1


if __name__ == "__main__":
    sys.exit(main())
