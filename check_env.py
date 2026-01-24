import flet as ft
print("--- Flet Environment Check ---")
print(f"Flet version: {ft.version}")
print(f"Has 'colors' module? {'colors' in dir(ft)}")
print(f"Has 'Colors' class? {'Colors' in dir(ft)}")
print(f"Has 'icons' module? {'icons' in dir(ft)}")
print(f"Has 'alignment' module? {'alignment' in dir(ft)}")

try:
    print(f"ft.colors.BLUE: {ft.colors.BLUE}")
except Exception as e:
    print(f"ft.colors.BLUE error: {e}")

try:
    print(f"ft.Colors.BLUE: {ft.Colors.BLUE}")
except Exception as e:
    print(f"ft.Colors.BLUE error: {e}")

print("------------------------------")
