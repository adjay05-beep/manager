import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(scope="session")
def test_user_id():
    # Use the mock admin ID for smoke testing
    return "00000000-0000-0000-0000-000000000001"

@pytest.fixture(scope="session")
def real_auth_creds():
    # In a real CI, these would come from env vars
    return {
        "email": "admin@example.com",
        "password": "password123"
    }
