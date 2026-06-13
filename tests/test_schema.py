#!/usr/bin/env python3
"""Phase 2 verification: schema accepts valid specs and rejects malformed ones.

Run: python tests/test_schema.py   (exit 0 = all pass)

Covers the build-spec requirement: validates all skill/examples/*.spec.json and
rejects >= 5 deliberately malformed specs, each breaking ONE rule so a failure
points at exactly what regressed.
"""
import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "cli"))
import validate_spec  # noqa: E402

VALID_EXAMPLE = REPO / "skill" / "examples" / "momentum_simple.spec.json"


def load_valid():
    return json.loads(VALID_EXAMPLE.read_text())


def malformed_cases():
    """Each case: (name, mutator) producing a spec that MUST be rejected."""
    cases = []

    def case(name):
        def deco(fn):
            cases.append((name, fn))
            return fn
        return deco

    @case("meta.version not semver")
    def _(s):
        s["meta"]["version"] = "v1"; return s

    @case("predicate references unknown feature")
    def _(s):
        s["regimes"][0]["predicate"]["args"][0]["left"]["feature"] = "does_not_exist"; return s

    @case("regime has no matching playbook")
    def _(s):
        del s["playbooks"]["risk_off"]; return s

    @case("sizing.asset_vol_feature is not a realized_vol feature")
    def _(s):
        s["sizing"]["asset_vol_feature"] = "btc_now"; return s  # btc_now is 'raw'

    @case("free-form / illegal predicate operator")
    def _(s):
        s["regimes"][0]["predicate"] = {"op": "eval", "code": "os.system('x')"}; return s

    @case("derisk gross_exposure_multiplier > 1")
    def _(s):
        s["risk"]["derisk_ladder"][0]["gross_exposure_multiplier"] = 1.5; return s

    @case("missing required top-level section (costs)")
    def _(s):
        del s["costs"]; return s

    @case("extra unknown top-level key (additionalProperties)")
    def _(s):
        s["surprise"] = {"x": 1}; return s

    return cases


def main():
    failures = []

    # 1) all example specs must be VALID
    examples = sorted((REPO / "skill" / "examples").glob("*.spec.json"))
    if not examples:
        print("FAIL: no example specs found")
        return 1
    for ex in examples:
        ok, errs = validate_spec.validate(json.loads(ex.read_text()))
        if ok:
            print(f"[PASS] valid example accepted: {ex.name}")
        else:
            print(f"[FAIL] valid example REJECTED: {ex.name}")
            for e in errs:
                print(f"         {e}")
            failures.append(ex.name)

    # 2) malformed specs must be REJECTED
    rejected = 0
    for name, mutate in malformed_cases():
        spec = mutate(copy.deepcopy(load_valid()))
        ok, errs = validate_spec.validate(spec)
        if ok:
            print(f"[FAIL] malformed spec WRONGLY accepted: {name}")
            failures.append(name)
        else:
            rejected += 1
            print(f"[PASS] malformed spec rejected: {name}")

    print(f"\nSummary: {len(examples)} example(s) valid, {rejected} malformed rejected.")
    if rejected < 5:
        print(f"FAIL: requirement is >= 5 malformed rejected, got {rejected}")
        return 1
    if failures:
        print(f"FAIL: {len(failures)} problem(s): {failures}")
        return 1
    print("ALL SCHEMA TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
