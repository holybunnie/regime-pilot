#!/usr/bin/env python3
"""Phase 3 verification: the Skill (compiler layer).

  - SKILL.md exists with the CMC-format frontmatter fields
  - compiler_prompt.md exists
  - >= 3 example intents exist (incl. an impossible/refusal one)
  - every example/flagship spec validates
  - determinism: the SAME spec backtested twice gives byte-identical output
    (proves the LLM's nondeterminism is quarantined upstream of the spec file)

Run: python cli/verify_phase3.py   (or: make verify-phase3)
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "cli"))
import validate_spec                       # noqa: E402
from engine import backtest as bt         # noqa: E402

SKILL = REPO / "skill" / "SKILL.md"
PROMPT = REPO / "skill" / "compiler_prompt.md"
FRONTMATTER_KEYS = ["name:", "description:", "license:", "compatibility:", "user-invocable:", "allowed-tools:"]


def _hash_dir(d):
    h = hashlib.sha256()
    for f in sorted(Path(d).iterdir()):
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()


def main():
    fails = []

    def check(c, m):
        print(f"  [{'PASS' if c else 'FAIL'}] {m}")
        if not c:
            fails.append(m)

    check(SKILL.exists(), "skill/SKILL.md exists")
    if SKILL.exists():
        head = SKILL.read_text()[:1200]
        for k in FRONTMATTER_KEYS:
            check(k in head, f"SKILL.md frontmatter has {k}")
    check(PROMPT.exists(), "skill/compiler_prompt.md exists")

    intents = sorted((REPO / "skill" / "examples").glob("*.intent.md"))
    check(len(intents) >= 3, f">= 3 example intents ({len(intents)})")
    names = " ".join(p.name for p in intents)
    check("impossible" in names, "includes an impossible/refusal example")

    # validate every spec the skill references
    specs = sorted((REPO / "skill" / "examples").glob("*.spec.json")) + \
            sorted((REPO / "spec").glob("regime_pilot*.spec.json"))
    for sp in specs:
        ok, errs = validate_spec.validate(json.loads(sp.read_text()))
        check(ok, f"validates: {sp.relative_to(REPO)}" + ("" if ok else f" -> {errs}"))

    # determinism on an example spec (downstream purity)
    ex = json.loads((REPO / "skill" / "examples" / "momentum_simple.spec.json").read_text())
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        bt.write_outputs(bt.run(ex), a)
        bt.write_outputs(bt.run(ex), b)
        check(_hash_dir(a) == _hash_dir(b), "same spec backtested twice -> byte-identical output")

    print()
    if fails:
        print(f"RESULT: {len(fails)} problem(s).")
        return 1
    print("ALL PHASE 3 CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
