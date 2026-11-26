"""Structured domain models for CONSERVA GRC, Evidence, SoA, EBIOS RM, and Open FAIR."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ControlStatus(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    PARTIAL = "PARTIAL"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    NOT_ASSESSED = "NOT_ASSESSED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ACCEPTED_EXCEPTION = "ACCEPTED_EXCEPTION"


class Role(str, Enum):
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    RISK_OWNER = "RISK_OWNER"
    VIEWER = "VIEWER"


class ControlDefinition(BaseModel):
    control_id: str
    framework: str
    framework_version: str
    domain: str
    title: str
    objective: str
    obligation_type: str  # legal | regulatory_guidance | certification_reference | voluntary_framework
    public_mappings: dict[str, list[str]] = Field(default_factory=dict)


class ControlAssessment(BaseModel):
    assessment_id: str
    org_id: str
    control_id: str
    applicable: bool = True
    applicability_justification: str = ""
    status: ControlStatus = ControlStatus.NOT_ASSESSED
    owner: str = "Unassigned"
    evidence_ids: list[str] = Field(default_factory=list)
    finding_notes: str = ""
    updated_at: str = Field(default_factory=utc_now_iso)


class EvidenceItem(BaseModel):
    evidence_id: str
    org_id: str
    control_id: str
    title: str
    evidence_type: str  # policy | technical_log | config_export | review_minutes | test_report
    source_ref: str
    sha256_digest: str
    owner: str
    collected_at: str = Field(default_factory=utc_now_iso)
    review_status: str = "PENDING_REVIEW"  # PENDING_REVIEW | APPROVED | REJECTED | EXPIRED
    reviewer: str | None = None
    next_review_due: str = ""
    limitations: str = ""


class FAIRScenarioInput(BaseModel):
    scenario_name: str
    currency: str = "EUR"  # EUR or MAD
    fx_eur_to_mad: float = 10.85
    fx_date: str = "2026-11-26"
    fx_source: str = "Reference demonstration rate (update from Bank Al-Maghrib / ECB for live budgeting)"
    # PERT triangular parameters (min, most_likely, max)
    tef_min: float = Field(ge=0.0)
    tef_mode: float = Field(ge=0.0)
    tef_max: float = Field(ge=0.0)
    vuln_min: float = Field(ge=0.0, le=1.0)
    vuln_mode: float = Field(ge=0.0, le=1.0)
    vuln_max: float = Field(ge=0.0, le=1.0)
    primary_loss_min: float = Field(ge=0.0)
    primary_loss_mode: float = Field(ge=0.0)
    primary_loss_max: float = Field(ge=0.0)
    secondary_freq: float = Field(default=0.25, ge=0.0, le=1.0)
    secondary_loss_min: float = Field(default=0.0, ge=0.0)
    secondary_loss_mode: float = Field(default=0.0, ge=0.0)
    secondary_loss_max: float = Field(default=0.0, ge=0.0)
    mitigated_vuln_factor: float = Field(default=0.45, gt=0.0, le=1.0)
    annual_control_cost: float = Field(default=0.0, ge=0.0)
    iterations: int = Field(default=10000, ge=1000, le=100000)
    seed: int = 2027


class FAIRResult(BaseModel):
    run_id: str | None = None
    scenario_name: str
    currency: str
    iterations: int
    seed: int
    expected_lef: float
    expected_sle: float
    expected_ale: float
    aggregate_loss_std: float = 0.0
    probability_of_zero_loss_pct: float = 0.0
    parameter_eal_p50: float = 0.0
    parameter_eal_p95: float = 0.0
    p50_ale: float
    p90_ale: float
    p95_ale: float
    p99_ale: float
    ci90_low: float
    ci90_high: float
    exceedance_curve: dict[str, float] = Field(default_factory=dict)
    residual_expected_ale: float
    residual_p95_ale: float
    risk_reduction_amount: float
    risk_reduction_pct: float
    annual_control_cost: float
    net_risk_benefit: float
    expected_ale_alternate_currency: float
    alternate_currency: str
    fx_metadata: dict[str, Any]
    sensitivity_spearman: dict[str, float]
    methodology_notes: str
