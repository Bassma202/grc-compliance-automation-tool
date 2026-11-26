"""Comprehensive CONSERVA test suite & remediation regression tests (CONSERVA-01 through CONSERVA-05)."""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conserva.auth import ConservaAuthService
from conserva.case_studies import seed_four_case_studies
from conserva.controls import import_custom_controls, load_builtin_controls
from conserva.fair import pert_mean, pert_variance, run_fair_simulation, spearman_corr
from conserva.models import ControlStatus, FAIRScenarioInput
from conserva.storage import ConservaStore
from conserva.web import create_app


def test_exact_93_annex_a_controls_and_separate_isms_clauses() -> None:
    controls = load_builtin_controls()
    annex = [c for c in controls if c.control_id.startswith("A.")]
    clauses = [c for c in controls if c.control_id.startswith("Clause")]
    assert len(annex) == 93
    assert len(clauses) == 7
    assert sum(1 for c in annex if c.domain == "Organizational") == 37
    assert sum(1 for c in annex if c.domain == "People") == 8
    assert sum(1 for c in annex if c.domain == "Physical") == 14
    assert sum(1 for c in annex if c.domain == "Technological") == 34


def test_extensible_control_importer(tmp_path: Path) -> None:
    custom = tmp_path / "custom_controls.json"
    custom.write_text(
        json.dumps(
            [
                {
                    "control_id": "CUST-01",
                    "framework": "Private Org Standard",
                    "framework_version": "1.0",
                    "domain": "Technological",
                    "title": "Hardware HSM Key Isolation",
                    "objective": "Verify private signing keys remain inside FIPS 140-3 HSM.",
                    "obligation_type": "voluntary_framework",
                }
            ]
        ),
        encoding="utf-8",
    )
    loaded = import_custom_controls(custom)
    assert len(loaded) == 1
    assert loaded[0].control_id == "CUST-01"


def test_conserva03_spearman_rank_correlation_with_ties_and_edge_cases() -> None:
    """CONSERVA-03: Mandatory tied-rank regression x=[1,1,2,3], y=[1,2,3,4] -> ~0.9486832980505139."""
    r_tied = spearman_corr([1, 1, 2, 3], [1, 2, 3, 4])
    assert math.isclose(r_tied, 0.9486832980505139, abs_tol=1e-12)

    assert math.isclose(spearman_corr([1, 2, 3, 4], [10, 20, 30, 40]), 1.0, abs_tol=1e-12)
    assert math.isclose(spearman_corr([1, 2, 3, 4], [40, 30, 20, 10]), -1.0, abs_tol=1e-12)
    assert spearman_corr([5, 5, 5, 5], [1, 2, 3, 4]) == 0.0

    with pytest.raises(ValueError):
        spearman_corr([1.0], [2.0])
    with pytest.raises(ValueError):
        spearman_corr([1.0, float("nan")], [1.0, 2.0])


def test_conserva04_compound_frequency_severity_matches_analytical_moments() -> None:
    """CONSERVA-04: Validate compound Poisson-PERT aggregate annual loss mean, variance, and zero-event behavior."""
    # 1. Zero-frequency scenario -> strictly 0 loss, 100% zero-loss years
    cfg_zero = FAIRScenarioInput(
        scenario_name="Zero Frequency Check",
        currency="EUR",
        tef_min=0.0, tef_mode=0.0, tef_max=0.0,
        vuln_min=0.5, vuln_mode=0.5, vuln_max=0.5,
        primary_loss_min=10000, primary_loss_mode=10000, primary_loss_max=10000,
        secondary_freq=0.0,
        iterations=5000,
        seed=42,
    )
    res_zero = run_fair_simulation(cfg_zero)
    assert res_zero.expected_ale == 0.0
    assert res_zero.probability_of_zero_loss_pct == 100.0

    # 2. Constant LEF = 1.0, deterministic loss = 100,000 -> Compound Poisson(1) * 100k:
    #    E[AAL] = 100,000, Std[AAL] = 100,000, P(N=0) = e^-1 = 36.79%
    cfg_pois = FAIRScenarioInput(
        scenario_name="Exact Compound Poisson Reference",
        currency="EUR",
        tef_min=1.0, tef_mode=1.0, tef_max=1.0,
        vuln_min=1.0, vuln_mode=1.0, vuln_max=1.0,
        primary_loss_min=100000, primary_loss_mode=100000, primary_loss_max=100000,
        secondary_freq=0.0,
        iterations=50000,
        seed=2027,
    )
    res_pois = run_fair_simulation(cfg_pois)
    assert math.isclose(res_pois.expected_ale, 100000.0, rel_tol=0.02)
    assert math.isclose(res_pois.aggregate_loss_std, 100000.0, rel_tol=0.02)
    assert math.isclose(res_pois.probability_of_zero_loss_pct, math.exp(-1.0) * 100.0, abs_tol=1.0)

    # 3. Full uncertain PERT parameters -> validate analytical E[AAL] and Var[AAL]
    cfg = FAIRScenarioInput(
        scenario_name="Analytical Validation Benchmark",
        currency="EUR",
        tef_min=2.0, tef_mode=4.0, tef_max=8.0,
        vuln_min=0.10, vuln_mode=0.25, vuln_max=0.50,
        primary_loss_min=50000, primary_loss_mode=100000, primary_loss_max=200000,
        secondary_freq=0.50,
        secondary_loss_min=20000, secondary_loss_mode=60000, secondary_loss_max=100000,
        mitigated_vuln_factor=0.50,
        annual_control_cost=25000,
        iterations=50000,
        seed=2027,
    )
    res = run_fair_simulation(cfg)
    # Reproducibility check
    res_repeat = run_fair_simulation(cfg)
    assert res.expected_ale == res_repeat.expected_ale and res.p95_ale == res_repeat.p95_ale

    e_tef, v_tef = pert_mean(2.0, 4.0, 8.0), pert_variance(2.0, 4.0, 8.0)
    e_v, v_v = pert_mean(0.10, 0.25, 0.50), pert_variance(0.10, 0.25, 0.50)
    e_lef = e_tef * e_v
    v_lef = v_tef * v_v + v_tef * (e_v ** 2) + v_v * (e_tef ** 2)
    e_plm, v_plm = pert_mean(50000, 100000, 200000), pert_variance(50000, 100000, 200000)
    e_slm, v_slm = pert_mean(20000, 60000, 100000), pert_variance(20000, 60000, 100000)
    e_sec = 0.50 * e_slm
    v_sec = 0.50 * (v_slm + e_slm ** 2) - e_sec ** 2
    mu_x = e_plm + e_sec
    var_x = v_plm + v_sec

    analytical_ale = e_lef * mu_x
    analytical_std = math.sqrt(e_lef * (var_x + mu_x ** 2) + v_lef * (mu_x ** 2))

    assert math.isclose(res.expected_ale, analytical_ale, rel_tol=0.03)
    assert math.isclose(res.aggregate_loss_std, analytical_std, rel_tol=0.04)
    assert res.p50_ale <= res.p90_ale <= res.p95_ale <= res.p99_ale
    assert res.residual_expected_ale < res.expected_ale
    assert res.alternate_currency == "MAD"


def test_four_case_studies_produce_materially_different_outcomes(tmp_path: Path) -> None:
    store = ConservaStore(tmp_path / "conserva.db")
    seeded = seed_four_case_studies(store)
    assert set(seeded.keys()) == {"maison-valmont", "atlaspath-lab", "fondation-alqarawiyyin", "observatoire-meridien"}
    ales = {k: v["fair"]["expected_ale"] for k, v in seeded.items()}
    assert len(set(ales.values())) == 4
    assert seeded["atlaspath-lab"]["fair"]["currency"] == "MAD"
    assert seeded["maison-valmont"]["fair"]["currency"] == "EUR"


def test_conserva01_02_05_authenticated_authz_report_isolation_and_uuid_fair_runs(tmp_path: Path) -> None:
    """CONSERVA-01, 02, 05: Reject anonymous/untrusted headers, isolate reports, persist UUIDv4 FAIR runs."""
    auth = ConservaAuthService(secret_key="test-ephemeral-signing-secret-2027")
    db = tmp_path / "c.db"
    app = create_app(db_path=db, seed_demo=True, auth_service=auth)
    client = TestClient(app)

    tok_admin = auth.issue_token("sub-admin-01")
    tok_valmont_aud = auth.issue_token("sub-valmont-auditor")
    tok_valmont_view = auth.issue_token("sub-valmont-viewer")
    tok_expired = auth.issue_token("sub-valmont-auditor", ttl_seconds=-10)

    # 1. Anonymous & spoofed-header requests MUST be rejected (401)
    assert client.get("/api/orgs/maison-valmont/soa").status_code == 401
    assert client.get("/api/orgs/maison-valmont/report.md").status_code == 401
    assert client.get(
        "/api/orgs/maison-valmont/soa",
        headers={"X-Conserva-Role": "ADMIN", "X-Conserva-Org": "maison-valmont"},
    ).status_code == 401
    assert client.get(
        "/api/orgs/maison-valmont/soa",
        headers={"Authorization": f"Bearer {tok_expired}"},
    ).status_code == 401

    # 2. Viewer cannot mutate assessment (403)
    r_denied = client.put(
        "/api/orgs/maison-valmont/assessments/A.5.1",
        headers={"Authorization": f"Bearer {tok_valmont_view}"},
        json={"applicable": True, "status": ControlStatus.IMPLEMENTED.value},
    )
    assert r_denied.status_code == 403

    # 3. Cross-tenant SoA AND cross-tenant Markdown report export MUST be rejected (403)
    assert client.get(
        "/api/orgs/atlaspath-lab/soa",
        headers={"Authorization": f"Bearer {tok_valmont_aud}"},
    ).status_code == 403
    assert client.get(
        "/api/orgs/atlaspath-lab/report.md",
        headers={"Authorization": f"Bearer {tok_valmont_aud}"},
    ).status_code == 403

    # 4. Authorized tenant report export succeeds and contains only authorized org data
    r_rep = client.get(
        "/api/orgs/maison-valmont/report.md",
        headers={"Authorization": f"Bearer {tok_valmont_aud}"},
    )
    assert r_rep.status_code == 200
    assert "Maison Valmont" in r_rep.text and "AtlasPath" not in r_rep.text

    # 5. Non-applicable without justification rejected (422); authorized write succeeds
    assert client.put(
        "/api/orgs/maison-valmont/assessments/A.7.11",
        headers={"Authorization": f"Bearer {tok_valmont_aud}"},
        json={"applicable": False, "applicability_justification": "", "status": ControlStatus.NOT_ASSESSED.value},
    ).status_code == 422
    assert client.put(
        "/api/orgs/maison-valmont/assessments/A.5.3",
        headers={"Authorization": f"Bearer {tok_valmont_aud}"},
        json={"applicable": True, "applicability_justification": "Applicable", "status": ControlStatus.IMPLEMENTED.value},
    ).status_code == 200

    # 6. CONSERVA-05: Repeated identical FAIR scenarios generate distinct persistent UUIDv4 IDs & tenant-safe lookup
    fair_body = {
        "scenario_name": "Duplicate Scenario Name Test",
        "currency": "EUR",
        "tef_min": 1.0, "tef_mode": 2.0, "tef_max": 3.0,
        "vuln_min": 0.1, "vuln_mode": 0.2, "vuln_max": 0.3,
        "primary_loss_min": 10000, "primary_loss_mode": 20000, "primary_loss_max": 40000,
        "iterations": 2000, "seed": 99,
    }
    r1 = client.post("/api/orgs/maison-valmont/fair", headers={"Authorization": f"Bearer {tok_valmont_aud}"}, json=fair_body)
    r2 = client.post("/api/orgs/maison-valmont/fair", headers={"Authorization": f"Bearer {tok_valmont_aud}"}, json=fair_body)
    assert r1.status_code == 200 and r2.status_code == 200
    id1, id2 = r1.json()["run_id"], r2.json()["run_id"]
    assert id1 != id2
    uuid.UUID(id1.removeprefix("FAIR-"))
    uuid.UUID(id2.removeprefix("FAIR-"))

    # Survives app restart (new app instance against same SQLite DB) and enforces tenant scope
    client2 = TestClient(create_app(db_path=db, seed_demo=False, auth_service=auth))
    assert client2.get(f"/api/orgs/maison-valmont/fair/{id1}", headers={"Authorization": f"Bearer {tok_valmont_aud}"}).status_code == 200
    assert client2.get(f"/api/orgs/atlaspath-lab/fair/{id1}", headers={"Authorization": f"Bearer {tok_admin}"}).status_code == 404
    assert client2.get(f"/api/orgs/maison-valmont/fair/{id1}", headers={"Authorization": f"Bearer {auth.issue_token('sub-atlaspath-risk')}"}).status_code == 403
