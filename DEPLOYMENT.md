# FRIZZLY API - PythonAnywhere Deployment Guide

## Step 1: Create PythonAnywhere Account
1. Go to https://www.pythonanywhere.com
2. Sign up for FREE account (no credit card needed)
3. Choose username (e.g., `frizzly`)

---

## Step 2: Upload Files

### Via Web Interface:
1. Go to **Files** tab
2. Create directory: `/home/YOUR_USERNAME/frizzly-api`
3. Upload these files:
   - `flask_app.py`
   - `serviceAccountKey.json` (from Firebase Console)
   - `requirements.txt`

### Via Bash Console (Alternative):
```bash
cd ~
mkdir frizzly-api
cd frizzly-api
# Upload files using "Upload a file" button
```

---

## Step 3: Install Dependencies

1. Go to **Consoles** tab
2. Start a **Bash console**
3. Run:

```bash
cd ~/frizzly-api
pip3.8 install --user flask flask-cors firebase-admin
```

---

## Step 4: Configure Web App

1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration**
4. Select **Python 3.8**
5. Click **Next**

### Configure WSGI file:
1. Click on WSGI configuration file link
2. **Delete all content**
3. Paste this:

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/YOUR_USERNAME/frizzly-api'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import flask app
from flask_app import app as application
```

4. Replace `YOUR_USERNAME` with your PythonAnywhere username
5. Save file

---

## Step 5: Set Working Directory

1. In **Web** tab, scroll to **Code** section
2. Set **Source code** to: `/home/YOUR_USERNAME/frizzly-api`
3. Set **Working directory** to: `/home/YOUR_USERNAME/frizzly-api`

---

## Step 6: Reload & Test

1. Click green **Reload** button at top
2. Your API will be live at: `https://YOUR_USERNAME.pythonanywhere.com`

Test it:
```
https://YOUR_USERNAME.pythonanywhere.com/
https://YOUR_USERNAME.pythonanywhere.com/api/health
```

---

## Step 7: Update Android App

In your Android app, change the API base URL to:
```kotlin
const val BASE_URL = "https://YOUR_USERNAME.pythonanywhere.com/api"
```

---

## Free Tier Limits:
- ✅ **Always-on** (no sleep)
- ✅ **100k requests/day**
- ✅ **512 MB disk space**
- ✅ **Custom domain** (paid plan)

---

## Troubleshooting:

### Check Error Logs:
1. Go to **Web** tab
2. Click **Error log** link
3. View recent errors

### Common Issues:

**Import Error:**
```bash
# Reinstall dependencies
pip3.8 install --user --force-reinstall flask flask-cors firebase-admin
```

**Firebase Error:**
- Make sure `serviceAccountKey.json` is uploaded
- Check file path in `flask_app.py`

**404 Error:**
- Check WSGI file configuration
- Verify working directory path
- Click Reload button

---

## Update Code:

1. Upload new `flask_app.py` via Files tab
2. Click **Reload** button in Web tab

---

## Your API Endpoints:

```
GET  https://YOUR_USERNAME.pythonanywhere.com/
GET  https://YOUR_USERNAME.pythonanywhere.com/api/health
GET  https://YOUR_USERNAME.pythonanywhere.com/api/orders?userId=xxx
POST https://YOUR_USERNAME.pythonanywhere.com/api/orders
PUT  https://YOUR_USERNAME.pythonanywhere.com/api/orders/{orderId}
DELETE https://YOUR_USERNAME.pythonanywhere.com/api/orders/{orderId}
GET  https://YOUR_USERNAME.pythonanywhere.com/api/products
POST https://YOUR_USERNAME.pythonanywhere.com/api/products
GET  https://YOUR_USERNAME.pythonanywhere.com/api/users/{userId}
POST https://YOUR_USERNAME.pythonanywhere.com/api/users
GET  https://YOUR_USERNAME.pythonanywhere.com/api/analytics/orders
```

---

## Done! 🎉

Your FRIZZLY API is now live and accessible from anywhere!
