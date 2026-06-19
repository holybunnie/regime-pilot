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
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

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
    feature_list = [f["name"] for f in spec.get("features", [])]
    feature_names = set(feature_list)
    feature_kind = {f["name"]: f.get("transform", {}).get("kind") for f in spec.get("features", [])}
    regime_list = [r["name"] for r in spec.get("regimes", [])]
    regime_names = set(regime_list)

    if len(feature_list) != len(feature_names):
        errors.append("feature names must be unique")
    if len(regime_list) != len(regime_names):
        errors.append("regime names must be unique")

    created = spec.get("meta", {}).get("created_at", "")
    try:
        parsed = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
            errors.append("meta.created_at must include an explicit UTC timezone")
    except (TypeError, ValueError):
        errors.append("meta.created_at must be a valid ISO-8601 date-time")

    universe = spec.get("universe", {})
    symbols = universe.get("symbols", [])
    excludes = universe.get("exclude_symbols", [])
    if universe.get("source") == "explicit" and not symbols:
        errors.append("universe.source=explicit requires a non-empty symbols list")
    if len(symbols) != len(set(symbols)):
        errors.append("universe.symbols must not contain duplicates")
    if len(excludes) != len(set(excludes)):
        errors.append("universe.exclude_symbols must not contain duplicates")
    overlap = sorted(set(symbols) & set(excludes))
    if overlap:
        errors.append(f"universe symbols cannot also be excluded: {overlap}")

    regimes = spec.get("regimes", [])
    if regimes and regimes[-1].get("predicate") != {"const_bool": True}:
        errors.append("the final regime must be the catch-all predicate {'const_bool': true}")

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

    # action-specific playbook requirements
    for name, pb in spec.get("playbooks", {}).items():
        action = pb.get("action")
        sel = pb.get("select", {})
        if action in ("hold_assets", "short_assets") and not sel:
            errors.append(f"playbook '{name}': action={action} requires select")
        if sel and sel.get("rank_by") != "volume_24h":
            errors.append(f"playbook '{name}': installed engine only supports rank_by=volume_24h")
        rf = pb.get("reentry_feature")
        if rf and rf not in feature_names:
            errors.append(f"playbook '{name}': reentry_feature '{rf}' unknown")
        if action == "staged_reentry":
            if not pb.get("assets"):
                errors.append(f"playbook '{name}': staged_reentry requires non-empty assets")
            if not rf:
                errors.append(f"playbook '{name}': staged_reentry requires reentry_feature")
        elif rf:
            errors.append(f"playbook '{name}': reentry_feature is only valid for staged_reentry")
        if action == "short_assets" and spec.get("costs", {}).get("short_borrow_bps_per_day", 0) <= 0:
            errors.append(f"playbook '{name}': short_assets requires positive short_borrow_bps_per_day")

    for f in spec.get("features", []):
        transform = f.get("transform", {})
        kind = transform.get("kind")
        if f.get("source") == "price" and kind != "breadth" and not f.get("asset"):
            errors.append(f"feature '{f['name']}': source=price requires asset unless transform=breadth")
        if kind != "breadth" and ("threshold_kind" in transform or "threshold_window" in transform):
            errors.append(f"feature '{f['name']}': breadth threshold fields require transform=breadth")

    # derisk_ladder.except_regimes
    for rung in spec.get("risk", {}).get("derisk_ladder", []):
        for rg in rung.get("except_regimes", []):
            if rg not in regime_names:
                errors.append(f"derisk_ladder.except_regimes references unknown regime '{rg}'")
    ladder = spec.get("risk", {}).get("derisk_ladder", [])
    triggers = [r.get("budget_consumed") for r in ladder]
    if triggers != sorted(triggers) or len(triggers) != len(set(triggers)):
        errors.append("risk.derisk_ladder budget_consumed values must be unique and increasing")

    return errors


def validate(spec):
    """Return (ok: bool, errors: list[str])."""
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
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
