#!/usr/bin/env python3
"""Validate a Regime Pilot strategy spec.

Two layers:
  1. JSON Schema (draft 2020-12) structural validation against spec/schema.json.
  2. Semantic cross-checks the schema cannot express:
       - every feature_ref in any predicate / sizing refers to a defined feature
       - every playbook key matches a defined regime name (and every regime has a playbook)
       - sizing.asset_vol_feature points at a realized_vol feature
       - playbook.select.feature / reentry_feature refer to defined features
       - derisk_ladder.except_regimes refer to defined regimes

Exit code 0 = VALID, 1 = INVALID. Prints plain-English errors.

Usage:
    python cli/validate_spec.py path/to/spec.json
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO / "spec" / "schema.json"


def _collect_feature_refs(node, out):
    """Walk a predicate AST collecting every {'feature': name}."""
    if isinstance(node, dict):
        if "feature" in node and len(node) == 1:
            out.add(node["feature"])
        for v in node.values():
            _collect_feature_refs(v, out)
    elif isinstance(node, list):
        for v in node:
            _collect_feature_refs(v, out)


def semantic_errors(spec):
    errors = []
    feature_names = {f["name"] for f in spec.get("features", [])}
    feature_kind = {f["name"]: f.get("transform", {}).get("kind") for f in spec.get("features", [])}
    regime_names = {r["name"] for r in spec.get("regimes", [])}

    # predicates in regimes + playbooks reference defined features
    refs = set()
    for r in spec.get("regimes", []):
        _collect_feature_refs(r.get("predicate", {}), refs)
    for pb in spec.get("playbooks", {}).values():
        for key in ("entry", "exit"):
            if key in pb:
                _collect_feature_refs(pb[key], refs)
    for ref in sorted(refs):
        if ref not in feature_names:
            errors.append(f"predicate references unknown feature '{ref}'")

    # playbooks <-> regimes
    pb_keys = set(spec.get("playbooks", {}).keys())
    for missing in sorted(regime_names - pb_keys):
        errors.append(f"regime '{missing}' has no playbook")
    for extra in sorted(pb_keys - regime_names):
        errors.append(f"playbook '{extra}' has no matching regime")

    # sizing.asset_vol_feature must be a realized_vol feature
    avf = spec.get("sizing", {}).get("asset_vol_feature")
    if avf is not None:
        if avf not in feature_names:
            errors.append(f"sizing.asset_vol_feature '{avf}' is not a defined feature")
        elif feature_kind.get(avf) != "realized_vol":
            errors.append(f"sizing.asset_vol_feature '{avf}' must be a realized_vol feature (is '{feature_kind.get(avf)}')")

    # playbook.select.feature / reentry_feature
    for name, pb in spec.get("playbooks", {}).items():
        sel = pb.get("select", {})
        if sel.get("rank_by") == "feature":
            f = sel.get("feature")
            if not f:
                errors.append(f"playbook '{name}': rank_by=feature requires 'feature'")
            elif f not in feature_names:
                errors.append(f"playbook '{name}': select.feature '{f}' unknown")
        rf = pb.get("reentry_feature")
        if rf and rf not in feature_names:
            errors.append(f"playbook '{name}': reentry_feature '{rf}' unknown")

    # derisk_ladder.except_regimes
    for rung in spec.get("risk", {}).get("derisk_ladder", []):
        for rg in rung.get("except_regimes", []):
            if rg not in regime_names:
                errors.append(f"derisk_ladder.except_regimes references unknown regime '{rg}'")

    return errors


def validate(spec):
    """Return (ok: bool, errors: list[str])."""
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    schema_errs = sorted(validator.iter_errors(spec), key=lambda e: list(e.path))
    errors = [f"schema: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in schema_errs]
    if not errors:
        # only run semantic checks if structure is sound (avoids noisy cascades)
        errors += semantic_errors(spec)
    return (len(errors) == 0, errors)


def main(argv):
    if len(argv) != 2:
        print("usage: validate_spec.py <spec.json>")
        return 2
    path = Path(argv[1])
    try:
        spec = json.loads(path.read_text())
    except Exception as e:
        print(f"INVALID: cannot parse JSON: {e}")
        return 1
    ok, errors = validate(spec)
    if ok:
        print(f"VALID: {path.name} ({spec['meta']['name']} v{spec['meta']['version']})")
        return 0
    print(f"INVALID: {path.name} — {len(errors)} problem(s):")
    for e in errors:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
