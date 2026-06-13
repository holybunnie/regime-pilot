#!/usr/bin/env python3
"""Pre-registered parameter grid + spec-variant generation for falsification.

The grid matches meta.configurations_tried (27) in the frozen flagship:
    persistence in {4, 8, 12} x k in {0.3, 0.5, 0.7} x breadth-high threshold in {55, 60, 65}

Variants are produced as deep copies; the frozen spec file on disk is never modified
(it must stay frozen for the live attestation). Variants in this grid share the SAME
features (only regime persistence, sizing k, and a predicate constant change), so the
caller can compute features once and inject them.
"""
import copy

PERSISTENCE = [4, 8, 12]
K = [0.3, 0.5, 0.7]
BREADTH_THR = [55, 60, 65]


def set_threshold(pred, feature, new_const):
    """Recursively set the constant compared against `feature` in a predicate AST."""
    if not isinstance(pred, dict):
        return
    if pred.get("op") in (">", "<", ">=", "<=", "crosses_above", "crosses_below"):
        left, right = pred.get("left", {}), pred.get("right", {})
        if left.get("feature") == feature and "const" in right:
            right["const"] = new_const
        elif right.get("feature") == feature and "const" in left:
            left["const"] = new_const
    for a in pred.get("args", []):
        set_threshold(a, feature, new_const)


def make_variant(base_spec, persistence, k, breadth_thr):
    s = copy.deepcopy(base_spec)
    for r in s["regimes"]:
        if r["name"] != "chop":                       # keep the catch-all responsive
            r["persistence_hours"] = persistence
    s["sizing"]["k"] = k
    for r in s["regimes"]:
        if r["name"] == "trend_up":
            set_threshold(r["predicate"], "breadth_pct", breadth_thr)
    s["meta"]["name"] = f"variant_p{persistence}_k{k}_b{breadth_thr}"
    return s


def grid(base_spec):
    """Yield (label, spec_variant) for all 27 configurations."""
    for p in PERSISTENCE:
        for k in K:
            for b in BREADTH_THR:
                yield (f"p{p}_k{k}_b{b}", make_variant(base_spec, p, k, b))


def n_configs():
    return len(PERSISTENCE) * len(K) * len(BREADTH_THR)
