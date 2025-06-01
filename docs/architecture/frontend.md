# 프론트엔드 아키텍처 지원

Teledrop은 **단일 백엔드**에서 **다양한 프론트엔드 방식**을 동시에 지원하도록 설계되었습니다. 이는 Handler 패턴을 통해 비즈니스 로직을 분리함으로써 가능해졌습니다.

## 다중 프론트엔드 아키텍처

Teledrop은 두 가지 주요 프론트엔드 방식을 지원합니다:

1. **SPA(Single Page Application)** - 현재 구현
2. **SSR(Server-Side Rendering)** - 향후 구현 예정

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Options                         │
│  ┌─────────────────┐                 ┌─────────────────┐    │
│  │   SPA Frontend  │                 │   SSR Frontend  │    │
│  │   (SvelteKit)   │                 │ (FastAPI+Jinja) │    │
│  │                 │                 │                 │    │
│  │ • REST API 호출  │                 │ • 템플릿 렌더링   │    │
│  │ • 클라이언트 렌더링 │                 │ • 서버 사이드 렌더링│    │
│  │ • JSON 응답     │                 │ • HTML 응답     │    │
│  └─────────────────┘                 └─────────────────┘    │
│           │                                   │             │
│           ▼                                   ▼             │
│  ┌─────────────────┐                 ┌─────────────────┐    │
│  │  API Routes     │                 │  Web Routes     │    │
│  │ /api/drops      │                 │ /drops          │    │
│  │ /api/files      │                 │ /files          │    │
│  │ /api/auth       │                 │ /auth           │    │
│  └─────────────────┘                 └─────────────────┘    │
│           │                                   │             │
│           └─────────────┬─────────────────────┘             │
│                         ▼                                   │
│              ┌─────────────────┐                            │
│              │    Handlers     │                            │
│              │  (공통 로직)     │                            │
│              │                 │                            │
│              │ • DropHandler   │                            │
│              │ • FileHandler   │                            │
│              │ • AuthHandler   │                            │
│              └─────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

## 핸들러를 통한 코드 중복 방지

Teledrop 아키텍처의 핵심은 **동일한 Handler가 다양한 프론트엔드를 지원**한다는 것입니다. 이를 통해:

1. **비즈니스 로직 중복 제거**: REST API와 SSR 웹 페이지가 동일한 비즈니스 로직을 공유
2. **일관된 데이터 처리**: 모든 인터페이스에서 동일한 검증 및 처리 로직 적용
3. **유지보수 간소화**: 로직 변경 시 한 곳만 수정하면 모든 프론트엔드에 반영
4. **테스트 용이성**: 핸들러만 테스트하면 모든 인터페이스에 대한 검증 가능

### 핸들러 재사용 패턴

```python
# 동일한 Handler, 다른 응답 방식
class DropCreateHandler(BaseHandler):
    async def execute(self, data: DropCreateData, auth_data=None) -> DropResponse:
        # 공통 비즈니스 로직
        # 1. 검증
        # 2. 데이터 처리
        # 3. 저장
        return DropResponse(...)

# API 엔드포인트 - JSON 응답
@api_router.post("/drops")
async def api_create_drop(
    data: DropCreateRequest,
    handler: DropCreateHandler = Depends(get_drop_create_handler()),
    auth_data: Optional[dict] = Depends(get_current_user_optional)
):
    """API 엔드포인트 - JSON 응답"""
    result = await handler.execute(data, auth_data)
    return result  # FastAPI가 자동으로 JSON으로 직렬화

# 웹 엔드포인트 - HTML 템플릿 응답
@web_router.post("/drops")
async def web_create_drop(
    request: Request,
    data: DropCreateRequest = Form(...),
    handler: DropCreateHandler = Depends(get_drop_create_handler()),
    auth_data: Optional[dict] = Depends(get_current_user_optional)
):
    """웹 엔드포인트 - HTML 템플릿 렌더링"""
    try:
        result = await handler.execute(data, auth_data)
        return templates.TemplateResponse("drop_success.html", {
            "request": request,
            "drop": result,
            "message": "Drop이 성공적으로 생성되었습니다."
        })
    except Exception as e:
        return templates.TemplateResponse("drop_form.html", {
            "request": request,
            "error": str(e),
            "form_data": data
        })
```

## 1. SPA 프론트엔드 (현재 구현)

**특징**:
- SvelteKit 기반 클라이언트 사이드 렌더링
- API Routes(`/api/*`)를 통한 데이터 통신
- JSON 응답 처리
- 동적인 사용자 인터페이스
- 현재 Teledrop의 기본 프론트엔드 방식

**API 호출 예시**:
```javascript
// SPA에서 Drop 생성
const response = await fetch('/api/drops', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dropData)
});
const result = await response.json();
```

**API 라우터 구현**:
```python
# app/routers/api/drop_router.py
@router.post("/drops", response_model=DropResponse)
async def create_drop_api(
    data: DropCreateRequest,
    handler: DropCreateHandler = Depends(get_drop_create_handler()),
    auth_data: Optional[dict] = Depends(get_current_user_optional)
):
    """API 엔드포인트 - JSON 응답"""
    result = await handler.execute(data, auth_data)
    return result  # FastAPI가 자동으로 JSON으로 직렬화
```

## 2. SSR 프론트엔드 (향후 구현)

**특징**:
- FastAPI + Jinja2 템플릿 기반 서버 사이드 렌더링
- Web Routes(`/web/*` 또는 직접 경로)를 통한 HTML 제공
- **동일한 Handler를 사용하여 로직 재사용** (핵심 장점)
- HTML 응답 및 서버에서 완성된 페이지 제공
- SEO 최적화 및 빠른 초기 로딩

**웹 라우터 구현 예시**:
```python
# app/routers/web/drop_router.py (향후 구현)
from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@router.post("/drops")
async def create_drop_web(
    request: Request,
    data: DropCreateRequest = Form(...),
    handler: DropCreateHandler = Depends(get_drop_create_handler()),
    auth_data: Optional[dict] = Depends(get_current_user_optional)
):
    """웹 엔드포인트 - 동일한 핸들러 사용, 다른 응답 형식"""
    try:
        # 핸들러 실행 - API 엔드포인트와 동일한 로직
        result = await handler.execute(data, auth_data)
        
        # 템플릿으로 응답 - API와 달리 HTML 반환
        return templates.TemplateResponse("drop_success.html", {
            "request": request,
            "drop": result,
            "message": "Drop이 성공적으로 생성되었습니다."
        })
    except Exception as e:
        return templates.TemplateResponse("drop_form.html", {
            "request": request,
            "error": str(e),
            "form_data": data
        })
```

## 핸들러 패턴의 이점: 실제 사례

### 중복 방지 사례: Drop 접근 권한 검증

```python
# API 라우터
@api_router.get("/drops/{key}")
async def get_drop_api(
    key: str,
    password: Optional[str] = None,
    handler: DropDetailHandler = Depends(get_drop_detail_handler()),
    auth_data: Optional[dict] = Depends(get_current_user_optional)
):
    """API를 통한 Drop 조회"""
    drop = await handler.execute(key, password, auth_data)
    return drop  # JSON 응답

# 웹 라우터 (향후 구현)
@web_router.get("/drops/{key}")
async def get_drop_web(
    request: Request,
    key: str,
    password: Optional[str] = Form(None),
    handler: DropDetailHandler = Depends(get_drop_detail_handler()),
    auth_data: Optional[dict] = Depends(get_current_user_optional)
):
    """웹 페이지를 통한 Drop 조회"""
    try:
        # 동일한 핸들러 사용 - 비즈니스 로직 중복 없음
        drop = await handler.execute(key, password, auth_data)
        return templates.TemplateResponse("drop_detail.html", {
            "request": request,
            "drop": drop
        })
    except DropNotFoundError:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "요청하신 Drop을 찾을 수 없습니다."
        }, status_code=404)
    except DropPasswordInvalidError:
        return templates.TemplateResponse("password_form.html", {
            "request": request,
            "key": key,
            "error": "잘못된 비밀번호입니다."
        })
```

### 비즈니스 로직 변경 시 이점

핸들러 패턴의 핵심 이점은 비즈니스 로직 변경 시 모든 인터페이스에 일관되게 적용된다는 점입니다:

```python
# 핸들러에 새로운 보안 기능 추가
class DropDetailHandler(BaseHandler):
    async def execute(self, key, password=None, auth_data=None):
        # 새로운 보안 기능: 접근 제한 로직 추가
        if self.settings.ENABLE_RATE_LIMITING:
            self._check_rate_limit(key, auth_data)
            
        # 기존 로직 계속 실행
        drop = self._get_drop(key)
        self._validate_access(drop, password, auth_data)
        return drop
```

이 변경 사항은 **API와 웹 인터페이스 모두에 자동으로 적용**됩니다. 라우터 코드를 수정할 필요가 없습니다.

## 라우터 구조

```
app/routers/
├── __init__.py          # 라우터 통합 및 등록
├── api/                 # REST API 엔드포인트 (현재 구현)
│   ├── __init__.py      # API 라우터 통합
│   ├── auth_router.py   # 인증 API (/api/auth/*)
│   ├── drop_router.py   # Drop 관리 API (/api/drops/*)
│   └── api_key_router.py # API Key 관리 (/api/keys/*)
└── web/                 # SSR 웹 인터페이스 (향후 구현)
    ├── __init__.py      # 웹 라우터 통합
    ├── auth_router.py   # 인증 웹 페이지 (/auth/*)
    ├── drop_router.py   # Drop 관리 웹 페이지 (/drops/*)
    └── dashboard_router.py # 대시보드 페이지 (/)
```

## 구현 상태

**✅ 구현 완료**:
- SPA 프론트엔드 (SvelteKit)
- REST API 엔드포인트 (`/api/*`)
- Handler 기반 비즈니스 로직
- API 기반 인증 시스템

**🔄 향후 구현 예정**:
- SSR 웹 인터페이스 (`/web/*`)
- Jinja2 템플릿 시스템
- 폼 기반 인증
- SEO 최적화된 페이지

## 다음 단계

향후 SSR 구현 시, 기존 핸들러를 재사용하여 웹 인터페이스를 구축함으로써 빠르고 일관된 개발이 가능할 것입니다. 이는 **하나의 백엔드에서 다양한 프론트엔드를 효율적으로 지원**하는 Teledrop 아키텍처의 핵심 강점입니다.

## 다음 문서

- [의존성 주입 시스템](dependency_injection.md) - 의존성 주입 패턴
- [데이터 모델](data_models.md) - SQLModel 기반 데이터 모델링 