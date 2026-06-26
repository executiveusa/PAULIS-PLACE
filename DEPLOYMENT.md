# PAULIS-PLACE Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    VERCEL (Frontend)                 │
│  Next.js Dashboard + Observation Center             │
│  URL: https://paulis-place.vercel.app               │
└──────────────────────┬──────────────────────────────┘
                       │ API calls
                       ▼
┌─────────────────────────────────────────────────────┐
│              RAILWAY / RENDER (Backend)               │
│  FastAPI + Celery Worker + Celery Beat               │
│  URL: https://paulis-place-backend.railway.app       │
└──────┬───────────────┬──────────────────────────────┘
       │               │
       ▼               ▼
┌──────────────┐  ┌──────────────────┐
│  Supabase     │  │  Upstash Redis    │
│  (Postgres)   │  │  (Celery broker)  │
└──────────────┘  └──────────────────┘
```

### Why not Vercel for everything?
Vercel is **serverless** — functions spin up, handle a request, then die. Celery workers need to run **continuously**. So:
- **Vercel**: Frontend only (Next.js)
- **Railway/Render**: Backend API + Celery workers (long-running)
- **Supabase**: Postgres database (free tier)
- **Upstash**: Redis for Celery (free tier, serverless Redis)

---

## Step 1: Deploy Frontend to Vercel

### Option A: Vercel Dashboard (easiest)
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import `executiveusa/PAULIS-PLACE`
3. Set:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js
   - **Build Command**: `npm install && npm run build`
   - **Output Directory**: `.next`
4. Add Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```
5. Click **Deploy**

### Option B: Vercel CLI
```bash
npm i -g vercel
cd PAULIS-PLACE
vercel
# Follow prompts, set root to frontend/
```

---

## Step 2: Deploy Backend to Railway

### Railway Setup
1. Go to [railway.app/new](https://railway.app/new)
2. Deploy from GitHub repo `executiveusa/PAULIS-PLACE`
3. Set **Root Directory**: `backend`
4. Set **Start Command**: 
   ```
   python start.py
   ```
5. Add Environment Variables (from your `.env`):
   ```
   DATABASE_URL=postgresql://... (from Supabase)
   REDIS_URL=redis://... (from Upstash)
   GROQ_API_KEY=gsk_...
   OPENROUTER_API_KEY=sk-or-v1-...
   OPENAI_API_KEY=sk-...
   APP_URL=https://paulis-place.vercel.app
   SECRET_KEY=your-secret
   CREEM_API_KEY=...
   ETSY_API_KEY=...
   REPLICATE_API_TOKEN=...
   ```

### Add Redis (Upstash)
1. Go to [upstash.com](https://upstash.com) → Create Redis database
2. Copy the `REDIS_URL`
3. Add it to Railway env vars

### Add Postgres (Supabase)
1. Go to [supabase.com](https://supabase.com) → New project
2. Settings → Database → Connection string
3. Copy the `DATABASE_URL`
4. Add it to Railway env vars

---

## Step 3: Deploy Celery Workers

### On Railway (separate service)
1. In your Railway project, click **New Service** → **GitHub Repo**
2. Select `PAULIS-PLACE` again
3. Set **Root Directory**: `backend`
4. Set **Start Command**:
   ```
   python start_worker.py
   ```
5. Add the same env vars as the backend

### For Celery Beat (scheduler)
1. Another Railway service
2. **Start Command**:
   ```
   celery -A workers.celery_app beat -l info
   ```

---

## Step 4: Run Migrations

After backend is deployed:
```bash
# Railway CLI
railway run python -c "from models.base import Base, engine; Base.metadata.create_all(bind=engine)"
railway run python scripts/seed_data.py
```

Or via the API:
```bash
curl -X POST https://your-backend-url.railway.app/api/trigger/boot
```

---

## Step 5: Connect Frontend to Backend

1. In Vercel, go to your project → Settings → Environment Variables
2. Set `NEXT_PUBLIC_API_URL` to your Railway backend URL
3. Redeploy

---

## Step 6: Watch the Workers

### Option A: Observation Center UI
Once both are deployed:
```
https://paulis-place.vercel.app/observation
```
This shows real-time agent activity, costs, and council debates.

### Option B: Railway Logs
```bash
railway logs --service backend
railway logs --service celery-worker
```

### Option C: API Endpoints
```bash
# Health check
curl https://your-backend-url.railway.app/api/health

# Cost report
curl https://your-backend-url.railway.app/api/research-lab/costs

# Memory stats
curl https://your-backend-url.railway.app/api/memory/stats

# Task summary
curl https://your-backend-url.railway.app/api/tasks/summary
```

---

## Quick Deploy Checklist

- [ ] Create Supabase project → get `DATABASE_URL`
- [ ] Create Upstash Redis → get `REDIS_URL`
- [ ] Deploy backend to Railway → get backend URL
- [ ] Add all env vars to Railway
- [ ] Deploy frontend to Vercel → set `NEXT_PUBLIC_API_URL`
- [ ] Deploy Celery worker to Railway (separate service)
- [ ] Deploy Celery beat to Railway (separate service)
- [ ] Run `POST /api/trigger/boot` to initialize
- [ ] Open `/observation` to watch agents work

---

## Cost Estimate

| Service | Free Tier | Paid (if needed) |
|---------|-----------|------------------|
| Vercel | ✅ Hobby plan | $20/mo Pro |
| Railway | $5 credit/mo | $5+ usage |
| Supabase | ✅ 500MB DB | $25/mo Pro |
| Upstash | ✅ 10k req/day | $10/mo |
| Groq | ✅ Free LLM | - |
| **Total** | **$0/mo** | **~$35/mo** |
