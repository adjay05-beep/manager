
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

try:
    from services.chat_service import cleanup_empty_topics
except ImportError:
    # Handle running from scripts/ subdirectory
    sys.path.append(os.path.dirname(os.getcwd()))
    from services.chat_service import cleanup_empty_topics

if __name__ == "__main__":
    print("Running 3-Day Empty Topic Cleanup...")
    try:
        cleanup_empty_topics(days=3)
        print("Cleanup completed.")
    except Exception as e:
        print(f"Cleanup Failed: {e}")
