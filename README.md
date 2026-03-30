# Cloud Optimizer MCP Demo

A net-new demo application with:

- `backend/`: FastAPI API with mocked AWS student-account onboarding, deterministic optimization recommendations, DynamoDB-ready storage, and Datadog telemetry hooks
- `frontend/`: React + TypeScript dashboard and chatbot UI

## Quick start

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

The frontend uses `VITE_API_BASE` when set. If it is missing, it falls back to the current origin plus `/api`.

## Environment

Backend variables:

- `PRISM_USE_DYNAMODB=false` to keep using the bundled local JSON store
- `PRISM_DYNAMODB_REGION=ap-south-1`
- `PRISM_DYNAMODB_TABLE_PREFIX=prism_demo`
- `PRISM_DATA_FILE=backend/.local/prism_state.json`
- `GEMINI_API_KEY=...` or `GOOGLE_API_KEY=...`
- `GEMINI_MODEL=gemini-2.5-flash`
- `GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta`
- `DD_API_KEY=...`
- `DD_APP_KEY=...` (optional, improves Datadog API compatibility)
- `DD_SITE=datadoghq.com`
- `DD_ENV=demo`
- `DD_SERVICE=cloud-optimizer-mcp-backend`
- `PRISM_FRONTEND_ORIGIN=http://localhost:5173`

When DynamoDB credentials are configured and `PRISM_USE_DYNAMODB=true`, the repository switches from local JSON persistence to DynamoDB tables. Datadog metrics and events are optional; the app also keeps mirrored telemetry for the in-app observability panel.

## Gemini setup

Set your Gemini key in the backend shell before starting FastAPI:

```powershell
$env:GEMINI_API_KEY="your-key-here"
$env:GEMINI_MODEL="gemini-2.5-flash"
uvicorn app.main:app --reload --port 8000
```

The backend keeps recommendations deterministic and uses Gemini only for the chatbot explanation layer. If the Gemini key is missing or the API call fails, the chatbot falls back to the built-in rule-based responses.

## Vercel deployment

The simplest production setup is two Vercel projects from the same GitHub repository:

1. `backend` project
2. `frontend` project

### Backend on Vercel

- Import the GitHub repo in Vercel
- Set the Root Directory to `backend`
- Vercel will use `backend/index.py` as the FastAPI entry point
- Add environment variables manually in Vercel:
  - `PRISM_FRONTEND_ORIGIN=https://YOUR_FRONTEND_DOMAIN`
  - `GEMINI_API_KEY=...` if you want Gemini enabled
  - `GEMINI_MODEL=gemini-2.5-flash`
  - `DD_API_KEY=...` if you want Datadog
  - `DD_APP_KEY=...` optional
  - `DD_SITE=datadoghq.com`
  - `DD_ENV=production`
  - `DD_SERVICE=cloud-optimizer-mcp-backend`
  - DynamoDB variables only if you want DynamoDB instead of local demo state

### Frontend on Vercel

- Import the same GitHub repo again in Vercel
- Set the Root Directory to `frontend`
- Add this environment variable manually:
  - `VITE_API_BASE=https://YOUR_BACKEND_DOMAIN/api`

### Manual secrets

Secrets are no longer stored in `backend/.env`. Use:

- `backend/.env.example`
- `frontend/.env.example`

as the template, and enter the real values manually in Vercel.

## AWS student account modes

The account screen now supports two modes:

1. `mocked`
2. `real`

### Mocked mode

In the UI:

1. Open `/account`
2. Choose `Mocked demo AWS`
3. Enter your student name, email, AWS student account ID, and placeholder credential values
4. Submit the form to seed the demo state

### Real mode

In the UI:

1. Open `/account`
2. Choose `Real AWS via backend validation`
3. Enter your student name and email
4. Enter your AWS access key ID and secret access key
5. Enter the session token too if your student/lab account uses temporary credentials
6. Submit the form

The backend will validate the credentials using AWS STS. If validation succeeds, the account is linked in `real` mode and the app seeds the dashboard state so you can still visualize recommendations. If validation fails, the API returns a `400` error with a credential-check message.

Security note: the backend uses the real credentials only for validation and does not persist or return the secret access key or session token.

### Verification

1. `GET http://localhost:8000/health` should return `{"status":"ok"}`
2. After linking an account, `GET http://localhost:8000/api/account` should return a profile with `connection_mode` set to `mocked` or `real`
3. In real mode, a bad key should fail cleanly instead of crashing the server
4. After linking, the dashboard and chat should both update from the same backend state

The current real-mode implementation validates AWS credentials in the backend, but it still seeds the demo dashboard dataset rather than reading live EC2/RDS/S3/Lambda inventory. The next iteration would replace the seed step with real `boto3` inventory collection.
