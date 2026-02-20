# 🧪 Local Testing Guide

## ✅ Server is Running!

Your API is now running locally at: **http://localhost:8080**

---

## 🚀 Quick Start

### 1. Start the Server
```bash
python3 run_local.py
```

### 2. Run Tests
```bash
bash test_api.sh
```

### 3. Stop the Server
Press `CTRL+C` in the terminal running the server

Or kill it:
```bash
pkill -f "python3 run_local.py"
```

---

## 📡 Test Endpoints

### Public Endpoints (No Auth Required)

```bash
# API Info
curl http://localhost:8080/

# Health Check
curl http://localhost:8080/api/health

# Get Products
curl http://localhost:8080/api/products

# Create User
curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test123",
    "email": "test@example.com",
    "displayName": "Test User"
  }'
```

### Protected Endpoints (Auth Required)

First, get a Firebase ID token from your Android app or Firebase Console.

```bash
# Set your token
TOKEN="your_firebase_id_token_here"

# Get Orders
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/orders

# Submit Order
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order": {
      "items": [
        {"name": "Apple", "price": 2.99, "quantity": 3}
      ],
      "totalAmount": 8.97,
      "deliveryLocation": "123 Main St"
    }
  }' \
  http://localhost:8080/api/order/submit

# Get Analytics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/analytics/orders
```

---

## 🔑 Getting Firebase Token

### From Android App (Kotlin):
```kotlin
FirebaseAuth.getInstance().currentUser?.getIdToken(false)?.addOnSuccessListener { result ->
    val token = result.token
    Log.d("Token", token)
}
```

### From Firebase Console:
1. Go to Firebase Console → Authentication
2. Click on a user
3. Copy the UID
4. Use Firebase Admin SDK to generate custom token

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or use different port in run_local.py
```

### Firebase Connection Issues
- Check `serviceAccountKey.json` exists
- Verify Firebase project ID matches
- Check internet connection

### 401 Unauthorized
- Token expired (tokens expire after 1 hour)
- Invalid token format
- User doesn't exist in Firebase Auth

---

## 📱 Update Android App for Local Testing

In your Android app, change the base URL:

```kotlin
// For local testing
const val BASE_URL = "http://10.0.2.2:8080/api"  // Android Emulator
// OR
const val BASE_URL = "http://YOUR_LOCAL_IP:8080/api"  // Physical Device

// For production
const val BASE_URL = "https://YOUR_USERNAME.pythonanywhere.com/api"
```

**Note:** Android emulator uses `10.0.2.2` to access host machine's localhost.

---

## 📊 View Server Logs

```bash
# Real-time logs
tail -f server.log

# View all logs
cat server.log
```

---

## ✅ What's Working

- ✅ Firebase connection
- ✅ Public endpoints (products, health)
- ✅ Protected endpoints (orders, analytics)
- ✅ Authentication validation
- ✅ Input validation
- ✅ Transaction-based order numbering

---

## 🎯 Next Steps

1. Test with real Firebase tokens from your Android app
2. Verify order submission works
3. Test all CRUD operations
4. Deploy to PythonAnywhere when ready
