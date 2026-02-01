try:
    from realtime import AsyncRealtimeClient
    print("AsyncRealtimeClient exists")
except ImportError as e:
    print(f"AsyncRealtimeClient import fail: {e}")
