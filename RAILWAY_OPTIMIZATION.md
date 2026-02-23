# ⚡ API Performance Optimization for Railway

**Issue:** API became slow after adding SSE  
**Cause:** SSE keeps connections open, consuming resources  
**Solution:** Optimized SSE with limits and cleanup

---

## 🔧 **Optimizations Applied**

### **1. Connection Limit**
```python
MAX_SSE_CONNECTIONS = 5  # Max 5 concurrent SSE connections
```

**Why:** Railway has limited resources. Too many open connections = slow API.

---

### **2. Queue Size Limit**
```python
message_queue = queue.Queue(maxsize=100)
```

**Why:** Prevents memory overflow if events pile up.

---

### **3. Auto-Disconnect**
```python
max_timeouts = 6  # 3 minutes of inactivity
```

**Why:** Closes idle connections automatically.

---

### **4. Reduced Listener Scope**
```python
col_query = db.collection('orders').limit(20)  # Was 50
```

**Why:** Less data = faster queries.

---

### **5. Non-Blocking Queue**
```python
message_queue.put_nowait(event_data)  # Don't block
```

**Why:** Drops events if queue full instead of blocking.

---

### **6. Proper Cleanup**
```python
finally:
    doc_watch.unsubscribe()
    sse_connections.remove(connection_id)
```

**Why:** Releases resources when connection closes.

---

## 📊 **Performance Impact**

### **Before:**
- ❌ Unlimited SSE connections
- ❌ Connections never timeout
- ❌ No cleanup on disconnect
- ❌ 50 orders monitored
- ❌ Blocking queue operations

**Result:** API slows down with each SSE connection

### **After:**
- ✅ Max 5 SSE connections
- ✅ Auto-disconnect after 3 min idle
- ✅ Proper cleanup
- ✅ 20 orders monitored
- ✅ Non-blocking queue

**Result:** API stays fast even with SSE

---

## 🚀 **Deploy to Railway**

```bash
cd ~/AndroidStudioProjects/API_FRIZZLY
git add flask_app.py
git commit -m "Optimize SSE for Railway"
git push railway main
```

---

## 🧪 **Test Performance**

### **Before Optimization:**
```bash
# Multiple SSE connections slow down API
curl http://your-api.railway.app/api/products  # Slow
```

### **After Optimization:**
```bash
# API stays fast
curl http://your-api.railway.app/api/products  # Fast
```

---

## 📈 **Monitoring**

### **Check Active Connections:**
```python
# Add endpoint to check SSE connections
@app.route('/api/admin/sse/status')
@require_admin
def sse_status():
    return jsonify({
        'active_connections': len(sse_connections),
        'max_connections': MAX_SSE_CONNECTIONS
    })
```

---

## ⚙️ **Configuration**

### **Adjust Limits:**
```python
# In flask_app.py
MAX_SSE_CONNECTIONS = 5  # Increase if needed
max_timeouts = 6         # 3 minutes (6 * 30s)
message_queue = queue.Queue(maxsize=100)
col_query.limit(20)      # Orders to monitor
```

### **Railway Resources:**
- Free tier: 512MB RAM, 0.5 vCPU
- Hobby tier: 8GB RAM, 8 vCPU

**Recommendation:** Keep MAX_SSE_CONNECTIONS = 5 for free tier

---

## 🐛 **Troubleshooting**

### **Issue: "Too many SSE connections"**
**Cause:** More than 5 admins connected  
**Solution:** Increase MAX_SSE_CONNECTIONS or close old connections

### **Issue: Events not received**
**Cause:** Queue full (100 events)  
**Solution:** Increase maxsize or process events faster

### **Issue: Connection drops after 3 min**
**Cause:** Auto-disconnect timeout  
**Solution:** Increase max_timeouts or send more heartbeats

---

## 💡 **Alternative: Disable SSE**

If SSE still causes issues, use polling instead:

```python
# Comment out SSE endpoint
# @app.route('/api/admin/stream/orders')
# def stream_orders():
#     ...

# Use polling endpoint instead
@app.route('/api/admin/orders/recent')
@require_admin
def get_recent_orders():
    # Returns last 10 orders
    # Dashboard polls every 5 seconds
```

**Dashboard will automatically fall back to polling.**

---

## ✅ **Summary**

**Changes:**
- ✅ Max 5 SSE connections
- ✅ Auto-disconnect after 3 min
- ✅ Queue size limit (100)
- ✅ Monitor only 20 orders
- ✅ Non-blocking operations
- ✅ Proper cleanup

**Result:**
- ⚡ API stays fast
- 💾 Lower memory usage
- 🔒 Resource limits enforced
- 🚀 Railway-optimized

**Deploy and test!** 🎉
