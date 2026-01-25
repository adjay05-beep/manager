import sys
import os

print("Verifying Refactor Imports...")

try:
    from views.login_view import get_login_controls
    print("✅ Login View Imported")
    
    from views.home_view import get_home_controls
    print("✅ Home View Imported")
    
    from views.chat_view import get_chat_controls
    print("✅ Chat View Imported") # Depends on services.chat_service
    
    from views.calendar_view import get_calendar_controls
    print("✅ Calendar View Imported")
    
    from views.order_view import get_order_controls
    print("✅ Order View Imported")
    
    from services import chat_service
    print("✅ Chat Service Imported")
    
    from services import calendar_service
    print("✅ Calendar Service Imported")
    
    from services import memo_service
    print("✅ Memo Service Imported")
    
    print("ALL IMPORTS SUCCESSFUL")
except Exception as e:
    print(f"❌ IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
