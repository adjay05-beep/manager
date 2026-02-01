import flet as ft

class CustomCheckbox(ft.Container):
    def __init__(self, label="", value=False, on_change=None, label_style=None, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label
        self.value = value
        self.on_change = on_change
        self.label_style = label_style or ft.TextStyle(color="grey", size=14)
        
        self.check_icon = ft.Icon(
            ft.Icons.CHECK_ROUNDED,
            color="black",
            size=18,
            visible=self.value
        )
        
        self.box = ft.Container(
            content=self.check_icon,
            width=22,
            height=22,
            border=ft.border.all(1.5, "black"),
            border_radius=4,
            bgcolor="white",
            alignment=ft.Alignment(0, 0),
        )
        
        self.content = ft.Row([
            self.box,
            ft.Text(self.label_text, style=self.label_style) if self.label_text else ft.Container()
        ], spacing=10, vertical_alignment="center")
        
        self.on_click = self._toggle
        self.mouse_cursor = ft.MouseCursor.CLICK

    def _toggle(self, e):
        self.value = not self.value
        self.check_icon.visible = self.value
        self.box.update()
        if self.on_change:
            # Simulate Flet event object if possible, or just pass value
            self.on_change(self)

    def update_value(self, new_val):
        self.value = new_val
        self.check_icon.visible = self.value
        if self.box.page:
            self.box.update()
