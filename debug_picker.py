import flet as ft
import asyncio

async def main(page: ft.Page):
    print("Starting Main...")
    page.add(ft.Text("Testing FilePicker..."))
    
    try:
        # Check AudioRecorder visibility
        try:
            print(f"AudioRecorder in ft: {hasattr(ft, 'AudioRecorder')}")
            from flet import AudioRecorder
            print("Imported AudioRecorder successfully")
        except ImportError:
            print("Could not import AudioRecorder")

        fp = ft.FilePicker()
        page.overlay.append(fp)
        page.add(ft.Button("Open Picker", on_click=lambda _: fp.pick_files()))
        print("FilePicker added successfully")
    except Exception as e:
        print(f"Error adding functionality: {e}")
        page.add(ft.Text(f"Error: {e}", color="red"))

    page.update()
    print("Page updated sync.")

if __name__ == "__main__":
    ft.app(target=main)
