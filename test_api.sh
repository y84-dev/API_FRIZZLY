#!/bin/bash
# Quick test script for FRIZZLY API endpoints

BASE_URL="http://localhost:8080"

echo "🧪 Testing FRIZZLY API..."
echo ""

# Test 1: Root endpoint
echo "1️⃣  Testing root endpoint..."
curl -s "$BASE_URL/" | python3 -m json.tool
echo ""

# Test 2: Health check
echo "2️⃣  Testing health check..."
curl -s "$BASE_URL/api/health" | python3 -m json.tool
echo ""

# Test 3: Get products
echo "3️⃣  Testing products endpoint..."
curl -s "$BASE_URL/api/products" | python3 -m json.tool
echo ""

# Test 4: Protected endpoint (should fail without auth)
echo "4️⃣  Testing protected endpoint (should return 401)..."
curl -s "$BASE_URL/api/orders" | python3 -m json.tool
echo ""

echo "✅ Basic tests complete!"
echo ""
echo "📝 To test authenticated endpoints:"
echo "   1. Get Firebase ID token from your Android app"
echo "   2. Run: curl -H 'Authorization: Bearer YOUR_TOKEN' $BASE_URL/api/orders"
