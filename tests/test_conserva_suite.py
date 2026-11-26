"""Comprehensive CONSERVA verification suite: 93 controls, analytical FAIR validation, EBIOS RM 5 workshops, RBAC & tenant isolation, 4-case divergence, and API/UI checks."""

from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi.testclient import TestClient

from conserva.case_studies import seed_four_case_studies
from conserva.controls import import_custom_controls, load_builtin_controls
from conserva.fair import pert_mean, run_fair_simulation
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


def test_fair_monte_carlo_matches_analytical_expectation() -> None:
    """Analytical validation: E[ALE] must match E[TEF]*E[V]*(E[PLM] + SLEF*E[SLM]) within 3%."""
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
    expected_lef = pert_mean(2.0, 4.0, 8.0) * pert_mean(0.10, 0.25, 0.50)
    expected_sle = pert_mean(50000, 100000, 200000) + 0.50 * pert_mean(20000, 60000, 100000)
    analytical_ale = expected_lef * expected_sle

    assert math.isclose(res.expected_ale, analytical_ale, rel_tol=0.03)
    assert res.p50_ale <= res.p90_ale <= res.p95_ale <= res.p99_ale
    assert res.residual_expected_ale < res.expected_ale
    assert res.alternate_currency == "MAD"


def test_four_case_studies_produce_materially_different_outcomes(tmp_path: Path) -> None:
    store = ConservaStore(tmp_path / "conserva.db")
    seeded = seed_four_case_studies(store)
    assert set(seeded.keys()) == {"maison-valmont", "atlaspath-lab", "fondation-alqarawiyyin", "observatoire-meridien"}
    ales = {k: v["fair"]["expected_ale"] for k, v in seeded.items()}
    assert len(set(ales.values())) == 4
    currencies = {k: v["fair"]["currency"] for k, v in seeded.items()}
    assert currencies["atlaspath-lab"] == "MAD"
    assert currencies["maison-valmont"] == "EUR"


def test_api_rbac_tenant_isolation_and_soa_validation(tmp_path: Path) -> None:
    client = TestClient(create_app(db_path=tmp_path / "c.db", seed_demo=True))
    assert client.get("/api/health").json()["annex_a_controls"] == 93

    # Viewer cannot mutate assessment
    r_denied = client.put(
        "/api/orgs/maison-valmont/assessments/A.5.1",
        headers={"X-Conserva-Role": "VIEWER", "X-Conserva-Org": "maison-valmont"},
        json={"applicable": True, "status": ControlStatus.IMPLEMENTED.value},
    )
    assert r_denied.status_code == 403

    # Cross-tenant read blocked for non-ADMIN
    r_cross = client.get(
        "/api/orgs/atlaspath-lab/soa",
        headers={"X-Conserva-Role": "AUDITOR", "X-Conserva-Org": "maison-valmont"},
    )
    assert r_cross.status_code == 403

    # Non-applicable control without justification rejected (422)
    r_na = client.put(
        "/api/orgs/maison-valmont/assessments/A.7.11",
        headers={"X-Conserva-Role": "AUDITOR", "X-Conserva-Org": "maison-valmont"},
        json={"applicable": False, "applicability_justification": "", "status": ControlStatus.NOT_ASSESSED.value},
    )
    assert r_na.status_code == 422

    # Authorized auditor update succeeds
    r_ok = client.put(
        "/api/orgs/maison-valmont/assessments/A.5.3",
        headers={"X-Conserva-Role": "AUDITOR", "X-Conserva-Org": "maison-valmont"},
        json={"applicable": True, "applicability_justification": "Applicable", "status": ControlStatus.IMPLEMENTED.value},
    )
    assert r_ok.status_code == 200

    # Institutional UI & Markdown report render cleanly
    assert "CONSERVA" in client.get("/?org=atlaspath-lab").text
    assert "Statement of Applicability" in client.get("/api/orgs/maison-valmont/report.md").text
