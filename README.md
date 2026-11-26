# CONSERVA — Cyber Governance & Quantitative Risk Engineering

**Repository:** `https://github.com/Bassma202/grc-compliance-automation-tool`  
**Author:** Bassma Alaoui Sossey — Final-Year Cybersecurity Engineering Student (Université Euromed de Fès — EIDIA)

## 1. Purpose
CONSERVA is a data-driven cybersecurity governance, compliance, and quantitative risk engineering platform. It replaces hardcoded scoring scripts with multi-tenant assessment persistence, evidence lifecycle management, Statement of Applicability (SoA) generation, a 5-workshop ANSSI EBIOS Risk Manager workflow, and a seeded Beta-PERT Monte Carlo Open FAIR simulator.

## 2. Implemented Capabilities
- **93 Annex A Structural Controls + 7 Separate ISMS Clauses (`src/conserva/controls.py`)**: Tracks all 93 ISO/IEC 27001:2022 Annex A control identifiers (`37` Organizational, `8` People, `14` Physical, `34` Technological) separately from ISMS Clauses 4–10, mapped to authoritative public frameworks (**NIST CSF 2.0**, **Moroccan Law 09-08 / CNDP**, **EU GDPR**, **EU DORA**). Includes a JSON/YAML importer so organizations can load privately licensed standard text locally without redistributing copyrighted ISO text.
- **Data-Driven Multi-Tenant Assessment & Evidence Store (`src/conserva/storage.py`, `src/conserva/web.py`)**: SQLite-backed FastAPI service with RBAC (`ADMIN`, `AUDITOR`, `RISK_OWNER`, `VIEWER`) and strict cross-tenant isolation (`403`). Enforces mandatory justification for non-applicable controls (`422`), evidence SHA-256 digests, and review status tracking.
- **5-Workshop ANSSI EBIOS Risk Manager (`src/conserva/ebios.py`)**: Models Workshop 1 (business values, supporting assets, feared events), Workshop 2 (risk sources & target objectives), Workshop 3 (ecosystem stakeholder threat levels & strategic scenarios), Workshop 4 (operational kill-chain scenarios), and Workshop 5 (treatment plans & residual ratings).
- **Monte Carlo Open FAIR Risk Engine (`src/conserva/fair.py`)**: Seeded `10,000`-iteration Beta-PERT Monte Carlo engine computing Expected ALE, `p50/p90/p95/p99`, 90% uncertainty intervals, post-mitigation residual ALE, control cost-benefit, Spearman rank sensitivity drivers, and EUR/MAD conversions with explicit FX date/source metadata. Validated analytically against closed-form Beta-PERT expectations.
- **4 Distinct Fictional Case Studies (`src/conserva/case_studies.py`)**:
  1. **Maison Valmont** (*Fictional Luxury Fashion House*, France/EU, GDPR + IP confidentiality, EUR)
  2. **Laboratoire AtlasPath** (*Fictional Digital Pathology Lab*, Morocco, Law 09-08/CNDP, MAD)
  3. **Fondation Al-Qarawiyyin Numérique** (*Fictional Cultural Heritage Archive*, WORM preservation, EUR)
  4. **Observatoire Méridien** (*Fictional Scientific Research Institute*, federated access & OT/HPC, EUR)
- **Institutional Web UI & Markdown Executive Reports (`src/conserva/web.py`)**: Live multi-organization switcher, SoA/EBIOS/FAIR/Evidence views, and `/api/orgs/{org_id}/report.md` export.

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
