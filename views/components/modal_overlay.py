import flet as ft

class ModalOverlay(ft.Container):
    def __init__(self, page: ft.Page, on_dismiss=None):
        super().__init__()
        self.page_ref = page
        self.on_dismiss = on_dismiss
        
        # Overlay Styles
        self.visible = False
        self.bgcolor = "#8A000000"  # Semi-transparent black
        self.alignment = ft.Alignment(0, 0)
        self.expand = True
        self.on_click = self._handle_backdrop_click
        self.content = None # Placeholder for dialog content

    def _handle_backdrop_click(self, e):
        # Click outside the dialog card closes it
        self.close()

    def open(self, content_control: ft.Control):
        """
        Opens the modal with the specific content control (the card).
        Wait for user interaction inside the content or backdrop click.
        """
        # Wrap content to stop propagation if clicked inside
        # Note: In Flet, clicking a child doesn't automatically propagate to parent 
        # unless specifically handled, but having a container wrapper is safer.
        # However, the content_control passed should handle its own internal clicks.
        # We just set it as content.
        
        # Ensure content captures clicks so they don't reach the backdrop
        if isinstance(content_control, ft.Container):
            original_click = content_control.on_click
            def prevent_close(e):
                e.control.page.update() # Just update, don't close
                if original_click:
                    original_click(e)
            
            # Only override if not set, or we need a wrapper.
            # Easiest way: The caller should ensure the card executes 'e.control.page.update()' 
            # or simply doesn't propagate. 
            # Actually, Flet's Container on_click bubbles? No. 
            # But let's act safely.
            content_control.on_click = lambda e: e.control.page.update() 
            
        self.content = content_control
        self.visible = True
        self.page_ref.update()

    def close(self, e=None):
        self.visible = False
        self.content = None
        self.page_ref.update()
        if self.on_dismiss:
            self.on_dismiss()
