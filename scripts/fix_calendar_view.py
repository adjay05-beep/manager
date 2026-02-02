import os

file_path = r"d:\Project A\views\calendar_view.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "class CalendarDialogManager:" in line:
        start_idx = i
    if "async def get_calendar_controls(page: ft.Page, navigate_to):" in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Found class at {start_idx}, next func at {end_idx}")
    
    new_class_code = [
        "    def __init__(self, page, rebuild_callback=None):\n",
        "        import uuid\n",
        "        self.page = page\n",
        "        self.current_dialog = None\n",
        "        self.rebuild_callback = rebuild_callback\n",
        "        self.mgr_id = str(uuid.uuid4())[:4]\n",
        "        print(f\"DEBUG_MGR [{self.mgr_id}]: INIT. Page ID: {id(page)}\")\n",
        "\n",
        "    def open(self, dialog):\n",
        "        print(f\"DEBUG_MGR [{self.mgr_id}]: Opening dialog {type(dialog).__name__} (Nuclear Combo). Page ID: {id(self.page)}\")\n",
        "        self.close_force() # Clean slate\n",
        "        \n",
        "        self.current_dialog = dialog\n",
        "        dialog.open = True\n",
        "        self.page.overlay.append(dialog)\n",
        "        self.page.update()\n",
        "\n",
        "    def close_force(self):\n",
        "        print(f\"DEBUG_MGR [{self.mgr_id}]: FORCE Closing dialog (Nuclear Combo). Page ID: {id(self.page)}\")\n",
        "        \n",
        "        # 1. SIGNAL CLOSE (Client needs this to remove Modal Barrier)\n",
        "        try:\n",
        "            if self.page.overlay:\n",
        "                for c in self.page.overlay:\n",
        "                    if hasattr(c, \"open\"):\n",
        "                        c.open = False\n",
        "                    if hasattr(c, \"visible\"):\n",
        "                        c.visible = False\n",
        "                self.page.update() # Flush Close Signal\n",
        "                print(f\"DEBUG_MGR [{self.mgr_id}]: Sent open=False signal.\")\n",
        "        except Exception as e:\n",
        "            print(f\"DEBUG_MGR [{self.mgr_id}]: Signal error: {e}\")\n",
        "\n",
        "        # 2. SCORCHED EARTH (Clear Overlay)\n",
        "        try:\n",
        "            count = len(self.page.overlay)\n",
        "            self.page.overlay.clear()\n",
        "            print(f\"DEBUG_MGR [{self.mgr_id}]: CLEARED {count} items from overlay.\")\n",
        "            self.page.update() # Flush Removal\n",
        "        except Exception as e:\n",
        "            print(f\"DEBUG_MGR [{self.mgr_id}]: Clear error: {e}\")\n",
        "        \n",
        "        self.current_dialog = None\n",
        "        \n",
        "        # Rebuild\n",
        "        try:\n",
        "            if self.rebuild_callback:\n",
        "                print(f\"DEBUG_MGR [{self.mgr_id}]: Rebuild triggered\")\n",
        "                self.rebuild_callback()\n",
        "        except: pass\n",
        "\n",
        "    def close(self):\n",
        "        self.close_force()\n",
        "        \n",
        "    def close_all(self):\n",
        "        self.close_force()\n",
        "\n",
        "    def cleanup_pickers(self):\n",
        "        # Already handled by clear()\n",
        "        pass\n",
        "\n"
    ]
    
    final_lines = lines[:start_idx+1] + new_class_code + lines[end_idx:]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
    print("SUCCESS: File updated with Nuclear Combo logic.")
else:
    print("ERROR: Could not find start/end markers.")
