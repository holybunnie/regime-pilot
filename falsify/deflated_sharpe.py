#!/usr/bin/env python3
"""Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

The Probabilistic Sharpe Ratio against a benchmark SR*:
    PSR(SR*) = Phi( (SR_hat - SR*) * sqrt(T-1) / sqrt(1 - skew*SR_hat + (kurt-1)/4 * SR_hat^2) )

The Deflated Sharpe Ratio sets SR* to the expected MAXIMUM Sharpe obtainable from N
independent trials of zero true skill, so a strategy found after trying many
configurations must clear a higher bar:
    SR* = sqrt(Var(SR_trials)) * [ (1-gamma) Z^-1(1 - 1/N) + gamma Z^-1(1 - 1/(N e)) ]
where gamma is the Euler-Mascheroni constant and Z^-1 is the inverse standard normal CDF.

All Sharpe ratios here are PER-PERIOD (not annualized). Pure-math norm CDF/PPF (no scipy).
Reference: Bailey, D. & López de Prado, M. (2014), "The Deflated Sharpe Ratio".
"""
import math

GAMMA = 0.5772156649015329  # Euler-Mascheroni
E = math.e


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p):
    """Inverse standard normal CDF via Acklam's rational approximation (|err| < 1.2e-9)."""
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def psr(sr_hat, sr_benchmark, n_obs, skew, kurt):
    """Probabilistic Sharpe Ratio (probability true SR > benchmark). All SR per-period."""
    denom = math.sqrt(max(1e-12, 1 - skew * sr_hat + (kurt - 1) / 4.0 * sr_hat ** 2))
    z = (sr_hat - sr_benchmark) * math.sqrt(n_obs - 1) / denom
    return norm_cdf(z)


def expected_max_sharpe(var_sr_trials, n_trials):
    """Expected maximum per-period Sharpe across n_trials of zero-skill strategies."""
    if n_trials < 2 or var_sr_trials <= 0:
        return 0.0
    sd = math.sqrt(var_sr_trials)
    return sd * ((1 - GAMMA) * norm_ppf(1 - 1.0 / n_trials)
                 + GAMMA * norm_ppf(1 - 1.0 / (n_trials * E)))


def deflated_sharpe(sr_hat, n_obs, skew, kurt, var_sr_trials, n_trials):
    """Return (DSR, SR*). DSR is the probability the true SR exceeds the deflated benchmark."""
    sr_star = expected_max_sharpe(var_sr_trials, n_trials)
    return psr(sr_hat, sr_star, n_obs, skew, kurt), sr_star
