#!/usr/bin/env python3
"""Known-answer tests for the deflated/probabilistic Sharpe ratio implementation.

Run: python tests/test_deflated_sharpe.py   (exit 0 = pass)
"""
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from falsify import deflated_sharpe as ds   # noqa: E402


def approx(a, b, tol=1e-4):
    return abs(a - b) <= tol


def main():
    fails = []

    def check(cond, msg):
        print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
        if not cond:
            fails.append(msg)

    # norm CDF/PPF known values
    check(approx(ds.norm_cdf(0.0), 0.5), "norm_cdf(0)=0.5")
    check(approx(ds.norm_cdf(1.959963985), 0.975), "norm_cdf(1.96)=0.975")
    check(approx(ds.norm_ppf(0.975), 1.959963985, tol=1e-4), "norm_ppf(0.975)=1.96")
    check(approx(ds.norm_ppf(0.5), 0.0, tol=1e-6), "norm_ppf(0.5)=0")

    # PSR hand-computed: sr=0.1, bench=0, T=1000, skew=0, kurt=3 (normal)
    #   denom = sqrt(1 - 0 + (3-1)/4*0.01) = sqrt(1.005) = 1.0024969
    #   z = 0.1*sqrt(999)/1.0024969 = 0.1*31.606961/1.0024969 = 3.152832
    #   PSR = Phi(3.152832) = 0.999191
    val = ds.psr(0.1, 0.0, 1000, 0.0, 3.0)
    check(approx(val, 0.999191, tol=1e-4), f"PSR known-answer = {val:.6f} (expect 0.999191)")

    # expected_max_sharpe: var=0.01 (sd=0.1), N=27
    #   SR* = 0.1*[(1-gamma)*ppf(1-1/27) + gamma*ppf(1-1/(27e))]
    sd = 0.1
    expect = sd * ((1 - ds.GAMMA) * ds.norm_ppf(1 - 1/27)
                   + ds.GAMMA * ds.norm_ppf(1 - 1/(27 * math.e)))
    got = ds.expected_max_sharpe(0.01, 27)
    check(approx(got, expect, tol=1e-9), f"expected_max_sharpe reproduces formula = {got:.6f}")
    check(got > 0.15 and got < 0.30, f"SR* in a sane range for N=27 ({got:.4f})")

    # deflating raises the bar: DSR <= PSR vs zero benchmark
    dsr, sr_star = ds.deflated_sharpe(0.1, 1000, 0.0, 3.0, 0.01, 27)
    psr0 = ds.psr(0.1, 0.0, 1000, 0.0, 3.0)
    check(dsr <= psr0, f"DSR ({dsr:.4f}) <= undeflated PSR ({psr0:.4f}) — deflation tightens")

    print()
    if fails:
        print(f"FAIL: {len(fails)} test(s)")
        return 1
    print("ALL DEFLATED-SHARPE TESTS PASS")
    return 0


def test_deflated_sharpe_contract():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
