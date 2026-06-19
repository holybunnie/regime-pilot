#!/usr/bin/env python3
"""OFFLINE verification scoreboard — the single command a judge/operator runs on a fresh
clone with NO secrets and NO downloaded data:  make verify

Every gate here is offline: schema fuzz, deterministic+no-lookahead engine on a committed
synthetic fixture, sizing ladder, deflated-Sharpe known-answer, falsification battery
integrity, attestation accounting (from the committed on-chain snapshot), the duplicate-race
guard, the secret-leak scan, and the doc/framing/universe/datasource checks. Live checks that
need a CMC key or the network live in `make verify-full`.

Prints one PASS/FAIL line per submission item, then a RESULT line.

Run: python cli/verify.py   (or: make verify)
"""
import contextlib
import hashlib
import importlib.util
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def run_pyfile(path, argv=None):
    """Exec a python file, call its main(), capture stdout. Returns (ok, output)."""
    p = REPO / path
    spec = importlib.util.spec_from_file_location(p.stem, p)
    mod = importlib.util.module_from_spec(spec)
    old_argv = sys.argv
    sys.argv = [str(p)] + (argv or [])
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            spec.loader.exec_module(mod)
            rc = mod.main()
        return (rc == 0 or rc is None), buf.getvalue()
    except SystemExit as e:
        return (e.code in (0, None)), buf.getvalue()
    except Exception as e:
        return False, buf.getvalue() + f"\nEXCEPTION: {e}"
    finally:
        sys.argv = old_argv


def gate_frozen():
    """Item 0: every frozen file matches its baseline or an approved documented hash."""
    baseline = {}
    for line in (REPO / "evidence" / "frozen_set_baseline.txt").read_text().splitlines():
        h, _, f = line.partition("  ")
        baseline[f.strip()] = h.strip()
    approved = {
        "attest/commit_hour.py":
            "797d7fea4e4559417592b674dc9b31affc90ec7a9c4e37d1f850e7fc01f854f3",
        "engine/backtest.py":
            "b6f6eb071444d8e5a68c96fc211359efd443cc3ec48c0565bc52d107188c6869",
    }
    out, ok = [], True
    for f, want in baseline.items():
        got = hashlib.sha256((REPO / f).read_bytes()).hexdigest()
        if got == want:
            out.append(f"  byte-identical: {f}")
        elif approved.get(f) == got:
            out.append(f"  approved guard-only change: {f}")
        else:
            ok = False
            out.append(f"  UNEXPECTED CHANGE: {f}\n    want {want}\n    got  {got}")
    return ok, "\n".join(out)


# Each item -> list of (sub-label, callable returning (ok, output)).
ITEMS = [
    ("0", "FROZEN SET unchanged (committer signal meaning intact)",
     [("frozen", gate_frozen)]),
    ("1", "Attestation: all on-chain commits accounted for (7,26 documented)",
     [("chain-complete", lambda: run_pyfile("attest/verify.py", ["--offline"]))]),
    ("2", "Duplicate-commit race: single-flight + on-chain guard hold",
     [("race-sim", lambda: run_pyfile("cli/verify_attest_race.py"))]),
    ("4/7", "Framing: full-window leads; no-edge stmt; precise timing wording",
     [("framing", lambda: run_pyfile("cli/verify_framing.py"))]),
    ("5", "Offline verify complete (schema, engine, sizing, dsr, falsification)",
     [("schema", lambda: run_pyfile("tests/test_schema.py")),
      ("engine-fixture", lambda: run_pyfile("tests/test_engine.py")),
      ("sizing", lambda: run_pyfile("tests/test_sizing.py")),
      ("deflated-sharpe", lambda: run_pyfile("tests/test_deflated_sharpe.py")),
      ("falsification", lambda: run_pyfile("cli/verify_falsification.py"))]),
    ("Skill", "Skill package valid; examples execute deterministically",
     [("skill", lambda: run_pyfile("cli/verify_skill.py"))]),
    ("6", "Attestation unit test runs on pinned deps (in-memory EVM)",
     [("test_attest", lambda: run_pyfile("tests/test_attest.py"))]),
    ("8", "Universe: 149-token file valid; one-switch swap",
     [("universe", lambda: run_pyfile("cli/verify_universe.py"))]),
    ("9/10", "README self-contained, system-first; source claim reworded",
     [("readme", lambda: run_pyfile("cli/verify_readme.py"))]),
    ("11", "CMC Pro adapter ready; source cutover remains explicit",
     [("datasource", lambda: run_pyfile("cli/verify_datasource.py"))]),
    ("12", "HANDOFF consistent with STATUS",
     [("docs", lambda: run_pyfile("cli/verify_docs_consistency.py"))]),
    ("13", "No secrets/salt seed in files or history",
     [("secrets", lambda: run_pyfile("cli/verify_secrets.py"))]),
    ("15", "Data-source & credential map matches real call sites",
     [("datasources", lambda: run_pyfile("cli/verify_datasources.py"))]),
    ("x402", "x402 data-cost plan integrity",
     [("x402", lambda: run_pyfile("cli/verify_x402.py"))]),
]


def main():
    from cli._fixture import use_fixture_cache
    use_fixture_cache()                       # route engine at the synthetic fixture

    print("######## REGIME PILOT — OFFLINE VERIFICATION SCOREBOARD ########")
    print("# Fresh clone, no secrets, no downloaded data. (Live checks: make verify-full)\n")

    rows, failures = [], []
    for item, claim, subs in ITEMS:
        sub_results = []
        for label, fn in subs:
            try:
                ok, out = fn()
            except Exception as e:
                ok, out = False, f"EXCEPTION: {e}"
            sub_results.append((label, ok, out))
        ok_all = all(ok for _, ok, _ in sub_results)
        rows.append((item, claim, ok_all))
        if not ok_all:
            for label, ok, out in sub_results:
                if not ok:
                    failures.append((item, label, out))

    npass = sum(1 for *_, ok in rows if ok)
    for item, claim, ok in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] Item{item:<5} {claim}")
    nfail = len(rows) - npass
    print()
    if failures:
        print("---- failure detail ----")
        for item, label, out in failures:
            print(f"## Item{item} / {label}:\n{out.strip()[-1500:]}\n")
    print("###############################################################")
    print(f"RESULT: {npass} PASS, {nfail} FAIL — "
          + ("offline gates passed" if nfail == 0 else "NOT READY"))
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
