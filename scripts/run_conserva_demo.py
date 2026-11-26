#!/usr/bin/env python3
"""Reproducible CONSERVA multi-sector demonstration & evidence exporter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conserva.case_studies import seed_four_case_studies
from conserva.models import utc_now_iso
from conserva.storage import ConservaStore


def main() -> None:
    ev_dir = ROOT / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    db = ROOT / "data" / "conserva.db"
    if db.exists():
        db.unlink()
    store = ConservaStore(db)
    results = seed_four_case_studies(store)
    payload = {
        "generated_at": utc_now_iso(),
        "evidence_classification": "Simulated business data (explicitly fictional case studies)",
        "case_studies": results,
    }
    out = ev_dir / "conserva_demo_evidence.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for oid, info in results.items():
        fair = info["fair"]
        print(
            f"[{oid}] controls={info['soa']['total_controls_tracked']} | "
            f"ALE={fair['expected_ale']:,.2f} {fair['currency']} (p95={fair['p95_ale']:,.2f}) -> "
            f"residual={fair['residual_expected_ale']:,.2f} ({fair['risk_reduction_pct']}% reduction)"
        )


if __name__ == "__main__":
    main()
