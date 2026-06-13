#!/usr/bin/env python3
"""Drawdown-budget position sizing law + de-risk ladder.

Sizing law (stated in README in plain math):
    position_size = min(vol_target_size, k * remaining_drawdown_budget / asset_vol)

where:
    vol_target_size       = vol_target_annual / asset_vol   (vol-targeting cap)
    remaining_drawdown_budget = 1 - (current_drawdown / max_drawdown_budget), floored at 0
    asset_vol             = annualized realized vol of the asset (from a realized_vol feature)
    k                     = conservative aggressiveness multiplier

The de-risk ladder then scales GROSS exposure down as the drawdown budget is
consumed:  at e.g. 50% consumed -> 0.5x, 75% -> 0x (except exempt regimes), 90% -> 0x.

All functions are pure and deterministic.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class Rung:
    budget_consumed: float
    gross_exposure_multiplier: float
    except_regimes: tuple = ()


def remaining_drawdown_budget(current_drawdown: float, max_drawdown_budget: float) -> float:
    """Fraction (0..1) of the drawdown budget still available."""
    if max_drawdown_budget <= 0:
        return 0.0
    frac_used = current_drawdown / max_drawdown_budget
    return max(0.0, min(1.0, 1.0 - frac_used))


def position_size(asset_vol: float, k: float, vol_target_annual: float,
                  current_drawdown: float, max_drawdown_budget: float,
                  max_position_weight: float) -> float:
    """Per-asset target weight before gross-exposure scaling. Always >= 0."""
    if asset_vol is None or asset_vol <= 0:
        return 0.0
    vol_target_size = vol_target_annual / asset_vol
    rem = remaining_drawdown_budget(current_drawdown, max_drawdown_budget)
    budget_size = k * rem / asset_vol
    size = min(vol_target_size, budget_size)
    return max(0.0, min(size, max_position_weight))


def gross_multiplier(current_drawdown: float, max_drawdown_budget: float,
                     ladder: List[Rung], regime: str) -> float:
    """Pick the most-aggressive de-risking rung whose trigger is met.

    Returns the gross-exposure multiplier (0..1). A rung is skipped for regimes
    listed in its except_regimes.
    """
    consumed = (current_drawdown / max_drawdown_budget) if max_drawdown_budget > 0 else 1.0
    eps = 1e-9  # so "exactly at the rung" triggers despite float rounding (0.15/0.20 = 0.74999…)
    mult = 1.0
    # apply the lowest multiplier among triggered, non-exempt rungs
    for rung in ladder:
        if consumed >= rung.budget_consumed - eps and regime not in rung.except_regimes:
            mult = min(mult, rung.gross_exposure_multiplier)
    return mult


def ladder_from_spec(risk_spec: dict) -> List[Rung]:
    return [Rung(r["budget_consumed"], r["gross_exposure_multiplier"],
                 tuple(r.get("except_regimes", []))) for r in risk_spec["derisk_ladder"]]
