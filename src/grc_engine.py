"""
GRC Assessment & Compliance Scoring Engine
Author: Bassma Alaoui Sossey
Supports ISO/IEC 27001:2022, Moroccan Law 09-08 (CNDP), and EBIOS RM Risk Matrices.
"""

import json
import os
from typing import Dict, List, Any

class GRCEngine:
    def __init__(self, frameworks_dir: str = None):
        if not frameworks_dir:
            frameworks_dir = os.path.join(os.path.dirname(__file__), "..", "frameworks")
        self.frameworks_dir = frameworks_dir
        self.iso_data = self._load_json("iso27001_2022.json")
        self.law0908_data = self._load_json("moroccan_law_0908_cndp.json")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.frameworks_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def evaluate_iso27001(self, audit_responses: Dict[str, str]) -> Dict[str, Any]:
        """
        audit_responses: dict of {control_id: 'IMPLEMENTED' | 'PARTIAL' | 'NOT_IMPLEMENTED' | 'N/A'}
        """
        total_weight = 0
        earned_weight = 0
        gaps = []
        
        status_multiplier = {
            "IMPLEMENTED": 1.0,
            "PARTIAL": 0.5,
            "NOT_IMPLEMENTED": 0.0,
            "N/A": None
        }

        for category in self.iso_data.get("categories", []):
            for control in category.get("controls", []):
                cid = control["id"]
                weight = control.get("weight", 3)
                status = audit_responses.get(cid, "NOT_IMPLEMENTED").upper()
                
                mult = status_multiplier.get(status, 0.0)
                if mult is not None:
                    total_weight += weight
                    earned_weight += (weight * mult)
                    if mult < 1.0:
                        gaps.append({
                            "control_id": cid,
                            "title": control["title"],
                            "status": status,
                            "priority": "HIGH" if weight >= 5 else "MEDIUM",
                            "recommendation": f"Implement documented procedures and technical controls for {control['title']}."
                        })

        score_pct = round((earned_weight / total_weight) * 100, 1) if total_weight > 0 else 0.0
        return {
            "framework": "ISO/IEC 27001:2022",
            "compliance_score_percent": score_pct,
            "total_controls_audited": len(audit_responses),
            "identified_gaps_count": len(gaps),
            "gaps": sorted(gaps, key=lambda x: 0 if x["priority"] == "HIGH" else 1)
        }

    def evaluate_law0908(self, audit_responses: Dict[str, str]) -> Dict[str, Any]:
        """
        Evaluates adherence to Moroccan Data Protection Law 09-08 and CNDP guidelines.
        """
        critical_violations = []
        compliant_count = 0
        total_articles = len(self.law0908_data.get("articles", []))

        for article in self.law0908_data.get("articles", []):
            aid = article["id"]
            status = audit_responses.get(aid, "NON_COMPLIANT").upper()
            
            if status == "COMPLIANT":
                compliant_count += 1
            else:
                critical_violations.append({
                    "article_id": aid,
                    "topic": article["topic"],
                    "criticality": article["criticality"],
                    "description": article["description"],
                    "legal_exposure": "Subject to CNDP formal notice or administrative sanctions under Chapter VII of Law 09-08."
                })

        compliance_pct = round((compliant_count / total_articles) * 100, 1) if total_articles > 0 else 0.0
        return {
            "framework": "Loi Marocaine 09-08 & CNDP",
            "compliance_score_percent": compliance_pct,
            "compliant_articles": compliant_count,
            "total_articles": total_articles,
            "violations": critical_violations
        }

    def calculate_ebios_risk(self, gravity: int, likelihood: int) -> Dict[str, Any]:
        """
        EBIOS RM Matrix: Gravity (1 to 4) x Likelihood (1 to 4) = Score (1 to 16)
        """
        g = max(1, min(4, gravity))
        l = max(1, min(4, likelihood))
        score = g * l
        
        if score >= 12:
            tier = "CRITICAL / UNACCEPTABLE"
            action = "Immediate remediation required; executive escalation and active compensating safeguards."
        elif score >= 8:
            tier = "HIGH"
            action = "Formal risk mitigation plan with deadline under 30 days."
        elif score >= 4:
            tier = "MEDIUM"
            action = "Remediation scheduled in next standard maintenance window."
        else:
            tier = "LOW / ACCEPTABLE"
            action = "Risk acceptance by asset owner; routine annual review."

        return {
            "gravity": g,
            "likelihood": l,
            "risk_score": score,
            "risk_tier": tier,
            "treatment_strategy": action
        }
