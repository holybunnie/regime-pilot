#!/usr/bin/env python3
"""Skill verification: the Skill (compiler layer).

  - SKILL.md exists with the CMC-format frontmatter fields
  - compiler_prompt.md exists
  - >= 3 example intents exist (incl. an impossible/refusal one)
  - every example/flagship spec validates
  - determinism: the SAME spec backtested twice gives byte-identical output
    (proves the LLM's nondeterminism is quarantined upstream of the spec file)

Run: python cli/verify_skill.py   (or: make verify-skill)
"""
import hashlib
import json
import re
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
AGENT_CONFIG = REPO / "skill" / "agents" / "openai.yaml"
REQUIRED_FRONTMATTER = {"name", "description"}
ALLOWED_FRONTMATTER = {"name", "description", "license", "metadata", "allowed-tools"}


def _frontmatter(path):
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}, ["SKILL.md must start with YAML frontmatter"]
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}, ["SKILL.md frontmatter is not closed"]
    keys = {}
    for line in parts[1].splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z0-9_-]+):(?:\s*(.*))?$", line)
        if m:
            keys[m.group(1)] = (m.group(2) or "").strip()
    errors = []
    missing = REQUIRED_FRONTMATTER - set(keys)
    extra = set(keys) - ALLOWED_FRONTMATTER
    if missing:
        errors.append(f"missing frontmatter keys: {sorted(missing)}")
    if extra:
        errors.append(f"unsupported frontmatter keys: {sorted(extra)}")
    name = keys.get("name", "").strip("\"'")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
        errors.append("name must be 1-64 lowercase letters, digits, or hyphens")
    return keys, errors


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
        frontmatter, errors = _frontmatter(SKILL)
        check(not errors, "SKILL.md has valid installable frontmatter"
              + ("" if not errors else f": {errors}"))
        check(frontmatter.get("name", "").strip("\"'") == "regime-pilot",
              "skill folder/name identity is regime-pilot")
    check(AGENT_CONFIG.exists(), "skill/agents/openai.yaml exists")
    if AGENT_CONFIG.exists():
        agent_text = AGENT_CONFIG.read_text()
        check("$regime-pilot" in agent_text, "agent default prompt invokes $regime-pilot")
        check("display_name:" in agent_text and "short_description:" in agent_text,
              "agent UI metadata is present")
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
    from cli._fixture import use_fixture_cache
    use_fixture_cache()
    ex = json.loads((REPO / "skill" / "examples" / "momentum_simple.spec.json").read_text())
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        bt.write_outputs(bt.run(ex), a)
        bt.write_outputs(bt.run(ex), b)
        check(_hash_dir(a) == _hash_dir(b), "same spec backtested twice -> byte-identical output")

    print()
    if fails:
        print(f"RESULT: {len(fails)} problem(s).")
        return 1
    print("ALL SKILL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
