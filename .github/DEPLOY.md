# GitHub Actions 자동 배포 설정 가이드

이 프로젝트는 GitHub에 푸시하면 자동으로 Fly.io에 배포됩니다.

## 🔐 초기 설정 (한 번만 필요)

### 1. Fly.io API 토큰 생성

터미널에서 다음 명령어 실행:
```bash
fly auth token
```

또는 Fly.io 대시보드에서:
1. https://fly.io/dashboard 접속
2. Account Settings → Access Tokens
3. "Create Token" 클릭
4. 토큰 복사

### 2. GitHub Secrets에 토큰 추가

1. GitHub 저장소 페이지로 이동: https://github.com/adjay05-beep/manager
2. **Settings** → **Secrets and variables** → **Actions** 클릭
3. **New repository secret** 클릭
4. 다음 정보 입력:
   - Name: `FLY_API_TOKEN`
   - Secret: (복사한 Fly.io 토큰 붙여넣기)
5. **Add secret** 클릭

## 🚀 사용 방법

설정이 완료되면, 이후에는 다음 명령어만 실행하면 자동 배포됩니다:

```bash
git add .
git commit -m "your commit message"
git push origin main
```

GitHub Actions가 자동으로:
1. 코드 체크아웃
2. Fly.io CLI 설정
3. Fly.io에 배포

를 수행합니다.

## 📊 배포 상태 확인

- GitHub 저장소의 **Actions** 탭에서 배포 진행 상황 확인
- 배포 완료 후 https://manager-beep-v1.fly.dev/ 에서 확인

## ⚠️ 주의사항

- `main` 브랜치에 푸시될 때만 자동 배포됩니다
- 배포는 약 2-5분 정도 소요됩니다
- 배포 실패 시 GitHub Actions 탭에서 로그를 확인하세요
