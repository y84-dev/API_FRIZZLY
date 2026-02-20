# Firebase Credentials - Environment Variable Setup

## ⚠️ NEVER commit serviceAccountKey.json to GitHub!

Add to `.gitignore`:
```
serviceAccountKey.json
*.base64.txt
.env
```

---

## Option 1: Base64 Environment Variable (Recommended)

### Step 1: Encode the key
```bash
cd ~/AndroidStudioProjects/API_FRIZZLY
./encode_key.sh
```

This creates `serviceAccountKey.base64.txt` with the encoded key.

### Step 2: Set environment variable

**Local development (.env file):**
```bash
# Create .env file
echo "FIREBASE_SERVICE_ACCOUNT_BASE64='$(cat serviceAccountKey.base64.txt)'" > .env
```

**Production (Fly.io):**
```bash
fly secrets set FIREBASE_SERVICE_ACCOUNT_BASE64="$(cat serviceAccountKey.base64.txt)"
```

**Production (Railway):**
```bash
# In Railway dashboard: Variables tab
# Add: FIREBASE_SERVICE_ACCOUNT_BASE64 = <paste content>
```

**Production (Render):**
```bash
# In Render dashboard: Environment tab
# Add: FIREBASE_SERVICE_ACCOUNT_BASE64 = <paste content>
```

### Step 3: Load .env in development

Install python-dotenv:
```bash
pip install python-dotenv
```

Add to top of `flask_app.py`:
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

---

## Option 2: Individual Environment Variables

Set each field separately:

```bash
export FIREBASE_PROJECT_ID="frizzly-9a65f"
export FIREBASE_PRIVATE_KEY_ID="..."
export FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
export FIREBASE_CLIENT_EMAIL="firebase-adminsdk-...@frizzly-9a65f.iam.gserviceaccount.com"
export FIREBASE_CLIENT_ID="..."
```

Then modify `flask_app.py`:
```python
service_account_dict = {
    "type": "service_account",
    "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
    "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.environ.get('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
    # ... other fields
}
```

---

## Option 3: Secret Management Service

**For production, use:**
- AWS Secrets Manager
- Google Secret Manager
- HashiCorp Vault
- Doppler

---

## Testing

### Test with environment variable:
```bash
export FIREBASE_SERVICE_ACCOUNT_BASE64="$(base64 -w 0 serviceAccountKey.json)"
python3 flask_app.py
```

### Test without (fallback to file):
```bash
unset FIREBASE_SERVICE_ACCOUNT_BASE64
python3 flask_app.py
```

---

## Deployment Checklist

- [ ] Add `serviceAccountKey.json` to `.gitignore`
- [ ] Encode key to base64
- [ ] Set environment variable in deployment platform
- [ ] Test API starts successfully
- [ ] Delete `serviceAccountKey.json` from repository (if already committed)
- [ ] Delete `serviceAccountKey.base64.txt` (don't commit this either!)

---

## Security Notes

✅ **DO:**
- Use environment variables
- Use secret management services
- Rotate keys regularly
- Use different keys for dev/staging/prod

❌ **DON'T:**
- Commit serviceAccountKey.json
- Share keys in chat/email
- Hardcode keys in code
- Use production keys in development

---

## Quick Setup

```bash
# 1. Encode key
cd ~/AndroidStudioProjects/API_FRIZZLY
./encode_key.sh

# 2. Create .env file
echo "FIREBASE_SERVICE_ACCOUNT_BASE64='$(cat serviceAccountKey.base64.txt)'" > .env

# 3. Install dotenv
pip install python-dotenv

# 4. Add to .gitignore
echo "serviceAccountKey.json" >> .gitignore
echo "*.base64.txt" >> .gitignore
echo ".env" >> .gitignore

# 5. Test
python3 flask_app.py
```

Done! Your API now loads credentials from environment variables.
