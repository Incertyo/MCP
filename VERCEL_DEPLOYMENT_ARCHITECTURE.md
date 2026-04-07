# Cloud Optimizer MCP - Vercel Deployment Architecture

This document describes the architecture of your deployed application.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User's Web Browser                          │
│                (Chrome, Firefox, Safari, etc.)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTPS (Port 443)
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
 ┌──────────────────┐         ┌──────────────────┐
 │   Vercel CDN     │         │   Vercel CDN     │
 │   (Frontend)     │         │   (Backend API)  │
 └────────┬─────────┘         └────────┬─────────┘
          │                            │
          ▼                            ▼
 ┌──────────────────────┐     ┌──────────────────────┐
 │  React + TypeScript  │     │   FastAPI Python    │
 │  (Vite built)        │     │   (Serverless Func) │
 │  dist/ folder        │     │                     │
 │                      │     │   Routes:           │
 │  Served by Vercel    │     │   - /api/dashboard  │
 │  CDN (static cache)  │     │   - /api/chat       │
 └──────────────────────┘     │   - /api/agent/     │
                              │   - /api/account    │
                              │   - /recommendations│
                              │   - /events         │
                              └──────────┬──────────┘
                                         │
                    CORS Headers         │
                    CHECK required       │
                                         │
                         ┌───────────────┴──────────────┐
                         │                              │
                         ▼ (optional)                   ▼ (optional)
                 ┌──────────────────┐          ┌──────────────────┐
                 │   AWS Services   │          │   Datadog API    │
                 │   (boto3)        │          │   (telemetry)    │
                 │                  │          │                  │
                 │  - EC2 describe  │          │  - Metrics       │
                 │  - Cost Explorer │          │  - Events        │
                 │  - Credentials   │          │  - Logs          │
                 └──────────────────┘          └──────────────────┘
                         ▲                              ▲
                         │                              │
                    Optional: Real                  Optional:
                    AWS mode with                   Observability
                    credentials
```

## Component Details

### 1. Frontend (React + Vite)

**Deployment Target**: Vercel Edge Network (CDN)

**What Gets Deployed**:
- HTML, CSS, JavaScript from `frontend/dist/` after build
- Static assets cached globally
- Automatic caching headers set by Vercel

**Build Process**:
```
vite build
  └─ Compiles TypeScript → JavaScript
  └─ Optimizes React components
  └─ Bundles into dist/
  └─ Ready for CDN distribution
```

**Environment Variables** (at build time):
- `VITE_API_BASE`: Points to backend API base URL
- Baked into JavaScript during build
- Change requires rebuild and redeploy

**Files Deployed**:
```
frontend/dist/
├── index.html          (Entry point)
├── assets/
│   ├── index-xxx.js    (Main app code)
│   ├── vendor-xxx.js   (React, React Router)
│   └── styles-xxx.css  (Compiled CSS)
└── vite.svg            (Assets)
```

### 2. Backend (FastAPI Python)

**Deployment Target**: Vercel Serverless Functions

**What Gets Deployed**:
- Python source code → compiled
- `requirements.txt` → pip installed into function environment
- Function handler: `backend/index.py` → `app`

**Request Flow**:
```
HTTP Request → Vercel Router
           ↓
    Matches: /(.*) → index.py
           ↓
    Python interpreter starts (cold start ~1sec first time)
           ↓
    FastAPI app loads
           ↓
    Route handler executes
           ↓
    Response returned (subsequent calls ~50ms)
```

**Dynamic Endpoints** (computed at request time):
- `/api/dashboard` → Loads recommendations, KPIs, cost data
- `/api/chat` → LLM agent processes messages (Gemini or mock)
- `/api/agent/messages` → Extended agent protocol
- `/api/account` → AWS credential validation
- `/api/recommendations/*` → CRUD operations

**Environment Variables** (at runtime):
- `FRONTEND_ORIGIN`: Verify CORS requests (set on Vercel)
- `AWS_ACCESS_KEY_ID`: AWS credentials (set on Vercel)
- `GOOGLE_API_KEY`: Gemini API key (set on Vercel)
- `DATADOG_API_KEY`: Observability (set on Vercel)

**Cold Start Details**:
- First request: Python interpreter starts, dependencies load (~1-2 sec)
- Subsequent requests: Same container reused (~50ms)
- Timeout: 60 seconds (default Vercel limit)
- Memory: Configurable in `vercel.json` if needed

### 3. CORS (Cross-Origin Resource Sharing)

**Why needed**: Frontend and backend are on different Vercel domains

```
Browser enforces same-origin policy:
  ❌ https://frontend.vercel.app → https://backend.vercel.app
     (different domain = blocked)

Solution: Backend sends CORS headers:
  ✅ Access-Control-Allow-Origin: https://frontend.vercel.app
     (frontend whitelisted = allowed)
```

**Backend Configuration** (in [backend/app/main.py](backend/app/main.py)):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,           # From env var
        "http://localhost:5173",            # Local dev
        "http://127.0.0.1:5173"
    ],
    allow_origin_regex=r"https://cloud-optimizer-mcp-frontend(?:-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Required Setup**:
1. Backend must have `FRONTEND_ORIGIN` env var = your frontend URL
2. Frontend must have `VITE_API_BASE` env var = your backend URL
3. Both must be exact matches (no trailing slashes)

### 4. Data Flow Examples

**Example 1: Loading Dashboard**

```
User clicks "Dashboard" link
    ↓
Frontend calls: GET https://backend.vercel.app/api/dashboard
    ↓
Browser checks CORS:
  - Is origin https://frontend.vercel.app allowed?
  - Check backend's CORS middleware
    ↓
Backend processes:
  1. Load mock/real AWS account data
  2. Compute cost metrics
  3. Generate KPI values
  4. Return JSON
    ↓
Frontend receives JSON
    ↓
React renders dashboard UI
    ↓
User sees charts, recommendations, KPIs
```

**Example 2: Sending Chat Message**

```
User types message + clicks Send
    ↓
Frontend calls: POST https://backend.vercel.app/api/chat
  Body: { message: "Optimize my AWS" }
    ↓
Backend processes:
  1. Check CORS (frontend origin allowed? ✅)
  2. Load chat history from state repository
  3. Call Gemini API or return mock response
  4. Save message and response to state
  5. Return ChatResponse JSON
    ↓
Frontend receives response
    ↓
React updates chat UI with new message
    ↓
User sees AI response
```

## Environment Configuration

### Frontend Environment Variables

Set in: **Vercel Dashboard → Frontend Project → Settings → Environment Variables**

```
VITE_API_BASE=https://cloud-optimizer-mcp-backend.vercel.app/api
```

Used at: **Build time** (Vite compiles this into JavaScript)

**Default fallback** (if not set):
```javascript
const API_BASE = window.location.origin + "/api"
// Would try: https://frontend.vercel.app/api
// ❌ Wrong! That's the frontend API, not backend
```

### Backend Environment Variables

Set in: **Vercel Dashboard → Backend Project → Settings → Environment Variables**

```
FRONTEND_ORIGIN=https://cloud-optimizer-mcp-frontend.vercel.app
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...  (if real AWS mode)
AWS_SECRET_ACCESS_KEY=...  (if real AWS mode)
GOOGLE_API_KEY=...         (if using Gemini)
DATADOG_API_KEY=...        (if using Datadog)
```

Used at: **Runtime** (every request checks these)

## Network Paths

### Public URLs

```
Frontend:  https://cloud-optimizer-mcp-frontend.vercel.app
Backend:   https://cloud-optimizer-mcp-backend.vercel.app
API Base:  https://cloud-optimizer-mcp-backend.vercel.app/api
```

### Internal Vercel Networks (Automatic)

```
Frontend ←→ Backend: Direct HTTPS (via public internet, no private VPC)
           (Vercel provides fast global CDN routing)

Backend ←→ AWS:      Direct HTTPS (boto3 uses AWS SDK)
Backend ←→ Datadog:  Direct HTTPS (telemetry sends metrics)
```

## Security Considerations

### What's Protected

✅ **Environment Variables**:
- Stored encrypted on Vercel servers
- Never exposed in browser or logs
- Only accessible to backend functions

✅ **CORS Headers**:
- Validates requests from allowed origins
- Prevents unauthorized cross-origin requests
- Whitelist regex checks Vercel preview URL patterns

✅ **HTTPS/TLS**:
- All data in transit encrypted
- Automatic SSL certificates via Vercel
- Automatic HTTPS redirects

### What's Exposed

⚠️ **Frontend Source Code**:
- JavaScript visible in browser (minified but readable)
- Should NOT contain secrets
- `VITE_API_BASE` is visible but OK (it's a public URL)

⚠️ **API Endpoints**:
- Backend routes visible in Network tab
- Rate limiting not configured (add if needed)
- No API key authentication (use Bearer tokens if private)

### Best Practices

1. **Never commit secrets**:
   ```powershell
   # ✅ Good
   GOOGLE_API_KEY=abc123 (set in Vercel Dashboard)
   
   # ❌ Bad
   GOOGLE_API_KEY=abc123 (stored in code/git)
   ```

2. **Use Vercel's environment variables**:
   - Secrets encrypted at rest
   - Automatic rotation support
   - Separate production/preview/development vars

3. **Consider API rate limiting**:
   - Add to backend if expecting API abuse
   - FastAPI middleware available

4. **Monitor function logs**:
   - Vercel Dashboard shows errors
   - Don't log sensitive data
   - Use Datadog for production monitoring

## Performance Characteristics

### Cold Start Times

| Request Type | Time | Notes |
|--------------|------|-------|
| (1) First request | 1000-2000ms | Python interpreter starts |
| (2) Warm cache | 50-200ms | Same container reused |
| (3) Cold after 15min idle | 1000-2000ms | Container recycled |

### Bandwidth

| Plan | Limits |
|------|--------|
| Free | 6 GB/month bandwidth |
| Pro | $20/month, 100 GB/month |

For demo/education: Free tier sufficient

### Function Timeouts

| Limit | Value |
|-------|-------|
| Vercel Serverless | 60 seconds default |
| Maximum | 900 seconds (paid) |

Long-running operations should use:
- Background jobs / queues
- Async processing (not recommended here)

## Scaling & Concurrency

### Frontend Scaling

- Automatic: Vercel CDN replicates globally
- No action needed

### Backend Scaling

- Automatic: Vercel creates new function instances
- Concurrent requests: Handled by Vercel's infrastructure
- No configuration needed for demo

---

## Deployment Checklist

- [ ] Frontend deployed to Vercel (React + Vite)
- [ ] Backend deployed to Vercel (FastAPI Python)
- [ ] `backend/vercel.json` correctly configured
- [ ] `VITE_API_BASE` set on frontend
- [ ] `FRONTEND_ORIGIN` set on backend
- [ ] CORS working (no 403 errors)
- [ ] API endpoints responding (test `/api/dashboard`)
- [ ] Mock AWS mode functional
- [ ] Chat/agent working

---

## References

- [Vercel Python Docs](https://vercel.com/docs/functions/serverless-functions/python)
- [Vercel Vite Framework](https://vercel.com/docs/frameworks/vite)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [OWASP CORS Guide](https://owasp.org/www-community/attacks/CORS)
