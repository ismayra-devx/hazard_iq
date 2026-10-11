# HazardIQ — Climate-Resilient Urban Navigation Engine

HazardIQ provides climate-aware routing decision support for urban commuters facing extreme heatwaves and sudden monsoon flooding.

## Repository Structure

- **[`backend/`](./backend)**: FastAPI backend service, Open-Meteo weather integration, Cedar deterministic safety policy engine, Amazon Bedrock vision analysis, and AWS cloud deployment (DynamoDB, S3, App Runner).
- **[`frontend/`](./frontend)**: Commuter user interface (React + Vite, Leaflet interactive mapping).

---

## Getting Started

### Backend
For detailed setup instructions, local development commands, and AWS production deployment guides, see [**`backend/README.md`**](./backend/README.md).

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
See [**`frontend/README.md`**](./frontend/README.md) for web client instructions.
