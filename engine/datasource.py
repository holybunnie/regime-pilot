#!/usr/bin/env python3
"""Optional data-source abstraction (Item 11): choose the price/history source by config.

The frozen v2 record uses Binance public klines for historical OHLCV because the original CMC
plan blocked historical price endpoints. The operator now has Pro access and the separate
CMC adapter can provide first-party prices/history without changing strategy logic. The engine
consumes a normalized panel either way.

This module is deliberately NOT wired into the live committer's frozen path: selecting CMC Pro is
an opt-in upgrade to be enabled after reveal day (see DATA_PLAN.md / README Item 11). It exists so
the wiring is ready and testable; it changes nothing about the attested forward record.

Selection is explicit during the live v2 record:
  1. REGIME_PILOT_PRICE_SOURCE = "binance" | "cmc_pro"
  2. default -> "binance"

A Pro-capable `CMC_API_KEY` makes the CMC adapter available but does not silently switch the
hourly committer. The source cutover must be deliberate and versioned.
"""
import os

BINANCE = "binance"
CMC_PRO = "cmc_pro"
VALID = (BINANCE, CMC_PRO)


def select_price_source(env=None):
    """Return the active price/history source id. Pure function of config (env)."""
    env = os.environ if env is None else env
    override = (env.get("REGIME_PILOT_PRICE_SOURCE") or "").strip().lower()
    if override in VALID:
        return override
    return BINANCE


def cmc_pro_available(env=None):
    """True if a CMC Pro key is configured (so the upgrade COULD be selected)."""
    env = os.environ if env is None else env
    return bool((env.get("CMC_API_KEY") or env.get("CMC_PRO_API_KEY") or "").strip())


def describe(env=None):
    src = select_price_source(env)
    return {
        "active_price_source": src,
        "cmc_pro_available": cmc_pro_available(env),
        "note": "default remains Binance for the frozen v2 record; set "
                "REGIME_PILOT_PRICE_SOURCE=cmc_pro only at a documented version cutover.",
    }
