from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth, messaging
import os
import json
import base64
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin
def init_firebase():
    if firebase_admin._apps:
        return firestore.client()
    
    # Try to load from environment variable (base64 encoded)
    service_account_base64 = os.environ.get('FIREBASE_SERVICE_ACCOUNT_BASE64')
    
    if service_account_base64:
        # Decode base64 and parse JSON
        service_account_json = base64.b64decode(service_account_base64).decode('utf-8')
        service_account_dict = json.loads(service_account_json)
        cred = credentials.Certificate(service_account_dict)
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to file (for local development)
        cert_path = os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json')
        if os.path.exists(cert_path):
            cred = credentials.Certificate(cert_path)
            firebase_admin.initialize_app(cred)
        else:
            raise ValueError("No Firebase credentials found. Set FIREBASE_SERVICE_ACCOUNT_BASE64 env variable or provide serviceAccountKey.json")
    
    return firestore.client()

db = init_firebase()

def make_error_response(message, status_code, code=None, details=None):
    """
    Creates a consistent error response format.
    """
    error_response = {
        "status": "error",
        "message": message,
        "statusCode": status_code
    }
    if code:
        error_response["code"] = code
    if details:
        error_response["details"] = details
    return jsonify(error_response), status_code

# Auth decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return make_error_response('Unauthorized', 401)
        try:
            decoded = auth.verify_id_token(token)
            request.user_id = decoded['uid']
        except:
            return make_error_response('Invalid token', 401)
        return f(*args, **kwargs)
    return decorated

# Admin auth decorator
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return make_error_response('Unauthorized', 401)
        try:
            # Token is the admin ID - verify it exists
            admin_doc = db.collection('admins').document(token).get()
            if not admin_doc.exists:
                return make_error_response('Forbidden - Admin access required', 403)
            request.user_id = token
        except Exception as e:
            return make_error_response('Invalid token', 401)
        return f(*args, **kwargs)
    return decorated

# ==================== ORDERS API ====================

@app.route('/api/orders', methods=['GET'])
@require_auth
def get_orders():
    """Get all orders for a user"""
    try:
        orders_ref = db.collection('orders').where('userId', '==', request.user_id).stream()
        orders = [{'id': doc.id, **doc.to_dict()} for doc in orders_ref]
        return jsonify({'orders': orders}), 200
    except Exception as e:
        return make_error_response('Failed to fetch orders', 500)

@app.route('/api/orders', methods=['POST'])
@require_auth
def create_order():
    """Create a new order"""
    try:
        data = request.json
        if not data:
            return make_error_response('Request body cannot be empty', 400)

        items = data.get('items')
        total_amount = data.get('totalAmount')
        delivery_location = data.get('deliveryLocation')

        if not isinstance(items, list) or not items:
            return make_error_response('Order items must be a non-empty list', 400)
        
        for item in items:
            if not isinstance(item, dict) or not item.get('productId') or not item.get('name') or not item.get('quantity') or not item.get('price'):
                return make_error_response('Each item must have productId, name, quantity, and price', 400)
            if not isinstance(item['quantity'], (int, float)) or item['quantity'] <= 0:
                return make_error_response('Item quantity must be a positive number', 400)
            if not isinstance(item['price'], (int, float)) or item['price'] <= 0:
                return make_error_response('Item price must be a positive number', 400)

        if not isinstance(total_amount, (int, float)) or total_amount <= 0:
            return make_error_response('Total amount must be a positive number', 400)
        
        if not isinstance(delivery_location, str) or not delivery_location.strip():
            return make_error_response('Delivery location must be a non-empty string', 400)

        order = {
            'userId': request.user_id,
            'orderId': data.get('orderId'), # Assuming orderId is generated client-side or will be replaced by server-side generation
            'items': items,
            'totalAmount': total_amount,
            'deliveryLocation': delivery_location,
            'status': 'PENDING',
            'timestamp': firestore.SERVER_TIMESTAMP,
            'createdAt': datetime.now().isoformat()
        }

        # If orderId is not provided, generate one (e.g., using Firestore's auto-ID)
        if not order.get('orderId'):
            doc_ref = db.collection('orders').document()
            order['orderId'] = doc_ref.id
            doc_ref.set(order)
        else:
            doc_ref = db.collection('orders').document(order['orderId'])
            doc_ref.set(order)

        return jsonify({'success': True, 'orderId': order['orderId']}), 201
    except Exception as e:
        return make_error_response('Failed to create order', 500, details=str(e))

@app.route('/api/orders/<order_id>', methods=['PUT'])
@require_auth
def update_order(order_id):
    """Update order status"""
    try:
        data = request.json
        if not data:
            return make_error_response('Request body cannot be empty', 400)

        if 'status' in data:
            status = data.get('status')
            valid_statuses = ['PENDING', 'CONFIRMED', 'PREPARING', 'DELIVERING', 'DELIVERED', 'CANCELLED']
            if status not in valid_statuses:
                return make_error_response('Invalid status', 400)

        if 'items' in data:
            items = data.get('items')
            if not isinstance(items, list) or not items:
                return make_error_response('Order items must be a non-empty list', 400)
            for item in items:
                if not isinstance(item, dict) or not item.get('productId') or not item.get('name') or not item.get('quantity') or not item.get('price'):
                    return make_error_response('Each item must have productId, name, quantity, and price', 400)
                if not isinstance(item['quantity'], (int, float)) or item['quantity'] <= 0:
                    return make_error_response('Item quantity must be a positive number', 400)
                if not isinstance(item['price'], (int, float)) or item['price'] <= 0:
                    return make_error_response('Item price must be a positive number', 400)
        
        if 'totalAmount' in data:
            total_amount = data.get('totalAmount')
            if not isinstance(total_amount, (int, float)) or total_amount <= 0:
                return make_error_response('Total amount must be a positive number', 400)
        
        if 'deliveryLocation' in data:
            delivery_location = data.get('deliveryLocation')
            if not isinstance(delivery_location, str) or not delivery_location.strip():
                return make_error_response('Delivery location must be a non-empty string', 400)

        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if not doc.exists or doc.to_dict().get('userId') != request.user_id:
            return make_error_response('Order not found', 404)

        doc_ref.update(data)

        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to update order', 500, details=str(e))

@app.route('/api/orders/<order_id>', methods=['DELETE'])
@require_auth
def delete_order(order_id):
    """Delete/cancel an order"""
    try:
        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if not doc.exists or doc.to_dict().get('userId') != request.user_id:
            return make_error_response('Order not found', 404)
            
        doc_ref.delete()
        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to delete order', 500)

# ==================== ORDER SUBMIT (SEQUENTIAL NUMBERING) ====================

@app.route('/api/order/submit', methods=['POST'])
@require_auth
def submit_order():
    """Submit order and get sequential order number"""
    try:
        data = request.get_json()
        order_data = data.get('order', {})
        
        if not order_data.get('items') or not order_data.get('totalAmount'):
            return make_error_response('Invalid order data', 400, code='INVALID_ORDER_DATA')

        # Use transaction to prevent race condition
        counter_ref = db.collection('system').document('counters')
        
        @firestore.transactional
        def create_order_with_counter(transaction):
            counter_doc = counter_ref.get(transaction=transaction)
            current_count = counter_doc.to_dict().get('orderCounter', 0) if counter_doc.exists else 0
            new_count = current_count + 1
            
            transaction.update(counter_ref, {'orderCounter': new_count})
            
            order_id = f"ORD{new_count}"
            order_data['orderId'] = order_id
            order_data['userId'] = request.user_id
            order_data['timestamp'] = datetime.now().timestamp() * 1000
            order_data['status'] = 'PENDING'
            
            transaction.set(db.collection('orders').document(order_id), order_data)
            return order_id, new_count
        
        transaction = db.transaction()
        order_id, order_number = create_order_with_counter(transaction)

        # Send notification to admin about new order
        try:
            admins = db.collection('admins').stream()
            for admin in admins:
                admin_data = admin.to_dict()
                fcm_token = admin_data.get('fcmToken')
                if fcm_token:
                    message = messaging.Message(
                        data={
                            'notification_type': 'new_order',
                            'order_id': order_id,
                            'title': '🆕 New Order',
                            'body': f'Order {order_id} received - ${order_data.get("totalAmount", 0):.2f}'
                        },
                        android=messaging.AndroidConfig(
                            priority='high'
                        ),
                        token=fcm_token
                    )
                    messaging.send(message)
                    print(f'✅ Admin notification sent for order {order_id}')
        except Exception as e:
            print(f'⚠️ Failed to send admin notification: {e}')
            # Don't fail the order if notification fails

        return jsonify({
            'success': True,
            'orderId': order_id,
            'orderNumber': order_number
        })

    except Exception as e:
        return make_error_response('Failed to submit order', 500, code='ORDER_SUBMISSION_FAILED')

# ==================== PRODUCTS API ====================

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products"""
    try:
        active_only = request.args.get('active', 'true').lower() == 'true'
        limit = min(int(request.args.get('limit', 100)), 100)
        
        products_ref = db.collection('products')
        if active_only:
            products_ref = products_ref.where('isActive', '==', True)
        
        products_ref = products_ref.limit(limit)
        products = [{'id': doc.id, **doc.to_dict()} for doc in products_ref.stream()]

        return jsonify({'products': products}), 200
    except Exception as e:
        return make_error_response('Failed to fetch products', 500)

@app.route('/api/products', methods=['POST'])
@require_auth
def create_product():
    """Create a new product"""
    try:
        data = request.json
        
        if not data.get('name') or not data.get('price') or data['price'] <= 0:
            return make_error_response('Invalid product data', 400)

        category_name = data.get('category')
        if category_name:
            valid_categories = get_cached_categories()
            if not any(cat['name'] == category_name for cat in valid_categories):
                return make_error_response('Invalid category provided', 400)

        product = {
            'name': data['name'],
            'price': data['price'],
            'category': category_name,
            'imageUrl': data.get('imageUrl'),
            'description': data.get('description', ''),
            'inStock': data.get('inStock', True),
            'isActive': data.get('isActive', True),
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        doc_ref = db.collection('products').add(product)
        return jsonify({'success': True, 'productId': doc_ref[1].id}), 201
    except Exception as e:
        return make_error_response('Failed to create product', 500)

@app.route('/api/products/<product_id>', methods=['PUT'])
@require_auth
def update_product(product_id):
    """Update a product"""
    try:
        data = request.json
        if 'price' in data and data['price'] <= 0:
            return make_error_response('Invalid price', 400)

        category_name = data.get('category')
        if category_name:
            valid_categories = get_cached_categories()
            if not any(cat['name'] == category_name for cat in valid_categories):
                return make_error_response('Invalid category provided', 400)

        db.collection('products').document(product_id).update(data)
        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to update product', 500)

@app.route('/api/products/<product_id>', methods=['DELETE'])
@require_auth
def delete_product(product_id):
    """Delete a product"""
    try:
        db.collection('products').document(product_id).delete()
        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to delete product', 500)

# ==================== USERS API ====================

@app.route('/api/users/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """Get user profile"""
    try:
        if user_id != request.user_id:
            return make_error_response('Unauthorized', 403)
            
        doc = db.collection('users').document(user_id).get()
        if doc.exists:
            return jsonify({'user': {'id': doc.id, **doc.to_dict()}}), 200
        return make_error_response('User not found', 404)
    except Exception as e:
        return make_error_response('Failed to fetch user', 500)

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create user profile"""
    try:
        data = request.json
        if not data:
            return make_error_response('Request body cannot be empty', 400)

        user_id = data.get('userId')
        email = data.get('email')
        display_name = data.get('displayName')
        phone_numbers = data.get('phoneNumbers')

        if not isinstance(user_id, str) or not user_id.strip():
            return make_error_response('userId must be a non-empty string', 400)
        
        if not isinstance(email, str) or not email.strip() or '@' not in email or '.' not in email:
            return make_error_response('Email must be a valid non-empty string', 400)
        
        if display_name is not None and not isinstance(display_name, str):
            return make_error_response('displayName must be a string', 400)
        
        if phone_numbers is not None and (not isinstance(phone_numbers, list) or not all(isinstance(num, str) for num in phone_numbers)):
            return make_error_response('phoneNumbers must be a list of strings', 400)

        user = {
            'userId': user_id,
            'email': email,
            'displayName': display_name,
            'phoneNumbers': phone_numbers if phone_numbers is not None else [],
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        db.collection('users').document(user_id).set(user)
        return jsonify({'success': True}), 201
    except Exception as e:
        return make_error_response('Failed to create user', 500, details=str(e))

# ==================== ANALYTICS API ====================

@app.route('/api/analytics/orders', methods=['GET'])
@require_auth
def get_order_analytics():
    """Get order statistics"""
    try:
        orders = list(db.collection('orders').where('userId', '==', request.user_id).stream())

        total_orders = len(orders)
        total_revenue = sum(doc.to_dict().get('totalAmount', 0) for doc in orders)
        status_counts = {}
        
        for doc in orders:
            status = doc.to_dict().get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1

        return jsonify({
            'totalOrders': total_orders,
            'totalRevenue': total_revenue,
            'statusCounts': status_counts
        }), 200
    except Exception as e:
        return make_error_response('Failed to fetch analytics', 500)

# ==================== HEALTH CHECK ====================

@app.route('/', methods=['GET'])
def home():
    """API welcome page"""
    return jsonify({
        'name': 'FRIZZLY API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'orders': '/api/orders',
            'order_submit': '/api/order/submit',
            'products': '/api/products',
            'users': '/api/users',
            'analytics': '/api/analytics/orders',
            'admin': '/api/admin/*'
        },
        'documentation': 'See README.md for full API documentation'
    }), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

# ==================== ADMIN ENDPOINTS ====================

@app.route('/api/admin/orders', methods=['GET'])
@require_admin
def admin_get_all_orders():
    """Get all orders (admin only)"""
    try:
        orders = [{'id': doc.id, **doc.to_dict()} for doc in db.collection('orders').stream()]
        return jsonify({'orders': orders}), 200
    except Exception as e:
        return make_error_response('Failed to fetch orders', 500)

@app.route('/api/admin/orders/<order_id>', methods=['GET'])
@require_admin
def admin_get_order(order_id):
    """Get single order (admin only)"""
    try:
        doc = db.collection('orders').document(order_id).get()
        if doc.exists:
            return jsonify({'order': {'id': doc.id, **doc.to_dict()}}), 200
        return make_error_response('Order not found', 404)
    except Exception as e:
        return make_error_response('Failed to fetch order', 500)

@app.route('/api/admin/orders/<order_id>', methods=['PUT'])
@require_admin
def admin_update_order(order_id):
    """Update order (admin only) - with notifications"""
    try:
        data = request.json
        
        # Get order to find userId
        order_doc = db.collection('orders').document(order_id).get()
        if not order_doc.exists:
            return make_error_response('Order not found', 404)
        
        order_data = order_doc.to_dict()
        user_id = order_data.get('userId')
        
        # Update order
        db.collection('orders').document(order_id).update(data)
        
        # Create notification if status changed
        if 'status' in data and user_id:
            new_status = data['status']
            
            # Status messages
            status_messages = {
                'PENDING': '⏳ Your order is pending confirmation.',
                'CONFIRMED': '✅ Your order has been confirmed!',
                'PREPARING_ORDER': '👨‍🍳 Your order is being prepared!',
                'READY_FOR_PICKUP': '📦 Your order is ready for pickup!',
                'ON_WAY': '🚚 Your order is on the way!',
                'OUT_FOR_DELIVERY': '🚚 Your order is out for delivery!',
                'DELIVERED': '✨ Your order has been delivered!',
                'CANCELLED': '❌ Your order has been cancelled.',
                'RETURNED': '↩️ Your order has been returned.'
            }
            
            title = 'FRIZZLY Order Update'
            body = status_messages.get(new_status, f'Order status: {new_status}')
            
            # Save to Firestore
            notification_data = {
                'userId': user_id,
                'title': title,
                'body': body,
                'type': 'order',
                'orderId': order_id,
                'status': new_status,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'isRead': False
            }
            db.collection('notifications').add(notification_data)
            print(f'✅ Notification saved to Firestore for user {user_id}')
            
            # Send FCM push notification
            try:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    fcm_token = user_doc.to_dict().get('fcmToken')
                    if fcm_token:
                        message = messaging.Message(
                            data={
                                'notification_type': 'order',
                                'order_id': order_id,
                                'status': new_status,
                                'title': title,
                                'body': body
                            },
                            android=messaging.AndroidConfig(
                                priority='high'
                            ),
                            token=fcm_token
                        )
                        response = messaging.send(message)
                        print(f'✅ FCM notification sent to user {user_id}: {response}')
                    else:
                        print(f'⚠️ No FCM token for user {user_id}')
                else:
                    print(f'⚠️ User {user_id} not found in Firestore')
            except Exception as fcm_error:
                print(f'❌ FCM error: {fcm_error}')
                # Don't fail the request if FCM fails
        
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f'❌ Error updating order: {e}')
        import traceback
        traceback.print_exc()
        return make_error_response(str(e), 500)

@app.route('/api/admin/orders/<order_id>', methods=['DELETE'])
@require_admin
def admin_delete_order(order_id):
    """Delete order (admin only)"""
    try:
        db.collection('orders').document(order_id).delete()
        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to delete order', 500)

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_get_all_users():
    """Get all users (admin only) - from Firebase Auth"""
    try:
        # Try Firestore first
        firestore_users = [{'id': doc.id, **doc.to_dict()} for doc in db.collection('users').stream()]
        
        if firestore_users:
            return jsonify({'users': firestore_users}), 200
        
        # Fallback to Firebase Auth
        page = auth.list_users()
        users = []
        for user in page.users:
            users.append({
                'id': user.uid,
                'email': user.email,
                'displayName': user.display_name or 'N/A',
                'phoneNumber': user.phone_number or 'N/A',
                'createdAt': user.user_metadata.creation_timestamp,
                'lastSignIn': user.user_metadata.last_sign_in_timestamp
            })
        
        return jsonify({'users': users}), 200
    except Exception as e:
        print(f"Error fetching users: {e}")
        return make_error_response('Failed to fetch users', 500)

@app.route('/api/admin/users/<user_id>', methods=['GET'])
@require_admin
def admin_get_user(user_id):
    """Get single user details (admin only)"""
    try:
        # Check Firestore for full user profile (includes device info)
        user_doc = db.collection('users').document(user_id).get()
        
        if user_doc.exists:
            # User profile exists in Firestore with all details
            user_data = user_doc.to_dict()
            
            # Convert Firestore Timestamp to milliseconds
            if 'lastLogin' in user_data:
                try:
                    user_data['lastLogin'] = int(user_data['lastLogin'].timestamp() * 1000)
                except:
                    pass
            
            if 'createdAt' in user_data:
                try:
                    user_data['createdAt'] = int(user_data['createdAt'].timestamp() * 1000)
                except:
                    pass
            
            user = {'id': user_doc.id, **user_data}
        else:
            # Fallback to Firebase Auth (basic info only)
            try:
                user_record = auth.get_user(user_id)
                user = {
                    'id': user_record.uid,
                    'email': user_record.email,
                    'displayName': user_record.display_name or 'N/A',
                    'phoneNumber': user_record.phone_number or 'N/A',
                    'phone': user_record.phone_number or 'N/A',
                    'createdAt': user_record.user_metadata.creation_timestamp,
                    'lastSignIn': user_record.user_metadata.last_sign_in_timestamp
                }
            except:
                return make_error_response('User not found', 404)
        
        # Get user's orders
        orders = [{'id': doc.id, **doc.to_dict()} 
                 for doc in db.collection('orders').where('userId', '==', user_id).stream()]
        
        return jsonify({'user': user, 'orders': orders}), 200
    except Exception as e:
        print(f"Error fetching user: {e}")
        return make_error_response('User not found', 404)

@app.route('/api/admin/analytics', methods=['GET'])
@require_admin
def admin_get_analytics():
    """Get analytics (admin only)"""
    try:
        stats = _get_admin_dashboard_stats()
        return jsonify(stats), 200
    except Exception as e:
        return make_error_response('Failed to fetch analytics', 500)

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login - returns admin ID as token"""
    try:
        data = request.json
        if not data:
            return make_error_response('Request body cannot be empty', 400)

        email = data.get('email')
        password = data.get('password')
        
        if not isinstance(email, str) or not email.strip() or '@' not in email or '.' not in email:
            return make_error_response('Email must be a valid non-empty string', 400)
        
        if not isinstance(password, str) or not password.strip():
            return make_error_response('Password must be a non-empty string', 400)
        
        # Query admin by email
        admins = db.collection('admins').where('email', '==', email).limit(1).stream()
        admin_doc = next(admins, None)
        
        if not admin_doc:
            return make_error_response('Invalid credentials', 401)
        
        admin_data = admin_doc.to_dict()
        
        # Verify password
        from werkzeug.security import check_password_hash
        if not check_password_hash(admin_data['password'], password):
            return make_error_response('Invalid credentials', 401)
        
        # Return admin ID as token (simple approach)
        return jsonify({
            'success': True,
            'token': admin_doc.id,  # Use admin ID as token
            'adminId': admin_doc.id,
            'email': admin_data['email'],
            'name': admin_data.get('name', '')
        }), 200
    except Exception as e:
        return make_error_response('Login failed', 500, details=str(e))

@app.route('/api/admin/fcm-token', methods=['POST'])
@require_admin
def save_admin_fcm_token():
    """Save FCM token for admin"""
    try:
        data = request.json
        token = data.get('token')
        
        if not token:
            return make_error_response('Token required', 400)
        
        # Save token to admin document
        db.collection('admins').document(request.user_id).update({
            'fcmToken': token,
            'fcmTokenUpdated': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to save token', 500)

def _get_admin_dashboard_stats():
    """Helper function to get admin dashboard statistics"""
    orders = list(db.collection('orders').stream())
    total_orders = len(orders)
    total_revenue = sum(doc.to_dict().get('totalAmount', 0) for doc in orders)
    status_counts = {}
    
    for doc in orders:
        status = doc.to_dict().get('status', 'UNKNOWN')
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        'totalOrders': total_orders,
        'totalRevenue': total_revenue,
        'statusCounts': status_counts
    }

@app.route('/api/admin/dashboard-stats', methods=['GET'])
@require_admin
def admin_dashboard_stats():
    """Get dashboard statistics (admin only)"""
    try:
        stats = _get_admin_dashboard_stats()
        return jsonify(stats), 200
    except Exception as e:
        return make_error_response('Failed to fetch dashboard statistics', 500)

# ==================== CATEGORY API ====================

# Simple in-memory cache for categories
category_cache = {
    "data": [],
    "last_updated": None,
    "ttl": 300 # Time to live in seconds (5 minutes)
}

def get_cached_categories():
    now = datetime.now()
    if category_cache["last_updated"] and (now - category_cache["last_updated"]).total_seconds() < category_cache["ttl"]:
        return category_cache["data"]
    
    # Fetch from Firestore
    categories_ref = db.collection('categories').stream()
    categories = [{'id': doc.id, **doc.to_dict()} for doc in categories_ref]
    
    category_cache["data"] = categories
    category_cache["last_updated"] = now
    return categories

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all product categories (cached)"""
    try:
        categories = get_cached_categories()
        return jsonify({'categories': categories}), 200
    except Exception as e:
        return make_error_response('Failed to fetch categories', 500)

@app.route('/api/admin/categories', methods=['POST'])
@require_admin
def create_category():
    """Create a new category (admin only)"""
    try:
        data = request.json
        name = data.get('name')
        
        if not name:
            return make_error_response('Category name required', 400)
        
        # Check if category already exists
        existing_category = db.collection('categories').where('name', '==', name).limit(1).get()
        if len(existing_category) > 0:
            return make_error_response('Category with this name already exists', 409) # Conflict
            
        category = {
            'name': name,
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection('categories').add(category)
        
        # Invalidate cache
        category_cache["last_updated"] = None
        
        return jsonify({'success': True, 'categoryId': doc_ref[1].id}), 201
    except Exception as e:
        return make_error_response('Failed to create category', 500)

@app.route('/api/admin/categories/<category_id>', methods=['PUT'])
@require_admin
def update_category(category_id):
    """Update a category (admin only)"""
    try:
        data = request.json
        name = data.get('name')
        
        if not name:
            return make_error_response('Category name required', 400)
            
        doc_ref = db.collection('categories').document(category_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return make_error_response('Category not found', 404)
            
        # Check if new name already exists for another category
        existing_category = db.collection('categories').where('name', '==', name).limit(1).get()
        for cat in existing_category:
            if cat.id != category_id:
                return make_error_response('Category with this name already exists', 409) # Conflict
        
        doc_ref.update({
            'name': name,
            'updatedAt': firestore.SERVER_TIMESTAMP
        })
        
        # Invalidate cache
        category_cache["last_updated"] = None
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to update category', 500)

@app.route('/api/admin/categories/<category_id>', methods=['DELETE'])
@require_admin
def delete_category(category_id):
    """Delete a category (admin only)"""
    try:
        doc_ref = db.collection('categories').document(category_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return make_error_response('Category not found', 404)
            
        # Optional: Check if any products are linked to this category before deleting
        # products_with_category = db.collection('products').where('category', '==', category_id).limit(1).get()
        # if len(products_with_category) > 0:
        #     return make_error_response('Cannot delete category with associated products', 409)
            
        doc_ref.delete()
        
        # Invalidate cache
        category_cache["last_updated"] = None
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return make_error_response('Failed to delete category', 500)

# ==================== SSE (Server-Sent Events) ====================

@app.route('/api/admin/stream/orders')
@require_admin
def stream_orders():
    """Real-time order updates via Server-Sent Events"""
    from flask import Response
    import queue
    import threading
    
    message_queue = queue.Queue()
    
    def on_snapshot(col_snapshot, changes, read_time):
        """Firestore snapshot callback"""
        for change in changes:
            if change.type.name in ['ADDED', 'MODIFIED']:
                doc = change.document
                data = doc.to_dict()
                event_data = {
                    'id': doc.id,
                    'orderId': data.get('orderId', doc.id),
                    'totalAmount': data.get('totalAmount', 0),
                    'status': data.get('status', 'PENDING'),
                    'timestamp': data.get('timestamp', 0),
                    'type': 'new_order' if change.type.name == 'ADDED' else 'order_update'
                }
                message_queue.put(event_data)
    
    # Start Firestore listener
    col_query = db.collection('orders').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50)
    doc_watch = col_query.on_snapshot(on_snapshot)
    
    def generate():
        try:
            # Send connection message
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            
            while True:
                try:
                    # Get message from queue (30s timeout)
                    event_data = message_queue.get(timeout=30)
                    event_type = event_data.pop('type', 'message')
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                except queue.Empty:
                    # Send heartbeat
                    yield f": heartbeat\n\n"
        except GeneratorExit:
            doc_watch.unsubscribe()
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/admin/orders/recent')
@require_admin
def get_recent_orders():
    """Get recent orders for polling fallback"""
    try:
        orders_ref = db.collection('orders').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        orders = []
        for doc in orders_ref:
            data = doc.to_dict()
            data['id'] = doc.id
            orders.append(data)
        return jsonify({'orders': orders}), 200
    except Exception as e:
        return make_error_response('Failed to fetch recent orders', 500)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
