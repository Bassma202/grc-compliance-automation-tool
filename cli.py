#!/usr/bin/env python3
"""
GRC Executive Audit CLI Tool
Author: Bassma Alaoui Sossey
"""

import argparse
import json
from src.grc_engine import GRCEngine

def generate_markdown_report(iso_res, law_res, client_name="DataPathology Pathology Lab"):
    md = f"""# Executive Cybersecurity & Data Protection Audit Report
**Target Entity:** {client_name}  
**Lead Auditor:** Bassma Alaoui Sossey (UEMF Cybersecurity Engineering)  
**Date:** 2026-11-24  

---

## 1. Compliance Scorecard

| Regulatory / Standard Framework | Compliance Score | Status | Identified Gaps |
| :--- | :--- | :--- | :--- |
| **ISO/IEC 27001:2022 (Annex A)** | **{iso_res['compliance_score_percent']}%** | {'✅ Satisfactory' if iso_res['compliance_score_percent'] >= 80 else '⚠️ Action Required'} | {iso_res['identified_gaps_count']} Non-conformities |
| **Moroccan Law 09-08 (CNDP)** | **{law_res['compliance_score_percent']}%** | {'✅ Compliant' if law_res['compliance_score_percent'] >= 90 else '🚨 Legal Exposure'} | {len(law_res['violations'])} Regulatory Gaps |

---

## 2. High-Priority ISO 27001 Gaps & Action Plan

"""
    for gap in iso_res["gaps"]:
        md += f"* **[{gap['priority']}] {gap['control_id']} — {gap['title']}**\n"
        md += f"  * *Current Status:* `{gap['status']}`\n"
        md += f"  * *Recommendation:* {gap['recommendation']}\n\n"

    md += """---

## 3. Moroccan Law 09-08 (CNDP) Sensitive Data Review

"""
    for viol in law_res["violations"]:
        md += f"* **[{viol['criticality']}] {viol['article_id']} — {viol['topic']}**\n"
        md += f"  * *Requirement:* {viol['description']}\n"
        md += f"  * *Risk:* {viol['legal_exposure']}\n\n"

    md += """---
*Report automatically compiled via GRC Compliance Automation Engine.*
"""
    return md

def main():
    parser = argparse.ArgumentParser(description="GRC Compliance Audit CLI")
    parser.add_argument("--client", default="Digital Pathology Lab", help="Client name")
    parser.add_argument("--export-md", help="Export executive Markdown report to file")
    args = parser.parse_args()

    engine = GRCEngine()

    # Representative audit assessment for a digital pathology workflow (reflecting DataPathology experience)
    iso_sample_responses = {
        "A.5.1": "IMPLEMENTED",
        "A.5.15": "PARTIAL",       # Access control partial (needs MFA rollout)
        "A.5.24": "IMPLEMENTED",
        "A.8.1": "IMPLEMENTED",
        "A.8.7": "IMPLEMENTED",
        "A.8.9": "PARTIAL",
        "A.8.12": "NOT_IMPLEMENTED", # Data leakage prevention missing
        "A.8.15": "IMPLEMENTED",     # Logging enabled
        "A.8.20": "IMPLEMENTED",
        "A.8.24": "PARTIAL"          # Cryptography partial
    }

    law_sample_responses = {
        "ART-03": "COMPLIANT",
        "ART-12": "COMPLIANT",     # Strict medical consent verified
        "ART-23": "COMPLIANT",     # Technical security safeguards active
        "ART-24": "COMPLIANT",     # Audit trails in place
        "ART-43": "NON_COMPLIANT"  # Cloud backup in foreign datacenter requires CNDP authorization
    }

    iso_res = engine.evaluate_iso27001(iso_sample_responses)
    law_res = engine.evaluate_law0908(law_sample_responses)

    report_md = generate_markdown_report(iso_res, law_res, args.client)

    print("\n" + "=" * 65)
    print(f"  EXECUTIVE AUDIT SUMMARY FOR: {args.client}")
    print("=" * 65)
    print(f"  ISO/IEC 27001:2022 Score : {iso_res['compliance_score_percent']}%")
    print(f"  Moroccan Law 09-08 Score : {law_res['compliance_score_percent']}%")
    print(f"  Total Gaps Identified    : {iso_res['identified_gaps_count']} ISO / {len(law_res['violations'])} Law 09-08")
    print("=" * 65 + "\n")

    if args.export_md:
        with open(args.export_md, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"[✓] Executive report successfully saved to: {args.export_md}")

if __name__ == "__main__":
    main()
