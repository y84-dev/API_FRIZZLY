<<<<<<< HEAD
# FRIZZLY API - Fixed Version

## What Was Fixed

### 1. **Authentication & Authorization** ✅
- Added `@require_auth` decorator to all protected endpoints
- Validates Firebase Auth tokens from `Authorization: Bearer <token>` header
- Users can only access their own orders and data

### 2. **Race Condition Fixed** ✅
- Order counter now uses Firestore transactions
- Prevents duplicate order numbers when multiple users submit simultaneously

### 3. **Hardcoded Path Fixed** ✅
- Changed from `/home/yacinedev84/mysite/serviceAccountKey.json`
- Now uses relative path: `os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')`
- Works on any deployment environment

### 4. **Input Validation** ✅
- Validates order amounts (must be > 0)
- Validates product prices (must be > 0)
- Validates order status transitions
- Validates required fields

### 5. **Security Improvements** ✅
- Users can only view/modify their own orders
- Generic error messages (no internal details exposed)
- Status validation (only allowed values)

### 6. **Performance** ✅
- Added pagination limit to products endpoint (max 100)
- Optimized queries

---

## API Usage

### Authentication Required
All endpoints except `/`, `/api/health`, `/api/products` (GET), and `/api/users` (POST) require authentication.

**Add this header to requests:**
```
Authorization: Bearer <firebase_id_token>
```

### Endpoints

#### Public Endpoints
```
GET  /                          - API info
GET  /api/health                - Health check
GET  /api/products              - Get products (limit=100, active=true)
POST /api/users                 - Create user profile
```

#### Protected Endpoints (Require Auth)
```
GET    /api/orders              - Get user's orders
POST   /api/orders              - Create order
PUT    /api/orders/{orderId}    - Update order status
DELETE /api/orders/{orderId}    - Delete order
POST   /api/order/submit        - Submit order with sequential numbering

POST   /api/products            - Create product
PUT    /api/products/{id}       - Update product
DELETE /api/products/{id}       - Delete product

GET    /api/users/{userId}      - Get user profile
GET    /api/analytics/orders    - Get order analytics
```

---

## Android App Integration

### 1. Add Authorization Header

```kotlin
// In your API service/repository
private fun getAuthHeaders(): Map<String, String> {
    val token = FirebaseAuth.getInstance().currentUser?.getIdToken(false)?.result?.token
    return mapOf("Authorization" to "Bearer $token")
}

// Example Retrofit call
@GET("orders")
suspend fun getOrders(
    @HeaderMap headers: Map<String, String>
): Response<OrdersResponse>

// Usage
val orders = apiService.getOrders(getAuthHeaders())
```

### 2. Remove userId from Requests

**Before:**
```kotlin
apiService.getOrders(userId = currentUserId)
```

**After:**
```kotlin
apiService.getOrders(headers = getAuthHeaders())
// userId is extracted from the auth token
```

### 3. Handle 401 Unauthorized

```kotlin
if (response.code() == 401) {
    // Token expired, refresh it
    FirebaseAuth.getInstance().currentUser?.getIdToken(true)
}
```

---

## Deployment to PythonAnywhere

### Update Steps:

1. **Upload new `flask_app.py`** via Files tab
2. **Ensure `serviceAccountKey.json` is in same directory**
3. **Click Reload** in Web tab

### File Structure:
```
/home/YOUR_USERNAME/frizzly-api/
├── flask_app.py
├── serviceAccountKey.json
├── requirements.txt
└── wsgi.py
```

---

## Testing

### Test Authentication:
```bash
# Get Firebase ID token from your app
TOKEN="your_firebase_id_token"

# Test protected endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://YOUR_USERNAME.pythonanywhere.com/api/orders
```

### Test Order Submission:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order": {
      "items": [{"name": "Pizza", "price": 15.99, "quantity": 2}],
      "totalAmount": 31.98,
      "deliveryLocation": "123 Main St"
    }
  }' \
  https://YOUR_USERNAME.pythonanywhere.com/api/order/submit
```

---

## Valid Order Statuses

- `PENDING` - Order placed
- `CONFIRMED` - Restaurant confirmed
- `PREPARING` - Being prepared
- `DELIVERING` - Out for delivery
- `DELIVERED` - Completed
- `CANCELLED` - Cancelled

---

## Error Responses

All errors return JSON:
```json
{
  "error": "Error message"
}
```

**Status Codes:**
- `400` - Bad request (invalid data)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (accessing other user's data)
- `404` - Not found
- `500` - Server error

---

## Migration Notes

### Breaking Changes:
1. **Authentication required** - Update your Android app to send auth tokens
2. **userId removed from query params** - Extracted from auth token
3. **Status validation** - Only valid statuses accepted

### Non-Breaking:
- Products GET endpoint still public
- Order structure unchanged
- Response formats unchanged
=======
# API_FRIZZLY
>>>>>>> af1601d5c28bfed4edb4b2d756a7b9e96989b17e
