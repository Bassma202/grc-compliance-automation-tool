"""Monte Carlo Open FAIR Quantitative Cyber-Risk Engine.

Implements Beta-PERT distributions over Threat Event Frequency (TEF), Vulnerability (V),
Primary Loss Magnitude (PLM), and Secondary Loss (SLEF * SLM), outputting annualized loss
distributions, percentiles (p50/p90/p95/p99), post-treatment residual exposure, cost-benefit,
and Spearman rank sensitivity analysis.
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
    if math.isclose(low, high):
        return np.full(size, low, dtype=np.float64)
    span = high - low
    alpha = 1.0 + lam * (mode - low) / span
    beta = 1.0 + lam * (high - mode) / span
    return low + rng.beta(alpha, beta, size=size) * span


def pert_mean(low: float, mode: float, high: float, lam: float = 4.0) -> float:
    return (low + lam * mode + high) / (lam + 2.0)


def _spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return 0.0
    rx = np.argsort(np.argsort(x)).astype(np.float64)
    ry = np.argsort(np.argsort(y)).astype(np.float64)
    rx -= rx.mean()
    ry -= ry.mean()
    denom = float(np.sqrt(np.sum(rx * rx) * np.sum(ry * ry)))
    return round(float(np.sum(rx * ry) / denom), 4) if denom > 0 else 0.0


def run_fair_simulation(cfg: FAIRScenarioInput) -> FAIRResult:
    """Execute seeded Monte Carlo Open FAIR simulation and return structured risk statistics."""
    rng = np.random.default_rng(cfg.seed)
    n = cfg.iterations

    tef = sample_pert(rng, cfg.tef_min, cfg.tef_mode, cfg.tef_max, n)
    vuln = sample_pert(rng, cfg.vuln_min, cfg.vuln_mode, cfg.vuln_max, n)
    lef = tef * vuln

    plm = sample_pert(rng, cfg.primary_loss_min, cfg.primary_loss_mode, cfg.primary_loss_max, n)
    slm_raw = sample_pert(rng, cfg.secondary_loss_min, cfg.secondary_loss_mode, cfg.secondary_loss_max, n)
    sec_occurs = (rng.random(n) < cfg.secondary_freq).astype(np.float64)
    slm = sec_occurs * slm_raw

    sle = plm + slm
    ale = lef * sle

    # Post-treatment residual simulation with reduced vulnerability factor
    res_vuln = np.clip(vuln * cfg.mitigated_vuln_factor, 0.0, 1.0)
    res_ale = (tef * res_vuln) * sle

    exp_ale = float(np.mean(ale))
    res_exp_ale = float(np.mean(res_ale))
    reduction = max(0.0, exp_ale - res_exp_ale)
    reduction_pct = (reduction / exp_ale * 100.0) if exp_ale > 0 else 0.0

    cur = cfg.currency.upper()
    if cur == "EUR":
        alt_cur = "MAD"
        alt_val = exp_ale * cfg.fx_eur_to_mad
    else:
        alt_cur = "EUR"
        alt_val = exp_ale / cfg.fx_eur_to_mad

    sensitivity = {
        "threat_event_frequency": _spearman_corr(tef, ale),
        "vulnerability": _spearman_corr(vuln, ale),
        "primary_loss_magnitude": _spearman_corr(plm, ale),
        "secondary_loss_magnitude": _spearman_corr(slm, ale),
    }

    return FAIRResult(
        scenario_name=cfg.scenario_name,
        currency=cur,
        iterations=n,
        seed=cfg.seed,
        expected_lef=round(float(np.mean(lef)), 4),
        expected_sle=round(float(np.mean(sle)), 2),
        expected_ale=round(exp_ale, 2),
        p50_ale=round(float(np.percentile(ale, 50)), 2),
        p90_ale=round(float(np.percentile(ale, 90)), 2),
        p95_ale=round(float(np.percentile(ale, 95)), 2),
        p99_ale=round(float(np.percentile(ale, 99)), 2),
        ci90_low=round(float(np.percentile(ale, 5)), 2),
        ci90_high=round(float(np.percentile(ale, 95)), 2),
        residual_expected_ale=round(res_exp_ale, 2),
        residual_p95_ale=round(float(np.percentile(res_ale, 95)), 2),
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
            "Beta-PERT Monte Carlo approximation inspired by Open FAIR taxonomy "
            "(LEF = TEF * Vulnerability; ALE = LEF * (Primary + Secondary Loss)). "
            "Assumes independent factor sampling; demonstration inputs are explicitly fictional."
        ),
    )
