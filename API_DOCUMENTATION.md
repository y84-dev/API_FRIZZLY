# FRIZZLY API - Complete Endpoint Documentation

## Base URL
- Production: `https://yacinedev84.pythonanywhere.com/api`
- Local: `http://localhost:5000/api`

## Authentication
- **User Auth**: `Authorization: Bearer {firebase_id_token}`
- **Admin Auth**: `Authorization: Bearer {admin_id}`

---

## 📋 PUBLIC ENDPOINTS

### GET `/`
**Welcome page** - API info and available endpoints
- **Auth**: None
- **Response**: API metadata

### GET `/api/health`
**Health check** - Verify API is running
- **Auth**: None
- **Response**: `{ status: 'healthy', timestamp: '...' }`

---

## 🛒 USER ORDER ENDPOINTS

### GET `/api/orders`
**Get user's orders**
- **Auth**: Required (User)
- **Response**: `{ orders: [...] }`

### POST `/api/orders`
**Create order** (legacy - use `/api/order/submit` instead)
- **Auth**: Required (User)
- **Body**: `{ items, totalAmount, deliveryLocation }`
- **Response**: `{ success: true, orderId: '...' }`

### POST `/api/order/submit` ⭐
**Submit order with sequential ID**
- **Auth**: Required (User)
- **Body**: 
```json
{
  "order": {
    "items": [{ "productName", "productPrice", "quantity" }],
    "totalAmount": 100.50,
    "deliveryLocation": { "latitude": 36.7, "longitude": 3.0 }
  }
}
```
- **Response**: `{ success: true, orderId: 'ORD123', orderNumber: 123 }`
- **Features**:
  - ✅ Sequential order numbering (ORD1, ORD2, ORD3...)
  - ✅ Transaction-safe counter
  - ✅ Sends FCM notification to all admins

### PUT `/api/orders/<order_id>`
**Update user's order**
- **Auth**: Required (User - must own order)
- **Body**: `{ status?, items?, totalAmount?, deliveryLocation? }`
- **Response**: `{ success: true }`

### DELETE `/api/orders/<order_id>`
**Delete/cancel user's order**
- **Auth**: Required (User - must own order)
- **Response**: `{ success: true }`

---

## 📦 PRODUCT ENDPOINTS

### GET `/api/products`
**Get all products**
- **Auth**: None
- **Query Params**:
  - `active=true` - Only active products (default: true)
  - `limit=100` - Max results (default: 100, max: 100)
- **Response**: `{ products: [...] }`

### POST `/api/products`
**Create product**
- **Auth**: Required (User)
- **Body**: `{ name, price, category?, imageUrl?, description?, inStock?, isActive? }`
- **Response**: `{ success: true, productId: '...' }`

### PUT `/api/products/<product_id>`
**Update product**
- **Auth**: Required (User)
- **Body**: `{ name?, price?, category?, ... }`
- **Response**: `{ success: true }`

### DELETE `/api/products/<product_id>`
**Delete product**
- **Auth**: Required (User)
- **Response**: `{ success: true }`

---

## 👤 USER ENDPOINTS

### GET `/api/users/<user_id>`
**Get user profile**
- **Auth**: Required (User - must be same user)
- **Response**: `{ user: {...} }`

### POST `/api/users`
**Create user profile**
- **Auth**: None
- **Body**: `{ userId, email, displayName?, phoneNumbers? }`
- **Response**: `{ success: true }`

### GET `/api/analytics/orders`
**Get user's order analytics**
- **Auth**: Required (User)
- **Response**: `{ totalOrders, totalRevenue, statusCounts }`

---

## 🏷️ CATEGORY ENDPOINTS

### GET `/api/categories`
**Get all categories** (cached 5 min)
- **Auth**: None
- **Response**: `{ categories: [...] }`

### POST `/api/admin/categories`
**Create category**
- **Auth**: Required (Admin)
- **Body**: `{ name }`
- **Response**: `{ success: true, categoryId: '...' }`

### PUT `/api/admin/categories/<category_id>`
**Update category**
- **Auth**: Required (Admin)
- **Body**: `{ name }`
- **Response**: `{ success: true }`

### DELETE `/api/admin/categories/<category_id>`
**Delete category**
- **Auth**: Required (Admin)
- **Response**: `{ success: true }`

---

## 👨‍💼 ADMIN ENDPOINTS

### POST `/api/admin/login`
**Admin login**
- **Auth**: None
- **Body**: `{ email, password }`
- **Response**: `{ success: true, token: 'admin_id', adminId, email, name }`

### POST `/api/admin/fcm-token`
**Save admin FCM token for push notifications**
- **Auth**: Required (Admin)
- **Body**: `{ token }`
- **Response**: `{ success: true }`

### GET `/api/admin/orders`
**Get all orders**
- **Auth**: Required (Admin)
- **Response**: `{ orders: [...] }`

### GET `/api/admin/orders/recent`
**Get 10 most recent orders** (for polling)
- **Auth**: Required (Admin)
- **Response**: `{ orders: [...] }`

### GET `/api/admin/orders/<order_id>`
**Get single order**
- **Auth**: Required (Admin)
- **Response**: `{ order: {...} }`

### PUT `/api/admin/orders/<order_id>` ⭐
**Update order status**
- **Auth**: Required (Admin)
- **Body**: `{ status, ... }`
- **Response**: `{ success: true }`
- **Features**:
  - ✅ Updates order in Firestore
  - ✅ Creates notification in `notifications` collection
  - ✅ Sends FCM push notification to user
  - ✅ Status-specific messages

**Status Messages**:
- `PENDING` → "⏳ Your order is pending confirmation."
- `CONFIRMED` → "✅ Your order has been confirmed!"
- `PREPARING_ORDER` → "👨‍🍳 Your order is being prepared!"
- `READY_FOR_PICKUP` → "📦 Your order is ready for pickup!"
- `ON_WAY` → "🚚 Your order is on the way!"
- `OUT_FOR_DELIVERY` → "🚚 Your order is out for delivery!"
- `DELIVERED` → "✨ Your order has been delivered!"
- `CANCELLED` → "❌ Your order has been cancelled."
- `RETURNED` → "↩️ Your order has been returned."

### DELETE `/api/admin/orders/<order_id>`
**Delete order**
- **Auth**: Required (Admin)
- **Response**: `{ success: true }`

### GET `/api/admin/users`
**Get all users**
- **Auth**: Required (Admin)
- **Response**: `{ users: [...] }`
- **Sources**: Firestore `users` collection, fallback to Firebase Auth

### GET `/api/admin/users/<user_id>`
**Get user details + orders**
- **Auth**: Required (Admin)
- **Response**: `{ user: {...}, orders: [...] }`

### GET `/api/admin/analytics`
**Get admin analytics**
- **Auth**: Required (Admin)
- **Response**: `{ totalOrders, totalRevenue, statusCounts }`

### GET `/api/admin/dashboard-stats`
**Get dashboard statistics**
- **Auth**: Required (Admin)
- **Response**: `{ totalOrders, totalRevenue, statusCounts }`

---

## 🔔 NOTIFICATION FLOW

### When User Places Order:
1. User calls `/api/order/submit`
2. API creates order with sequential ID (ORD123)
3. API queries `admins` collection
4. API sends FCM to each admin's `fcmToken`
5. Admin dashboard receives notification

### When Admin Updates Order:
1. Admin calls `/api/admin/orders/<order_id>` with new status
2. API updates order in Firestore
3. API creates notification in `notifications` collection
4. API gets user's `fcmToken` from `users` collection
5. API sends FCM push notification to user
6. User's app receives notification

---

## 📊 DATA MODELS

### Order
```json
{
  "orderId": "ORD123",
  "userId": "firebase_uid",
  "items": [
    {
      "productName": "Apple",
      "productPrice": "$2.50",
      "quantity": 3
    }
  ],
  "totalAmount": 7.50,
  "deliveryLocation": {
    "latitude": 36.7538,
    "longitude": 3.0588
  },
  "status": "PENDING",
  "timestamp": 1708800000000
}
```

### Product
```json
{
  "name": "Apple",
  "price": 2.50,
  "category": "Fruits",
  "imageUrl": "https://...",
  "description": "Fresh red apples",
  "inStock": true,
  "isActive": true,
  "createdAt": "2024-02-24T..."
}
```

### User
```json
{
  "userId": "firebase_uid",
  "email": "user@example.com",
  "displayName": "John Doe",
  "phoneNumbers": ["0551234567"],
  "fcmToken": "fcm_token_here",
  "createdAt": "2024-02-24T..."
}
```

### Admin
```json
{
  "email": "admin@frizzly.com",
  "password": "hashed_password",
  "name": "Admin Name",
  "fcmToken": "fcm_token_here",
  "fcmTokenUpdated": "2024-02-24T..."
}
```

### Notification
```json
{
  "userId": "firebase_uid",
  "title": "FRIZZLY Order Update",
  "body": "✅ Your order has been confirmed!",
  "type": "order",
  "orderId": "ORD123",
  "status": "CONFIRMED",
  "timestamp": "2024-02-24T...",
  "isRead": false
}
```

---

## 🔐 SECURITY

### User Authentication
- Uses Firebase ID tokens
- Verified via `firebase_admin.auth.verify_id_token()`
- User can only access their own data

### Admin Authentication
- Simple token-based (admin document ID)
- Verified by checking `admins` collection
- Full access to all data

### Firestore Rules
- Users can read/write their own orders
- Admins can read/write all data
- Products are publicly readable

---

## ⚡ PERFORMANCE

### Caching
- **Categories**: 5-minute in-memory cache
- Reduces Firestore reads

### Transactions
- **Order counter**: Uses Firestore transactions
- Prevents race conditions for sequential IDs

### Limits
- Products: Max 100 per request
- Recent orders: Max 10

---

## 🚀 DEPLOYMENT

- **Platform**: PythonAnywhere / Railway
- **Environment Variables**:
  - `FIREBASE_SERVICE_ACCOUNT_BASE64` - Base64-encoded service account JSON
- **CORS**: Enabled for all origins

---

## 📝 NOTES

1. **Sequential Order IDs**: Use `/api/order/submit` for ORD1, ORD2, ORD3...
2. **Notifications**: Require FCM tokens saved in Firestore
3. **Admin Auth**: Simple token = admin document ID
4. **Error Format**: `{ status: 'error', message: '...', statusCode: 400 }`
