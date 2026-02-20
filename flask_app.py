from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth
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

# Auth decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Unauthorized'}), 401
        try:
            decoded = auth.verify_id_token(token)
            request.user_id = decoded['uid']
        except:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

# Admin auth decorator
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Unauthorized'}), 401
        try:
            # Token is the admin ID - verify it exists
            admin_doc = db.collection('admins').document(token).get()
            if not admin_doc.exists:
                return jsonify({'error': 'Forbidden - Admin access required'}), 403
            request.user_id = token
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
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
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/orders', methods=['POST'])
@require_auth
def create_order():
    """Create a new order"""
    try:
        data = request.json
        if not data.get('items') or not data.get('totalAmount'):
            return jsonify({'error': 'Invalid order data'}), 400
        
        if data['totalAmount'] <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        order = {
            'userId': request.user_id,
            'orderId': data.get('orderId'),
            'items': data['items'],
            'totalAmount': data['totalAmount'],
            'deliveryLocation': data.get('deliveryLocation'),
            'status': 'PENDING',
            'timestamp': firestore.SERVER_TIMESTAMP,
            'createdAt': datetime.now().isoformat()
        }

        doc_ref = db.collection('orders').document(order['orderId'])
        doc_ref.set(order)

        return jsonify({'success': True, 'orderId': order['orderId']}), 201
    except Exception as e:
        return jsonify({'error': 'Failed to create order'}), 500

@app.route('/api/orders/<order_id>', methods=['PUT'])
@require_auth
def update_order(order_id):
    """Update order status"""
    try:
        data = request.json
        status = data.get('status')
        valid_statuses = ['PENDING', 'CONFIRMED', 'PREPARING', 'DELIVERING', 'DELIVERED', 'CANCELLED']
        
        if status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400

        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if not doc.exists or doc.to_dict().get('userId') != request.user_id:
            return jsonify({'error': 'Order not found'}), 404

        doc_ref.update({
            'status': status,
            'updatedAt': firestore.SERVER_TIMESTAMP
        })

        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to update order'}), 500

@app.route('/api/orders/<order_id>', methods=['DELETE'])
@require_auth
def delete_order(order_id):
    """Delete/cancel an order"""
    try:
        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if not doc.exists or doc.to_dict().get('userId') != request.user_id:
            return jsonify({'error': 'Order not found'}), 404
            
        doc_ref.delete()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to delete order'}), 500

# ==================== ORDER SUBMIT (SEQUENTIAL NUMBERING) ====================

@app.route('/api/order/submit', methods=['POST'])
@require_auth
def submit_order():
    """Submit order and get sequential order number"""
    try:
        data = request.get_json()
        order_data = data.get('order', {})
        
        if not order_data.get('items') or not order_data.get('totalAmount'):
            return jsonify({'success': False, 'error': 'Invalid order data'}), 400

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

        return jsonify({
            'success': True,
            'orderId': order_id,
            'orderNumber': order_number
        })

    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to submit order'}), 500

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
        return jsonify({'error': 'Failed to fetch products'}), 500

@app.route('/api/products', methods=['POST'])
@require_auth
def create_product():
    """Create a new product"""
    try:
        data = request.json
        
        if not data.get('name') or not data.get('price') or data['price'] <= 0:
            return jsonify({'error': 'Invalid product data'}), 400

        product = {
            'name': data['name'],
            'price': data['price'],
            'category': data.get('category'),
            'imageUrl': data.get('imageUrl'),
            'description': data.get('description', ''),
            'inStock': data.get('inStock', True),
            'isActive': data.get('isActive', True),
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        doc_ref = db.collection('products').add(product)
        return jsonify({'success': True, 'productId': doc_ref[1].id}), 201
    except Exception as e:
        return jsonify({'error': 'Failed to create product'}), 500

@app.route('/api/products/<product_id>', methods=['PUT'])
@require_auth
def update_product(product_id):
    """Update a product"""
    try:
        data = request.json
        if 'price' in data and data['price'] <= 0:
            return jsonify({'error': 'Invalid price'}), 400

        db.collection('products').document(product_id).update(data)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to update product'}), 500

@app.route('/api/products/<product_id>', methods=['DELETE'])
@require_auth
def delete_product(product_id):
    """Delete a product"""
    try:
        db.collection('products').document(product_id).delete()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to delete product'}), 500

# ==================== USERS API ====================

@app.route('/api/users/<user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    """Get user profile"""
    try:
        if user_id != request.user_id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        doc = db.collection('users').document(user_id).get()
        if doc.exists:
            return jsonify({'user': {'id': doc.id, **doc.to_dict()}}), 200
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create user profile"""
    try:
        data = request.json
        user_id = data.get('userId')

        if not user_id or not data.get('email'):
            return jsonify({'error': 'userId and email required'}), 400

        user = {
            'userId': user_id,
            'email': data['email'],
            'displayName': data.get('displayName'),
            'phoneNumbers': data.get('phoneNumbers', []),
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        db.collection('users').document(user_id).set(user)
        return jsonify({'success': True}), 201
    except Exception as e:
        return jsonify({'error': 'Failed to create user'}), 500

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
        return jsonify({'error': 'Failed to fetch analytics'}), 500

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
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/admin/orders/<order_id>', methods=['GET'])
@require_admin
def admin_get_order(order_id):
    """Get single order (admin only)"""
    try:
        doc = db.collection('orders').document(order_id).get()
        if doc.exists:
            return jsonify({'order': {'id': doc.id, **doc.to_dict()}}), 200
        return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'error': 'Failed to fetch order'}), 500

@app.route('/api/admin/orders/<order_id>', methods=['PUT'])
@require_admin
def admin_update_order(order_id):
    """Update order (admin only)"""
    try:
        data = request.json
        db.collection('orders').document(order_id).update(data)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to update order'}), 500

@app.route('/api/admin/orders/<order_id>', methods=['DELETE'])
@require_admin
def admin_delete_order(order_id):
    """Delete order (admin only)"""
    try:
        db.collection('orders').document(order_id).delete()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to delete order'}), 500

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_get_all_users():
    """Get all users (admin only)"""
    try:
        users = [{'id': doc.id, **doc.to_dict()} for doc in db.collection('users').stream()]
        return jsonify({'users': users}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/admin/analytics', methods=['GET'])
@require_admin
def admin_get_analytics():
    """Get analytics (admin only)"""
    try:
        orders = list(db.collection('orders').stream())
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
        return jsonify({'error': 'Failed to fetch analytics'}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login - returns admin ID as token"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Query admin by email
        admins = db.collection('admins').where('email', '==', email).limit(1).stream()
        admin_doc = next(admins, None)
        
        if not admin_doc:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        admin_data = admin_doc.to_dict()
        
        # Verify password
        from werkzeug.security import check_password_hash
        if not check_password_hash(admin_data['password'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Return admin ID as token (simple approach)
        return jsonify({
            'success': True,
            'token': admin_doc.id,  # Use admin ID as token
            'adminId': admin_doc.id,
            'email': admin_data['email'],
            'name': admin_data.get('name', '')
        }), 200
    except Exception as e:
        return jsonify({'error': 'Login failed'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
