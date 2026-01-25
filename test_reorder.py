import flet as ft

def main(page: ft.Page):
    def on_reorder(e):
        c = lv.controls.pop(e.old_index)
        lv.controls.insert(e.new_index, c)
        page.update()

    lv = ft.ReorderableListView(
        show_default_drag_handles=False,
        on_reorder=on_reorder,
        controls=[
            ft.Container(
                key="1",
                content=ft.Row([
                    ft.Icon(ft.Icons.DRAG_HANDLE), # Can I make this a handle?
                    ft.Text("Item 1")
                ])
            ),
            ft.Container(
                key="2",
                content=ft.Row([
                    ft.Icon(ft.Icons.DRAG_HANDLE),
                    ft.Text("Item 2")
                ])
            )
        ]
    )
    page.add(lv)

ft.app(target=main)
