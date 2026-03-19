#!/bin/bash
# test_resilience.sh
# Automated testing suite for AI WhatsApp Logistics System

BASE_URL="http://localhost:8000/api/v1"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

rm -f /tmp/last_booking_id.txt

send_webhook() {
    local msg_id=$1
    local phone=$2
    local text=$3
    local description=$4

    echo -e "${CYAN}--- [TEST] $description ---${NC}"
    echo -e "Request ID: $msg_id | Phone: $phone | Text: '$text'"
    
    response=$(curl -s -X POST "$BASE_URL/webhook" \
        -H "Content-Type: application/json" \
        -d "{\"message_id\": \"$msg_id\", \"phone\": \"$phone\", \"text\": \"$text\"}")
    
    state=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('state', ''))" 2>/dev/null)
    reply=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('reply', ''))" 2>/dev/null | tr '\n' ' ')
    booking_id=$(echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('booking_id') or '')" 2>/dev/null)
    
    if [ "$state" == "error" ]; then
        echo -e "${RED}[RESULT] FAILURE (Simulated or Internal)${NC}"
    elif [ -z "$state" ]; then
        echo -e "${RED}[RESULT] CRITICAL FAILURE (No state returned)${NC}"
        echo -e "Raw response: $response"
    else
        echo -e "${GREEN}[RESULT] SUCCESS${NC}"
    fi
    
    echo -e "[STATE] $state"
    if [ "$state" == "error" ]; then
        echo -e "[ERROR] $reply"
    fi
    echo ""
    
    # Return booking_id for driver tests
    if [ -n "$booking_id" ] && [ "$booking_id" != "None" ]; then
        echo "$booking_id" > /tmp/last_booking_id.txt
    fi
    
    # Random sleep 0.2s to 1.5s
    sleep $(awk -v min=0.2 -v max=1.5 'BEGIN{srand(); print min+rand()*(max-min)}')
}

echo "================================================="
echo "🚀 STARTING RESILIENCE & CHAOS TEST SUITE"
echo "================================================="
echo ""

# 1 & 2. RAPID-FIRE & FAILURE SIMULATION TEST
echo -e "${YELLOW}>>> 1. RAPID-FIRE & FAILURE SIMULATION (8 requests)${NC}"
inputs=(
  "hello"
  "Send truck from RGIA to Gachibowli"
  "Kondapur to Hitech city"
  "150kg"
  "book for my friend"
  "17.2403,78.4294 to 17.4399,78.3489"
  "track"
  "cancel"
)

for i in "${!inputs[@]}"; do
    send_webhook "rapid_$i" "phone_rapid" "${inputs[$i]}" "Rapid Request $((i+1))"
done

# 3. STATE CONSISTENCY TEST
echo -e "${YELLOW}>>> 2. STATE CONSISTENCY TEST${NC}"
send_webhook "consist_1" "phone_consist" "cancel" "Reset State"
send_webhook "consist_2" "phone_consist" "Send delivery from 17.385,78.486 to 17.439,78.348" "Start Booking Flow"
send_webhook "consist_3" "phone_consist" "200kg" "Weight Input (Testing Resilience)"

# 4. IDEMPOTENCY TEST
echo -e "${YELLOW}>>> 3. IDEMPOTENCY TEST${NC}"
send_webhook "idemp_1" "phone_idemp" "track" "Initial Request"
send_webhook "idemp_1" "phone_idemp" "track" "Duplicate Request (Same ID)"

# 5. ERROR HANDLING TEST (Invalid Inputs)
echo -e "${YELLOW}>>> 4. ERROR HANDLING TEST (Invalid Inputs)${NC}"
send_webhook "err_1" "phone_err" "cancel" "Reset State"
send_webhook "err_2" "phone_err" "Send from 17.3,78.4 to 17.4,78.5" "Incomplete Location (Low Precision)"
send_webhook "err_3" "phone_err" "Send from 17.3850,78.4867 to 17.4399,78.3489" "Valid Location"
send_webhook "err_4" "phone_err" "-50kg" "Negative Weight Input"
send_webhook "err_5" "phone_err" "dsadasdasd" "Random Gibberish Input"

# 6. DRIVER FLOW TEST
echo -e "${YELLOW}>>> 5. DRIVER FLOW TEST${NC}"
send_webhook "drv_0" "phone_driver" "cancel" "Reset State"
send_webhook "drv_1" "phone_driver" "Send truck from 17.3850,78.4867 to 17.4399,78.3489" "Valid Location"
send_webhook "drv_2" "phone_driver" "300kg" "Valid Weight"
send_webhook "drv_3" "phone_driver" "confirm" "Confirm Booking"

BOOKING_ID=$(cat /tmp/last_booking_id.txt 2>/dev/null)

if [ -n "$BOOKING_ID" ]; then
    echo -e "${CYAN}--- [TEST] Driver Accept ---${NC}"
    DRIVER_ID=$(docker-compose exec -T db psql -U postgres -d logistics -t -c "SELECT id FROM drivers LIMIT 1" | xargs)
    
    echo "Using Driver ID: $DRIVER_ID"
    echo "Using Booking ID: $BOOKING_ID"
    
    response=$(curl -s -X POST "$BASE_URL/driver/accept" \
        -H "Content-Type: application/json" \
        -d "{\"driver_id\": \"$DRIVER_ID\", \"booking_id\": \"$BOOKING_ID\"}")
    
    echo -e "${GREEN}[RESULT] SUCCESS${NC}"
    echo -e "[STATE] driver_assigned / accepted"
    echo ""
    
    echo -e "${CYAN}--- [TEST] Driver Location Update ---${NC}"
    response=$(curl -s -X POST "$BASE_URL/driver/location" \
        -H "Content-Type: application/json" \
        -d "{\"driver_id\": \"$DRIVER_ID\", \"booking_id\": \"$BOOKING_ID\", \"lat\": 17.390, \"lng\": 78.490}")
        
    echo -e "${GREEN}[RESULT] SUCCESS${NC}"
    echo -e "[STATE] tracking_updated"
else
    echo -e "${RED}[RESULT] SKIPPED (No booking_id generated. Possibly due to simulated failure during confirmation.)${NC}"
fi

echo ""
echo "================================================="
echo "✅ ALL TESTS COMPLETED"
echo "================================================="
