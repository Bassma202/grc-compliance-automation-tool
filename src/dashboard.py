"""
GRC Compliance & Risk Dashboard Server
Author: Bassma Alaoui Sossey
Lightweight web dashboard rendering compliance scores, radar benchmarks, and risk matrices.
"""

import http.server
import socketserver
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.grc_engine import GRCEngine
from src.fair_engine import FAIRRiskCalculator

def build_dashboard_html():
    engine = GRCEngine()
    fair = FAIRRiskCalculator(currency="MAD")
    
    # Audit state
    iso_res = engine.evaluate_iso27001({
        "A.5.1": "IMPLEMENTED", "A.5.15": "PARTIAL", "A.5.24": "IMPLEMENTED",
        "A.8.1": "IMPLEMENTED", "A.8.7": "IMPLEMENTED", "A.8.12": "NOT_IMPLEMENTED",
        "A.8.15": "IMPLEMENTED", "A.8.20": "IMPLEMENTED"
    })
    law_res = engine.evaluate_law0908({
        "ART-03": "COMPLIANT", "ART-12": "COMPLIANT", "ART-23": "COMPLIANT",
        "ART-24": "COMPLIANT", "ART-43": "NON_COMPLIANT"
    })
    fair_res = fair.calculate_ale(0.7, 5.0, 0.25, 120000.0, 250000.0)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Enterprise GRC & Cyber Risk Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }}
        .title {{ font-size: 24px; font-weight: bold; color: #38bdf8; }}
        .subtitle {{ font-size: 14px; color: #94a3b8; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 20px; border: 1px solid #334155; }}
        .metric {{ font-size: 36px; font-weight: bold; margin: 10px 0; }}
        .metric.good {{ color: #4ade80; }}
        .metric.warning {{ color: #fbbf24; }}
        .metric.danger {{ color: #f87171; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
        .badge.high {{ background: #7f1d1d; color: #fca5a5; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        .table th, .table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #334155; }}
        .table th {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">Enterprise GRC & Regulatory Compliance Dashboard</div>
            <div class="subtitle">Audited Entity: Digital Pathology Laboratory | Lead Auditor: Bassma Alaoui Sossey (UEMF)</div>
        </div>
        <div>
            <span class="badge" style="background: #0369a1; color: #e0f2fe;">ISO 27001:2022</span>
            <span class="badge" style="background: #831843; color: #fce7f3;">Morocco Law 09-08</span>
            <span class="badge" style="background: #14532d; color: #dcfce7;">FAIR Quantitative</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>ISO/IEC 27001:2022 Maturity</h3>
            <div class="metric warning">{iso_res['compliance_score_percent']}%</div>
            <p style="color: #94a3b8;">Controls Audited: {iso_res['total_controls_audited']} | Non-conformities: {iso_res['identified_gaps_count']}</p>
        </div>

        <div class="card">
            <h3>Moroccan Law 09-08 / CNDP</h3>
            <div class="metric warning">{law_res['compliance_score_percent']}%</div>
            <p style="color: #94a3b8;">Compliant Articles: {law_res['compliant_articles']} / {law_res['total_articles']} | Violations: {len(law_res['violations'])}</p>
        </div>

        <div class="card">
            <h3>FAIR Annualized Loss Expectancy</h3>
            <div class="metric danger">{fair_res['annualized_loss_expectancy_ale']:,.2f} MAD</div>
            <p style="color: #94a3b8;">Loss Event Freq: {fair_res['loss_event_frequency_per_year']}/yr | Single Loss: {fair_res['single_loss_expectancy']:,.0f} MAD</p>
        </div>
    </div>

    <div class="grid" style="margin-top: 20px;">
        <div class="card">
            <h3>Identified Regulatory & Compliance Gaps</h3>
            <table class="table">
                <thead>
                    <tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th></tr>
                </thead>
                <tbody>
                    <tr><td>A.8.12</td><td>Data Leakage Prevention</td><td>NOT_IMPLEMENTED</td><td><span class="badge high">HIGH</span></td></tr>
                    <tr><td>A.5.15</td><td>Access Control (MFA)</td><td>PARTIAL</td><td><span class="badge high">HIGH</span></td></tr>
                    <tr><td>ART-43</td><td>Cross-Border Transfer</td><td>NON_COMPLIANT</td><td><span class="badge high">CRITICAL</span></td></tr>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
    return html

def export_dashboard_html(output_path="reports/compliance_dashboard.html"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(build_dashboard_html())
    print(f"[✓] Interactive GRC Dashboard exported to: {output_path}")

if __name__ == "__main__":
    export_dashboard_html()
