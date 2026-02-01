import pytest
import uuid
import asyncio
from services.chat_service import create_topic, get_topics, send_message, get_messages, delete_topic, supabase as chat_db
from services.calendar_service import create_event, get_all_events, delete_event
from services.memo_service import save_transcription, get_memos, delete_memo
from services.auth_service import auth_service

# Mock User ID for integration tests (Must exist in profiles table via migrate_db.py)
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
# Mock Channel ID for integration tests
TEST_CHANNEL_ID = 1 

@pytest.fixture(scope="function")
def setup_test_user():
    # Login/Signup as a Test User to get a real token
    # Use random email to avoid Rate Limit Exceeded during rapid dev/test cycles
    rand_suff = uuid.uuid4().hex[:8]
    email = f"robot_{rand_suff}@example.com"
    password = "password123" 
    
    # Try Signup first
    try:
        auth_service.sign_up(email, password, "Test Robot")
    except Exception:
        # If exists, ignore
        pass

    # Login
    try:
        user = auth_service.sign_in(email, password)
        if user:
            # [CRITICAL FIX] Patch the DB client headers with the new token
            session = auth_service.get_user().session if hasattr(auth_service.get_user(), 'session') else None
            tok = chat_db.auth.get_session().access_token
            chat_db.rest.headers["Authorization"] = f"Bearer {tok}"
            print(f"Logged in as {user.email}. Token injected.")
            yield user.id
        else:
            print("Login failed. Using Mock ID (Might fail RLS).")
            yield TEST_USER_ID
    except Exception as e:
        print(f"Login Setup Error: {e}. Using Mock ID.")
        yield TEST_USER_ID

@pytest.mark.asyncio
async def test_full_chat_flow(setup_test_user):
    """Simulate: Create Topic -> Send Message -> Read -> Delete"""
    user_id = setup_test_user
    topic_name = f"Test Topic {uuid.uuid4().hex[:8]}"
    
    # 1. Create
    create_topic(topic_name, "일반", user_id, TEST_CHANNEL_ID)

    # 2. Verify Visibility
    topics = get_topics(user_id, TEST_CHANNEL_ID)
    target_topic = next((t for t in topics if t['name'] == topic_name), None)
    assert target_topic is not None, "Failed to create topic or it is invisible."
    
    tid = target_topic['id']
    
    # 3. Send Message
    send_message(tid, "Hello Robot", user_id=user_id)
    
    # 4. Read Message
    msgs = get_messages(tid)
    assert len(msgs) > 0
    assert msgs[0]['content'] == "Hello Robot"
    
    # 5. Delete Topic
    delete_topic(tid)
    
    # 6. Verify Deletion
    topics_after = get_topics(user_id, TEST_CHANNEL_ID)
    assert not any(t['id'] == tid for t in topics_after)

@pytest.mark.asyncio
async def test_full_calendar_flow(setup_test_user):
    """Simulate: Create Event -> Read -> Delete"""
    user_id = setup_test_user
    title = f"Test Event {uuid.uuid4()}"
    
    # 1. Create
    await create_event({
        "title": title,
        "start_date": "2026-01-01 10:00:00",
        "end_date": "2026-01-01 11:00:00",
        "created_by": user_id,
        "channel_id": TEST_CHANNEL_ID,
        "participant_ids": [user_id]
    })

    # 2. Verify
    events = await get_all_events(user_id, TEST_CHANNEL_ID)
    target_event = next((e for e in events if e['title'] == title), None)
    assert target_event is not None

    # 3. Delete
    await delete_event(target_event['id'], user_id)

    # 4. Verify Gone
    events_after = await get_all_events(user_id, TEST_CHANNEL_ID)
    assert not any(e['id'] == target_event['id'] for e in events_after)

@pytest.mark.asyncio
async def test_full_memo_flow(setup_test_user):
    """Simulate: Create Memo -> Read -> Delete"""
    user_id = setup_test_user
    content = f"Test Memo {uuid.uuid4()}"
    
    # 1. Create
    await save_transcription(content, user_id)
    
    # 2. Verify
    memos = await get_memos(user_id)
    target = next((m for m in memos if m['content'] == content), None)
    assert target is not None
    
    # 3. Delete
    await delete_memo(target['id'])
    
    # 4. Verify Gone
    memos_after = await get_memos(user_id)
    assert not any(m['id'] == target['id'] for m in memos_after)
