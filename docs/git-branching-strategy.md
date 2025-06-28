# Teledrop Git 브랜치 전략

## 개요

Teledrop 프로젝트는 레거시 코드의 안정성을 유지하면서 동시에 리팩터링된 코드로의 점진적 전환을 지원하는 브랜치 전략을 채택합니다. 이 문서는 모든 개발자가 일관된 방식으로 Git을 사용할 수 있도록 가이드라인을 제공합니다.

## 브랜치 구조

```
main (레거시 안정 브랜치)
├── hotfix/legacy-* (레거시 긴급 수정)
└── production (배포 브랜치)
    └── hotfix/prod-* (프로덕션 긴급 수정)

develop (새로운 개발 중심)
├── feature/* (기능 개발)
├── bugfix/* (버그 수정)
└── refactor/* (리팩터링 작업)
```

## 브랜치 역할 및 규칙

### 🏛️ main (레거시 안정 브랜치)

**목적**: 기존 레거시 코드의 안정적인 버전 유지

**규칙**:
- 직접 push 금지 (PR 필수)
- 긴급 hotfix만 허용
- 새로운 기능 개발 금지
- 리팩터링 완료 후 아카이브 예정

**사용 시나리오**:
- 레거시 시스템의 긴급 버그 수정
- 보안 패치 적용

### 🚀 production (배포 브랜치)

**목적**: 실제 프로덕션 환경에 배포되는 안정적인 코드

**규칙**:
- 관리자만 직접 push 가능
- Docker 이미지 자동 빌드 대상
- 현재는 main과 동일한 코드 유지
- 리팩터링 완료 후 develop과 동기화

**사용 시나리오**:
- 프로덕션 배포
- 긴급 hotfix 배포

### 🔧 develop (새로운 개발 중심)

**목적**: 리팩터링된 코드 기반의 모든 새로운 개발

**규칙**:
- 직접 push 금지 (PR 필수)
- 코드 리뷰 필수
- 모든 새로운 개발의 기준점
- CI/CD 테스트 통과 필수

**사용 시나리오**:
- 새로운 기능 개발의 병합 대상
- 리팩터링 작업의 중심
- 개발 환경 테스트

### 🌟 feature/* (기능 개발 브랜치)

**목적**: 새로운 기능 개발 및 개선사항

**네이밍 규칙**: `feature/[기능명]` (예: `feature/file-preview`, `feature/api-v2`)

**규칙**:
- develop에서 분기
- 하나의 기능/개선사항만 포함
- PR을 통해 develop으로 병합
- 병합 후 브랜치 삭제

**워크플로우**:
```bash
git checkout develop
git pull origin develop
git checkout -b feature/new-feature
# 개발 작업
git push origin feature/new-feature
# PR 생성: feature/new-feature → develop
```

### 🐛 bugfix/* (버그 수정 브랜치)

**목적**: develop 브랜치의 버그 수정

**네이밍 규칙**: `bugfix/[버그명]` (예: `bugfix/upload-error`, `bugfix/auth-token`)

**규칙**:
- develop에서 분기
- 하나의 버그만 수정
- PR을 통해 develop으로 병합

### 🚨 hotfix/* (긴급 수정 브랜치)

**목적**: 프로덕션 환경의 긴급 수정

**네이밍 규칙**: 
- `hotfix/legacy-[수정명]` (main에서 분기)
- `hotfix/prod-[수정명]` (production에서 분기)

**규칙**:
- main 또는 production에서 분기
- 긴급성이 확인된 이슈만 처리
- 즉시 테스트 및 배포
- 관련 브랜치들에 백포트 필요

## CI/CD 파이프라인

### 자동화된 워크플로우

| 브랜치 | 트리거 | 작업 |
|--------|--------|------|
| `production` | push | Docker 이미지 빌드 및 배포 |
| `develop` | push, PR | 테스트 실행, 코드 품질 검사 |
| `feature/*` | PR → develop | 테스트 실행, 코드 리뷰 |
| `hotfix/*` | PR | 긴급 테스트, 즉시 배포 |

### GitHub Actions 설정

현재 `.github/workflows/deploy.yml`은 production 브랜치에서 Docker 이미지를 빌드합니다.

추가 권장 워크플로우:
```yaml
# .github/workflows/test.yml
name: Test and Quality Check
on:
  push:
    branches: [ "develop" ]
  pull_request:
    branches: [ "develop" ]
```

## 브랜치 보호 규칙

GitHub에서 다음 보호 규칙을 설정해야 합니다:

### main 브랜치
- ✅ 직접 push 금지
- ✅ PR 필수
- ✅ 최소 1명의 리뷰 필요
- ✅ 관리자도 규칙 적용

### develop 브랜치
- ✅ 직접 push 금지
- ✅ PR 필수
- ✅ 최소 1명의 리뷰 필요
- ✅ CI 통과 필수
- ✅ 최신 커밋 대상만 병합 허용

### production 브랜치
- ✅ 관리자만 push 가능
- ✅ 직접 push 허용 (긴급 상황)
- ✅ CI 통과 필수

## 릴리스 프로세스

### 정기 릴리스 (리팩터링 완료 후)

1. **준비 단계**
   ```bash
   git checkout develop
   git pull origin develop
   # 최종 테스트 및 코드 리뷰
   ```

2. **릴리스 단계**
   ```bash
   git checkout production
   git merge develop
   git tag v1.0.0
   git push origin production --tags
   ```

3. **배포 확인**
   - Docker 이미지 자동 빌드 확인
   - 프로덕션 환경 상태 모니터링

### 긴급 릴리스 (Hotfix)

1. **긴급 수정**
   ```bash
   git checkout production
   git checkout -b hotfix/prod-critical-fix
   # 수정 작업
   git push origin hotfix/prod-critical-fix
   ```

2. **즉시 배포**
   ```bash
   git checkout production
   git merge hotfix/prod-critical-fix
   git push origin production
   ```

3. **백포트** (필요시)
   ```bash
   git checkout develop
   git cherry-pick <hotfix-commit>
   git push origin develop
   ```

## 마이그레이션 계획

### Phase 1: 브랜치 정리 (즉시 실행)

```bash
# 1. refactor/backend를 develop으로 rename
git checkout refactor/backend
git branch -m develop
git push origin develop
git push origin --delete refactor/backend

# 2. development 브랜치 삭제
git push origin --delete development

# 3. 로컬 브랜치 정리
git branch -d refactor/backend
git remote prune origin
```

### Phase 2: 브랜치 보호 규칙 적용 (1주 내)

- GitHub 저장소 설정에서 브랜치 보호 규칙 설정
- 팀원들에게 새로운 전략 공유

### Phase 3: 리팩터링 완료 후 (향후)

```bash
# production 브랜치를 develop과 동기화
git checkout production
git merge develop
git push origin production

# main 브랜치 아카이브
git tag archive/main-legacy
git push origin archive/main-legacy
```

## 베스트 프랙티스

### 커밋 메시지

Conventional Commits 형식을 따릅니다:
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

예시:
```
feat(api): Add file preview endpoint
fix(auth): Resolve JWT token validation issue
docs(readme): Update installation instructions
```

### 브랜치 명명 규칙

- `feature/[기능명]`: 새 기능 개발
- `bugfix/[버그명]`: 버그 수정
- `hotfix/[유형]-[수정명]`: 긴급 수정
- `refactor/[영역]`: 리팩터링 작업

### PR 가이드라인

1. **제목**: 명확하고 간결한 변경사항 설명
2. **설명**: 변경 이유, 영향도, 테스트 방법 포함
3. **리뷰어**: 적절한 리뷰어 지정
4. **라벨**: 변경 유형에 맞는 라벨 추가

## 문제 해결

### 일반적인 시나리오

**Q: develop 브랜치가 main보다 앞서있는 상황**
A: 정상적인 상황입니다. 리팩터링 완료 후 production과 동기화할 예정입니다.

**Q: 긴급 수정이 필요한 경우**
A: production에서 hotfix 브랜치를 생성하여 수정 후 즉시 병합합니다.

**Q: feature 브랜치가 오래된 경우**
A: develop에서 rebase 또는 merge하여 최신 상태로 유지합니다.

## 연락처

이 브랜치 전략에 대한 질문이나 개선 제안이 있으시면 프로젝트 관리자에게 연락해 주세요.

---

**문서 버전**: 1.0  
**최종 수정**: 2024-12-19  
**다음 검토**: 리팩터링 완료 후 