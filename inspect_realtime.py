from realtime import SyncRealtimeClient
import inspect
client = SyncRealtimeClient("ws://localhost", "key")
print("Client methods:", dir(client))
channel = client.channel("test")
print("Channel methods:", dir(channel))
