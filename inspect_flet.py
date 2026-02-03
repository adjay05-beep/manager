import flet as ft
import inspect

print("Dropdown Init Args:")
try:
    sig = inspect.signature(ft.Dropdown.__init__)
    for param in sig.parameters.values():
        print(f" - {param.name}")
except Exception as e:
    print(f"Error inspecting Dropdown: {e}")

print("\nAlignment attributes:")
try:
    for attr in dir(ft.alignment):
        if not attr.startswith("_"):
            print(f" - {attr}")
except Exception as e:
    print(f"Error inspecting alignment: {e}")
