"""Faithful 5-Workshop ANSSI EBIOS Risk Manager data model & analytical workflow."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessValue(BaseModel):
    id: str
    name: str
    supporting_assets: list[str]
    feared_events: list[str]
    severity: int = Field(ge=1, le=4)  # 1=Negligible, 2=Limited, 3=Significant, 4=Critical


class RiskSourceObjective(BaseModel):
    id: str
    risk_source: str
    target_objective: str
    motivation: int = Field(ge=1, le=4)
    resources: int = Field(ge=1, le=4)
    retained: bool = True


class EcosystemStakeholder(BaseModel):
    id: str
    name: str
    category: str  # supplier | partner | contractor | cloud_host
    dependency: int = Field(ge=1, le=4)
    penetration: int = Field(ge=1, le=4)
    cyber_maturity: int = Field(ge=1, le=4)
    trust: int = Field(ge=1, le=4)

    @property
    def exposure(self) -> int:
        return self.dependency * self.penetration

    @property
    def reliability(self) -> int:
        return self.cyber_maturity * self.trust

    @property
    def threat_level(self) -> float:
        return round(self.exposure / max(1, self.reliability), 2)


class StrategicScenario(BaseModel):
    id: str
    title: str
    risk_source_id: str
    stakeholder_id: str | None = None
    feared_event: str
    initial_severity: int = Field(ge=1, le=4)


class OperationalScenario(BaseModel):
    id: str
    strategic_scenario_id: str
    title: str
    kill_chain_steps: list[str]  # Know -> Enter -> Discover -> Exploit
    likelihood: int = Field(ge=1, le=4)  # 1=Minimal, 2=Significant, 3=High, 4=Maximal
    severity: int = Field(ge=1, le=4)
    linked_controls: list[str] = Field(default_factory=list)


class RiskTreatmentPlan(BaseModel):
    id: str
    operational_scenario_id: str
    decision: str  # REDUCE | ACCEPT | TRANSFER | AVOID
    measures: list[str]
    residual_likelihood: int = Field(ge=1, le=4)
    residual_severity: int = Field(ge=1, le=4)
    owner: str
    target_date: str
    review_cycle: str = "Quarterly"


class EBIOSStudy(BaseModel):
    study_id: str
    org_id: str
    scope_statement: str
    workshop1_values: list[BusinessValue]
    workshop2_sources: list[RiskSourceObjective]
    workshop3_stakeholders: list[EcosystemStakeholder]
    workshop3_strategic: list[StrategicScenario]
    workshop4_operational: list[OperationalScenario]
    workshop5_treatments: list[RiskTreatmentPlan]

    def summary(self) -> dict[str, object]:
        critical_initial = sum(1 for op in self.workshop4_operational if op.severity * op.likelihood >= 9)
        critical_residual = sum(1 for tr in self.workshop5_treatments if tr.residual_severity * tr.residual_likelihood >= 9)
        top_stakeholder = max(self.workshop3_stakeholders, key=lambda s: s.threat_level, default=None)
        return {
            "study_id": self.study_id,
            "business_values_count": len(self.workshop1_values),
            "retained_risk_sources": sum(1 for s in self.workshop2_sources if s.retained),
            "ecosystem_stakeholders": len(self.workshop3_stakeholders),
            "highest_threat_stakeholder": top_stakeholder.name if top_stakeholder else None,
            "highest_stakeholder_threat_level": top_stakeholder.threat_level if top_stakeholder else 0.0,
            "strategic_scenarios": len(self.workshop3_strategic),
            "operational_scenarios": len(self.workshop4_operational),
            "high_risk_initial_count": critical_initial,
            "high_risk_residual_count": critical_residual,
            "treatments_defined": len(self.workshop5_treatments),
        }
