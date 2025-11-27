#!/bin/bash
# Production API Testing Script
# Tests all endpoints to verify production setup

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
VERBOSE="${VERBOSE:-false}"

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5

    if [ "$VERBOSE" = "true" ]; then
        echo "Testing: $description"
        echo "  $method $endpoint"
    fi

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" 2>&1)
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "$expected_status" ]; then
        print_success "$description (HTTP $http_code)"
        if [ "$VERBOSE" = "true" ]; then
            echo "$body" | jq . 2>/dev/null || echo "$body"
        fi
        echo "$body"
    else
        print_error "$description (Expected HTTP $expected_status, got $http_code)"
        echo "$body" | jq . 2>/dev/null || echo "$body"
        return 1
    fi
}

echo "=========================================="
echo "Production API Testing Script"
echo "=========================================="
echo "API URL: $API_URL"
echo ""

# Test 1: Health - Liveness
echo "=== Health Endpoints ==="
test_endpoint "GET" "/health/live" "" "200" "Liveness probe"
LIVE_RESPONSE=$body

# Test 2: Health - Readiness
test_endpoint "GET" "/health/ready" "" "200" "Readiness probe"
READY_RESPONSE=$body

# Check if services are healthy
if echo "$READY_RESPONSE" | jq -e '.checks.database.status == "healthy"' > /dev/null 2>&1; then
    print_success "Database is healthy"
else
    print_error "Database is unhealthy - check DATABASE_URL"
fi

if echo "$READY_RESPONSE" | jq -e '.checks.redis.status == "healthy"' > /dev/null 2>&1; then
    print_success "Redis is healthy"
else
    print_error "Redis is unhealthy - check REDIS_URL"
fi

echo ""

# Test 3: Products - List (empty)
echo "=== Product API Tests ==="
test_endpoint "GET" "/api/products" "" "200" "List products (empty)"
PRODUCTS_RESPONSE=$body

# Test 4: Products - Create
PRODUCT_DATA='{"sku":"TEST-001","name":"Test Product","description":"API Test Product","active":true}'
test_endpoint "POST" "/api/products" "$PRODUCT_DATA" "201" "Create product"
CREATED_PRODUCT=$body
PRODUCT_ID=$(echo "$CREATED_PRODUCT" | jq -r '.id' 2>/dev/null)

if [ -z "$PRODUCT_ID" ] || [ "$PRODUCT_ID" = "null" ]; then
    print_error "Failed to extract product ID"
    PRODUCT_ID="unknown"
else
    print_info "Created product ID: $PRODUCT_ID"
fi

# Test 5: Products - List (with data)
test_endpoint "GET" "/api/products" "" "200" "List products (with data)"

# Test 6: Products - Get by ID
if [ "$PRODUCT_ID" != "unknown" ]; then
    test_endpoint "GET" "/api/products/$PRODUCT_ID" "" "200" "Get product by ID"
fi

# Test 7: Products - Update
if [ "$PRODUCT_ID" != "unknown" ]; then
    UPDATE_DATA='{"name":"Updated Test Product"}'
    test_endpoint "PUT" "/api/products/$PRODUCT_ID" "$UPDATE_DATA" "200" "Update product"
fi

# Test 8: Products - Filter
test_endpoint "GET" "/api/products?sku=TEST" "" "200" "Filter products by SKU"

echo ""

# Test 9: CSV Upload
echo "=== CSV Upload Tests ==="
# Create test CSV
cat > /tmp/test_products.csv << 'EOF'
sku,name,description
CSV-001,CSV Product One,First CSV product
CSV-002,CSV Product Two,Second CSV product
EOF

UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/uploads/" -F "file=@/tmp/test_products.csv")
UPLOAD_STATUS=$(echo "$UPLOAD_RESPONSE" | jq -r '.status' 2>/dev/null)
JOB_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.id' 2>/dev/null)

if [ -n "$JOB_ID" ] && [ "$JOB_ID" != "null" ]; then
    print_success "CSV upload created job (ID: $JOB_ID)"
    print_info "Waiting 5 seconds for processing..."
    sleep 5
    
    # Test 10: Check job status
    test_endpoint "GET" "/api/jobs/$JOB_ID" "" "200" "Check import job status"
    
    # Test 11: Verify products imported
    test_endpoint "GET" "/api/products?sku=CSV" "" "200" "Verify CSV products imported"
else
    print_error "CSV upload failed"
fi

echo ""

# Test 12: Webhooks
echo "=== Webhook API Tests ==="
test_endpoint "GET" "/api/webhooks" "" "200" "List webhooks (empty)"

# Test 13: Create webhook
WEBHOOK_URL="https://webhook.site/$(openssl rand -hex 8)"
WEBHOOK_DATA="{\"url\":\"$WEBHOOK_URL\",\"event\":\"product.created\",\"enabled\":true}"
test_endpoint "POST" "/api/webhooks" "$WEBHOOK_DATA" "201" "Create webhook"
CREATED_WEBHOOK=$body
WEBHOOK_ID=$(echo "$CREATED_WEBHOOK" | jq -r '.id' 2>/dev/null)

if [ -z "$WEBHOOK_ID" ] || [ "$WEBHOOK_ID" = "null" ]; then
    print_error "Failed to extract webhook ID"
    WEBHOOK_ID="unknown"
else
    print_info "Created webhook ID: $WEBHOOK_ID"
    print_info "Test webhook URL: $WEBHOOK_URL"
fi

# Test 14: Test webhook
if [ "$WEBHOOK_ID" != "unknown" ]; then
    test_endpoint "POST" "/api/webhooks/$WEBHOOK_ID/test" "" "202" "Test webhook delivery"
    print_info "Check $WEBHOOK_URL for webhook payload"
fi

# Test 15: List webhooks
test_endpoint "GET" "/api/webhooks" "" "200" "List webhooks (with data)"

# Test 16: Update webhook
if [ "$WEBHOOK_ID" != "unknown" ]; then
    UPDATE_WEBHOOK='{"enabled":false}'
    test_endpoint "PUT" "/api/webhooks/$WEBHOOK_ID" "$UPDATE_WEBHOOK" "200" "Update webhook"
fi

echo ""

# Test 17: Delete product
echo "=== Cleanup Tests ==="
if [ "$PRODUCT_ID" != "unknown" ]; then
    test_endpoint "DELETE" "/api/products/$PRODUCT_ID" "" "204" "Delete product (soft delete)"
fi

# Test 18: Delete webhook
if [ "$WEBHOOK_ID" != "unknown" ]; then
    test_endpoint "DELETE" "/api/webhooks/$WEBHOOK_ID" "" "204" "Delete webhook"
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
fi

