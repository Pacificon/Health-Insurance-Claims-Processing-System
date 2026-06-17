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

**Stage 9** — Next.js UI: claim submission form, test-case presets, and decision trace timeline viewer.

See [PLUM_CLAIMS_PLANNING.md](PLUM_CLAIMS_PLANNING.md) for the full build plan and staged commit workflow.

## Repository layout

```
├── assignment.md              # Plum assignment specification
├── policy_terms.json          # Policy rules, coverage, member roster
├── test_cases.json            # 12 evaluation scenarios
├── sample_documents_guide.md  # Indian medical document formats
├── PLUM_CLAIMS_PLANNING.md    # Implementation plan
├── backend/                   # FastAPI + agents
├── frontend/                  # Next.js claim UI + trace viewer
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

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload --app-dir .
```

API runs at `http://127.0.0.1:8000`. Try `GET /health` and `GET /policy/summary`.

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open `http://localhost:3000` with the API running. The UI supports:

- Claim submission with document metadata and optional eval extraction JSON
- Loading any of the 12 Plum test-case presets
- Full decision trace timeline after submit
- Lookup of previously saved claims by ID

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
