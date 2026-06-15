#!/usr/bin/env python3
"""Optional data-source abstraction (Item 11): choose the price/history source by config.

By default the build uses the free Binance public klines for historical OHLCV (the operator's
CMC free tier blocks historical price endpoints). When a CMC Pro key is present, prices/history
(and, later, derivatives) can come first-party from CoinMarketCap instead — WITHOUT changing any
engine logic. The engine consumes a normalized panel either way.

This module is deliberately NOT wired into the live committer's frozen path: selecting CMC Pro is
an opt-in upgrade to be enabled after reveal day (see DATA_PLAN.md / README Item 11). It exists so
the wiring is ready and testable; it changes nothing about the attested forward record.

Selection precedence (highest first):
  1. explicit override env REGIME_PILOT_PRICE_SOURCE = "binance" | "cmc_pro"
  2. CMC Pro key present (env CMC_PRO_API_KEY) -> "cmc_pro"
  3. default -> "binance"
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
    if (env.get("CMC_PRO_API_KEY") or "").strip():
        return CMC_PRO
    return BINANCE


def cmc_pro_available(env=None):
    """True if a CMC Pro key is configured (so the upgrade COULD be selected)."""
    env = os.environ if env is None else env
    return bool((env.get("CMC_PRO_API_KEY") or "").strip())


def describe(env=None):
    src = select_price_source(env)
    return {
        "active_price_source": src,
        "cmc_pro_available": cmc_pro_available(env),
        "note": "default Binance; set CMC_PRO_API_KEY (or REGIME_PILOT_PRICE_SOURCE=cmc_pro) "
                "to source prices first-party from CMC — a coherence upgrade, not an edge.",
    }
