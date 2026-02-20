# Railway Deployment - Direct Python (Free Tier Optimized)

## Setup

### 1. Create railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn flask_app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 60",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### 2. Update requirements.txt
Add gunicorn:
```
flask==3.0.0
flask-cors==4.0.0
firebase-admin==6.4.0
python-dotenv==1.0.0
gunicorn==21.2.0
```

### 3. Set Environment Variables in Railway

In Railway dashboard:
- `FIREBASE_SERVICE_ACCOUNT_BASE64` = (paste your base64 key)
- `PORT` = (Railway sets this automatically)

### 4. Deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up
```

---

## Cost Optimization Tips

### 1. Use 1 Worker (Not 4)
```python
# In railway.json
"startCommand": "gunicorn flask_app:app --workers 1 --threads 2"
```

### 2. Add Sleep on Idle
Railway sleeps inactive apps automatically - this is FREE!

### 3. Reduce Memory Usage
```python
# Add to flask_app.py
import gc
gc.set_threshold(700, 10, 10)  # Aggressive garbage collection
```

### 4. Use Lightweight Server
Gunicorn is lighter than uWSGI or Waitress.

---

## Expected Costs (Free Tier)

**With $5/month credit:**
- Direct Python: ~$1-2/month = **3-5 months free**
- Docker: ~$3-4/month = **1-2 months free**

**Recommendation: Direct Python = 3x longer free usage!**

---

## Alternative: Fly.io (Better Free Tier)

Fly.io offers:
- 3 VMs free (256MB each)
- 160GB bandwidth free
- **Truly free forever** (no credit expiry)

```bash
# Deploy to Fly.io instead
fly launch
fly deploy
```

---

## Quick Deploy to Railway

```bash
cd ~/AndroidStudioProjects/API_FRIZZLY

# 1. Add gunicorn
echo "gunicorn==21.2.0" >> requirements.txt

# 2. Create railway.json (see above)

# 3. Push to GitHub
git init
git add .
git commit -m "Initial commit"
git push

# 4. In Railway dashboard:
# - New Project → Deploy from GitHub
# - Add environment variable: FIREBASE_SERVICE_ACCOUNT_BASE64
# - Deploy!
```

**Cost: ~$1-2/month = 3-5 months free with $5 credit**
