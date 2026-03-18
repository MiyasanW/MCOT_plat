# Checkout Flow & Recovery Mechanism

## Overview

This document explains the idempotent checkout system and how it handles network failures, page refreshes, and duplicate submission prevention. It's essential for understanding customer-facing reliability and for maintaining/extending the flow in the future.

---

## Problem Statement

**Original Issue**: When a customer clicked "ยืนยันการทำรายการ" (confirm booking) during slow network conditions or then refreshed the page, they would:
1. See the review page remain on-screen (unclear if booking was created)
2. Risk creating duplicate bookings if they clicked confirm again
3. Lose confidence in the system and retry manually

**Solution**: Implement idempotent checkout with server-state recovery and visual feedback to reassure users during in-flight submission.

---

## Core Architecture

### 1. Request ID (Client-Side Session)

```javascript
// In templates/booking/cart_review.html
ensureCheckoutRequestId() {
    const key = 'mcot_checkout_request_id';
    let requestId = sessionStorage.getItem(key);
    if (!requestId) {
        requestId = `req_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
        sessionStorage.setItem(key, requestId);
    }
    this.checkoutRequestId = requestId;
}
```

**Purpose**: Each checkout attempt is tagged with a unique session-scoped ID. If a user refreshes, the same ID is reused to query the server state.

**Scope**: SessionStorage (cleared when user closes browser tab, persists across page reloads in same tab).

---

### 2. Backend Idempotency Lock

```python
# In apps/store/views/booking.py
def create_booking_api(request):
    request_id = payload.get('request_id', '')
    user_id = request.user.id
    
    lock_key = f"booking_create_lock:{user_id}:{request_id}"
    result_key = f"booking_create_result:{user_id}:{request_id}"
    
    # Check if already created
    cached_result = cache.get(result_key)
    if cached_result:
        return {"success": True, "booking_id": cached_result}
    
    # Acquire lock; if lock exists, return 409 (processing)
    if cache.get(lock_key):
        return {"success": False, "processing": True}, 409
    
    # Acquire lock for 30 seconds
    cache.set(lock_key, 1, timeout=30)
    
    try:
        # Create booking...
        booking = create_booking(...)
        
        # Cache result for future recovery
        cache.set(result_key, booking.id, timeout=300)  # 5 minutes
        
        return {"success": True, "booking_id": booking.id}
    finally:
        cache.delete(lock_key)
```

**Why This Works**:
- **Idempotency via request ID**: Same `request_id` → same booking returned
- **Lock prevents race**: Concurrent submissions get a 409 "processing" response
- **Result caching**: If server crashes between booking creation and response, client can still recover the booking ID via status API

**Timeout Strategy**:
- Lock: 30 seconds (reasonable max booking creation time)
- Result cache: 5 minutes (customer has time to refresh and recover)

---

### 3. Status Polling API

```python
# In apps/store/views/booking.py
def booking_create_status_api(request):
    """
    GET /api/booking-create-status/?request_id=<request_id>
    
    Returns current state of a checkout attempt:
    - created=true + booking_id: Booking was successfully created
    - processing=true: Lock exists; server is still processing
    - (neither): No prior request found; user can submit again
    """
    request_id = request.GET.get('request_id', '')
    user_id = request.user.id
    
    result_key = f"booking_create_result:{user_id}:{request_id}"
    lock_key = f"booking_create_lock:{user_id}:{request_id}"
    
    # Case 1: Booking already created
    booking_id = cache.get(result_key)
    if booking_id:
        return {"success": True, "created": True, "booking_id": booking_id}
    
    # Case 2: Lock exists (still processing)
    if cache.get(lock_key):
        return {"success": True, "created": False, "processing": True}
    
    # Case 3: No state found (safe to submit a new request)
    return {"success": True, "created": False, "processing": False}
```

**Endpoint**: Lightweight GET-only query (no side effects, no form data required).

---

## Frontend Flow (Alpine.js)

```javascript
// 1. On page load, check if user previously submitted
init() {
    this.hasSubmittedCheckout = sessionStorage.getItem('mcot_checkout_submitted') === '1';
    if (this.hasSubmittedCheckout) {
        this.recoverCheckoutStatus();  // Auto-poll to find out result
    }
}

// 2. User clicks confirm button
async submitBooking() {
    this.isSubmitting = true;
    sessionStorage.setItem('mcot_checkout_submitted', '1');  // Mark submission attempt
    this.hasSubmittedCheckout = true;
    
    try {
        const response = await fetch("/api/create-booking/", {
            method: 'POST',
            body: JSON.stringify({ request_id: this.checkoutRequestId, ... })
        });
        
        if (response.ok && data.success) {
            // Success! Redirect to checkout page
            window.location.href = `/cart/checkout/${data.booking_id}/`;
        } else if (response.status === 409 && data.processing) {
            // Lock exists; server is processing our request
            this.isRecoveryProcessing = true;
            this.queueRecoveryPolling();  // Start polling every 2.5 seconds
        }
    } catch (error) {
        // Network error; try recovery
        await this.recoverCheckoutStatus();
    }
}

// 3. Auto-recovery polling (on 409 or network error)
async recoverCheckoutStatus() {
    const response = await fetch(`/api/booking-create-status/?request_id=${this.checkoutRequestId}`);
    const data = await response.json();
    
    if (data.created && data.booking_id) {
        // Booking exists! Redirect
        window.location.href = `/cart/checkout/${data.booking_id}/`;
        return;
    }
    
    if (data.processing) {
        // Still processing; queue next poll
        this.queueRecoveryPolling();
        return;
    }
    
    // No state found; user can submit again
    this.hasSubmittedCheckout = false;
}

// 4. Display status banner during recovery
```

**Visual Feedback**:
```html
<!-- Shows during active submission or recovery -->
<div x-show="hasSubmittedCheckout" class="mb-4 rounded-xl ... bg-amber-500/10">
    <i class="fas fa-circle-notch fa-spin" x-show="isSubmitting || isRecoveryProcessing"></i>
    <p class="text-sm font-bold" x-text="checkoutStatusTitle"></p>
    <p class="text-xs" x-text="checkoutStatusHint"></p>
</div>
```

**Status Title/Hint**:
- Submitting: "กำลังส่งคำขอของคุณ" / "กรุณารอสักครู่..."
- Recovery: "กำลังตรวจสอบสถานะใบจอง" / "ระบบกำลังตามคำขอเดิมให้อัตโนมัติ"

---

## Scenario Walkthrough

### Scenario 1: Happy Path (Successful First Submission)

```
Customer                    Frontend                  Backend
   |                            |                         |
   |-- "Click Confirm" -------->|                         |
   |                    [Mark submitted]                  |
   |                            |-- POST /api/create-booking/ -->|
   |                            |   (request_id: req_123)         |
   |                            |                    [Acquire lock]
   |                            |                    [Create booking #100]
   |                            |                    [Cache result]
   |                            |<-- 200 OK, booking_id: 100 --|
   |                    [Clear markers]                    |
   |<-- Redirect to /cart/checkout/100/ --------         |
   |
   [Success page loads]
```

**User Experience**: Sees status banner → briefly shows "กำลังส่งคำขอของคุณ" → auto-redirects within ~200ms.

---

### Scenario 2: Slow Network → Page Refresh

```
Customer                    Frontend                  Backend
   |                            |                         |
   |-- "Click Confirm" -------->|                         |
   |                    [Mark submitted]                  |
   |                            |-- POST /api/create-booking/ -->|
   |                            |                    [Acquire lock]
   |                            |                    [Creating... 2 sec]
   |
   |-- [Page is slow, user refreshes] ---|
   |                                      |
   |<-- Page reloads ---|                 |
   |                    [Init detects: submitted=1]
   |                    [Call recoverCheckoutStatus()]
   |                            |-- GET /api/booking-create-status/ -->|
   |                            |        (request_id: req_123)         |
   |                            |                    [Lock still exists]
   |                            |<-- 200 OK, processing: true ---|
   |                    [Show recovery banner]                    |
   |                    [Queue polling in 2.5s]                  |
   |
   |-- [After 2.5 sec, auto-poll] ---|
   |                            |-- GET /api/booking-create-status/ -->|
   |                            |        (request_id: req_123)         |
   |                            |                    [Booking #100 cached]
   |                            |<-- 200 OK, created: true, booking_id: 100 --|
   |                    [Clear markers]                    |
   |<-- Redirect to /cart/checkout/100/ --------         |
   |
   [Success page loads]
```

**User Experience**: Sees status banner → message changes to "กำลังตรวจสอบสถานะใบจอง" → auto-polls → auto-redirects within ~2.5 sec.

---

### Scenario 3: Server Lock Before Booking Creation

```
Customer                    Frontend                  Backend
   |                            |                         |
   |-- "Click Confirm" -------->|                         |
   |                    [Mark submitted]                  |
   |                            |-- POST /api/create-booking/ -->|
   |                            |   (request_id: req_123)         |
   |                            |<-- 409: processing ---|
   |                    [Set isRecoveryProcessing]       |
   |                    [Start polling in 2.5s]          |
   |
   |-- [2.5 sec later, 1st poll] ---|
   |                            |-- GET /api/booking-create-status/ -->|
   |                            |<-- Still processing ---|
   |                    [Show banner, queue next poll]
   |
   |-- [2.5 sec later, 2nd poll] ---|
   |                            |-- GET /api/booking-create-status/ -->|
   |                            |                    [Booking #100 ready]
   |                            |<-- 200 OK, created: true, booking_id: 100 --|
   |                    [Clear markers]                    |
   |<-- Redirect to /cart/checkout/100/ --------         |
```

**User Experience**: Gets popup "ระบบกำลังดำเนินการ" → sees recovery banner → auto-recovers within ~5 sec.

---

### Scenario 4: Network Failure During Submission

```
Customer                    Frontend                  Backend
   |                            |                         |
   |-- "Click Confirm" -------->|                         |
   |                    [Mark submitted]                  |
   |                            |-- POST /api/create-booking/ -->|
   |                            |   [Network error / timeout]    |
   |                    [catch block triggered]           |
   |                    [Call recoverCheckoutStatus()]
   |                            |-- GET /api/booking-create-status/ -->|
   |                            |   [Network OK]                  |
   |                            |<-- 200 OK, processing: true --|
   |                    [Show recovery banner]
   |                    [Start polling]
   |
   |-- [Auto-polls, eventually retrieves booking] ---|
   |<-- Redirect to /cart/checkout/100/ --------         |
```

**User Experience**: Sees "ข้อผิดพลาดระบบ" popup, but recovery banner keeps polling → when network recovers, auto-redirects.

---

## Testing

### Unit Tests

All tests are in `apps/store/tests.py` under `BookingFlowTests`:

```python
def test_create_booking_idempotent_request_id():
    """Same request_id returns same booking, no duplicate created."""
    
def test_booking_create_status_returns_created_booking():
    """Status API returns created booking when result cached."""
    
def test_booking_create_status_returns_processing_when_lock_exists():
    """Status API returns processing=true when lock still exists."""
    
def test_offline_recovery_on_refresh_returns_existing_booking():
    """Full workflow: create → refresh → status API returns same booking."""
```

**Run Tests**:
```bash
python3 manage.py test apps.store -v 2
```

All 25 tests should pass.

---

## Configuration & Tuning

### Cache Timeouts

Edit in `apps/store/views/booking.py`:

```python
# Lock timeout (how long to hold the lock while creating booking)
lock_timeout = 30  # seconds

# Result cache (how long to keep booking ID for recovery)
result_timeout = 300  # 5 minutes
```

**Recommendations**:
- Lock timeout: Set to ~130% of typical booking creation time
- Result cache: Set to ~5-10 minutes (gives customer buffer time to refresh)

### Polling Interval

Edit in `templates/booking/cart_review.html`:

```javascript
queueRecoveryPolling() {
    this.recoveryTimer = setTimeout(() => {
        this.recoverCheckoutStatus();
    }, 2500);  // Poll every 2.5 seconds
}
```

**Recommendations**:
- 2-3 seconds for good UX (not too aggressive, not too slow)
- Adjust if server-side booking creation is slower/faster

---

## Maintenance & Debugging

### Checking Server State

If a customer reports a stuck checkout:

```bash
# SSH into VPS (if using production cache)
# Check if lock exists:
# (depends on cache backend; if using redis:)
redis-cli GET "booking_create_lock:USER_ID:REQUEST_ID"

# Check if result cached:
redis-cli GET "booking_create_result:USER_ID:REQUEST_ID"
```

### Clearing Stuck State (if needed)

```python
# In Django shell
from django.core.cache import cache

user_id = 123
request_id = "req_1234567_abcdef"

lock_key = f"booking_create_lock:{user_id}:{request_id}"
result_key = f"booking_create_result:{user_id}:{request_id}"

cache.delete(lock_key)
cache.delete(result_key)
```

---

## Future Enhancements

### 1. Webhook Notification to Customer
When booking successfully creates (even if user lost network), email customer immediately.

### 2. Per-User Concurrent Submission Limit
Prevent customer from accidentally submitting same request twice in parallel.

### 3. Persistent Recovery UI
Remember recovery state across page navigations (use `localStorage` in addition to session).

### 4. Metrics & Monitoring
Track:
- % of requests that hit lock condition
- % of requests that use recovery path
- Average recovery time
- Cache hit/miss rates

---

## Summary for Next Developer

**Key Takeaways**:
1. **Request ID**: Client-generated, session-scoped, persists across page refreshes
2. **Idempotency**: Server locks submissions by user + request ID, caches result
3. **Status API**: Lightweight endpoint to query without side effects
4. **Frontend Recovery**: Auto-polling when submission fails or on page refresh
5. **UX**: Persistent banner + retry logic = customer confidence

**Files to Know**:
- `apps/store/views/booking.py` — Core API logic
- `templates/booking/cart_review.html` — Frontend UI & Alpine data
- `apps/store/urls.py` — Route registration
- `apps/store/tests.py` — Test coverage

**Before Deploying Changes**:
- Run `python3 manage.py test apps.store -v 2`
- Test manually: slow network (DevTools throttle) + refresh during confirmation
- Verify lock timeout appropriate for your server speed

---

**Last Updated**: March 18, 2026
