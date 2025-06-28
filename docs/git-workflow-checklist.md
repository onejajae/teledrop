# Git 워크플로우 체크리스트

## 🚀 새 기능 개발

### 시작하기
- [ ] `develop` 브랜치에서 최신 코드 pull
- [ ] 기능명으로 새 브랜치 생성: `feature/[기능명]`
- [ ] 브랜치가 올바른 명명 규칙을 따르는지 확인

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### 개발 중
- [ ] 커밋 메시지가 Conventional Commits 형식을 따르는지 확인
- [ ] 하나의 기능/개선사항만 포함되었는지 확인
- [ ] 적절한 테스트 코드 작성
- [ ] 코드 스타일 가이드 준수

### 완료 후
- [ ] 최종 테스트 실행
- [ ] `develop` 브랜치와 충돌 확인 및 해결
- [ ] PR 생성 (`feature/[기능명]` → `develop`)
- [ ] PR에 적절한 설명과 라벨 추가
- [ ] 코드 리뷰 완료 후 병합
- [ ] 로컬 feature 브랜치 삭제

```bash
# PR 병합 후
git checkout develop
git pull origin develop
git branch -d feature/your-feature-name
```

## 🐛 버그 수정

### 시작하기
- [ ] `develop` 브랜치에서 최신 코드 pull
- [ ] 버그명으로 새 브랜치 생성: `bugfix/[버그명]`

```bash
git checkout develop
git pull origin develop
git checkout -b bugfix/fix-upload-error
```

### 수정 완료 후
- [ ] 버그가 실제로 수정되었는지 테스트
- [ ] PR 생성 (`bugfix/[버그명]` → `develop`)
- [ ] 리뷰 완료 후 병합

## 🚨 긴급 수정 (Hotfix)

### 레거시 시스템 긴급 수정
- [ ] `main` 브랜치에서 분기
- [ ] 브랜치명: `hotfix/legacy-[수정명]`
- [ ] 즉시 테스트 및 검증
- [ ] PR 생성 (`hotfix/legacy-[수정명]` → `main`)

```bash
git checkout main
git pull origin main
git checkout -b hotfix/legacy-security-fix
# 수정 작업
git push origin hotfix/legacy-security-fix
```

### 프로덕션 긴급 수정
- [ ] `production` 브랜치에서 분기
- [ ] 브랜치명: `hotfix/prod-[수정명]`
- [ ] 즉시 테스트 및 검증
- [ ] PR 생성 (`hotfix/prod-[수정명]` → `production`)
- [ ] 필요시 `develop` 브랜치에 백포트

```bash
git checkout production
git pull origin production
git checkout -b hotfix/prod-critical-fix
# 수정 작업
git push origin hotfix/prod-critical-fix
```

## 📋 PR 생성 체크리스트

### PR 제목
- [ ] 명확하고 간결한 변경사항 설명
- [ ] Conventional Commits 형식 사용 (선택사항)

### PR 설명
- [ ] **변경사항**: 무엇을 변경했는지
- [ ] **이유**: 왜 이 변경이 필요한지
- [ ] **테스트**: 어떻게 테스트했는지
- [ ] **영향도**: 다른 부분에 미치는 영향
- [ ] **스크린샷**: UI 변경시 스크린샷 첨부

### 리뷰 전
- [ ] 적절한 리뷰어 지정
- [ ] 관련 라벨 추가
- [ ] CI 테스트 통과 확인
- [ ] 충돌 해결 완료

## 🔄 일반적인 작업

### 브랜치 상태 확인
```bash
# 현재 브랜치 확인
git branch

# 원격 브랜치와 동기화 상태 확인
git status

# 리모트 브랜치 목록 확인
git branch -r
```

### develop과 동기화
```bash
# feature 브랜치에서 develop의 최신 변경사항 가져오기
git checkout feature/your-feature
git fetch origin
git rebase origin/develop

# 또는 merge 사용
git merge origin/develop
```

### 브랜치 정리
```bash
# 원격에서 삭제된 브랜치 정리
git remote prune origin

# 로컬에서 병합된 브랜치 삭제
git branch --merged develop | grep -v "develop\|main\|production" | xargs -n 1 git branch -d
```

## ⚠️ 주의사항

### 절대 하지 말아야 할 것
- [ ] ❌ `main` 브랜치에 직접 push
- [ ] ❌ `production` 브랜치에 직접 push (관리자 제외)
- [ ] ❌ `develop` 브랜치에 직접 push
- [ ] ❌ force push를 공유 브랜치에 사용
- [ ] ❌ 여러 기능을 하나의 PR에 포함

### 권장사항
- [ ] ✅ 작은 단위로 자주 커밋
- [ ] ✅ 의미있는 커밋 메시지 작성
- [ ] ✅ PR 전에 로컬에서 충분히 테스트
- [ ] ✅ 코드 리뷰에서 받은 피드백 적극 반영
- [ ] ✅ 브랜치를 최신 상태로 유지

## 📞 도움이 필요할 때

### 자주 발생하는 문제
1. **충돌 해결이 어려울 때**: 팀원에게 도움 요청
2. **실수로 잘못된 브랜치에 커밋**: `git cherry-pick` 사용
3. **커밋 메시지 수정**: `git commit --amend` 사용
4. **브랜치 전략이 헷갈릴 때**: [docs/git-branching-strategy.md](git-branching-strategy.md) 참고

### 비상 연락처
Git 관련 문제나 브랜치 전략에 대한 질문이 있으면 프로젝트 관리자에게 연락하세요.

---

**💡 팁**: 이 체크리스트를 즐겨찾기에 추가하여 매번 Git 작업 시 참고하세요! 