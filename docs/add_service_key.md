# Supabase Service Role 키 추가 가이드

## ⚠ RLS 정책 오류 해결

프로필 생성 시 다음 오류가 발생합니다:
```
'new row violates row-level security policy for table "profiles"'
```

이는 현재 **anon key**를 사용하고 있어 RLS 정책을 통과할 수 없기 때문입니다.

## ✅ 해결 방법: Service Role 키 추가

### 1단계: Supabase Dashboard에서 키 복사

1. **Supabase Dashboard** 접속: https://supabase.com/dashboard
2. 프로젝트 선택
3. 왼쪽 메뉴에서 **Settings** (⚙️) 클릭
4. **API** 클릭
5. **Project API keys** 섹션에서:
   - `service_role` **secret** 키 찾기
   - **복사** 버튼 클릭

> ⚠ **주의**: service_role 키는 절대 공개하지 마세요! 모든 RLS를 우회할 수 있는 관리자 키입니다.

### 2단계: .env 파일에 추가

`d:\Project A\.env` 파일을 열고 아래 줄을 **추가**하세요:

```env
SUPABASE_SERVICE_KEY=여기에_복사한_service_role_키를_붙여넣으세요
```

예시:
```env
SUPABASE_URL=https://vtsttqtbewxkxxdoyhrj.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...existing_anon_key...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...your_service_role_key...

# OpenAI (Whisper)
OPENAI_API_KEY=sk-proj-...
```

### 3단계: 서버 재시작

`start.bat`를 더블클릭하여 서버를 재시작하세요.

## 🧪 테스트

1. 브라우저 새로고침 (F5)
2. 홈 → "🆕 프로필 만들기"
3. 이름과 역할 입력
4. "프로필 만들기" 클릭

이제 정상적으로 프로필이 생성됩니다!

## 📝 기술 설명

- **anon key**: 클라이언트에서 사용, RLS 정책 적용
- **service_role key**: 서버/관리자용, RLS 우회 (모든 권한)

프로필 생성은 관리 작업이므로 service_role 키를 사용합니다.
