"""License-respecting control catalog & extensible importer for CONSERVA.

Provides:
- All 93 structural ISO/IEC 27001:2022 Annex A control identifiers (A.5.1-A.5.37, A.6.1-A.6.8,
  A.7.1-A.7.14, A.8.1-A.8.34) with concise original engineering summaries (zero verbatim ISO
  copyrighted normative text reproduced).
- Separate ISMS core clauses (Clauses 4-10) so Annex A controls are never conflated with ISMS clauses.
- Sourced public regulatory mappings: NIST CSF 2.0, Moroccan Law 09-08 / CNDP, EU GDPR, EU DORA.
- Extensible JSON/YAML importer enabling authorized users to load privately licensed control text locally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import yaml

from conserva.models import ControlDefinition

# Original concise engineering titles & objectives mapped to the 93 structural Annex A IDs.
# No copyrighted ISO/IEC normative text is copied or redistributed.
ANNEX_A_STRUCTURE: list[tuple[str, str, str, dict[str, list[str]]]] = [
    # A.5 Organizational (37 controls: A.5.1 - A.5.37)
    ("A.5.1", "Organizational", "Information security policy governance", {"NIST_CSF_2": ["GV.PO-01"], "GDPR": ["Art.24"], "LAW_0908": ["Art.23"]}),
    ("A.5.2", "Organizational", "Security roles and accountability", {"NIST_CSF_2": ["GV.RR-02"], "DORA": ["Art.5"]}),
    ("A.5.3", "Organizational", "Segregation of incompatible duties", {"NIST_CSF_2": ["PR.AA-05"], "DORA": ["Art.9"]}),
    ("A.5.4", "Organizational", "Management governance responsibilities", {"NIST_CSF_2": ["GV.RR-01"]}),
    ("A.5.5", "Organizational", "Authority and regulator liaison", {"NIST_CSF_2": ["RS.CO-02"], "LAW_0908": ["Art.12"], "GDPR": ["Art.33"]}),
    ("A.5.6", "Organizational", "Specialist threat and community groups", {"NIST_CSF_2": ["ID.RA-02"]}),
    ("A.5.7", "Organizational", "Threat intelligence ingestion and analysis", {"NIST_CSF_2": ["ID.RA-02"], "DORA": ["Art.45"]}),
    ("A.5.8", "Organizational", "Security integration in project delivery", {"NIST_CSF_2": ["GV.OC-04"]}),
    ("A.5.9", "Organizational", "Inventory of information and supporting assets", {"NIST_CSF_2": ["ID.AM-01"], "DORA": ["Art.8"]}),
    ("A.5.10", "Organizational", "Acceptable use rules for organizational assets", {"NIST_CSF_2": ["GV.PO-01"]}),
    ("A.5.11", "Organizational", "Return of equipment and credentials on departure", {"NIST_CSF_2": ["ID.AM-08"]}),
    ("A.5.12", "Organizational", "Information sensitivity classification", {"NIST_CSF_2": ["ID.AM-05"], "LAW_0908": ["Art.1"], "GDPR": ["Art.9"]}),
    ("A.5.13", "Organizational", "Data labeling and handling markers", {"NIST_CSF_2": ["PR.DS-01"]}),
    ("A.5.14", "Organizational", "Secure information transfer controls", {"NIST_CSF_2": ["PR.DS-02"], "LAW_0908": ["Art.43"], "GDPR": ["Art.44"]}),
    ("A.5.15", "Organizational", "Logical and physical access control rules", {"NIST_CSF_2": ["PR.AA-05"], "LAW_0908": ["Art.23"], "GDPR": ["Art.32"]}),
    ("A.5.16", "Organizational", "Identity lifecycle governance (joiner/mover/leaver)", {"NIST_CSF_2": ["PR.AA-01"]}),
    ("A.5.17", "Organizational", "Authentication credential and secret management", {"NIST_CSF_2": ["PR.AA-02"]}),
    ("A.5.18", "Organizational", "Access rights provisioning and periodic review", {"NIST_CSF_2": ["PR.AA-05"], "DORA": ["Art.9"]}),
    ("A.5.19", "Organizational", "Supplier cybersecurity risk governance", {"NIST_CSF_2": ["GV.SC-01"], "DORA": ["Art.28"]}),
    ("A.5.20", "Organizational", "Security clauses in supplier agreements", {"NIST_CSF_2": ["GV.SC-05"], "GDPR": ["Art.28"], "LAW_0908": ["Art.24"]}),
    ("A.5.21", "Organizational", "ICT supply-chain dependency risk controls", {"NIST_CSF_2": ["GV.SC-07"], "DORA": ["Art.28"]}),
    ("A.5.22", "Organizational", "Ongoing monitoring of supplier service changes", {"NIST_CSF_2": ["GV.SC-09"], "DORA": ["Art.29"]}),
    ("A.5.23", "Organizational", "Cloud service acquisition, use, and exit security", {"NIST_CSF_2": ["GV.SC-10"], "DORA": ["Art.28"]}),
    ("A.5.24", "Organizational", "Incident management preparation and playbooks", {"NIST_CSF_2": ["RS.MA-01"], "DORA": ["Art.17"]}),
    ("A.5.25", "Organizational", "Security event triage and classification", {"NIST_CSF_2": ["DE.AE-06"], "DORA": ["Art.18"]}),
    ("A.5.26", "Organizational", "Incident containment and response execution", {"NIST_CSF_2": ["RS.MI-01"]}),
    ("A.5.27", "Organizational", "Post-incident lessons learned and control updates", {"NIST_CSF_2": ["ID.IM-03"]}),
    ("A.5.28", "Organizational", "Forensic evidence preservation and integrity", {"NIST_CSF_2": ["RS.AN-08"]}),
    ("A.5.29", "Organizational", "Information security during operational disruption", {"NIST_CSF_2": ["PR.IR-04"], "DORA": ["Art.11"]}),
    ("A.5.30", "Organizational", "ICT readiness for business continuity and RTO/RPO", {"NIST_CSF_2": ["RC.RP-01"], "DORA": ["Art.11"]}),
    ("A.5.31", "Organizational", "Identification of legal, statutory, and contractual duties", {"NIST_CSF_2": ["GV.OC-03"], "LAW_0908": ["Art.12"], "GDPR": ["Art.6"]}),
    ("A.5.32", "Organizational", "Intellectual property and licensing protection", {"NIST_CSF_2": ["GV.OC-03"]}),
    ("A.5.33", "Organizational", "Protection and retention of statutory records", {"NIST_CSF_2": ["PR.DS-10"], "LAW_0908": ["Art.3"]}),
    ("A.5.34", "Organizational", "Privacy and personal data protection compliance", {"NIST_CSF_2": ["GV.OC-03"], "LAW_0908": ["Art.1-24"], "GDPR": ["Art.5-35"]}),
    ("A.5.35", "Organizational", "Independent review of security posture", {"NIST_CSF_2": ["ID.IM-02"], "DORA": ["Art.24"]}),
    ("A.5.36", "Organizational", "Compliance verification with internal security standards", {"NIST_CSF_2": ["GV.OV-03"]}),
    ("A.5.37", "Organizational", "Documented operating and maintenance procedures", {"NIST_CSF_2": ["PR.PS-01"]}),
    # A.6 People (8 controls: A.6.1 - A.6.8)
    ("A.6.1", "People", "Pre-employment background verification", {"NIST_CSF_2": ["GV.RR-04"]}),
    ("A.6.2", "People", "Contractual security terms of employment", {"NIST_CSF_2": ["GV.RR-04"]}),
    ("A.6.3", "People", "Security awareness, role-based education, and training", {"NIST_CSF_2": ["PR.AT-01"], "DORA": ["Art.13"]}),
    ("A.6.4", "People", "Disciplinary process for security policy breaches", {"NIST_CSF_2": ["GV.RR-02"]}),
    ("A.6.5", "People", "Post-termination and role-change obligations", {"NIST_CSF_2": ["PR.AA-01"]}),
    ("A.6.6", "People", "Confidentiality and non-disclosure agreements", {"NIST_CSF_2": ["GV.OC-03"]}),
    ("A.6.7", "People", "Remote and hybrid working endpoint safeguards", {"NIST_CSF_2": ["PR.AA-03"]}),
    ("A.6.8", "People", "Timely internal reporting of security events", {"NIST_CSF_2": ["DE.AE-06"]}),
    # A.7 Physical (14 controls: A.7.1 - A.7.14)
    ("A.7.1", "Physical", "Physical security perimeters for sensitive sites", {"NIST_CSF_2": ["PR.AA-06"]}),
    ("A.7.2", "Physical", "Physical entry badge and visitor logging controls", {"NIST_CSF_2": ["PR.AA-06"]}),
    ("A.7.3", "Physical", "Securing offices, laboratories, and server rooms", {"NIST_CSF_2": ["PR.AA-06"]}),
    ("A.7.4", "Physical", "Continuous physical security monitoring", {"NIST_CSF_2": ["DE.CM-02"]}),
    ("A.7.5", "Physical", "Protection against environmental and physical hazards", {"NIST_CSF_2": ["PR.IR-02"]}),
    ("A.7.6", "Physical", "Operating procedures inside restricted zones", {"NIST_CSF_2": ["PR.AA-06"]}),
    ("A.7.7", "Physical", "Clear desk and automatic screen-lock discipline", {"NIST_CSF_2": ["PR.DS-01"]}),
    ("A.7.8", "Physical", "Equipment siting and physical exposure protection", {"NIST_CSF_2": ["PR.IR-02"]}),
    ("A.7.9", "Physical", "Protection of off-premises portable assets", {"NIST_CSF_2": ["PR.DS-01"]}),
    ("A.7.10", "Physical", "Removable storage media lifecycle controls", {"NIST_CSF_2": ["PR.DS-01"]}),
    ("A.7.11", "Physical", "Supporting power, cooling, and utility redundancy", {"NIST_CSF_2": ["PR.IR-02"]}),
    ("A.7.12", "Physical", "Physical protection of power and network cabling", {"NIST_CSF_2": ["PR.IR-02"]}),
    ("A.7.13", "Physical", "Scheduled preventive hardware maintenance", {"NIST_CSF_2": ["PR.PS-02"]}),
    ("A.7.14", "Physical", "Verified sanitization prior to asset disposal or reuse", {"NIST_CSF_2": ["PR.DS-10"], "LAW_0908": ["Art.23"]}),
    # A.8 Technological (34 controls: A.8.1 - A.8.34)
    ("A.8.1", "Technological", "User endpoint device hardening and encryption", {"NIST_CSF_2": ["PR.PS-01"]}),
    ("A.8.2", "Technological", "Privileged access management and approval", {"NIST_CSF_2": ["PR.AA-05"], "DORA": ["Art.9"]}),
    ("A.8.3", "Technological", "Application and dataset access restriction", {"NIST_CSF_2": ["PR.AA-05"], "GDPR": ["Art.32"]}),
    ("A.8.4", "Technological", "Controlled access to source code and build tools", {"NIST_CSF_2": ["PR.PS-06"]}),
    ("A.8.5", "Technological", "Strong authentication and MFA enforcement", {"NIST_CSF_2": ["PR.AA-03"], "DORA": ["Art.9"]}),
    ("A.8.6", "Technological", "Capacity monitoring and resource headroom planning", {"NIST_CSF_2": ["PR.IR-04"]}),
    ("A.8.7", "Technological", "Malware defense and execution controls", {"NIST_CSF_2": ["DE.CM-09"]}),
    ("A.8.8", "Technological", "Technical vulnerability discovery and patching", {"NIST_CSF_2": ["ID.RA-01"], "DORA": ["Art.25"]}),
    ("A.8.9", "Technological", "Hardened configuration baselines and drift detection", {"NIST_CSF_2": ["PR.PS-01"]}),
    ("A.8.10", "Technological", "Scheduled deletion of expired personal and operational data", {"NIST_CSF_2": ["PR.DS-10"], "GDPR": ["Art.17"], "LAW_0908": ["Art.3"]}),
    ("A.8.11", "Technological", "Data masking, anonymization, and pseudonymization", {"NIST_CSF_2": ["PR.DS-01"], "GDPR": ["Art.25"], "LAW_0908": ["Art.23"]}),
    ("A.8.12", "Technological", "Data leakage prevention on egress channels", {"NIST_CSF_2": ["PR.DS-02"]}),
    ("A.8.13", "Technological", "Immutable offline backups and restore testing", {"NIST_CSF_2": ["PR.DS-11"], "DORA": ["Art.12"]}),
    ("A.8.14", "Technological", "Redundancy of critical processing infrastructure", {"NIST_CSF_2": ["PR.IR-04"]}),
    ("A.8.15", "Technological", "Tamper-evident security event logging and retention", {"NIST_CSF_2": ["PR.PS-04"], "LAW_0908": ["Art.23"], "DORA": ["Art.10"]}),
    ("A.8.16", "Technological", "Continuous anomaly detection and SIEM monitoring", {"NIST_CSF_2": ["DE.CM-01"], "DORA": ["Art.10"]}),
    ("A.8.17", "Technological", "Synchronized trusted time sources across logs", {"NIST_CSF_2": ["PR.PS-04"]}),
    ("A.8.18", "Technological", "Restricted control over privileged utility programs", {"NIST_CSF_2": ["PR.AA-05"]}),
    ("A.8.19", "Technological", "Controlled software installation on operational hosts", {"NIST_CSF_2": ["PR.PS-02"]}),
    ("A.8.20", "Technological", "Network perimeter and internal traffic controls", {"NIST_CSF_2": ["PR.IR-01"]}),
    ("A.8.21", "Technological", "Security requirements for network transport services", {"NIST_CSF_2": ["PR.IR-01"]}),
    ("A.8.22", "Technological", "Network zone segmentation and micro-isolation", {"NIST_CSF_2": ["PR.IR-01"]}),
    ("A.8.23", "Technological", "Egress web filtering against malicious destinations", {"NIST_CSF_2": ["PR.IR-01"]}),
    ("A.8.24", "Technological", "Cryptographic policy, TLS, and key lifecycle management", {"NIST_CSF_2": ["PR.DS-02"], "GDPR": ["Art.32"]}),
    ("A.8.25", "Technological", "Secure software development lifecycle (SDLC)", {"NIST_CSF_2": ["PR.PS-06"]}),
    ("A.8.26", "Technological", "Application security validation and threat modeling", {"NIST_CSF_2": ["PR.PS-06"]}),
    ("A.8.27", "Technological", "Secure systems architecture and Zero-Trust principles", {"NIST_CSF_2": ["PR.IR-01"]}),
    ("A.8.28", "Technological", "Secure coding standards and automated SAST gates", {"NIST_CSF_2": ["PR.PS-06"]}),
    ("A.8.29", "Technological", "Security acceptance testing before release", {"NIST_CSF_2": ["ID.RA-01"], "DORA": ["Art.25"]}),
    ("A.8.30", "Technological", "Governance of outsourced software development", {"NIST_CSF_2": ["GV.SC-06"]}),
    ("A.8.31", "Technological", "Separation of development, staging, and production", {"NIST_CSF_2": ["PR.PS-01"]}),
    ("A.8.32", "Technological", "Formal change management and rollback approvals", {"NIST_CSF_2": ["PR.PS-02"], "DORA": ["Art.9"]}),
    ("A.8.33", "Technological", "Sanitized synthetic test data protection", {"NIST_CSF_2": ["PR.DS-01"], "GDPR": ["Art.5"]}),
    ("A.8.34", "Technological", "Minimizing operational disruption during technical audits", {"NIST_CSF_2": ["ID.IM-02"]}),
]

ISMS_CLAUSES: list[tuple[str, str, str]] = [
    ("Clause 4", "ISMS Core", "Organizational context, interested parties, and ISMS scope definition"),
    ("Clause 5", "ISMS Core", "Leadership commitment, policy ownership, and accountability"),
    ("Clause 6", "ISMS Core", "Risk assessment methodology, risk treatment planning, and measurable objectives"),
    ("Clause 7", "ISMS Core", "Competence, resources, awareness, communication, and documented evidence control"),
    ("Clause 8", "ISMS Core", "Operational execution of risk assessments and treatment plans"),
    ("Clause 9", "ISMS Core", "Performance metrics, internal audits, and management review"),
    ("Clause 10", "ISMS Core", "Nonconformity remediation and continual improvement"),
]


def load_builtin_controls() -> list[ControlDefinition]:
    controls: list[ControlDefinition] = []
    for cid, domain, title, maps in ANNEX_A_STRUCTURE:
        controls.append(
            ControlDefinition(
                control_id=cid,
                framework="ISO/IEC 27001:2022 Structural Index",
                framework_version="2022 (structural reference; no copyrighted normative text)",
                domain=domain,
                title=title,
                objective=f"Verify and evidence '{title.lower()}' within organizational scope.",
                obligation_type="certification_reference",
                public_mappings=maps,
            )
        )
    for cid, domain, title in ISMS_CLAUSES:
        controls.append(
            ControlDefinition(
                control_id=cid,
                framework="ISO/IEC 27001:2022 ISMS Clauses",
                framework_version="2022 (structural reference)",
                domain=domain,
                title=title,
                objective=f"Maintain management-system governance for {title.lower()}.",
                obligation_type="certification_reference",
                public_mappings={"NIST_CSF_2": ["GV.OV-01"]},
            )
        )
    return controls


def import_custom_controls(file_path: str | Path) -> list[ControlDefinition]:
    """Import organization-owned or privately licensed controls from local JSON or YAML."""
    p = Path(file_path)
    raw = p.read_text(encoding="utf-8")
    data: Any = yaml.safe_load(raw) if p.suffix.lower() in {".yml", ".yaml"} else json.loads(raw)
    items = data if isinstance(data, list) else data.get("controls", [])
    return [ControlDefinition(**item) for item in items]
