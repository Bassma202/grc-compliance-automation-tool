"""Four genuinely distinct fictional organizational case studies for CONSERVA.

Every organization, asset, stakeholder, and financial parameter is explicitly FICTIONAL and
calibrated to demonstrate meaningful sectoral differences in legal applicability, control
posture, EBIOS RM scenarios, and Monte Carlo Open FAIR loss distributions.
"""

from __future__ import annotations

import hashlib

from conserva.controls import load_builtin_controls
from conserva.ebios import (
    BusinessValue,
    EBIOSStudy,
    EcosystemStakeholder,
    OperationalScenario,
    RiskSourceObjective,
    RiskTreatmentPlan,
    StrategicScenario,
)
from conserva.fair import run_fair_simulation
from conserva.models import ControlAssessment, ControlStatus, EvidenceItem, FAIRScenarioInput
from conserva.storage import ConservaStore


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def seed_four_case_studies(store: ConservaStore) -> dict[str, dict[str, object]]:
    controls = load_builtin_controls()
    annex_a = [c for c in controls if c.control_id.startswith("A.")]

    specs = [
        {
            "org_id": "maison-valmont",
            "name": "Maison Valmont (Fictional Luxury Fashion House)",
            "sector": "Luxury Couture & Digital Commerce",
            "jurisdiction": "France / EU",
            "laws": ["EU GDPR", "NIS2 (supply-chain readiness)", "IP Confidentiality"],
            "summary": "Fictional Parisian haute-couture maison protecting unreleased seasonal designs, VIP clientele CRM, and atelier supplier portals.",
            "na_controls": {"A.7.11": "No dedicated on-premise data center; workloads hosted on managed EU cloud."},
            "impl_set": {"A.5.1", "A.5.12", "A.5.15", "A.5.32", "A.6.6", "A.7.1", "A.8.1", "A.8.5", "A.8.24"},
            "partial_set": {"A.5.19", "A.5.20", "A.8.2", "A.8.12", "A.8.15", "A.8.16"},
            "missing_set": {"A.5.3", "A.5.22", "A.8.11", "A.8.22"},
            "fair": FAIRScenarioInput(
                scenario_name="Pre-show unreleased couture archive & VIP CRM exfiltration via compromised atelier vendor",
                currency="EUR",
                tef_min=1.0, tef_mode=3.0, tef_max=8.0,
                vuln_min=0.15, vuln_mode=0.30, vuln_max=0.55,
                primary_loss_min=45000, primary_loss_mode=120000, primary_loss_max=320000,
                secondary_freq=0.45,
                secondary_loss_min=80000, secondary_loss_mode=250000, secondary_loss_max=700000,
                mitigated_vuln_factor=0.35, annual_control_cost=65000, iterations=10000, seed=4101,
            ),
            "ebios": EBIOSStudy(
                study_id="EBIOS-VALMONT-2026",
                org_id="maison-valmont",
                scope_statement="Atelier PLM design vault, VIP CRM platform, and external textile/embroidery supplier portal.",
                workshop1_values=[
                    BusinessValue(id="BV-1", name="Unreleased Haute Couture Collections", supporting_assets=["PLM Vault", "CAD Workstations"], feared_events=["Pre-launch design leak"], severity=4),
                    BusinessValue(id="BV-2", name="VIP Clientele Registry", supporting_assets=["CRM Cloud DB", "Boutique Tablets"], feared_events=["Personal data breach (GDPR Art.33)"], severity=3),
                ],
                workshop2_sources=[
                    RiskSourceObjective(id="RS-1", risk_source="Organized IP brokers", target_objective="Exfiltrate seasonal lookbooks prior to Paris Fashion Week", motivation=4, resources=3),
                    RiskSourceObjective(id="RS-2", risk_source="Opportunistic extortion group", target_objective="Ransom VIP CRM records", motivation=3, resources=3),
                ],
                workshop3_stakeholders=[
                    EcosystemStakeholder(id="ST-1", name="External Embroidery Atelier", category="supplier", dependency=3, penetration=3, cyber_maturity=1, trust=2),
                    EcosystemStakeholder(id="ST-2", name="EU Managed Cloud Host", category="cloud_host", dependency=4, penetration=3, cyber_maturity=4, trust=3),
                ],
                workshop3_strategic=[
                    StrategicScenario(id="SS-1", title="Supplier portal credential hijack into PLM design vault", risk_source_id="RS-1", stakeholder_id="ST-1", feared_event="Pre-launch design leak", initial_severity=4),
                ],
                workshop4_operational=[
                    OperationalScenario(id="OS-1", strategic_scenario_id="SS-1", title="Phishing supplier account -> reuse VPN -> bulk download PLM CAD files", kill_chain_steps=["Recon supplier contacts", "Credential phishing", "Reuse shared vendor VPN", "Bulk archive download"], likelihood=3, severity=4, linked_controls=["A.5.19", "A.8.2", "A.8.5", "A.8.12"]),
                ],
                workshop5_treatments=[
                    RiskTreatmentPlan(id="RT-1", operational_scenario_id="OS-1", decision="REDUCE", measures=["Enforce FIDO2 MFA on vendor portal", "Deploy watermarking & egress DLP on PLM", "Quarterly supplier access reviews"], residual_likelihood=1, residual_severity=3, owner="CISO Maison Valmont", target_date="2027-03-31"),
                ],
            ),
            "evidence": [
                EvidenceItem(evidence_id="EV-VAL-01", org_id="maison-valmont", control_id="A.8.5", title="IdP MFA Enforcement Export (Fictional)", evidence_type="config_export", source_ref="idp/mfa_policy_2026.json", sha256_digest=_digest("valmont-mfa"), owner="IAM Lead", review_status="APPROVED", reviewer="Internal Audit", next_review_due="2027-05-01"),
            ],
        },
        {
            "org_id": "atlaspath-lab",
            "name": "Laboratoire AtlasPath (Fictional Digital Pathology Lab)",
            "sector": "Healthcare & Digital Pathology",
            "jurisdiction": "Morocco (Law 09-08 / CNDP)",
            "laws": ["Moroccan Law 09-08", "CNDP Health-Data Prior Authorization", "ISO 15189 Quality Context"],
            "summary": "Fictional Moroccan digital pathology laboratory managing whole-slide microscopy images (WSI), LIS diagnostic workflows, and remote pathologist review.",
            "na_controls": {"A.8.30": "Diagnostic LIS software is commercial off-the-shelf; no outsourced custom software development."},
            "impl_set": {"A.5.1", "A.5.15", "A.5.31", "A.5.34", "A.7.2", "A.8.3", "A.8.13", "A.8.24"},
            "partial_set": {"A.5.14", "A.8.10", "A.8.11", "A.8.15", "A.8.22"},
            "missing_set": {"A.5.28", "A.8.8", "A.8.16"},
            "fair": FAIRScenarioInput(
                scenario_name="Unauthorized remote access & disclosure of sensitive patient pathology slides (Law 09-08)",
                currency="MAD",
                tef_min=2.0, tef_mode=5.0, tef_max=12.0,
                vuln_min=0.20, vuln_mode=0.35, vuln_max=0.60,
                primary_loss_min=180000, primary_loss_mode=420000, primary_loss_max=950000,
                secondary_freq=0.55,
                secondary_loss_min=250000, secondary_loss_mode=650000, secondary_loss_max=1800000,
                mitigated_vuln_factor=0.30, annual_control_cost=280000, iterations=10000, seed=4102,
            ),
            "ebios": EBIOSStudy(
                study_id="EBIOS-ATLASPATH-2026",
                org_id="atlaspath-lab",
                scope_statement="Whole-Slide Imaging (WSI) scanner network, LIS database, and remote tele-pathology portal.",
                workshop1_values=[
                    BusinessValue(id="BV-1", name="Patient Diagnostic Integrity & Confidentiality", supporting_assets=["LIS Database", "WSI Storage NAS", "Remote Viewer"], feared_events=["Unauthorized patient record disclosure", "Diagnostic delay from ransomware"], severity=4),
                ],
                workshop2_sources=[
                    RiskSourceObjective(id="RS-1", risk_source="Healthcare ransomware operator", target_objective="Encrypt WSI archive and coerce rapid payment", motivation=4, resources=3),
                    RiskSourceObjective(id="RS-2", risk_source="Misconfigured contractor / insider", target_objective="Bulk export un-pseudonymized slides for external training", motivation=2, resources=2),
                ],
                workshop3_stakeholders=[
                    EcosystemStakeholder(id="ST-1", name="WSI Scanner Maintenance Vendor", category="supplier", dependency=4, penetration=4, cyber_maturity=2, trust=2),
                ],
                workshop3_strategic=[
                    StrategicScenario(id="SS-1", title="Lateral movement from scanner maintenance VPN to LIS database", risk_source_id="RS-1", stakeholder_id="ST-1", feared_event="Diagnostic delay from ransomware", initial_severity=4),
                ],
                workshop4_operational=[
                    OperationalScenario(id="OS-1", strategic_scenario_id="SS-1", title="Abuse always-on vendor VPN -> flat lab LAN -> encrypt WSI shares", kill_chain_steps=["Compromise vendor workstation", "Connect persistent maintenance VPN", "Traverse unsegmented LAN", "Encrypt SMB WSI shares"], likelihood=3, severity=4, linked_controls=["A.8.22", "A.8.13", "A.8.15", "A.5.34"]),
                ],
                workshop5_treatments=[
                    RiskTreatmentPlan(id="RT-1", operational_scenario_id="OS-1", decision="REDUCE", measures=["Segment scanner VLAN from LIS DB", "Just-in-time approved vendor remote access", "Immutable 3-2-1 WSI backups & CNDP audit trails"], residual_likelihood=1, residual_severity=3, owner="Lab Director & DPO", target_date="2027-04-15"),
                ],
            ),
            "evidence": [
                EvidenceItem(evidence_id="EV-ATL-01", org_id="atlaspath-lab", control_id="A.5.34", title="CNDP Health-Data Processing Register Draft (Fictional)", evidence_type="policy", source_ref="privacy/cndp_register_v2.pdf", sha256_digest=_digest("atlas-cndp"), owner="DPO", review_status="APPROVED", reviewer="Legal Counsel", next_review_due="2027-06-01"),
            ],
        },
        {
            "org_id": "fondation-alqarawiyyin",
            "name": "Fondation Al-Qarawiyyin Numérique (Fictional Cultural Heritage Archive)",
            "sector": "Cultural Heritage & Digital Preservation",
            "jurisdiction": "Morocco / International Research Consortia",
            "laws": ["Moroccan Law 09-08 (researcher accounts)", "Cultural Heritage Preservation Charter"],
            "summary": "Fictional manuscript preservation foundation maintaining high-resolution historical scans, checksummed preservation vaults, and visiting-scholar portals.",
            "na_controls": {"A.8.12": "Public manuscript catalog is open-access; DLP applies only to administrative vault."},
            "impl_set": {"A.5.9", "A.5.33", "A.7.1", "A.7.5", "A.8.13", "A.8.14", "A.8.24"},
            "partial_set": {"A.5.24", "A.5.30", "A.8.1", "A.8.8", "A.8.15"},
            "missing_set": {"A.5.19", "A.8.16", "A.8.22"},
            "fair": FAIRScenarioInput(
                scenario_name="Ransomware & integrity corruption of digitized historical manuscript master vault",
                currency="EUR",
                tef_min=0.5, tef_mode=2.0, tef_max=5.0,
                vuln_min=0.20, vuln_mode=0.40, vuln_max=0.65,
                primary_loss_min=30000, primary_loss_mode=95000, primary_loss_max=260000,
                secondary_freq=0.30,
                secondary_loss_min=20000, secondary_loss_mode=70000, secondary_loss_max=190000,
                mitigated_vuln_factor=0.30, annual_control_cost=32000, iterations=10000, seed=4103,
            ),
            "ebios": EBIOSStudy(
                study_id="EBIOS-HERITAGE-2026",
                org_id="fondation-alqarawiyyin",
                scope_statement="Master TIFF preservation vault, IIIF researcher portal, and third-party digitization station.",
                workshop1_values=[
                    BusinessValue(id="BV-1", name="Master Digitized Manuscripts & Checksums", supporting_assets=["WORM Archive", "Preservation Catalog DB"], feared_events=["Irreversible file corruption or prolonged archival outage"], severity=4),
                ],
                workshop2_sources=[
                    RiskSourceObjective(id="RS-1", risk_source="Ransomware affiliate", target_objective="Disrupt public archive and hold storage volume hostage", motivation=3, resources=3),
                ],
                workshop3_stakeholders=[
                    EcosystemStakeholder(id="ST-1", name="External Digitization Contractor", category="contractor", dependency=3, penetration=3, cyber_maturity=2, trust=2),
                ],
                workshop3_strategic=[
                    StrategicScenario(id="SS-1", title="Infected removable media from digitization station reaches preservation share", risk_source_id="RS-1", stakeholder_id="ST-1", feared_event="Irreversible file corruption or prolonged archival outage", initial_severity=4),
                ],
                workshop4_operational=[
                    OperationalScenario(id="OS-1", strategic_scenario_id="SS-1", title="Malware on ingest workstation encrypts mounted archive before offline sync", kill_chain_steps=["Infected USB/ingest laptop", "Write access to master share", "Encrypt TIFF masters"], likelihood=2, severity=4, linked_controls=["A.7.10", "A.8.13", "A.8.22"]),
                ],
                workshop5_treatments=[
                    RiskTreatmentPlan(id="RT-1", operational_scenario_id="OS-1", decision="REDUCE", measures=["Air-gapped WORM preservation vault", "Quarantine ingest staging zone with SHA-256 verification"], residual_likelihood=1, residual_severity=2, owner="Head Archivist", target_date="2027-05-01"),
                ],
            ),
            "evidence": [
                EvidenceItem(evidence_id="EV-HER-01", org_id="fondation-alqarawiyyin", control_id="A.8.13", title="Quarterly Offline WORM Restore Drill Log (Fictional)", evidence_type="test_report", source_ref="backups/restore_drill_q4.txt", sha256_digest=_digest("heritage-restore"), owner="Archive Engineer", review_status="APPROVED", reviewer="Director", next_review_due="2027-02-28"),
            ],
        },
        {
            "org_id": "observatoire-meridien",
            "name": "Observatoire Méridien (Fictional Scientific Research Institute)",
            "sector": "Astrophysics & Scientific Computing",
            "jurisdiction": "EU / International Collaboration",
            "laws": ["EU GDPR (research staff)", "Horizon Research Data Integrity Guidelines"],
            "summary": "Fictional astronomical research institute operating telescope instrumentation networks, federated researcher identities, and open-science HPC datasets.",
            "na_controls": {"A.8.10": "Raw astronomical sky-survey telemetry is archived indefinitely as public scientific record."},
            "impl_set": {"A.5.16", "A.5.18", "A.8.4", "A.8.5", "A.8.22", "A.8.25", "A.8.28"},
            "partial_set": {"A.5.21", "A.8.8", "A.8.15", "A.8.20"},
            "missing_set": {"A.5.24", "A.5.29", "A.8.16"},
            "fair": FAIRScenarioInput(
                scenario_name="Compromise of federated researcher account causing telemetry tampering & telescope downtime",
                currency="EUR",
                tef_min=1.5, tef_mode=4.0, tef_max=10.0,
                vuln_min=0.12, vuln_mode=0.25, vuln_max=0.45,
                primary_loss_min=25000, primary_loss_mode=85000, primary_loss_max=220000,
                secondary_freq=0.25,
                secondary_loss_min=15000, secondary_loss_mode=55000, secondary_loss_max=140000,
                mitigated_vuln_factor=0.40, annual_control_cost=40000, iterations=10000, seed=4104,
            ),
            "ebios": EBIOSStudy(
                study_id="EBIOS-MERIDIEN-2026",
                org_id="observatoire-meridien",
                scope_statement="Telescope OT cooling/control subnet, federated OIDC researcher portal, and HPC data pipeline.",
                workshop1_values=[
                    BusinessValue(id="BV-1", name="Telescope Observation Continuity & Telemetry Integrity", supporting_assets=["OT Control VLAN", "HPC Ingest Pipeline"], feared_events=["Observation window loss", "Dataset integrity alteration"], severity=4),
                ],
                workshop2_sources=[
                    RiskSourceObjective(id="RS-1", risk_source="Compute-hijacking threat actor", target_objective="Abuse HPC cluster and pivot into instrument subnet", motivation=3, resources=3),
                ],
                workshop3_stakeholders=[
                    EcosystemStakeholder(id="ST-1", name="Visiting University Consortium", category="partner", dependency=3, penetration=3, cyber_maturity=2, trust=3),
                ],
                workshop3_strategic=[
                    StrategicScenario(id="SS-1", title="Stale visiting-researcher account used to deploy cryptominer and probe OT gateway", risk_source_id="RS-1", stakeholder_id="ST-1", feared_event="Observation window loss", initial_severity=3),
                ],
                workshop4_operational=[
                    OperationalScenario(id="OS-1", strategic_scenario_id="SS-1", title="Abuse expired visiting-fellow SSH key -> HPC node -> scan OT DMZ", kill_chain_steps=["Reuse stale academic key", "Escalate on shared HPC", "Scan OT Modbus gateway"], likelihood=2, severity=3, linked_controls=["A.5.16", "A.8.2", "A.8.22", "A.8.16"]),
                ],
                workshop5_treatments=[
                    RiskTreatmentPlan(id="RT-1", operational_scenario_id="OS-1", decision="REDUCE", measures=["Time-bound federated grants with automated expiry", "Zero-Trust OT gateway with Suricata monitoring"], residual_likelihood=1, residual_severity=2, owner="Observatory Security Lead", target_date="2027-04-30"),
                ],
            ),
            "evidence": [
                EvidenceItem(evidence_id="EV-MER-01", org_id="observatoire-meridien", control_id="A.8.22", title="IT/OT Firewall & Gateway Segmentation Verification (Fictional)", evidence_type="technical_log", source_ref="network/ot_segmentation_audit.json", sha256_digest=_digest("meridien-seg"), owner="OT Engineer", review_status="APPROVED", reviewer="Security Lead", next_review_due="2027-05-15"),
            ],
        },
    ]

    results: dict[str, dict[str, object]] = {}
    for s in specs:
        oid = s["org_id"]
        store.upsert_org(oid, s["name"], s["sector"], s["jurisdiction"], s["laws"], s["summary"])
        for c in annex_a:
            na_map: dict[str, str] = s["na_controls"]
            if c.control_id in na_map:
                applicable = False
                just = na_map[c.control_id]
                status = ControlStatus.NOT_ASSESSED
            else:
                applicable = True
                just = "Applicable to organizational scope."
                if c.control_id in s["impl_set"]:
                    status = ControlStatus.IMPLEMENTED
                elif c.control_id in s["partial_set"]:
                    status = ControlStatus.PARTIAL
                elif c.control_id in s["missing_set"]:
                    status = ControlStatus.NOT_IMPLEMENTED
                else:
                    status = ControlStatus.NOT_ASSESSED
            store.upsert_assessment(
                ControlAssessment(
                    assessment_id=f"ASM-{oid}-{c.control_id}",
                    org_id=oid,
                    control_id=c.control_id,
                    applicable=applicable,
                    applicability_justification=just,
                    status=status,
                    owner="Security Governance Lead",
                )
            )
        for ev in s["evidence"]:
            store.save_evidence(ev)
        store.save_ebios(s["ebios"])
        fair_res = run_fair_simulation(s["fair"])
        store.save_fair_run(f"FAIR-{oid.upper()}-01", oid, fair_res)
        results[oid] = {
            "soa": store.compute_soa_summary(oid),
            "ebios": s["ebios"].summary(),
            "fair": fair_res.model_dump(),
        }
    return results
