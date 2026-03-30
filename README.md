# Cloud Optimizer MCP

Cloud Optimizer MCP is a presentation-ready cloud optimization demo with a glassmorphic React frontend and a FastAPI backend. It simulates cloud cost optimization workflows, supports a chatbot copilot, and lets you demonstrate recommendation acceptance, rejection, replay, observability, and AWS account onboarding in either mocked or real-validation mode.

## Live deployment

- Frontend: [https://cloud-optimizer-mcp-frontend.vercel.app](https://cloud-optimizer-mcp-frontend.vercel.app)
- Backend: [https://cloud-optimizer-mcp-backend.vercel.app](https://cloud-optimizer-mcp-backend.vercel.app)
- Health: [https://cloud-optimizer-mcp-backend.vercel.app/health](https://cloud-optimizer-mcp-backend.vercel.app/health)

## What the project includes

- `frontend/`
  - React + TypeScript + Vite
  - dashboard, services, chat, account, impact studio, and observability views
  - dark mode, glassmorphic UI, charts, internal scrolling panels, and demo-focused interactions
- `backend/`
  - FastAPI API
  - mocked AWS student account mode
  - real AWS credential validation mode through backend-only STS checks
  - deterministic recommendation engine
  - chat orchestration with Gemini fallback support
  - DynamoDB-ready repository layer
  - Datadog-style telemetry hooks

## Main features

- Dashboard with KPIs, resource inventory, line graph, pie chart, timeline, and observability panel
- Impact Studio with accept, reject, and recurring replay flows for demo recommendations
- Optimization Copilot chat with backend-backed state awareness
- Services tab that shows backend-fed service clusters
- Account flow with:
  - `mocked` mode for demo presentations
  - `real` mode for backend validation of AWS credentials
- Observability panel with metrics and separate events feed

## Architecture

- Frontend calls the backend through `VITE_API_BASE`
- Backend serves API routes under `/api`
- State is stored in:
  - local JSON by default
  - DynamoDB when enabled
- Telemetry is mirrored in-app and can also be sent to Datadog
- Gemini is used only for the assistant response layer; recommendation logic stays deterministic

## Local development

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Local URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`

## Environment variables

### Backend

- `PRISM_USE_DYNAMODB=false`
- `PRISM_DYNAMODB_REGION=ap-south-1`
- `PRISM_DYNAMODB_TABLE_PREFIX=prism_demo`
- `PRISM_DATA_FILE=backend/.local/prism_state.json`
- `PRISM_FRONTEND_ORIGIN=http://localhost:5173`
- `GEMINI_API_KEY=...`
- `GOOGLE_API_KEY=...`
- `GEMINI_MODEL=gemini-2.5-flash`
- `GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta`
- `DD_API_KEY=...`
- `DD_APP_KEY=...`
- `DD_SITE=datadoghq.com`
- `DD_ENV=demo`
- `DD_SERVICE=cloud-optimizer-mcp-backend`

### Frontend

- `VITE_API_BASE=http://localhost:8000/api`

Templates:

- [backend/.env.example](C:\Users\Mohan Achary\Documents\MCP\backend\.env.example)
- [frontend/.env.example](C:\Users\Mohan Achary\Documents\MCP\frontend\.env.example)

## Gemini setup

Do not paste your API key into the codebase or commit it to Git.

### Local

```powershell
cd backend
$env:GEMINI_API_KEY="your-real-key"
$env:GEMINI_MODEL="gemini-2.5-flash"
uvicorn app.main:app --reload --port 8000
```

### Vercel

Add these in the backend Vercel project:

- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-2.5-flash`

If the key is missing or Gemini fails, the backend falls back to built-in rule-based chat responses.

## AWS account modes

### Mocked mode

Best for presentation/demo use.

1. Open `/account`
2. Choose `Mocked demo AWS`
3. Enter student details and placeholder credentials
4. Submit to seed resources, recommendations, events, and chat context

### Real mode

Best for validating a real AWS student or lab account.

1. Open `/account`
2. Choose `Real AWS via backend validation`
3. Enter AWS access key ID and secret access key
4. Add session token if your student account uses temporary credentials
5. Submit

The backend validates the credentials using AWS STS. The current implementation validates the account and then still uses demo resource data for visualization.

Security note:

- secret access keys and session tokens are not returned to the frontend
- backend validation is performed server-side

## Vercel deployment

This project is designed as two Vercel projects from the same GitHub repo.

### Backend project

- Root directory: `backend`
- Entry point: [backend/index.py](C:\Users\Mohan Achary\Documents\MCP\backend\index.py)
- Routing config: [backend/vercel.json](C:\Users\Mohan Achary\Documents\MCP\backend\vercel.json)

Required env vars:

- `PRISM_FRONTEND_ORIGIN=https://YOUR_FRONTEND_DOMAIN`
- `GEMINI_API_KEY=...` if using Gemini
- `GEMINI_MODEL=gemini-2.5-flash`
- `DD_API_KEY=...` if using Datadog
- `DD_APP_KEY=...`
- `DD_SITE=datadoghq.com`
- `DD_ENV=production`
- `DD_SERVICE=cloud-optimizer-mcp-backend`

### Frontend project

- Root directory: `frontend`

Required env vars:

- `VITE_API_BASE=https://YOUR_BACKEND_DOMAIN/api`

## Important deployment notes

- Vercel frontend deployment URLs are supported by backend CORS
- Vercel backend state writes use temp storage to avoid read-only filesystem failures
- The live app should no longer show generic `Failed to fetch` for normal interactions

## Verification checklist

1. Open the frontend
2. Confirm dashboard loads without a request error
3. Open `/account` and submit mocked mode
4. Open `/chat` and send a message
5. Accept or reject a recommendation
6. Clear timeline or chat
7. Confirm the UI updates after each action

## Presentation flow

1. Start on `/account`
2. Link a mocked AWS student account
3. Show the dashboard KPIs and charts
4. Open Impact Studio and accept or reject a recommendation
5. Replay a recurring recommendation in mocked mode
6. Open Services to show backend-fed service inventory
7. Open Chat to show Optimization Copilot
8. Open Observability and show metrics plus events

## Current limitations

- Real AWS mode validates credentials but does not yet pull live inventory from EC2, RDS, S3, and Lambda
- Local JSON persistence on Vercel is temporary by design; enable DynamoDB for durable production state
- Gemini is optional and only powers the assistant explanation layer

## Repository

- GitHub: [https://github.com/Incertyo/MCP](https://github.com/Incertyo/MCP)
