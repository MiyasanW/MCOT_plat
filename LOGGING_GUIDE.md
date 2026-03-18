# Logging Guide for MCOT Equipment Service

This document explains the logging system in place for debugging, monitoring, and troubleshooting issues in the MCOT Equipment Service application.

---

## Overview

The application uses Django's built-in `logging` module configured in `config/settings.py`. Logs are written to multiple files in the `logs/` directory with different severity levels and organization.

**Purpose**: When customers report issues or the system crashes, logs provide a detailed audit trail of what happened before, during, and after the failure.

---

## Log Files

The logging system creates several log files in `/logs/` directory:

### 1. **app.log** — Main Application Log
- **Contains**: All application-level logs, info, warnings, errors from views and services
- **Size**: Max 5MB, keeps 5 backup files before rotating
- **Use When**: General troubleshooting, understanding application flow
- **Format**: `[LEVEL] TIMESTAMP MODULE_NAME FUNCTION:LINE — MESSAGE`

```
[INFO] 2026-03-18 10:32:42 apps.store.views.booking create_booking_api:203 — 
  [CREATE_BOOKING] User: 1 (test_booker) | Request ID: req_123_abc
[DEBUG] 2026-03-18 10:32:43 apps.store.views.booking create_booking_api:204 — 
  [CREATE_BOOKING] Cart items: 3 items | Start: 2026-03-19 | End: 2026-03-20
[INFO] 2026-03-18 10:32:45 apps.store.views.booking create_booking_api:278 — 
  [CREATE_BOOKING] Success: Booking 100 created for user 1 | Items: 3 | Amount: ฿15,000
```

### 2. **error.log** — Errors and Warnings Only
- **Contains**: ERROR and WARNING level logs only (filtered for quick issue finding)
- **Size**: Max 5MB, keeps 5 backup files
- **Use When**: Something failed, looking for root cause quickly
- **Example**:

```
[ERROR] 2026-03-18 10:32:48 apps.store.views.booking create_booking_api:284 — 
  [CREATE_BOOKING] Service error: Insufficient stock for product 5
  Traceback (most recent call last):
    ...
    
[WARNING] 2026-03-18 10:33:10 apps.store.views.booking check_promo_api:169 — 
  [CHECK_PROMO] Invalid/expired promo code: EXPIRED2026
```

### 3. **api.log** — API Request/Response Tracking
- **Contains**: INFO and above from booking/checkout APIs and services
- **Size**: Max 10MB, keeps 10 backup files (more logs for tracking API patterns)
- **Use When**: Tracking specific customer's requests, understanding API call sequence
- **Tagged with**: `[API_NAME]` prefix for easy filtering

```
[INFO] 2026-03-18 10:32:42 apps.store.views.booking create_booking_api:203 — 
  [CREATE_BOOKING] User: 5 (customer_name) | Request ID: req_456_def
[INFO] 2026-03-18 10:32:45 apps.store.services.booking_service apply_promotion:92 — 
  [BOOKING_SERVICE] Applied promo SUMMER20 | Discount: ฿2,000
[INFO] 2026-03-18 10:32:47 apps.store.views.staff mark_active:156 — 
  [MARK_ACTIVE] Booking 101 marked active by staff user 2
```

### 4. **db.log** — Database Query Logging
- **Contains**: Raw SQL queries (DEBUG mode only)
- **Size**: Max 5MB, keeps 3 backup files
- **Use When**: Debugging slow queries, checking for N+1 problems, understanding data flow
- **Only enabled**: When `DEBUG=True` in settings
- **Security Note**: This file may contain sensitive data; handle carefully

```
[DEBUG] 2026-03-18 10:32:42 django.db.backends execute:103 — 
  SELECT "store_booking"."id", "store_booking"."status" ... FROM "store_booking" 
  WHERE "store_booking"."id" = 100
```

---

## Logging Tags/Prefixes

Throughout the code, log messages use consistent **tags** in square brackets to make them searchable:

| Tag | Location | Purpose |
|-----|----------|---------|
| `[CREATE_BOOKING]` | `apps/store/views/booking.py` | Track booking creation flow |
| `[BOOKING_STATUS]` | `apps/store/views/booking.py` | Track status checks for recovery |
| `[CHECK_PROMO]` | `apps/store/views/booking.py` | Promo code validation |
| `[CHECK_AVAIL]` | `apps/store/views/booking.py` | Availability checks |
| `[BOOKING_SERVICE]` | `apps/store/services/booking_service.py` | Service-level business logic |
| `[AVAILABILITY_SERVICE]` | `apps/store/services/availability.py` | Stock & availability logic |
| `[NOTIFICATION_SERVICE]` | `apps/store/services/notification_service.py` | Email & notification ops |
| `[STAFF_ACTION]` | `apps/store/views/staff.py` | Staff booking operations |
| `[MARK_ACTIVE]` | `apps/store/views/staff.py` | Equipment release/activation |

---

## How to Find Issues

### Scenario 1: Customer says "I got a 500 error when confirming booking"

**Steps**:
1. Get customer's approximate time of attempt
2. Open `logs/error.log`
3. Search for timestamp near that time + user ID/email if available
4. Look for full stack trace

**Example**:
```
[ERROR] 2026-03-18 10:32:48 apps.store.views.booking create_booking_api:284 — 
  [CREATE_BOOKING] Service error: Insufficient stock for product 5
Traceback (most recent call last):
  File ".../views/booking.py", line 268, in create_booking_api
    booking = BookingService.create_booking_from_cart(...)
  File ".../services/booking_service.py", line 45, in create_booking_from_cart
    raise ValueError("Not enough stock available")
ValueError: Not enough stock available
```

Then look at `app.log` for more context:
```
[INFO] 2026-03-18 10:32:42 apps.store.views.booking create_booking_api:203 — 
  [CREATE_BOOKING] User: 5 (thailand_customer) | Request ID: req_789_xyz
[DEBUG] 2026-03-18 10:32:43 apps.store.views.booking create_booking_api:204 — 
  [CREATE_BOOKING] Cart items: 3 items | Start: 2026-03-19 | End: 2026-03-22
[DEBUG] 2026-03-18 10:32:44 apps.store.views.booking check_availability_api:135 — 
  [CHECK_AVAIL] Product: 5 (RED Lights) | Available: true | Remaining: 2
[ERROR] 2026-03-18 10:32:48 ... [CREATE_BOOKING] Service error: ...
```

**Analysis**: Customer had 3 items in cart, product 5 showed 2 units remaining during check, but by the time of booking creation, stock was gone (another customer booked it in the meantime).

---

### Scenario 2: "Checkout keeps looking stuck, then takes very long"

**Steps**:
1. Open `logs/api.log`
2. Search for `[BOOKING_STATUS]` and `[CREATE_BOOKING]`
3. Check timing between messages

**Example**:
```
[INFO] 10:32:42 ... [CREATE_BOOKING] User: 7 ... Request ID: req_111_xyz
[DEBUG] 10:32:43 ... [CREATE_BOOKING] Cart items: 2 items | Start: ... | End: ...
[INFO] 10:32:47 ... [BOOKING_STATUS] Status: PROCESSING | User: 7 | Request: req_111_xyz
[INFO] 10:32:50 ... [BOOKING_STATUS] Status: PROCESSING | User: 7 | Request: req_111_xyz
[INFO] 10:32:53 ... [BOOKING_STATUS] Status: CREATED | User: 7 | Request: req_111_xyz | Booking: 200
```

**Analysis**: Booking took ~5-6 seconds to create (normal for slow DB hardware). Customer's frontend was polling every 2.5 seconds, which is appropriate.

---

### Scenario 3: "I noticed slow performance in the evening"

**Steps**:
1. Open `logs/db.log` (if DEBUG=True)
2. Search for slow query patterns or repeated queries for same data
3. Check if N+1 problem

**Example pattern** (N+1 problem):
```
[DEBUG] 10:45:23 django.db.backends ... SELECT ... FROM "store_booking" WHERE id=100
[DEBUG] 10:45:23 django.db.backends ... SELECT ... FROM "store_bookingitem" WHERE "booking_id"=100
[DEBUG] 10:45:24 django.db.backends ... SELECT ... FROM "store_bookingitem" WHERE "booking_id"=100  ← Duplicate!
[DEBUG] 10:45:24 django.db.backends ... SELECT ... FROM "store_product" WHERE id=5
[DEBUG] 10:45:24 django.db.backends ... SELECT ... FROM "store_product" WHERE id=5  ← Duplicate!
```

**Fix suggestion**: Optimize queries with `select_related()` or `prefetch_related()` in `BookingService`.

---

## Log Levels

| Level | Usage | Example Scenario |
|-------|-------|------------------|
| **DEBUG** | Detailed diagnostics, variable values, flow steps | Cart items loaded, date parsed, availability checked |
| **INFO** | Significant application events | Booking created, payment confirmed, email sent |
| **WARNING** | Something unexpected but app continues | Invalid promo code, deprecated API endpoint used |
| **ERROR** | Something failed, customer impact likely | Booking creation failed, payment integration error |
| **CRITICAL** | System-level failure (rare) | Database connection lost, cache server down |

---

## Configuration

All logging configuration lives in `config/settings.py` in the `LOGGING` dictionary. Key settings:

```python
LOGGING = {
    'handlers': {
        'file': {
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 5 * 1024 * 1024,      # 5MB per file
            'backupCount': 5,                   # Keep 5 old files
            'formatter': 'verbose',             # Include timestamp, module, line #
        },
    },
    'loggers': {
        'apps.store': {
            'level': 'DEBUG',                   # Capture DEBUG and above
            'handlers': ['console', 'file', 'error_file', 'api_file'],
        },
    },
}
```

### Tuning for Production

When deploying to production, consider:

1. **Change DEBUG=False** to disable `db.log` (avoids SQL leaks)
2. **Reduce log levels** for less important modules:
   ```python
   'django': {
       'level': 'WARNING',  # Only WARNING and above for Django framework
   },
   ```
3. **Rotate logs more aggressively** if disk space is limited:
   ```python
   'maxBytes': 10 * 1024 * 1024,  # 10MB instead of 5MB
   'backupCount': 3,                # Keep only 3 files instead of 5
   ```
4. **Add a logging aggregation service** (e.g., Sentry, ELK Stack) for central log search

---

## Useful Log Search Commands

### Find all booking creation attempts:
```bash
grep "\[CREATE_BOOKING\]" logs/app.log
grep "\[CREATE_BOOKING\]" logs/error.log
```

### Find errors from a specific user:
```bash
grep "User: 7" logs/error.log
```

### Find slow bookings (take >10 seconds):
```bash
# Look for time gaps between [CREATE_BOOKING] start and success
grep "\[CREATE_BOOKING\].*Success" logs/api.log | grep "Booking [0-9]*"
```

### Find all promo code validations:
```bash
grep "\[CHECK_PROMO\]" logs/api.log
```

### Monitor logs in real-time (while testing):
```bash
tail -f logs/app.log
tail -f logs/error.log
```

---

## Adding New Logs

When adding new features or debugging, add logging following this pattern:

```python
import logging
logger = logging.getLogger(__name__)

def my_view(request):
    logger.info(f"[MY_FEATURE] Starting operation | User: {request.user.id}")
    
    try:
        # Do something
        result = expensive_operation()
        logger.debug(f"[MY_FEATURE] Operation result: {result}")
        
    except ValueError as e:
        logger.warning(f"[MY_FEATURE] Validation error: {str(e)}")
        
    except Exception as e:
        logger.error(f"[MY_FEATURE] Unexpected error: {str(e)}", exc_info=True)
        # exc_info=True includes the full stack trace
```

**Guidelines**:
- Use consistent tag prefix in square brackets
- Log at appropriately: DEBUG for details, INFO for important events, ERROR for failures
- Include context: user ID, IDs of related objects, relevant data
- Use `exc_info=True` for exceptions to get full stack trace

---

## Summary

| Need | File | Search Term |
|------|------|-------------|
| General troubleshooting | `app.log` | Tag like `[CREATE_BOOKING]` |
| Find errors quickly | `error.log` | grep for ERROR/WARNING  |
| Track specific customer | `api.log` | grep for `User: {id}` |
| Debug slow performance | `db.log` | SQL patterns, query count |

**Remember**: Logs are your best friend when debugging production issues. Keep them clean, read them thoroughly, and use them to prevent the same bug twice.

---

**Last Updated**: March 18, 2026
