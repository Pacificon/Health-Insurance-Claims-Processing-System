# Health Insurance Claims Processing System

Multi-agent health insurance claims adjudication system for the **Plum AI Engineer** take-home assignment.

Automates claim review for Indian group health insurance: document validation, structured extraction, policy rule evaluation, and explainable approve / partial / reject decisions.

## Stack (planned)

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, LangGraph |
| LLM | Google Gemini 1.5 Flash (vision + extraction) |
| Policy engine | Deterministic Python (rules from `policy_terms.json`) |
| Frontend | Next.js 14, Tailwind CSS |
| Database | SQLite (local) / PostgreSQL (production) |
| Deploy | Railway |

## Status

**Stage 0** — Repository initialized with assignment spec and implementation plan.

See [PLUM_CLAIMS_PLANNING.md](PLUM_CLAIMS_PLANNING.md) for the full build plan and staged commit workflow.

## Repository layout

```
├── assignment.md              # Plum assignment specification
├── policy_terms.json          # Policy rules, coverage, member roster
├── test_cases.json            # 12 evaluation scenarios
├── sample_documents_guide.md  # Indian medical document formats
├── PLUM_CLAIMS_PLANNING.md    # Implementation plan
├── backend/                   # (Stage 1+) FastAPI + agents
├── frontend/                  # (Stage 9+) Next.js UI
└── docs/                      # (Stage 10+) Architecture, contracts
```

## Assignment resources

| File | Purpose |
|------|---------|
| [assignment.md](assignment.md) | Full problem statement and deliverables |
| [policy_terms.json](policy_terms.json) | Policy configuration — do not hardcode rules |
| [test_cases.json](test_cases.json) | 12 test cases with expected outcomes |
| [sample_documents_guide.md](sample_documents_guide.md) | Document types and extraction guidance |

## Local setup

_Coming in Stage 1._

```bash
# Backend (after Stage 1)
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (after Stage 9)
cd frontend
npm install
npm run dev
```

## Environment variables

```bash
# .env.example (added in later stages)
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./claims.db
```

## Live demo

_Deploy URL will be added in Stage 10._

## Author

Built as part of the Plum AI Engineer hiring process.
