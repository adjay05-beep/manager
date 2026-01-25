try:
    from realtime import SyncRealtimeClient
    import os
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    socket_url = f"{url.replace('https', 'wss')}/realtime/v1"
    
    # Simple test
    client = SyncRealtimeClient(socket_url, key)
    print("SyncRealtimeClient initialized success")
except Exception as e:
    print(f"Error: {e}")
