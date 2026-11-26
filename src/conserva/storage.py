"""Multi-tenant SQLite persistence layer for CONSERVA organizations, assessments, evidence, EBIOS RM, and FAIR runs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from conserva.ebios import EBIOSStudy
from conserva.models import ControlAssessment, ControlStatus, EvidenceItem, FAIRResult, utc_now_iso

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    fictional_disclaimer TEXT NOT NULL,
    applicable_laws_json TEXT NOT NULL,
    profile_summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    assessment_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    control_id TEXT NOT NULL,
    applicable INTEGER NOT NULL,
    applicability_justification TEXT NOT NULL,
    status TEXT NOT NULL,
    owner TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    finding_notes TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(org_id, control_id)
);

CREATE TABLE IF NOT EXISTS evidence_items (
    evidence_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    control_id TEXT NOT NULL,
    title TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    sha256_digest TEXT NOT NULL,
    owner TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    review_status TEXT NOT NULL,
    reviewer TEXT,
    next_review_due TEXT NOT NULL,
    limitations TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ebios_studies (
    study_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fair_runs (
    run_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    scenario_name TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    org_id TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


class ConservaStore:
    def __init__(self, db_path: str | Path = "data/conserva.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def upsert_org(
        self,
        org_id: str,
        name: str,
        sector: str,
        jurisdiction: str,
        applicable_laws: list[str],
        profile_summary: str,
        fictional_disclaimer: str = "FICTIONAL DEMONSTRATION CASE STUDY — NOT A REAL CLIENT AUDIT.",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO organizations
                (org_id, name, sector, jurisdiction, fictional_disclaimer, applicable_laws_json, profile_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (org_id, name, sector, jurisdiction, fictional_disclaimer, json.dumps(applicable_laws), profile_summary),
            )

    def list_orgs(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM organizations ORDER BY org_id").fetchall()
        return [{**dict(r), "applicable_laws": json.loads(r["applicable_laws_json"])} for r in rows]

    def get_org(self, org_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM organizations WHERE org_id = ?", (org_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["applicable_laws"] = json.loads(d.pop("applicable_laws_json"))
        return d

    def upsert_assessment(self, a: ControlAssessment) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO assessments
                (assessment_id, org_id, control_id, applicable, applicability_justification,
                 status, owner, evidence_ids_json, finding_notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    a.assessment_id,
                    a.org_id,
                    a.control_id,
                    1 if a.applicable else 0,
                    a.applicability_justification,
                    a.status.value,
                    a.owner,
                    json.dumps(a.evidence_ids),
                    a.finding_notes,
                    a.updated_at,
                ),
            )

    def list_assessments(self, org_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM assessments WHERE org_id = ? ORDER BY control_id", (org_id,)
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["applicable"] = bool(d["applicable"])
            d["evidence_ids"] = json.loads(d.pop("evidence_ids_json"))
            out.append(d)
        return out

    def compute_soa_summary(self, org_id: str) -> dict[str, Any]:
        rows = self.list_assessments(org_id)
        applicable = [r for r in rows if r["applicable"]]
        non_applicable = [r for r in rows if not r["applicable"]]
        counts = {s.value: 0 for s in ControlStatus}
        for r in applicable:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        assessed = sum(
            counts[k]
            for k in (
                ControlStatus.IMPLEMENTED.value,
                ControlStatus.PARTIAL.value,
                ControlStatus.NOT_IMPLEMENTED.value,
                ControlStatus.INSUFFICIENT_EVIDENCE.value,
                ControlStatus.ACCEPTED_EXCEPTION.value,
            )
        )
        weighted = counts[ControlStatus.IMPLEMENTED.value] + 0.5 * counts[ControlStatus.PARTIAL.value]
        coverage_pct = round((weighted / len(applicable) * 100.0), 1) if applicable else 0.0
        return {
            "org_id": org_id,
            "total_controls_tracked": len(rows),
            "applicable_controls": len(applicable),
            "non_applicable_controls": len(non_applicable),
            "assessed_controls": assessed,
            "status_counts": counts,
            "implementation_index_pct": coverage_pct,
            "disclaimer": "Self-assessment index based on recorded evidence; does not represent formal certification or legal compliance.",
        }

    def save_evidence(self, ev: EvidenceItem) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO evidence_items
                (evidence_id, org_id, control_id, title, evidence_type, source_ref, sha256_digest,
                 owner, collected_at, review_status, reviewer, next_review_due, limitations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ev.evidence_id,
                    ev.org_id,
                    ev.control_id,
                    ev.title,
                    ev.evidence_type,
                    ev.source_ref,
                    ev.sha256_digest,
                    ev.owner,
                    ev.collected_at,
                    ev.review_status,
                    ev.reviewer,
                    ev.next_review_due,
                    ev.limitations,
                ),
            )

    def list_evidence(self, org_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM evidence_items WHERE org_id = ? ORDER BY collected_at DESC", (org_id,)
                ).fetchall()
            ]

    def save_ebios(self, study: EBIOSStudy) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ebios_studies (study_id, org_id, payload_json, updated_at) VALUES (?, ?, ?, ?)",
                (study.study_id, study.org_id, study.model_dump_json(), utc_now_iso()),
            )

    def get_ebios(self, org_id: str) -> EBIOSStudy | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM ebios_studies WHERE org_id = ? ORDER BY updated_at DESC LIMIT 1",
                (org_id,),
            ).fetchone()
        return EBIOSStudy.model_validate_json(row["payload_json"]) if row else None

    def save_fair_run(self, run_id: str, org_id: str, res: FAIRResult) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO fair_runs (run_id, org_id, scenario_name, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, org_id, res.scenario_name, res.model_dump_json(), utc_now_iso()),
            )

    def list_fair_runs(self, org_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id, payload_json, created_at FROM fair_runs WHERE org_id = ? ORDER BY created_at DESC",
                (org_id,),
            ).fetchall()
        return [{"run_id": r["run_id"], "created_at": r["created_at"], **json.loads(r["payload_json"])} for r in rows]

    def log_audit(self, actor_role: str, org_id: str, action: str, detail: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (timestamp, actor_role, org_id, action, detail) VALUES (?, ?, ?, ?, ?)",
                (utc_now_iso(), actor_role, org_id, action, detail),
            )
