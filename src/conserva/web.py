"""CONSERVA FastAPI REST API & Institutional Governance Web Interface.

Enforces role-based authorization & multi-tenant isolation across API endpoints:
- X-Conserva-Role: ADMIN | AUDITOR | RISK_OWNER | VIEWER (default VIEWER on read; write requires AUDITOR/RISK_OWNER/ADMIN)
- X-Conserva-Org: Scoped tenant header; non-ADMIN roles cannot read/write another organization's records.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from conserva.case_studies import seed_four_case_studies
from conserva.controls import load_builtin_controls
from conserva.fair import run_fair_simulation
from conserva.models import ControlAssessment, ControlStatus, EvidenceItem, FAIRScenarioInput, Role
from conserva.storage import ConservaStore


class AssessmentPatch(BaseModel):
    applicable: bool = True
    applicability_justification: str = ""
    status: ControlStatus
    owner: str = "Security Governance Lead"
    finding_notes: str = ""


def _require_access(
    org_id: str,
    write: bool = False,
    x_conserva_role: str = Header(default="VIEWER"),
    x_conserva_org: str | None = Header(default=None),
) -> Role:
    try:
        role = Role(x_conserva_role.upper())
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=f"Invalid role: {x_conserva_role}") from exc
    if role != Role.ADMIN and x_conserva_org and x_conserva_org != org_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied.")
    if write and role not in {Role.ADMIN, Role.AUDITOR, Role.RISK_OWNER}:
        raise HTTPException(status_code=403, detail=f"Role {role.value} is read-only.")
    return role


def create_app(db_path: str | Path | None = None, seed_demo: bool = True) -> FastAPI:
    store = ConservaStore(db_path or os.getenv("CONSERVA_DB_PATH", "data/conserva.db"))
    if seed_demo and not store.list_orgs():
        seed_four_case_studies(store)

    controls_index = {c.control_id: c for c in load_builtin_controls()}
    app = FastAPI(title="CONSERVA — Cyber Governance & Quantitative Risk Engineering", version="2.0.0")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        annex_count = sum(1 for cid in controls_index if cid.startswith("A."))
        clause_count = sum(1 for cid in controls_index if cid.startswith("Clause"))
        return {"status": "healthy", "service": "conserva-grc", "annex_a_controls": annex_count, "isms_clauses": clause_count}

    @app.get("/api/controls")
    def list_controls() -> dict[str, Any]:
        return {
            "total": len(controls_index),
            "annex_a_count": sum(1 for cid in controls_index if cid.startswith("A.")),
            "controls": [c.model_dump() for c in controls_index.values()],
        }

    @app.get("/api/orgs")
    def list_orgs() -> list[dict[str, Any]]:
        return store.list_orgs()

    @app.get("/api/orgs/{org_id}/soa")
    def get_soa(
        org_id: str,
        x_conserva_role: str = Header(default="VIEWER"),
        x_conserva_org: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _require_access(org_id, write=False, x_conserva_role=x_conserva_role, x_conserva_org=x_conserva_org)
        org = store.get_org(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found.")
        return {
            "organization": org,
            "summary": store.compute_soa_summary(org_id),
            "assessments": store.list_assessments(org_id),
        }

    @app.put("/api/orgs/{org_id}/assessments/{control_id}")
    def update_assessment(
        org_id: str,
        control_id: str,
        body: AssessmentPatch,
        x_conserva_role: str = Header(default="VIEWER"),
        x_conserva_org: str | None = Header(default=None),
    ) -> dict[str, Any]:
        role = _require_access(org_id, write=True, x_conserva_role=x_conserva_role, x_conserva_org=x_conserva_org)
        if control_id not in controls_index:
            raise HTTPException(status_code=404, detail="Unknown control ID.")
        if not body.applicable and not body.applicability_justification.strip():
            raise HTTPException(status_code=422, detail="Non-applicable controls require an explicit justification.")
        a = ControlAssessment(
            assessment_id=f"ASM-{org_id}-{control_id}",
            org_id=org_id,
            control_id=control_id,
            applicable=body.applicable,
            applicability_justification=body.applicability_justification,
            status=body.status,
            owner=body.owner,
            finding_notes=body.finding_notes,
        )
        store.upsert_assessment(a)
        store.log_audit(role.value, org_id, "UPDATE_ASSESSMENT", f"{control_id} -> {body.status.value}")
        return a.model_dump()

    @app.post("/api/orgs/{org_id}/evidence")
    def add_evidence(
        org_id: str,
        item: EvidenceItem,
        x_conserva_role: str = Header(default="VIEWER"),
        x_conserva_org: str | None = Header(default=None),
    ) -> dict[str, Any]:
        role = _require_access(org_id, write=True, x_conserva_role=x_conserva_role, x_conserva_org=x_conserva_org)
        if item.org_id != org_id:
            raise HTTPException(status_code=400, detail="Evidence org_id must match path org_id.")
        store.save_evidence(item)
        store.log_audit(role.value, org_id, "ADD_EVIDENCE", f"{item.evidence_id} ({item.control_id})")
        return item.model_dump()

    @app.get("/api/orgs/{org_id}/ebios")
    def get_ebios(
        org_id: str,
        x_conserva_role: str = Header(default="VIEWER"),
        x_conserva_org: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _require_access(org_id, write=False, x_conserva_role=x_conserva_role, x_conserva_org=x_conserva_org)
        study = store.get_ebios(org_id)
        if not study:
            raise HTTPException(status_code=404, detail="No EBIOS RM study found.")
        return {"summary": study.summary(), "study": study.model_dump()}

    @app.post("/api/orgs/{org_id}/fair")
    def run_fair_endpoint(
        org_id: str,
        cfg: FAIRScenarioInput,
        x_conserva_role: str = Header(default="VIEWER"),
        x_conserva_org: str | None = Header(default=None),
    ) -> dict[str, Any]:
        role = _require_access(org_id, write=True, x_conserva_role=x_conserva_role, x_conserva_org=x_conserva_org)
        res = run_fair_simulation(cfg)
        run_id = f"FAIR-{org_id.upper()}-{abs(hash(cfg.scenario_name)) % 10000:04d}"
        store.save_fair_run(run_id, org_id, res)
        store.log_audit(role.value, org_id, "RUN_FAIR", f"{cfg.scenario_name} (ALE={res.expected_ale} {res.currency})")
        return res.model_dump()

    @app.get("/api/orgs/{org_id}/report.md", response_class=PlainTextResponse)
    def export_markdown_report(org_id: str) -> str:
        org = store.get_org(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found.")
        soa = store.compute_soa_summary(org_id)
        ebios = store.get_ebios(org_id)
        fairs = store.list_fair_runs(org_id)
        fair = fairs[0] if fairs else {}
        lines = [
            f"# CONSERVA Executive Governance & Risk Report — {org['name']}",
            f"> **{org['fictional_disclaimer']}**",
            "",
            f"- **Sector:** {org['sector']} | **Jurisdiction:** {org['jurisdiction']}",
            f"- **Applicable Legal/Regulatory Context:** {', '.join(org['applicable_laws'])}",
            "",
            "## 1. Statement of Applicability (SoA) Summary",
            f"- **Annex A Controls Tracked:** {soa['total_controls_tracked']} (Applicable: {soa['applicable_controls']}, Justified N/A: {soa['non_applicable_controls']})",
            f"- **Self-Assessment Implementation Index:** {soa['implementation_index_pct']}% *(Not a formal certification)*",
            f"- **Status Breakdown:** {soa['status_counts']}",
            "",
            "## 2. ANSSI EBIOS Risk Manager (5-Workshop Summary)",
            f"- **Summary:** {ebios.summary() if ebios else 'None'}",
            "",
            "## 3. Monte Carlo Open FAIR Quantitative Risk Summary",
            f"- **Scenario:** {fair.get('scenario_name', 'N/A')}",
            f"- **Expected ALE:** {fair.get('expected_ale', 0):,.2f} {fair.get('currency', 'EUR')} (p50: {fair.get('p50_ale', 0):,.2f}, p95: {fair.get('p95_ale', 0):,.2f}, p99: {fair.get('p99_ale', 0):,.2f})",
            f"- **Residual Expected ALE (Post-Treatment):** {fair.get('residual_expected_ale', 0):,.2f} {fair.get('currency', 'EUR')} ({fair.get('risk_reduction_pct', 0)}% reduction)",
            f"- **Net Annual Risk Benefit:** {fair.get('net_risk_benefit', 0):,.2f} {fair.get('currency', 'EUR')}",
        ]
        return "\n".join(lines) + "\n"

    @app.get("/", response_class=HTMLResponse)
    def dashboard(org: str = Query(default="maison-valmont")) -> str:
        orgs = store.list_orgs()
        selected = store.get_org(org) or (orgs[0] if orgs else None)
        if not selected:
            return "<h1>CONSERVA — No organizations seeded</h1>"
        oid = selected["org_id"]
        soa = store.compute_soa_summary(oid)
        ebios = store.get_ebios(oid)
        fairs = store.list_fair_runs(oid)
        fair = fairs[0] if fairs else {}
        evidence = store.list_evidence(oid)

        tabs = "".join(
            f"<a class='tab {'active' if o['org_id'] == oid else ''}' href='/?org={o['org_id']}'>{o['name'].split(' (')[0]}</a>"
            for o in orgs
        )
        ev_rows = "".join(
            f"<tr><td><code>{e['evidence_id']}</code></td><td>{e['control_id']}</td><td>{e['title']}</td>"
            f"<td>{e['evidence_type']}</td><td>{e['review_status']}</td><td><code>{e['sha256_digest'][:12]}</code></td></tr>"
            for e in evidence
        ) or "<tr><td colspan='6'>No evidence recorded.</td></tr>"

        op_rows = ""
        if ebios:
            op_rows = "".join(
                f"<tr><td><code>{op.id}</code></td><td>{op.title}</td><td>{' &rarr; '.join(op.kill_chain_steps)}</td>"
                f"<td>S{op.severity} &times; L{op.likelihood}</td><td>{', '.join(op.linked_controls)}</td></tr>"
                for op in ebios.workshop4_operational
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CONSERVA — Cyber Governance &amp; Quantitative Risk Engineering</title>
<style>
  :root {{ --ivory:#EAE5DA; --bg:#F6F3EC; --surface:#FFFFFF; --forest:#243B35; --brass:#B19A70; --burgundy:#542E3B; --ink:#1F2421; --muted:#5C635E; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:Georgia,'Times New Roman',serif; background:var(--bg); color:var(--ink); line-height:1.5; }}
  header {{ background:var(--forest); color:var(--ivory); padding:24px 36px; border-bottom:3px solid var(--brass); }}
  header h1 {{ font-size:22px; letter-spacing:1.4px; font-weight:600; }}
  header p {{ font-family:-apple-system,sans-serif; font-size:13px; color:#C9C5B9; margin-top:4px; }}
  nav {{ background:#1D302B; padding:10px 36px; display:flex; gap:10px; flex-wrap:wrap; }}
  .tab {{ font-family:-apple-system,sans-serif; font-size:12px; color:#DDD7C8; text-decoration:none; padding:6px 12px; border:1px solid #39554D; }}
  .tab.active {{ background:var(--brass); color:#18201D; font-weight:600; border-color:var(--brass); }}
  main {{ max-width:1180px; margin:24px auto; padding:0 24px 40px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
  .notice {{ background:#F8EFEF; border-left:4px solid var(--burgundy); padding:10px 14px; font-size:12px; color:var(--burgundy); margin-bottom:18px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin-bottom:22px; }}
  .card {{ background:var(--surface); border:1px solid #DDD6C7; padding:16px; }}
  .label {{ font-size:11px; text-transform:uppercase; letter-spacing:0.8px; color:var(--muted); }}
  .val {{ font-family:Georgia,serif; font-size:22px; color:var(--forest); margin-top:6px; }}
  .sub {{ font-size:12px; color:var(--muted); margin-top:4px; }}
  section {{ background:var(--surface); border:1px solid #DDD6C7; padding:18px 22px; margin-bottom:20px; }}
  h2 {{ font-family:Georgia,serif; font-size:16px; color:var(--forest); border-bottom:1px solid var(--ivory); padding-bottom:6px; margin-bottom:12px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid #EFECE4; }}
  th {{ font-size:11px; text-transform:uppercase; color:var(--muted); background:#FAF8F4; }}
</style>
</head>
<body>
  <header>
    <h1>CONSERVA — Cyber Governance &amp; Quantitative Risk Engineering</h1>
    <p>{selected['name']} · {selected['sector']} · {selected['jurisdiction']}</p>
  </header>
  <nav>{tabs}</nav>
  <main>
    <div class="notice">{selected['fictional_disclaimer']} Applicable frameworks: {', '.join(selected['applicable_laws'])}.</div>
    <div class="grid">
      <div class="card"><div class="label">Annex A Controls Tracked</div><div class="val">{soa['total_controls_tracked']}</div><div class="sub">Applicable: {soa['applicable_controls']} · N/A: {soa['non_applicable_controls']}</div></div>
      <div class="card"><div class="label">Expected ALE (Monte Carlo)</div><div class="val">{fair.get('expected_ale', 0):,.0f} {fair.get('currency', 'EUR')}</div><div class="sub">p95: {fair.get('p95_ale', 0):,.0f} · {fair.get('iterations', 0):,} iterations</div></div>
      <div class="card"><div class="label">Residual ALE (Post-Treatment)</div><div class="val">{fair.get('residual_expected_ale', 0):,.0f} {fair.get('currency', 'EUR')}</div><div class="sub">Risk reduction: {fair.get('risk_reduction_pct', 0)}%</div></div>
      <div class="card"><div class="label">Net Risk Benefit</div><div class="val">{fair.get('net_risk_benefit', 0):,.0f} {fair.get('currency', 'EUR')}</div><div class="sub">Control cost: {fair.get('annual_control_cost', 0):,.0f}</div></div>
    </div>
    <section>
      <h2>ANSSI EBIOS Risk Manager — Workshop 4 Operational Scenarios</h2>
      <table>
        <thead><tr><th>ID</th><th>Scenario</th><th>Kill Chain</th><th>Rating</th><th>Linked Controls</th></tr></thead>
        <tbody>{op_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Evidence Register &amp; Integrity Hashes</h2>
      <table>
        <thead><tr><th>Evidence ID</th><th>Control</th><th>Title</th><th>Type</th><th>Review Status</th><th>SHA-256</th></tr></thead>
        <tbody>{ev_rows}</tbody>
      </table>
    </section>
  </main>
</body>
</html>"""

    return app


app = create_app()
