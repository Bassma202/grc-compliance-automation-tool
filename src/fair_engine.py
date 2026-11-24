"""
FAIR (Factor Analysis of Information Risk) Quantitative Risk Calculator
Author: Bassma Alaoui Sossey
Quantifies financial loss exposure for healthcare and enterprise environments.
Calculates Loss Event Frequency (LEF), Loss Magnitude (LM), and Annualized Loss Expectancy (ALE).
"""

from typing import Dict, Any

class FAIRRiskCalculator:
    def __init__(self, currency: str = "MAD"):
        self.currency = currency

    def calculate_ale(
        self,
        threat_capability: float,    # 0.0 - 1.0 (Attacker skill/resource level)
        contact_frequency_per_year: float, # Expected attempts per year (e.g., 12.0 phishing attempts)
        vulnerability_probability: float,  # 0.0 - 1.0 (Probability controls fail against threat)
        primary_loss: float,         # Direct incident response, forensic triage, and recovery costs
        secondary_loss: float        # Regulatory fines (CNDP/CNIL), litigation, and reputation loss
    ) -> Dict[str, Any]:
        """
        Calculates expected Annualized Loss Expectancy (ALE).
        Loss Event Frequency (LEF) = Contact Frequency * Vulnerability Probability
        Single Loss Expectancy (SLE) = Primary Loss + Secondary Loss
        ALE = LEF * SLE
        """
        # Threat capability scales vulnerability
        effective_vuln = min(1.0, max(0.01, vulnerability_probability * (0.8 + 0.4 * threat_capability)))
        
        # Loss Event Frequency (times per year an attack succeeds)
        lef = contact_frequency_per_year * effective_vuln
        
        # Single Loss Expectancy
        sle = primary_loss + secondary_loss
        
        # Annualized Loss Expectancy
        ale = round(lef * sle, 2)
        
        return {
            "currency": self.currency,
            "threat_capability": threat_capability,
            "loss_event_frequency_per_year": round(lef, 3),
            "single_loss_expectancy": round(sle, 2),
            "primary_loss_breakdown": primary_loss,
            "secondary_loss_breakdown": secondary_loss,
            "annualized_loss_expectancy_ale": ale,
            "risk_significance": "HIGH FINANCIAL EXPOSURE" if ale > 200000 else "MANAGED RISK EXPOSURE"
        }

if __name__ == "__main__":
    fair = FAIRRiskCalculator(currency="MAD")
    # Healthcare Pathology Lab Ransomware Scenario
    res = fair.calculate_ale(
        threat_capability=0.75,
        contact_frequency_per_year=6.0,
        vulnerability_probability=0.30,
        primary_loss=150000.0,   # Restoration & DFIR triage
        secondary_loss=350000.0  # CNDP regulatory notice + hospital patient notification
    )
    print("FAIR Quantitative Loss Report:", res)
