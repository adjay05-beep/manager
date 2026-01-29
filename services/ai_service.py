import os
import requests
import json
import datetime
from typing import List, Dict, Any, Optional
from utils.logger import log_info, log_error

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def analyze_chat_for_calendar(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes a list of chat messages to extract a summary and a target date for a calendar event.
    Returns:
        {
            "summary": "Short description of the task/event",
            "date": "YYYY-MM-DD" (or None if not found, logic should default to today)
        }
    """
    if not OPENAI_API_KEY:
        log_error("AI Service Error: OPENAI_API_KEY not found.")
        return {"summary": "Error: API Key missing", "date": None}

    # 1. Format messages for prompt
    # specific format: "User (Time): Message"
    conversation_text = ""
    for msg in messages:
        # Check keys based on db schema: 'content', 'profiles' -> 'full_name'
        sender = msg.get('profiles', {}).get('full_name', 'Unknown')
        content = msg.get('content', '')
        ts = msg.get('created_at', '')
        conversation_text += f"- [{ts[:10]}] {sender}: {content}\n"

    today_str = datetime.date.today().isoformat()

    # 2. Construct Prompt
    system_prompt = f"""
    You are a helpful assistant for a store management team.
    Analyze the following chat conversation history.
    Your goal is to extract a "To-Do" or "Event" that needs to be put on a calendar.
    
    1. **Summary**: Create a concise, one-line summary of the main task or event discussed (max 10 words). Korean language.
    2. **Date**: Identify the specific date mentioned (YYYY-MM-DD). If none, use {today_str}.
    3. **Time**: Identify the specific time mentioned (HH:MM 24-hour format). If none, return null.

    Return ONLY a JSON object with keys "summary", "date", and "time".
    Example: {{"summary": "체험단 2명 방문", "date": "2024-02-15", "time": "19:00"}}
    """

    user_prompt = f"Conversation:\n{conversation_text}"

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini", # Cost-effective model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            },
            timeout=10
        )
        
        response.raise_for_status()
        result = response.json()
        
        content_str = result['choices'][0]['message']['content']
        parsed = json.loads(content_str)
        
        log_info(f"AI Analysis Result: {parsed}")
        return parsed

    except requests.exceptions.HTTPError as http_err:
        log_error(f"AI Service HTTP Error: {http_err}")
        status = http_err.response.status_code
        msg = "AI 요청 실패"
        if status == 401: msg = "오류: API 키 인증 실패 (환경변수 확인)"
        elif status == 429: msg = "오류: API 사용 한도 초과 (충전 필요)"
        elif status == 500: msg = "오류: AI 서버 내부 에러"
        
        return {"summary": msg, "date": today_str}
        
    except requests.exceptions.Timeout:
        log_error("AI Service Timeout")
        return {"summary": "오류: 응답 시간 초과 (네트워크 확인)", "date": today_str}
        
    except Exception as e:
        log_error(f"AI Service Error: {e}")
        return {
            "summary": f"오류: {str(e)[:30]}...", 
            "date": today_str
        }
