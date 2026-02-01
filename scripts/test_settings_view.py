import flet as ft
from views.store_manage_view import get_store_manage_controls
import logging

# Mock logging
logging.basicConfig(level=logging.DEBUG)

class MockSession:
    def __init__(self):
        self.data = {
            "user_id": "ce89c5a4-7f97-4900-a89e-18a713c7968f",
            "channel_id": 1,
            "user_role": "owner",
            "user_email": "test@example.com"
        }
    def get(self, key): return self.data.get(key)
    def set(self, key, value): self.data[key] = value

class MockPage:
    def __init__(self):
        self.session = MockSession()
        self.controls = []
        self.snack_bar = None
    def update(self): print("Page updated")
    def set_clipboard(self, val): print(f"Clipboard: {val}")

def test_view():
    print("--- Testing Store Manage View ---")
    page = MockPage()
    controls = get_store_manage_controls(page, lambda x: print(f"Navigate to {x}"))
    print("View Loaded.")

if __name__ == "__main__":
    test_view()
