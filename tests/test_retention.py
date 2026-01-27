import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from services.voice_service import VoiceService

@pytest.mark.asyncio
async def test_retention_dates():
    service = VoiceService()
    
    # Mock DB Fetch for Tier
    with patch('services.voice_service.service_supabase') as mock_db:
        # 1. Test FREE Tier
        # Mock: .table()...single().execute() -> data={"subscription_tier": "free"}
        mock_query = MagicMock()
        mock_query.execute.return_value.data = {"subscription_tier": "free"}
        mock_db.table.return_value.select.return_value.eq.return_value.single.return_value = mock_query
        
        # Test creation logic (we can't easily test internal var without refactoring, 
        # but we can check what strictly gets passed to insert)
        
        # We need to spy on the insert call
        user_id = "test-user"
        channel_id = 1
        
        await service.create_memo(user_id, channel_id, "test content")
        
        # Assert insert called with correct dates
        # Get the args passed to insert
        insert_call = mock_db.table.return_value.insert.call_args
        data = insert_call[0][0] # Arguments usually positional or kw
        
        # Check Expiry
        # Audio: ~3 days
        # Text: ~30 days
        audio_exp = datetime.fromisoformat(data['audio_expires_at'])
        text_exp = datetime.fromisoformat(data['text_expires_at'])
        
        now = datetime.now()
        diff_audio = (audio_exp - now).days
        diff_text = (text_exp - now).days
        
        assert 2 <= diff_audio <= 3  # allowing small delta
        assert 29 <= diff_text <= 30
        
        print("Free Tier Logic Verified: Audio=3d, Text=30d")

if __name__ == "__main__":
    # Manual run wrapper if pytest not avail in runtime
    import asyncio
    asyncio.run(test_retention_dates())
