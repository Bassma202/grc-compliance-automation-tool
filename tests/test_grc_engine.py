"""
Unit Tests for GRC Scoring, Law 09-08, EBIOS RM, and FAIR Quantitative Risk
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.grc_engine import GRCEngine
from src.fair_engine import FAIRRiskCalculator

class TestGRCEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GRCEngine()
        self.fair = FAIRRiskCalculator(currency="MAD")

    def test_iso27001_full_compliance(self):
        responses = {
            "A.5.1": "IMPLEMENTED", "A.5.15": "IMPLEMENTED", "A.5.24": "IMPLEMENTED",
            "A.8.1": "IMPLEMENTED", "A.8.7": "IMPLEMENTED", "A.8.9": "IMPLEMENTED",
            "A.8.12": "IMPLEMENTED", "A.8.15": "IMPLEMENTED", "A.8.20": "IMPLEMENTED",
            "A.8.24": "IMPLEMENTED"
        }
        res = self.engine.evaluate_iso27001(responses)
        self.assertEqual(res["compliance_score_percent"], 100.0)
        self.assertEqual(res["identified_gaps_count"], 0)

    def test_iso27001_partial_compliance(self):
        responses = {
            "A.5.1": "IMPLEMENTED",
            "A.5.15": "PARTIAL",
            "A.8.12": "NOT_IMPLEMENTED"
        }
        res = self.engine.evaluate_iso27001(responses)
        self.assertLess(res["compliance_score_percent"], 100.0)
        self.assertGreater(res["identified_gaps_count"], 0)

    def test_law0908_gap_detection(self):
        responses = {
            "ART-03": "COMPLIANT",
            "ART-12": "COMPLIANT",
            "ART-23": "NON_COMPLIANT" # Missing encryption on patient data
        }
        res = self.engine.evaluate_law0908(responses)
        self.assertEqual(res["compliant_articles"], 2)
        self.assertTrue(any(v["article_id"] == "ART-23" for v in res["violations"]))

    def test_ebios_risk_calculation(self):
        risk = self.engine.calculate_ebios_risk(gravity=4, likelihood=4)
        self.assertEqual(risk["risk_score"], 16)
        self.assertEqual(risk["risk_tier"], "CRITICAL / UNACCEPTABLE")

    def test_fair_quantitative_ale(self):
        # Threat capability 0.5, 10 attempts/yr, 0.2 vuln, 10k primary, 40k secondary
        fair_res = self.fair.calculate_ale(0.5, 10.0, 0.2, 10000.0, 40000.0)
        self.assertGreater(fair_res["annualized_loss_expectancy_ale"], 0)
        self.assertEqual(fair_res["single_loss_expectancy"], 50000.0)
        self.assertEqual(fair_res["currency"], "MAD")

if __name__ == "__main__":
    unittest.main()
