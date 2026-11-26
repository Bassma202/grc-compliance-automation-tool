"""Compound Frequency-Severity Monte Carlo Quantitative Risk Engine (Open FAIR-aligned).

Distinguishes clearly between:
1. Parameter uncertainty in Expected Annual Loss (EAL_param = LEF * SLE)
2. Compound aggregate annual loss distribution:
   - Annual event count N_i ~ Poisson(LEF_i) (captures true zero-event years & multi-event tail risk)
   - Individual event severity X_{i,k} = PrimaryLoss_{i,k} + Bernoulli(SLEF) * SecondaryLoss_{i,k}
   - Aggregate Annual Loss AAL_i = sum_{k=1}^{N_i} X_{i,k}
3. Mathematically exact tie-aware Spearman rank correlation (average-rank midranks) for sensitivity analysis.
"""

from __future__ import annotations

import math

import numpy as np

from conserva.models import FAIRResult, FAIRScenarioInput


def sample_pert(
    rng: np.random.Generator,
    low: float,
    mode: float,
    high: float,
    size: int,
    lam: float = 4.0,
) -> np.ndarray:
    """Sample from a standard Beta-PERT distribution bounded on [low, high]."""
    if high < mode or mode < low:
        raise ValueError(f"PERT bounds must satisfy low <= mode <= high (got {low}, {mode}, {high}).")
    if size <= 0:
        return np.empty(0, dtype=np.float64)
    if math.isclose(low, high):
        return np.full(size, low, dtype=np.float64)
    span = high - low
    alpha = 1.0 + lam * (mode - low) / span
    beta = 1.0 + lam * (high - mode) / span
    return low + rng.beta(alpha, beta, size=size) * span


def pert_mean(low: float, mode: float, high: float, lam: float = 4.0) -> float:
    return (low + lam * mode + high) / (lam + 2.0)


def pert_variance(low: float, mode: float, high: float, lam: float = 4.0) -> float:
    if math.isclose(low, high):
        return 0.0
    mu = pert_mean(low, mode, high, lam)
    return ((mu - low) * (high - mu)) / (lam + 3.0)


def _average_ranks(arr: np.ndarray) -> np.ndarray:
    """Assign exact fractional average ranks (midranks) when ties are present."""
    n = len(arr)
    order = np.argsort(arr, kind="mergesort")
    sorted_vals = arr[order]
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_vals[j] == sorted_vals[i]:
            j += 1
        avg_rank = 0.5 * (i + j - 1) + 1.0
        ranks[order[i:j]] = avg_rank
        i = j
    return ranks


def spearman_corr(x: np.ndarray | list[float], y: np.ndarray | list[float]) -> float:
    """Tie-aware Spearman rank correlation validated against SciPy reference semantics."""
    xa = np.asarray(x, dtype=np.float64)
    ya = np.asarray(y, dtype=np.float64)
    if xa.ndim != 1 or ya.ndim != 1 or len(xa) != len(ya):
        raise ValueError("Inputs must be 1-D sequences of equal length.")
    if len(xa) < 2:
        raise ValueError("At least 2 samples are required for Spearman correlation.")
    if not (np.all(np.isfinite(xa)) and np.all(np.isfinite(ya))):
        raise ValueError("Inputs must not contain NaN or infinite values.")
    if np.all(xa == xa[0]) or np.all(ya == ya[0]):
        return 0.0

    rx = _average_ranks(xa)
    ry = _average_ranks(ya)
    rx -= rx.mean()
    ry -= ry.mean()
    denom = float(np.sqrt(np.sum(rx * rx) * np.sum(ry * ry)))
    return float(np.sum(rx * ry) / denom) if denom > 0.0 else 0.0


# Preserve internal alias for callers
_spearman_corr = spearman_corr


def _simulate_compound_annual_losses(
    rng: np.random.Generator,
    lef_per_year: np.ndarray,
    cfg: FAIRScenarioInput,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate true compound Poisson frequency x per-event Beta-PERT severity aggregate annual losses."""
    event_counts = rng.poisson(lam=np.maximum(lef_per_year, 0.0))
    total_events = int(np.sum(event_counts))
    aal = np.zeros(len(lef_per_year), dtype=np.float64)
    if total_events == 0:
        return aal, event_counts

    ev_plm = sample_pert(rng, cfg.primary_loss_min, cfg.primary_loss_mode, cfg.primary_loss_max, total_events)
    ev_slm_raw = sample_pert(rng, cfg.secondary_loss_min, cfg.secondary_loss_mode, cfg.secondary_loss_max, total_events)
    ev_sec = (rng.random(total_events) < cfg.secondary_freq).astype(np.float64)
    ev_loss = ev_plm + ev_sec * ev_slm_raw

    year_indices = np.repeat(np.arange(len(lef_per_year)), event_counts)
    np.add.at(aal, year_indices, ev_loss)
    return aal, event_counts


def run_fair_simulation(cfg: FAIRScenarioInput) -> FAIRResult:
    """Execute seeded compound frequency-severity Monte Carlo simulation inspired by Open FAIR."""
    rng = np.random.default_rng(cfg.seed)
    n = cfg.iterations

    tef = sample_pert(rng, cfg.tef_min, cfg.tef_mode, cfg.tef_max, n)
    vuln = sample_pert(rng, cfg.vuln_min, cfg.vuln_mode, cfg.vuln_max, n)
    lef = tef * vuln

    # 1. Single-event severity reference samples (for parameter-level expected loss uncertainty & sensitivity)
    plm_ref = sample_pert(rng, cfg.primary_loss_min, cfg.primary_loss_mode, cfg.primary_loss_max, n)
    slm_ref_raw = sample_pert(rng, cfg.secondary_loss_min, cfg.secondary_loss_mode, cfg.secondary_loss_max, n)
    slm_ref = (rng.random(n) < cfg.secondary_freq).astype(np.float64) * slm_ref_raw
    sle_ref = plm_ref + slm_ref
    param_eal = lef * sle_ref

    # 2. Compound Aggregate Annual Loss (Poisson event counts x individual event severities)
    aal, event_counts = _simulate_compound_annual_losses(rng, lef, cfg)
    zero_loss_pct = round(float(np.mean(event_counts == 0) * 100.0), 2)

    # 3. Post-treatment residual compound simulation
    res_vuln = np.clip(vuln * cfg.mitigated_vuln_factor, 0.0, 1.0)
    res_lef = tef * res_vuln
    res_aal, _ = _simulate_compound_annual_losses(rng, res_lef, cfg)

    exp_ale = float(np.mean(aal))
    std_ale = float(np.std(aal, ddof=1)) if n > 1 else 0.0
    res_exp_ale = float(np.mean(res_aal))
    reduction = max(0.0, exp_ale - res_exp_ale)
    reduction_pct = (reduction / exp_ale * 100.0) if exp_ale > 0 else 0.0

    # Loss Exceedance Curve: P(Annual Loss >= threshold)
    thresholds = [0.5 * exp_ale, exp_ale, 2.0 * exp_ale, 3.0 * exp_ale] if exp_ale > 0 else [0.0]
    exceedance = {
        f">={int(round(th))}": round(float(np.mean(aal >= th) * 100.0), 2)
        for th in thresholds
        if th > 0
    }

    cur = cfg.currency.upper()
    if cur == "EUR":
        alt_cur = "MAD"
        alt_val = exp_ale * cfg.fx_eur_to_mad
    else:
        alt_cur = "EUR"
        alt_val = exp_ale / cfg.fx_eur_to_mad

    sensitivity = {
        "threat_event_frequency": round(spearman_corr(tef, param_eal), 4),
        "vulnerability": round(spearman_corr(vuln, param_eal), 4),
        "primary_loss_magnitude": round(spearman_corr(plm_ref, param_eal), 4),
        "secondary_loss_magnitude": round(spearman_corr(slm_ref, param_eal), 4),
    }

    return FAIRResult(
        scenario_name=cfg.scenario_name,
        currency=cur,
        iterations=n,
        seed=cfg.seed,
        expected_lef=round(float(np.mean(lef)), 4),
        expected_sle=round(float(np.mean(sle_ref)), 2),
        expected_ale=round(exp_ale, 2),
        aggregate_loss_std=round(std_ale, 2),
        probability_of_zero_loss_pct=zero_loss_pct,
        parameter_eal_p50=round(float(np.percentile(param_eal, 50)), 2),
        parameter_eal_p95=round(float(np.percentile(param_eal, 95)), 2),
        p50_ale=round(float(np.percentile(aal, 50)), 2),
        p90_ale=round(float(np.percentile(aal, 90)), 2),
        p95_ale=round(float(np.percentile(aal, 95)), 2),
        p99_ale=round(float(np.percentile(aal, 99)), 2),
        ci90_low=round(float(np.percentile(aal, 5)), 2),
        ci90_high=round(float(np.percentile(aal, 95)), 2),
        exceedance_curve=exceedance,
        residual_expected_ale=round(res_exp_ale, 2),
        residual_p95_ale=round(float(np.percentile(res_aal, 95)), 2),
        risk_reduction_amount=round(reduction, 2),
        risk_reduction_pct=round(reduction_pct, 2),
        annual_control_cost=round(cfg.annual_control_cost, 2),
        net_risk_benefit=round(reduction - cfg.annual_control_cost, 2),
        expected_ale_alternate_currency=round(alt_val, 2),
        alternate_currency=alt_cur,
        fx_metadata={
            "eur_to_mad": cfg.fx_eur_to_mad,
            "date": cfg.fx_date,
            "source": cfg.fx_source,
        },
        sensitivity_spearman=sensitivity,
        methodology_notes=(
            "Compound frequency-severity Monte Carlo model aligned with Open FAIR concepts: "
            "annual event counts N ~ Poisson(TEF * Vulnerability), each event severity sampled independently "
            "from Beta-PERT Primary + Bernoulli(SLEF)*Beta-PERT Secondary Loss. Separates parameter EAL "
            "uncertainty from true aggregate annual loss exceedance distribution; demonstration inputs are fictional."
        ),
    )
