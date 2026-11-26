# CONSERVA — Cyber Governance & Quantitative Risk Engineering

**Repository:** `https://github.com/Bassma202/grc-compliance-automation-tool`  
**Author:** Bassma Alaoui Sossey — Final-Year Cybersecurity Engineering Student (Université Euromed de Fès — EIDIA)

## 1. Purpose
CONSERVA is a data-driven cybersecurity governance, compliance, and quantitative risk engineering platform. It provides authenticated multi-tenant assessment persistence, evidence lifecycle management, Statement of Applicability (SoA) generation, a 5-workshop ANSSI EBIOS Risk Manager workflow, and a compound frequency-severity Beta-PERT Monte Carlo Open FAIR risk engine.

## 2. Implemented Capabilities
- **Server-Verified Session Authentication & Strict Multi-Tenant Isolation (`src/conserva/auth.py`, `src/conserva/web.py`):** Issues and verifies HMAC-SHA256 Bearer session tokens resolved exclusively against a server-side principal registry (`ADMIN`, `AUDITOR`, `RISK_OWNER`, `VIEWER`). Untrusted role/org headers (`X-Conserva-Role`, `X-Conserva-Org`) are rejected (`401`); cross-tenant API access—including `/api/orgs/{org_id}/report.md`—enforces strict `403` isolation.
- **93 Annex A Structural Controls + 7 Separate ISMS Clauses (`src/conserva/controls.py`):** Tracks all 93 ISO/IEC 27001:2022 Annex A control identifiers (`37` Organizational, `8` People, `14` Physical, `34` Technological) separately from ISMS Clauses 4–10, mapped to authoritative public frameworks (**NIST CSF 2.0**, **Moroccan Law 09-08 / CNDP**, **EU GDPR**, **EU DORA**). Enforces mandatory justification for non-applicable controls (`422`) and includes a JSON/YAML importer for privately licensed standard text without redistributing copyrighted ISO text.
- **5-Workshop ANSSI EBIOS Risk Manager (`src/conserva/ebios.py`):** Models Workshop 1 (business values, supporting assets, feared events), Workshop 2 (risk sources & target objectives), Workshop 3 (ecosystem stakeholder threat levels & strategic scenarios), Workshop 4 (operational kill-chain scenarios), and Workshop 5 (treatment plans & residual ratings).
- **Compound Frequency-Severity Monte Carlo Open FAIR Engine (`src/conserva/fair.py`):**
  - Seeded `10,000`-iteration compound Poisson–Beta-PERT simulation (`N ~ Poisson(LEF)` loss events per simulated year, each drawing independent primary Beta-PERT magnitude + secondary `Bernoulli(SLEF)` × secondary Beta-PERT magnitude), explicitly separating parameter EAL uncertainty from aggregate annual loss distribution (`probability_of_zero_loss_pct`, `p50/p90/p95/p99`, `exceedance_curve`, `aggregate_loss_std`).
  - Validated analytically against BOTH closed-form expected annual loss (`<3%` error) AND the analytical Law of Total Variance standard deviation (`<4%` error), plus exact zero-frequency and `Poisson(1)` checks.
  - Exact midrank (average-rank) Spearman rank correlation (`spearman_corr`) verified against tie-aware analytical values, with EUR/MAD conversion metadata.
  - Every FAIR simulation is persisted under a globally unique `FAIR-{uuid4}` identifier in SQLite and retrievable via tenant-scoped `GET /api/orgs/{org_id}/fair/{run_id}` across restarts.
- **4 Distinct Fictional Case Studies (`src/conserva/case_studies.py`):**
  1. **Maison Valmont** (*Fictional Luxury Fashion House*, France/EU, GDPR + IP confidentiality, EUR)
  2. **Laboratoire AtlasPath** (*Fictional Digital Pathology Lab*, Morocco, Law 09-08/CNDP, MAD)
  3. **Fondation Al-Qarawiyyin Numérique** (*Fictional Cultural Heritage Archive*, WORM preservation, EUR)
  4. **Observatoire Méridien** (*Fictional Scientific Research Institute*, federated access & OT/HPC, EUR)

## 3. Quick Start & Reproduction
```bash
make setup
make test
make security
make demo
make up   # Opens CONSERVA institutional UI on http://127.0.0.1:8003
```

## 4. Known Limitations & Disclaimers
- All four pre-seeded organizations and financial loss parameters are explicitly **fictional demonstration case studies** and do not represent completed client audits.
- Self-assessment indices and SoA exports do not establish legal compliance or formal ISO certification.
- Copyrighted ISO/IEC normative text is intentionally excluded to respect ISO licensing terms.

## 5. License
MIT License.
