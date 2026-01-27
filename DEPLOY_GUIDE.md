# Render 배포 가이드

## 개요
제공해주신 URL (Render)에서 앱이 작동하도록 설정 파일을 추가했습니다.
GitHub에 코드가 올라가면(Push), Render가 자동으로 감지하여 배포하게 됩니다.

## 1. Render 대시보드 설정 (필수!)
Render 사이트에서 해당 프로젝트의 **Environment Variables** (환경 변수) 설정에 들어가 다음 항목을 꼭 추가해야 합니다.
(GitHub Secrets와 별개로, Render 서버에도 직접 등록해야 합니다)

*   **Key**: `SUPABASE_URL`
    *   **Value**: (사용 중인 Supabase URL)
*   **Key**: `SUPABASE_KEY`
    *   **Value**: (사용 중인 Supabase Anon Key)

## 2. 배포 확인
1. 코드를 Push 하면 Render에서 자동으로 빌드 및 배포가 시작됩니다.
2. 약 2~3분 뒤 제공해주신 URL(`https://manager-gk6g.onrender.com/`)로 접속하면 앱을 확인할 수 있습니다.

> **참고**: `render.yaml` 파일을 통해 Python 버전과 실행 명령어가 자동으로 설정됩니다.
