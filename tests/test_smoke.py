import pytest
from services.chat_service import get_topics
from services.calendar_service import get_all_events
from services.auth_service import auth_service

@pytest.mark.asyncio
async def test_chat_service_rbac_security():
    """Verify that an unknown user sees NO topics."""
    # Use a random UUID that definitely has no access
    random_user_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    
    topics = await get_topics(random_user_id)
    assert isinstance(topics, list)
    assert len(topics) == 0, "Security Leak: Random user saw topics!"

@pytest.mark.asyncio
async def test_calendar_service_rbac_security():
    """Verify that an unknown user sees NO events."""
    random_user_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    
    events = await get_all_events(random_user_id)
    assert isinstance(events, list)
    assert len(events) == 0, "Security Leak: Random user saw events!"

def test_auth_service_structure():
    """Verify Auth Service singleton exists and has methods."""
    assert auth_service is not None
    assert hasattr(auth_service, "sign_in")
    assert hasattr(auth_service, "sign_up")
    assert hasattr(auth_service, "verify_otp")
