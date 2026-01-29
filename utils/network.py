import time
import functools
from utils.logger import log_warning, log_error

def retry_operation(max_retries=3, delay=1.0, backoff=2.0, exceptions=(Exception,)):
    """
    Decorator to retry a function upon exception.
    
    :param max_retries: Number of retries before giving up.
    :param delay: Initial delay in seconds.
    :param backoff: Multiplier for delay after each fail.
    :param exceptions: Tuple of exceptions to catch (default: Exception).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_retries, delay
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    # Don't retry if it's a Logic Error (e.g. 400 Bad Request, Validation Error)
                    # Unless it's a 5xx Server Error or Network Error
                    msg = str(e)
                    if "400" in msg: # Client Error, do not retry
                        raise e
                    
                    log_warning(f"Retry ({max_retries - mtries + 1}/{max_retries}) for {func.__name__}: {e}")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator
