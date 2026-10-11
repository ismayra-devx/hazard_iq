# HazardIQ Backend - Climate-Aware Navigation Engine

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143+-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2.14-e92063.svg)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Tests-40%20Passed-brightgreen.svg)]()
[![AWS App Runner Ready](https://img.shields.io/badge/AWS-App%20Runner%20Ready-orange.svg)]()

> **Decision Support Disclaimer:** HazardIQ provides advisory risk estimation to help commuters navigate extreme weather hazards. It does **not** certify physical road safety or replace municipal emergency directives.

---

## 1. What HazardIQ Does

During extreme heatwaves and sudden monsoon downpours, commuters in dense urban areas (such as Delhi) face acute climate hazards:
- **Heatwave Mode:** Surfaces reach scorching temperatures; unshaded corridors cause solar stroke, and hydration points are unmapped or non-functional.
- **Monsoon Mode:** Road underpasses and arterial intersections experience flash flooding and waterlogging. Two-wheelers stall, manholes become submerged, and cars hydroplane.
- **Citizen Hazard Reporting:** Commuters submit real-time reports and photographs of waterlogging, broken water kiosks, or tree obstructions to alert fellow travelers.

HazardIQ merges live meteorological data, static topographical infrastructure attributes, and citizen ground truth to calculate transparent route risk scores and vehicle-specific safety guidance.

---

## 2. Team Architecture & Responsibilities

In our four-person hackathon team:
- **Member 1 (Frontend Lead):** React + Vite user interface and mobile web view.
- **Member 2 (Mapping Lead):** Leaflet mapping, road geometry, and alternative route pathfinding.
- **Member 3 (Me - Backend Lead):** Python backend, Open-Meteo weather integration, transparent heat/monsoon risk scoring, conservative safety policy rules, citizen report validation, and OpenAPI contracts.
- **Member 4 (AWS Cloud Lead):** AWS App Runner deployment, Amazon Bedrock (Nova Lite) model access, IAM roles, and DynamoDB/S3 configuration.

---

## 3. Project Structure

```text
hazardiq-backend/
├── app/
│   ├── __init__.py                  # App package indicator
│   ├── main.py                      # FastAPI app entry point, CORS, and health check
│   ├── config.py                    # Environment settings via Pydantic BaseSettings
│   ├── schemas.py                   # Strict Pydantic models with coordinate & unit validation
│   ├── api/
│   │   ├── __init__.py
│   │   ├── hotspots.py              # GET /api/hotspots & GET /api/hotspots/{id}
│   │   ├── reports.py               # POST /api/report & GET /api/reports
│   │   └── weather.py               # GET /api/weather/current
│   ├── services/
│   │   ├── __init__.py
│   │   ├── weather_service.py       # Open-Meteo HTTPX async client with in-memory caching
│   │   ├── risk_service.py          # Explainable heatwave & monsoon heuristic scoring
│   │   ├── safety_service.py        # Conservative vehicle-specific rules & Cedar fallback
│   │   ├── image_analysis_service.py # Amazon Bedrock (Nova Lite) vision integration
│   │   ├── storage_service.py       # Local JSON persistence & DynamoDB/S3 adapters
│   │   └── report_service.py        # Full Golden Path report processing coordinator
│   ├── policies/
│   │   └── cedar_policy.cedar       # Authentic Cedar safety specification (version 1.0)
│   └── data/
│       └── hotspots.json            # 20 synthetic demonstration hotspot records (Delhi)
├── data/
│   ├── hotspots.json                # Root mirror of hotspot demonstration data
│   └── local_reports.json           # Local JSON persistence store for reports
├── tests/
│   ├── test_health.py               # Health & root endpoint tests
│   ├── test_hotspots.py             # Hotspot schema & filter tests
│   ├── test_weather.py              # Weather caching & fallback tests
│   ├── test_risk.py                 # Heat & monsoon calculation boundary tests
│   ├── test_safety.py               # Vehicle clearance & policy rules tests
│   ├── test_reports.py              # Report creation, validation, & image tests
│   └── test_golden_path.py          # End-to-end integration scenarios
├── Dockerfile                       # Production non-root multi-stage container
├── requirements.txt                 # Frozen production & test dependencies
├── .env.example                     # Environment variables template
├── .gitignore                       # Git exclusions
└── README.md                        # Complete project manual
```

---

## 4. Python and Environment Setup (Windows PowerShell)

Ensure Python 3.11+ is installed. On your Windows machine, open **PowerShell** and run:

```powershell
# 1. Navigate to the project root
cd "E:\hizard iq"

# 2. Verify Python version
python --version

# 3. Create a dedicated virtual environment
python -m venv .venv

# 4. Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

> **PowerShell ExecutionPolicy Tip:** If you see `execution of scripts is disabled on this system`, run PowerShell as Administrator once and run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## 5. Dependency Installation

With the `.venv` activated, install the locked dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify installed packages:
```powershell
python -m pip list
```

---

## 6. Environment Configuration (`.env`)

Copy the configuration template:

```powershell
Copy-Item .env.example .env
```

Key environment variables:
| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | Comma-separated list of permitted frontend origins for CORS |
| `OPEN_METEO_BASE_URL` | `https://api.open-meteo.com/v1/forecast` | Open-Meteo forecast API URL |
| `WEATHER_CACHE_TTL_SECONDS` | `300` | In-memory weather cache duration (5 minutes) |
| `DEFAULT_CITY` | `Delhi` | Focus urban area for demonstration |
| `MAX_IMAGE_SIZE_BYTES` | `5242880` | Maximum allowable image upload (5 MB) |
| `ENABLE_BEDROCK` | `false` | Enable live Amazon Bedrock calls (`true` requires AWS credentials) |
| `BEDROCK_MODEL_ID` | `amazon.nova-lite-v1:0` | Target vision model on AWS Bedrock |
| `ENABLE_DYNAMODB` | `false` | Persist reports to DynamoDB (`false` uses `data/local_reports.json`) |
| `ENABLE_S3` | `false` | Store report photographs in S3 bucket |

---

## 7. How to Run the Server Locally

Start the development server with live reload:

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

Output:
```text
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

---

## 8. Interactive API Documentation (`/docs`)

Open your browser to:
- **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

Teammates (Member 1 and Member 2) can test and copy real JSON request and response models directly from `/docs`.

---

## 9. How to Run Automated Tests

Run the complete test suite (40 unit and integration tests):

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Expected result:
```text
============================= 40 passed in 5.24s ==============================
```

To run a specific test file:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_golden_path.py -v
```

---

## 10. API Contract Examples

### 10.1 Health Check: `GET /health`

**Request:**
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**Response (HTTP 200 OK):**
```json
{
  "status": "ok",
  "app_name": "HazardIQ Backend",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-10-11T01:17:00.000000Z",
  "services": {
    "weather_service": "online (Open-Meteo, cache=300s)",
    "storage_backend": "local_json (data/local_reports.json)",
    "bedrock_vision": "disabled (fallback to PENDING_REVIEW)",
    "s3_photo_storage": "disabled",
    "policy_engine": "cedar_spec_v1 (deterministic_python_evaluator)"
  }
}
```

---

### 10.2 Hotspots Listing: `GET /api/hotspots`

**Request:**
```http
GET /api/hotspots?hotspot_type=waterlogging HTTP/1.1
Host: localhost:8000
```

**Response (HTTP 200 OK):**
```json
{
  "hotspots": [
    {
      "hotspot_id": "delhi-hotspot-001",
      "name": "Minto Bridge Underpass (Demo)",
      "latitude": 28.6328,
      "longitude": 77.2223,
      "elevation_dip_meters": 2.8,
      "impermeability_ratio": 0.95,
      "road_type": "ARTERIAL",
      "shade_ratio": 0.1,
      "drinking_water_available": false,
      "hotspot_type": "waterlogging",
      "road_segment_id": "seg-del-001",
      "data_source": "delhi_demo_synthetic",
      "is_demo_data": true,
      "heat_risk": {
        "score": 34.2,
        "level": "MODERATE",
        "is_estimate": true,
        "shade_status": "UNSHADED",
        "contributing_factors": [
          "Ambient temperature 30.5°C",
          "Low shade coverage (10%): exposed to solar insolation (+5.0 pts)"
        ],
        "calculation_notes": "Score 34.2/100 (MODERATE)..."
      },
      "monsoon_risk": {
        "score": 78.4,
        "level": "HIGH",
        "is_estimate": true,
        "waterlogging_hazard": true,
        "contributing_factors": [
          "Precipitation: 18.0 mm/hr accumulation",
          "Topographic elevation dip: 2.8 meters",
          "Surface impermeability: 95% concrete/asphalt",
          "High-capacity underpass corridor vulnerable to flash drainage overflow (+10 pts)"
        ],
        "calculation_notes": "Score 78.4/100 (HIGH)..."
      },
      "weather_snapshot": {
        "temperature_celsius": 30.5,
        "relative_humidity_percentage": 68.0,
        "precipitation_mm": 18.0,
        "wind_speed_kmh": 14.2,
        "observation_time": "2026-10-11T12:00",
        "source": "Open-Meteo API (CC BY 4.0)",
        "is_live": true
      },
      "last_evaluated_at": "2026-10-11T01:17:00.000000Z"
    }
  ],
  "total_count": 1,
  "data_source": "Open-Meteo & Synthetic Delhi Demonstration Survey",
  "target_city": "Delhi",
  "limitations": [
    "Sample coordinates and attributes are synthetic demonstration data for hackathon evaluation.",
    "Weather data is obtained from Open-Meteo under CC BY 4.0 license.",
    "Risk scores are prototype heuristics and do not represent verified ground truth.",
    "Unmeasured shade attributes are flagged as UNKNOWN and never assumed shaded."
  ]
}
```

---

### 10.3 Citizen Hazard Report: `POST /api/report`

**Request:**
```http
POST /api/report HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "hazard_category": "WATERLOGGING",
  "latitude": 28.6328,
  "longitude": 77.2223,
  "description": "Severe flooding under Minto Bridge. Water above knee height.",
  "road_segment_id": "seg-del-001",
  "vehicle_type": "TWO_WHEELER"
}
```

**Response (HTTP 201 Created):**
```json
{
  "report_id": "rep-4a2bc194d8e0",
  "hazard_category": "WATERLOGGING",
  "latitude": 28.6328,
  "longitude": 77.2223,
  "status": "PENDING_REVIEW",
  "created_at": "2026-10-11T01:17:15.000000Z",
  "vehicle_type": "TWO_WHEELER",
  "image_analyzed": false,
  "ai_analysis": null,
  "risk_assessment": {
    "monsoon_risk": {
      "score": 68.5,
      "level": "HIGH",
      "waterlogging_hazard": true
    }
  },
  "safety_evaluation": {
    "action": "AVOID",
    "reason": "Two-wheelers risk hydroplaning, exhaust back-flooding, and submerged road depression accidents.",
    "policy_engine": "deterministic_python_safety_engine (Cedar fallback - native engine unavailable on Python 3.14 Windows)",
    "rules_triggered": [
      "CEDAR_POLICY_2: FORBID TWO_WHEELER on moderate/severe waterlogging"
    ],
    "uncertainty_warning": null
  },
  "route_avoidance_recommendation": {
    "avoid_segment": true,
    "road_segment_id": "seg-del-001",
    "alternative_route_available": false,
    "guidance_notes": "Action 'AVOID': Two-wheelers risk hydroplaning, exhaust back-flooding, and submerged road depression accidents. Alternative route avoidance must be computed by Member 2's Leaflet mapping engine."
  },
  "service_limitations": [
    "No photograph attached; queued as PENDING_REVIEW."
  ]
}
```

---

## 11. Weather Integration (Open-Meteo)

- **Provider:** [Open-Meteo Forecast API](https://open-meteo.com) under Creative Commons Attribution 4.0 (CC BY 4.0).
- **Endpoint:** `GET https://api.open-meteo.com/v1/forecast`
- **Variables Queried:**
  - `temperature_2m`: Air temperature in °C.
  - `relative_humidity_2m`: Relative humidity percentage (0-100%).
  - `precipitation`: Preceding hour accumulated precipitation in mm.
  - `wind_speed_10m`: Wind speed at 10 meters in km/h.
- **In-Memory Caching:** Responses are cached on a 2-decimal coordinate grid (~1.1 km resolution) with a 300-second TTL.
- **Concurrent Optimization:** Hotspot weather queries are executed simultaneously using `asyncio.gather`, reducing cold-start latency from 5.1s to **1.69s**.
- **Resilience:** Network timeouts or HTTP errors return an explicit snapshot (`is_live=False`) without throwing 500 errors.

---

## 12. Transparent Risk Scoring Heuristics

### 12.1 Heat Risk Formulation
$$\text{Score}_{\text{heat}} = \text{BaseThermalStress}(T_{\text{apparent}}) - \text{Mitigation}_{\text{shade}} - \text{Mitigation}_{\text{water}}$$

1. **Apparent Temperature ($T_{\text{apparent}}$):**
   $$e = \frac{\text{humidity}}{100} \cdot 6.105 \cdot \exp\left(\frac{17.27 \cdot T}{237.7 + T}\right)$$
   $$T_{\text{apparent}} = T + 0.33 \cdot e - 4.0$$
2. **Shade Adjustment Rules:**
   - **Unmeasured Shade ($= \text{null}$):** Flagged as `UNKNOWN`. **No shade is assumed.**
   - **Verified Shade ($\ge 35\%$):** Mitigates thermal stress by up to $-15$ points.
   - **Unshaded ($< 15\%$):** Adds $+5$ point solar exposure penalty.
3. **Hydration Relief:** Verified active drinking water kiosks deduct $-5$ points.
4. **Categorization:**
   - `< 30`: `LOW`
   - `30 - 59`: `MODERATE`
   - `60 - 84`: `HIGH`
   - `≥ 85`: `SEVERE`

### 12.2 Monsoon / Waterlogging Risk Formulation
$$\text{Runoff} = \text{RainfallFactor}(\text{mm}) \cdot \text{Impermeability} \cdot (1 + 0.35 \cdot \text{Dip}_{\text{meters}})$$
$$\text{Score}_{\text{monsoon}} = \min(100, \text{Runoff} + \text{Bonus}_{\text{reports}})$$

1. **Topography Multiplier:** Low-lying road depressions trap runoff; impermeable pavement prevents natural infiltration.
2. **Citizen Ground Truth:** Each verified report adds $+20$ points; unverified reports add $+8$ points.
3. **Safety Ground Rule:** A road is **never** declared safe solely because an estimated water depth is below an arbitrary threshold.

---

## 13. Amazon Bedrock Vision Integration (Nova Lite)

- **Model ID:** `amazon.nova-lite-v1:0`
- **Region:** `us-east-1` (configurable via `AWS_REGION`)
- **Safety Standard:**
  - AI vision outputs are strictly treated as **candidate evaluations**, never confirmed ground truth measurements.
  - The model is prompted to identify visible signs (e.g. standing water, submerged wheels, stalled traffic) and **never** hallucinate exact centimeter depths.
  - If `ENABLE_BEDROCK=false` or AWS credentials are unavailable, reports gracefully fall back to `PENDING_REVIEW` with full local persistence.

---

## 14. Cedar Policy Engine Integration Status

- **Cedar Policy Specification:** Available at `app/policies/cedar_policy.cedar`. Defines formal `forbid` and `permit` rules for `PEDESTRIAN`, `TWO_WHEELER`, `THREE_WHEELER_AUTO`, `FOUR_WHEELER_CAR`, and `BUS_HEAVY`.
- **Status on Python 3.14 Windows:** The official Rust-backed `cedarpolicy` Python wheel is not currently compiled for Python 3.14 on Windows.
- **Verified Adapter:** As directed, HazardIQ integrates `app/services/safety_service.py`, a deterministic Python safety-rule evaluator implementing the exact Cedar policy specification.
- **Transparency:** The engine transparently identifies itself in every response as:
  `"deterministic_python_safety_engine (Cedar fallback - native engine unavailable on Python 3.14 Windows)"`.

---

## 15. Storage Configuration

- **Local Development / Demo:** Stores report metadata in `data/local_reports.json`.
- **AWS Cloud Production:**
  - Reports stored in Amazon DynamoDB (`HazardIQ-Reports`).
  - Base64 images are uploaded to Amazon S3 (`hazardiq-hazard-photos`) with private object ACLs (`AES256` server-side encryption) and referenced via S3 keys.

---

## 16. Docker Containerization

### Build Container Image:
```powershell
docker build -t hazardiq-backend:latest .
```

### Run Container Locally:
```powershell
docker run -p 8000:8000 --env-file .env hazardiq-backend:latest
```

### Test Container Health:
```powershell
curl http://localhost:8000/health
```

---

## 17. AWS App Runner Deployment Coordination (Member 4 Checklist)

Provide the following details to Member 4:
1. **Container Port:** `8000`
2. **Health Check Path:** `/health` (Interval: 30s, Timeout: 5s, Protocol: HTTP)
3. **Required Environment Variables in App Runner Console:**
   - `ENVIRONMENT=production`
   - `ALLOWED_ORIGINS=https://main.<app-id>.amplifyapp.com` (Frontend Amplify URL)
   - `ENABLE_BEDROCK=true`
   - `BEDROCK_MODEL_ID=amazon.nova-lite-v1:0`
   - `ENABLE_DYNAMODB=true`
   - `DYNAMODB_TABLE_REPORTS=HazardIQ-Reports`
   - `ENABLE_S3=true`
   - `S3_BUCKET_PHOTOS=hazardiq-hazard-photos`
4. **IAM Role (Instance Role):**
   - `bedrock:InvokeModel` and `bedrock:Converse`
   - `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:Scan` on `HazardIQ-Reports`
   - `s3:PutObject`, `s3:GetObject` on `arn:aws:s3:::hazardiq-hazard-photos/*`

---

## 18. Common Troubleshooting

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `Cannot activate .venv (ExecutionPolicy error)` | PowerShell script restrictions | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `CORS Error in React browser console` | Frontend port not in `ALLOWED_ORIGINS` | Add `http://localhost:5173` or Amplify domain to `.env` |
| `Open-Meteo Timeout` | Temporary network drop | The service automatically serves cached data or fallback without crashing |
| `HTTP 422 Unprocessable Content` | Latitude > 90, Longitude > 180, or malformed image | Inspect the structured error response in `/docs` |

---

## 19. Known Limitations & Next Steps

1. **Synthetic Hotspot Geometry:** All 20 sample coordinates in `app/data/hotspots.json` are synthetic demonstration data for Delhi underpasses and intersections. Real-world municipal hydrological survey data should replace them in production.
2. **Routing Graph Ownership:** Member 2's Leaflet mapping engine owns graph topology and alternative route generation. The backend provides segment avoidance recommendations (`avoid_segment: true`), not polyline generation.
3. **Rate Limiting:** IP-based rate limiting is not yet active on the local demo server; AWS WAF should be placed in front of App Runner in production.
