# 의존성 주입 시스템

Teledrop은 **FastAPI의 의존성 주입 시스템**을 활용하여 **제어의 역전(IoC)** 및 **의존성 주입(DI)** 원칙을 구현합니다. 이를 통해 코드의 결합도를 낮추고 테스트 용이성을 높입니다.

## 의존성 주입 구조

```
app/dependencies/
├── __init__.py          # 의존성 통합 export (101줄)
├── base.py              # 기본 인프라 의존성 (30줄)
├── auth.py              # 인증 관련 의존성 (117줄)
├── types.py             # 타입 별칭 정의 (27줄)
└── handlers/            # Handler 팩토리 모듈들
    ├── __init__.py      # 핸들러 의존성 통합
    ├── drop.py          # Drop 핸들러 팩토리
    ├── file.py          # File 핸들러 팩토리
    ├── api_key.py       # API Key 핸들러 팩토리
    └── auth.py          # Auth 핸들러 팩토리
```

## 핵심 의존성 종류

Teledrop에서 사용하는 주요 의존성은 다음과 같습니다:

1. **인프라 의존성**: 데이터베이스, 스토리지, 설정 등 인프라 레이어 컴포넌트
2. **인증 의존성**: 현재 사용자, API 키 인증 등 보안 관련 컴포넌트
3. **핸들러 의존성**: 비즈니스 로직을 구현하는 핸들러 인스턴스
4. **유틸리티 의존성**: 로깅, 보안, 유효성 검사 등 유틸리티 기능

## 기본 의존성 (app/dependencies/base.py)

기본 인프라스트럭처 의존성을 제공합니다:

```python
def get_db_session() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성"""
    yield from get_session()

def get_app_settings() -> Settings:
    """애플리케이션 설정 의존성"""
    return get_settings()

def get_storage(settings: Settings = Depends(get_app_settings)) -> StorageInterface:
    """스토리지 서비스 의존성"""
    return get_storage_service(settings)
```

## 타입 별칭 (app/dependencies/types.py)

타입 힌트를 간결하게 만들기 위한 별칭을 정의합니다:

```python
# 기본 의존성들
DatabaseDep = Annotated[Session, Depends(get_db_session)]
StorageDep = Annotated[StorageInterface, Depends(get_storage)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]

# 인증 의존성들
CurrentUserDep = Annotated[dict, Depends(get_current_user)]
CurrentUserOptionalDep = Annotated[Optional[dict], Depends(get_current_user_optional)]
ApiKeyUserDep = Annotated[dict, Depends(get_api_key_user)]
```

## Handler 팩토리 패턴

핸들러 인스턴스를 생성하는 팩토리 함수들을 제공합니다:

```python
# app/dependencies/handlers/drop.py
def get_drop_create_handler():
    """DropCreateHandler 의존성 팩토리"""
    
    def _get_handler(
        session: DatabaseDep,
        storage: StorageDep,
        settings: SettingsDep
    ) -> DropCreateHandler:
        return DropCreateHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler

def get_drop_list_handler():
    """DropListHandler 의존성 팩토리"""
    
    def _get_handler(
        session: DatabaseDep,
        storage: StorageDep,
        settings: SettingsDep
    ) -> DropListHandler:
        return DropListHandler(session=session, storage_service=storage, settings=settings)
    
    return _get_handler
```

이 패턴의 장점:

1. **계층적 의존성 주입**: 핸들러가 필요로 하는 의존성들이 자동으로 주입됨
2. **재사용성**: 동일한 핸들러를 여러 라우터에서 재사용 가능
3. **테스트 용이성**: 단위 테스트에서 의존성을 쉽게 모의(Mock) 객체로 대체 가능

## 인증 의존성 (app/dependencies/auth.py)

다양한 인증 방식을 지원하는 의존성 함수들을 제공합니다:

```python
def get_current_user_optional(
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings)
) -> Optional[Dict[str, Any]]:
    """선택적 사용자 인증 - 실패해도 None 반환 (API/웹 공통)"""
    try:
        return get_user_from_auth_header(request, session, settings)
    except Exception:
        return None

def get_current_user(
    auth_data: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """필수 사용자 인증 - 실패 시 401 에러"""
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return auth_data

def get_api_key_user(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings)
) -> Dict[str, Any]:
    """API Key 인증 - X-API-Key 헤더 사용"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key가 필요합니다"
        )
    
    # API Key 검증 로직
    handler = ApiKeyValidateHandler(session=session, settings=settings)
    try:
        result = handler.execute(api_key)
        return {
            "user_id": "api",
            "is_api_key": True,
            "api_key_data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"API Key 인증 실패: {str(e)}"
        )
```

## 의존성 주입 흐름

FastAPI에서 라우터 함수가 호출될 때 의존성 주입 흐름은 다음과 같습니다:

```
1. 라우터 함수 호출 (예: GET /api/drops/{key})
   ↓
2. 함수 매개변수의 의존성 확인
   ↓
3. 기본 의존성 해결 (DB 세션, 설정 등)
   ↓
4. 인증 의존성 해결 (사용자 인증 데이터)
   ↓
5. 핸들러 의존성 해결 (핸들러 팩토리에서 핸들러 인스턴스 생성)
   ↓
6. 핸들러에 필요한 의존성 주입 (세션, 스토리지, 설정)
   ↓
7. 라우터 함수 실행 (핸들러.execute() 호출)
```

## 라우터에서의 사용 예시

```python
@router.post("/drops", response_model=DropPublic)
async def create_drop(
    drop_data: DropCreate,
    file: UploadFile = File(...),
    handler: DropCreateHandler = Depends(get_drop_create_handler()),
    auth_data: Dict[str, Any] = Depends(get_current_user)
):
    """인증된 사용자만 Drop 생성 가능"""
    result = await handler.execute(drop_data, file, auth_data=auth_data)
    return result

@router.get("/drops/{key}", response_model=DropPublic)
async def get_drop(
    key: str,
    password: Optional[str] = None,
    handler: DropDetailHandler = Depends(get_drop_detail_handler()),
    auth_data: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Drop 조회 - 인증은 선택적이지만 비밀번호 설정된 Drop은 검증 필요"""
    result = handler.execute(key, password, auth_data=auth_data)
    return result
```

## 의존성 주입의 장점

1. **관심사 분리**: 각 컴포넌트는 필요한 의존성을 명시적으로 요청
2. **단위 테스트 용이성**: 의존성을 모의 객체(Mock)로 쉽게 대체 가능
3. **코드 재사용**: 공통 의존성은 한 번 정의하고 여러 곳에서 재사용
4. **런타임 효율성**: FastAPI는 의존성 트리를 최적화하여 중복 계산 방지
5. **구성 유연성**: 런타임에 적절한 구현체를 주입 가능 (예: 테스트용 DB vs 프로덕션 DB)
6. **가독성**: 의존성이 명시적으로 선언되어 코드 의도가 명확
7. **확장성**: 새로운 의존성 추가가 기존 코드에 영향을 최소화

## 단위 테스트에서의 활용

```python
def test_drop_create_handler():
    # Mock 의존성 생성
    mock_session = Mock()
    mock_storage = Mock()
    mock_settings = Mock()
    
    # 반환 값 설정
    mock_session.add.return_value = None
    mock_storage.save_file_streaming.return_value = (Mock(), Mock())
    mock_settings.MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # Handler 인스턴스 생성 (의존성 수동 주입)
    handler = DropCreateHandler(
        session=mock_session,
        storage_service=mock_storage,
        settings=mock_settings
    )
    
    # 테스트 실행
    result = handler.execute(test_drop_data, test_file)
    
    # 검증
    assert result.title == test_drop_data.title
    mock_session.add.assert_called_once()
    mock_storage.save_file_streaming.assert_called_once()
```

## 다음 문서

- [데이터 모델](data_models.md) - SQLModel 기반 데이터 모델링
- [인프라스트럭처](infrastructure.md) - 데이터베이스 및 스토리지 