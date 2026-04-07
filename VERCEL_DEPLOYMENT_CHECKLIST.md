# Vercel Deployment Quick Start Checklist

Use this checklist for a quick reference during deployment.

## Pre-Deployment (5 minutes)

- [ ] Vercel account created at vercel.com
- [ ] Code pushed to GitHub/GitLab/Bitbucket repository
- [ ] Backend `requirements.txt` valid
- [ ] Frontend `package.json` valid
- [ ] `backend/vercel.json` exists and is correct
- [ ] `backend/index.py` exists and imports the app

## Backend Deployment (10 minutes)

- [ ] Go to vercel.com/new
- [ ] Select your Git repository
- [ ] Set Root Directory to `./backend`
- [ ] Click Deploy
- [ ] Wait for ✅ deployment success
- [ ] Copy backend URL (e.g., `https://cloud-optimizer-mcp-backend.vercel.app`)

## Backend Environment Variables (5 minutes)

In Vercel Dashboard → Backend Project → Settings → Environment Variables:

- [ ] Add `FRONTEND_ORIGIN` = `https://<your-frontend>.vercel.app`
- [ ] Add `ENVIRONMENT` = `production`
- [ ] Add `AWS_REGION` = `us-east-1` (if needed)
- [ ] Add `GOOGLE_API_KEY` = (if using Gemini)
- [ ] Add `DATADOG_API_KEY` = (if using observability)
- [ ] Wait for automatic redeploy (1-2 min)

## Frontend Deployment (10 minutes)

- [ ] Go to vercel.com/new
- [ ] Select your Git repository
- [ ] Set Root Directory to `./frontend`
- [ ] Framework should show "Vite"
- [ ] Click Deploy
- [ ] Wait for ✅ deployment success
- [ ] Copy frontend URL (e.g., `https://cloud-optimizer-mcp-frontend.vercel.app`)

## Frontend Environment Variables (2 minutes)

In Vercel Dashboard → Frontend Project → Settings → Environment Variables:

- [ ] Add `VITE_API_BASE` = `https://<your-backend>.vercel.app/api`
  - Example: `https://cloud-optimizer-mcp-backend.vercel.app/api`
- [ ] Wait for automatic redeploy (1-2 min)

## Testing (5 minutes)

- [ ] Open frontend URL in browser
- [ ] Verify UI loads without errors (check F12 console)
- [ ] Try creating a mock AWS account
- [ ] Try sending a chat message
- [ ] Try accepting/rejecting a recommendation

**If any errors:**
1. Check browser F12 console for CORS errors
2. Verify `VITE_API_BASE` env var on frontend
3. Verify `FRONTEND_ORIGIN` env var on backend
4. Check Vercel build logs for deployment errors

## Total Time: ~35 minutes

---

## URLs After Deployment

| Component | URL |
|-----------|-----|
| Frontend | `https://<your-frontend-project>.vercel.app` |
| Backend API | `https://<your-backend-project>.vercel.app/api` |
| Backend Health | `https://<your-backend-project>.vercel.app/health` |

---

## When Tests Pass ✅

You're done! Your Cloud Optimizer MCP is live.

- Share the frontend URL with others
- Monitor Datadog if configured
- Update README with live URLs

---

## Need Help?

See [VERCEL_DEPLOYMENT_GUIDE.md](VERCEL_DEPLOYMENT_GUIDE.md) for:
- Detailed step-by-step instructions
- Troubleshooting guide
- Environment variable reference
- CORS & API configuration details
