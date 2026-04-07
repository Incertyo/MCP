# Vercel Deployment Guide - Cloud Optimizer MCP

This guide walks you through deploying the Cloud Optimizer MCP application to Vercel, with both the FastAPI backend and React frontend.

## Prerequisites

Before you begin, ensure you have:

1. **Vercel Account**
   - Sign up at [vercel.com](https://vercel.com)
   - Free tier is sufficient for this demo

2. **Git Repository**
   - Your project must be in a Git repository (GitHub, GitLab, or Bitbucket)
   - Push your code to your preferred platform
   - Example: `git init` → `git add .` → `git commit -m "Initial commit"` → `git push`

3. **Tools Installed**
   - Git CLI
   - Node.js 18+ (for Vercel CLI, optional but recommended)
   - Python 3.11+ (local development, not needed for deployment)

4. **Environment Variables Ready**
   - AWS credentials (if using real AWS mode)
   - Datadog API key (optional, for observability)
   - Gemini API key or other LLM credentials (optional, for chat features)

---

## Part 1: Backend Deployment (FastAPI on Vercel)

### Step 1: Prepare the Backend

Your `vercel.json` is already configured correctly:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "index.py"
    }
  ]
}
```

Ensure your [backend/index.py](backend/index.py) exists and imports/starts your FastAPI app:

```python
from app.main import create_app

app = create_app()
```

### Step 2: Create a Vercel Project for Backend

**Option A: Using Vercel Dashboard**

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click "Select Git Repository"
3. Search for and select your repository
4. **Important**: Under "Project Settings":
   - Set **Root Directory** to `./backend`
   - Framework should be auto-detected or left as "Other" (Python)
5. Click "Deploy"

**Option B: Using Vercel CLI**

```powershell
# Install Vercel CLI (if not already installed)
npm i -g vercel

# Navigate to backend directory
cd backend

# Deploy
vercel --prod

# Follow prompts:
# - Link to existing project or create new
# - Set root directory to current directory
# - Confirm deployment
```

### Step 3: Configure Backend Environment Variables

1. Go to Vercel Dashboard → Your Backend Project → Settings → Environment Variables
2. Add these variables (adjust based on your setup):

```
ENVIRONMENT=production
FRONTEND_ORIGIN=https://cloud-optimizer-mcp-frontend.vercel.app
AWS_REGION=us-east-1
AWS_PROFILE=default
```

**If using real AWS mode:**
```
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
```

**If using Datadog:**
```
DATADOG_API_KEY=<your-key>
DATADOG_SITE=us5.datadoghq.com
```

**If using Gemini or other LLM:**
```
GOOGLE_API_KEY=<your-key>
```

3. Click "Save" after adding each variable
4. Vercel automatically redeploys with new variables

### Step 4: Verify Backend URL

After deployment:
1. Visit your backend URL (shown in Vercel Dashboard, e.g., `https://cloud-optimizer-mcp-backend.vercel.app`)
2. Test the health endpoint: `https://<your-backend>.vercel.app/health`
3. Verify CORS is working: The backend dashboard URLs are already whitelisted

---

## Part 2: Frontend Deployment (React + Vite on Vercel)

### Step 1: Verify Frontend Configuration

Check [frontend/vite.config.ts](frontend/vite.config.ts) - it should be standard:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
```

Your [frontend/package.json](frontend/package.json) has the correct build script:
```json
{
  "scripts": {
    "build": "vite build",
    "dev": "vite"
  }
}
```

### Step 2: Create a Vercel Project for Frontend

**Option A: Using Vercel Dashboard**

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click "Select Git Repository"
3. Search for and select your repository
4. **Important**: Under "Project Settings":
   - Set **Root Directory** to `./frontend`
   - Framework should auto-detect as "Vite"
   - Build Command: `vite build`
   - Output Directory: `dist`
5. Click "Deploy"

**Option B: Using Vercel CLI**

```powershell
# Navigate to frontend directory
cd frontend

# Deploy
vercel --prod

# Follow prompts to link project and confirm deployment
```

### Step 3: Configure Frontend Environment Variables

1. Go to Vercel Dashboard → Your Frontend Project → Settings → Environment Variables

2. Add **Production Environment** variables:

```
VITE_API_BASE=https://<your-backend-project>.vercel.app/api
```

Replace `<your-backend-project>` with your actual backend project name.

**Example:**
```
VITE_API_BASE=https://cloud-optimizer-mcp-backend.vercel.app/api
```

3. Add **Preview/Development Environment** variables (optional):

```
VITE_API_BASE=https://<your-backend-project>.vercel.app/api
```

4. Click "Save"
5. Vercel automatically redeploys with new variables

### Step 4: Verify Frontend Build

Check that the build succeeded:
1. In Vercel Dashboard, go to your Frontend Project → Deployments
2. Look for the latest deployment with a ✅ green checkmark
3. Click on it to view build logs
4. Should see: `✓ Build completed, 123 files generated`

---

## Part 3: Testing the Deployment

### 1. Test Frontend Access

1. Open your frontend URL: `https://<your-frontend-project>.vercel.app`
2. Should see the Cloud Optimizer UI (if running in mock mode)
3. Check browser console for any errors: F12 → Console tab

### 2. Test API Connectivity

1. In browser console, run:
```javascript
fetch('https://<your-backend-project>.vercel.app/api/dashboard')
  .then(r => r.json())
  .then(data => console.log('API works:', data))
  .catch(e => console.error('API error:', e))
```

2. Should see dashboard data in the console

### 3. Test CORS

The backend CORS middleware is already configured to allow:
- Your frontend Vercel domain (auto-detected via regex)
- `http://localhost:5173` and `http://127.0.0.1:5173` (local dev)

If you get CORS errors:
1. Verify `FRONTEND_ORIGIN` env var matches your frontend URL
2. Wait 5 minutes for Vercel to fully deploy updated vars

### 4. Functional Testing

- Create a mock AWS account (no real credentials needed)
- View dashboard and recommendations
- Send a chat message to test agent
- Accept/reject recommendations

---

## Part 4: Environment Variable Reference

### Backend Environment Variables

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `ENVIRONMENT` | `development` | Deployment environment | ❌ |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Frontend URL for CORS | ✅ Production |
| `AWS_REGION` | `us-east-1` | AWS region | ❌ |
| `AWS_PROFILE` | `default` | AWS profile name | ❌ |
| `AWS_ACCESS_KEY_ID` | (none) | AWS access key (real mode) | ❌ |
| `AWS_SECRET_ACCESS_KEY` | (none) | AWS secret key (real mode) | ❌ |
| `GOOGLE_API_KEY` | (none) | Gemini API key | ❌ |
| `DATADOG_API_KEY` | (none) | Datadog API key | ❌ |
| `MCP_API_KEY` | (none) | Optional MCP endpoint security | ❌ |

### Frontend Environment Variables

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `VITE_API_BASE` | `{window.location.origin}/api` | Backend API base URL | ❌ |

---

## Part 5: Special Configurations & Troubleshooting

### CORS Issues

**Problem**: Frontend shows "CORS error" or request blocked

**Solution**:
1. Verify `FRONTEND_ORIGIN` backend env var matches your frontend URL exactly
2. Check in [backend/app/main.py](backend/app/main.py) - CORS is configured to allow:
   - Exact match: `settings.frontend_origin`
   - Local dev: `http://localhost:5173` and `http://127.0.0.1:5173`
   - Vercel preview: `https://cloud-optimizer-mcp-frontend-*.vercel.app` (regex)
3. Redeploy backend after changing vars: Push to git or redeploy in Vercel Dashboard

### API Base URL Issues

**Problem**: Frontend shows 404 or connection errors

**Solution**:
1. In Vercel Dashboard → Frontend Project → Settings → Environment Variables
2. Verify `VITE_API_BASE` is set to your backend URL
3. Example: `https://cloud-optimizer-mcp-backend.vercel.app/api`
4. Redeploy frontend after changes

### Deployment Failures

**Python Build Errors**:
1. Check [backend/requirements.txt](backend/requirements.txt) has no syntax errors
2. Vercel automatically handles `pip install`
3. View Vercel build logs for details

**Node Build Errors**:
1. Check [frontend/package.json](frontend/package.json) has valid JSON
2. Ensure dependencies are listed correctly
3. View Vercel build logs

### Cold Starts & Performance

Vercel Serverless Functions have a ~1 second cold start. This is expected and not a problem.
- Subsequent requests are faster (~50ms)
- Consider the free tier's limitations: 6GB total bandwidth, 1000 function invocations

---

## Part 6: Post-Deployment Checklist

- [ ] Backend deployed and accessible
- [ ] Frontend deployed and accessible
- [ ] `VITE_API_BASE` environment variable set on frontend
- [ ] `FRONTEND_ORIGIN` environment variable set on backend
- [ ] Frontend loads without console errors
- [ ] API requests from frontend work (no 403 CORS errors)
- [ ] Mock AWS mode works (dashboard, recommendations, chat)
- [ ] Real AWS mode works (if using credentials)
- [ ] Chat send/receive works
- [ ] Recommendations accept/reject actions work

---

## Part 7: Updating After Deployment

### To update the frontend:
```powershell
# Make changes in /frontend
git add .
git commit -m "Update frontend"
git push
# Vercel automatically deploys
```

### To update the backend:
```powershell
# Make changes in /backend
git add .
git commit -m "Update backend"
git push
# Vercel automatically deploys
```

### To change environment variables:
1. Go to Vercel Dashboard
2. Navigate to Project Settings → Environment Variables
3. Update the value
4. Vercel automatically redeploys with new variables

---

## Quick Reference: Vercel Project Setup

### Backend Project
- **Root Directory**: `./backend`
- **Framework**: Python / Vercel Python
- **Build Command**: (automatic)
- **Output Directory**: (not applicable)
- **Environment Variables**: See Part 4

### Frontend Project
- **Root Directory**: `./frontend`
- **Framework**: Vite
- **Build Command**: `vite build`
- **Output Directory**: `dist`
- **Environment Variables**: `VITE_API_BASE=<backend-url>`

---

## Support & Resources

- **Vercel Python Docs**: https://vercel.com/docs/functions/serverless-functions/python
- **Vercel Frontend Docs**: https://vercel.com/docs/frameworks/vite
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Vite Docs**: https://vitejs.dev/guide/
- **Your Project**: [Cloud Optimizer MCP](https://github.com/yourusername/yourrepo)

---

## Current Deployment Status

Based on PROJECT_DESCRIPTION.md, your app is already deployed at:

- **Frontend**: https://cloud-optimizer-mcp-frontend.vercel.app
- **Backend**: https://cloud-optimizer-mcp-backend.vercel.app

If these are outdated or you need to deploy to a new project, follow the steps above from the beginning.
