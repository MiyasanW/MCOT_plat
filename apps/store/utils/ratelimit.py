import time
from functools import wraps
from django.core.cache import cache
from django.http import HttpResponseForbidden

def get_client_ip(request):
    """
    Get the client's IP address from the request.
    Handles proxies and direct connections.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def ratelimit(key_prefix='ratelimit', rate=5, period=60, block=True):
    """
    Simple Token Bucket rate limiter using Django's cache.
    
    :param key_prefix: Prefix for the cache key.
    :param rate: Maximum number of requests allowed within the period.
    :param period: Time period in seconds.
    :param block: If True, blocks the request returning 403 Forbidden. If False, just attaches request.limited.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            ip = get_client_ip(request)
            
            # Create a unique cache key based on the prefix, IP, and the view name
            view_name = view_func.__name__
            cache_key = f"{key_prefix}:{view_name}:{ip}"
            
            # Simple counter approach (Fixed window)
            current_count = cache.get(cache_key, 0)
            
            request.limited = False
            
            if current_count >= rate:
                request.limited = True
                if block:
                    return HttpResponseForbidden("<h1>429 Too Many Requests</h1><p>กรุณารอสักครู่ก่อนทำรายการอีกครั้ง (Rate limit exceeded)</p>")
            else:
                # Increment the counter or set it if it doesn't exist
                if current_count == 0:
                    cache.set(cache_key, 1, timeout=period)
                else:
                    # In some cache backends, incr() doesn't reset timeout. 
                    # For simplicity, we just use incr and let the original timeout expire.
                    try:
                        cache.incr(cache_key)
                    except ValueError:
                        cache.set(cache_key, 1, timeout=period)
                        
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
