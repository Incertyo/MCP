# Vercel Deployment Troubleshooting Guide

Quick solutions for common deployment issues.

## ❌ Deployment Failed in Vercel Dashboard

### Python/Backend Build Failed

**Error**: `ModuleNotFoundError`, `ImportError`, or build error in logs

**Fixes**:
1. Check [backend/requirements.txt](backend/requirements.txt) syntax
   - Each package on new line
   - Format: `package-name>=version,<next-version`
2. Verify [backend/index.py](backend/index.py) exists at root of `/backend` folder
3. Verify [backend/app/__init__.py](backend/app/__init__.py) exists
4. Check Vercel build logs for specific error message
5. Redeploy after fixes: `git push origin main`

**Example fix**:
```powershell
# Make changes
cd backend
git add requirements.txt
git commit -m "Fix requirements"
git push
```

### Node/Frontend Build Failed

**Error**: `npm ERR!`, `ENOENT`, or dependency error in logs

**Fixes**:
1. Check [frontend/package.json](frontend/package.json) is valid JSON
   - Use jsonlint.com to validate
2. Verify dependencies are spelled correctly
3. Check for circular dependencies
4. Delete `node_modules` and `package-lock.json` locally, reinstall:
   ```powershell
   cd frontend
   rm -r node_modules package-lock.json
   npm install
   ```
5. Push updated `package-lock.json` to git
6. Redeploy

---

## ❌ Frontend Loads But Shows API Errors

### Browser Console Shows: "CORS error" or "Access-Control-Allow-Origin"

**Issue**: Frontend can't talk to backend

**Fixes**:

1. **Check `VITE_API_BASE` is set**:
   - Vercel Dashboard → Frontend Project → Settings → Environment Variables
   - Should be: `VITE_API_BASE=https://<your-backend>.vercel.app/api`
   - **Not** `https://<your-backend>.vercel.app` (missing `/api`)

2. **Check `FRONTEND_ORIGIN` on backend**:
   - Vercel Dashboard → Backend Project → Settings → Environment Variables
   - Should be: `FRONTEND_ORIGIN=https://<your-frontend>.vercel.app`
   - Must match your frontend URL exactly

3. **Wait for redeploy**:
   - After changing env vars, Vercel takes 1-2 minutes to redeploy
   - Don't test immediately

4. **Clear browser cache**:
   - In browser, press Ctrl+Shift+Delete
   - Select "All time"
   - Click "Clear data"
   - Refresh the page

5. **Test in incognito mode**:
   - Press Ctrl+Shift+N (ignore cache completely)

### Browser Console Shows: "404 Not Found" or "Cannot GET /api/..."

**Issue**: Wrong API base URL

**Fixes**:

1. Open browser F12 → Network tab
2. Try to load dashboard (reload page)
3. Look for a failed request starting with `/api/`
4. Check the full URL
   - Should be: `https://cloud-optimizer-mcp-backend.vercel.app/api/dashboard`
   - **Not**: `undefined/api/dashboard` or `http://localhost:8000/api/...`

5. Verify frontend env var:
   ```
   VITE_API_BASE=https://cloud-optimizer-mcp-backend.vercel.app/api
   ```

6. If it shows `http://localhost:8000`:
   - You forgot to set the env var
   - Frontend is using the development default
   - Add the env var and redeploy

---

## ❌ "Cannot find module" or Import Errors

### Backend Shows: `ModuleNotFoundError: No module named 'fastapi'`

**Issue**: Dependencies not installed

**Fixes**:
1. Check [backend/requirements.txt](backend/requirements.txt) has all packages:
   ```
   fastapi>=0.110.0,<1
   uvicorn[standard]>=0.24.0,<1
   pydantic>=2.6.0,<3
   boto3>=1.34.0,<2
   requests>=2.31.0,<3
   ```
2. Vercel auto-installs from requirements.txt
3. If still failing, check Vercel build logs for pip errors
4. Try `pip install -r requirements.txt` locally to test

### Frontend Shows: Module not found (in build logs)

**Issue**: Missing dependency or wrong import

**Fixes**:
1. Install locally and test:
   ```powershell
   cd frontend
   npm install
   npm run build
   ```
2. Fix any errors shown locally
3. Check [frontend/package.json](frontend/package.json) includes all dependencies
4. Push fixes and redeploy

---

## ❌ "502 Bad Gateway" or "500 Internal Server Error"

### Backend Returns 502/500

**Issue**: Backend function crashed or times out

**Fixes**:
1. Check Vercel function logs:
   - Vercel Dashboard → Backend Project → Functions
   - Click on a failed function
2. Check for:
   - Import errors (see above)
   - Missing environment variables
   - AWS credential errors (if using real AWS)
   - API key errors (Gemini, Datadog, etc.)
3. Add missing env vars and redeploy
4. Test locally first:
   ```powershell
   cd backend
   python -m uvicorn app.main:app --reload
   ```

---

## ❌ Chat/Agent Requests Fail

### Browser Shows: "Failed to send message" or "Agent error"

**Issue**: Backend agent or LLM not configured

**Fixes**:

1. **Using mock mode** (no LLM needed):
   - Should work automatically
   - Check no errors in console

2. **Using real Gemini**:
   - Add `GOOGLE_API_KEY` env var to backend
   - Must be valid API key from Google Cloud
   - Allow 1-2 min for redeploy

3. **Debug**:
   - Open browser Network tab
   - Send a chat message
   - Look for POST to `/api/chat` or `/api/agent/messages`
   - Check response in Network tab
   - Error details often in response body

---

## ❌ AWS Account Features Don't Work

### "Failed to validate AWS account" or AWS errors

**Issue**: AWS credentials missing or invalid

**Fixes**:

1. **To use mock mode** (recommended):
   - Just click "Use mock AWS account"
   - No credentials needed
   - All features work without real AWS

2. **To use real AWS**:
   - Get AWS Access Key and Secret Key
   - Add to backend env vars:
     ```
     AWS_ACCESS_KEY_ID=AKIA...
     AWS_SECRET_ACCESS_KEY=...
     ```
   - Allow 1-2 min for redeploy
   - Avoid committing credentials to git!

3. **Better**: Use Vercel's authentication:
   - Never put secrets in code
   - Always use Environment Variables in Vercel Dashboard

---

## ✅ Deployment Working but Slow

### Page loads slowly or API requests slow (>2 seconds)

**Normal**:
- First request: 1-2 seconds (cold start)
- Subsequent: 100-300ms (warm)

**Not a problem**: Cold starts are expected on Vercel serverless

**To improve**:
1. Use regional backend (set `AWS_REGION` if using AWS)
2. Optimize database queries
3. Cache responses where possible

---

## ✅ Everything Works! Next Steps

- [ ] Share frontend URL with others
- [ ] Monitor errors in Vercel Dashboard
- [ ] Set up observability if needed (Datadog, etc.)
- [ ] Update [README.md](README.md) with live URLs
- [ ] Configure domain/CNAME if needed (Vercel docs)
- [ ] Set up git branch deployments for preview URLs

---

## Debug Checklist

When something fails, check in this order:

1. **Vercel Dashboard Deployments**
   - Is the latest deployment ✅ green?
   - If red, click to view build logs

2. **Browser Console (F12)**
   - Any red errors?
   - Search for "CORS", "404", "undefined"

3. **Browser Network Tab (F12)**
   - Click a request to your API
   - Check Response tab for errors

4. **Vercel Environment Variables**
   - Backend: `FRONTEND_ORIGIN` set correctly?
   - Frontend: `VITE_API_BASE` set correctly?

5. **Wait for Redeploy**
   - After changing env vars, wait 2-3 minutes
   - Force refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

6. **Local Testing**
   - Run backend locally: `python -m uvicorn app.main:app`
   - Run frontend locally: `npm run dev`
   - Fix issues locally first, then deploy

---

## Still Stuck?

Check the full guide: [VERCEL_DEPLOYMENT_GUIDE.md](VERCEL_DEPLOYMENT_GUIDE.md)

Or refer to official docs:
- Vercel Python: https://vercel.com/docs/functions/serverless-functions/python
- Vercel Vite: https://vercel.com/docs/frameworks/vite
- FastAPI: https://fastapi.tiangolo.com/deployment/concepts/
