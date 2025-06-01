# 에러 처리

Teledrop은 견고한 예외 처리 시스템을 통해 애플리케이션의 안정성과 사용자 경험을 향상시킵니다. 이 문서에서는 예외 계층 구조, 처리 패턴, HTTP 응답 매핑에 대해 설명합니다.

## 계층적 예외 구조

Teledrop은 명확한 예외 계층 구조를 사용하여 다양한 오류 상황을 구분합니다:

```
app/core/exceptions.py
```

```python
# 기본 예외 클래스
class TeledropError(Exception):
    """Teledrop 애플리케이션의 기본 예외 클래스"""
    
    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)

# 도메인별 예외 그룹
class ValidationError(TeledropError):
    """입력 검증 관련 오류"""
    pass

class NotFoundError(TeledropError):
    """리소스를 찾을 수 없는 오류"""
    pass

class AuthenticationError(TeledropError):
    """인증 관련 오류"""
    pass

class AuthorizationError(TeledropError):
    """권한 관련 오류"""
    pass

class StorageError(TeledropError):
    """스토리지 관련 오류"""
    pass

# 구체적인 예외들
class DropNotFoundError(NotFoundError):
    """Drop을 찾을 수 없는 경우"""
    pass

class FileNotFoundError(NotFoundError):
    """파일을 찾을 수 없는 경우"""
    pass

class DropPasswordRequiredError(ValidationError):
    """Drop 패스워드가 필요한 경우"""
    pass

class DropPasswordInvalidError(AuthenticationError):
    """Drop 패스워드가 유효하지 않은 경우"""
    pass

class DropAccessDeniedError(AuthorizationError):
    """Drop 접근 권한이 없는 경우"""
    pass

class ApiKeyNotFoundError(NotFoundError):
    """API 키를 찾을 수 없는 경우"""
    pass

class ApiKeyExpiredError(AuthenticationError):
    """API 키가 만료된 경우"""
    pass

class FileSizeExceededError(ValidationError):
    """파일 크기가 제한을 초과한 경우"""
    pass

class FileTypeNotAllowedError(ValidationError):
    """허용되지 않는 파일 타입인 경우"""
    pass

class StorageWriteError(StorageError):
    """스토리지 쓰기 오류"""
    pass

class StorageReadError(StorageError):
    """스토리지 읽기 오류"""
    pass
```

## Handler 내 예외 처리

핸들러는 비즈니스 로직에서 발생하는 예외를 명확히 정의하고 처리합니다:

```python
# app/handlers/drop/access.py
@dataclass
class DropAccessHandler(BaseHandler, ValidationMixin):
    """Drop 접근 권한 검증 Handler"""
    
    session: Session
    settings: Settings
    
    def execute(
        self,
        drop_key: str,
        password: Optional[str] = None,
        auth_data: Optional[Dict[str, Any]] = None,
        require_auth: bool = False
    ) -> Drop:
        """
        Drop 접근 권한을 검증합니다.
        
        Args:
            drop_key: Drop 키
            password: Drop 패스워드 (있는 경우)
            auth_data: 인증 정보
            require_auth: 인증 필수 여부
            
        Returns:
            Drop: 검증된 Drop 객체
            
        Raises:
            DropNotFoundError: Drop을 찾을 수 없는 경우
            DropPasswordRequiredError: 패스워드가 필요하지만 제공되지 않은 경우
            DropPasswordInvalidError: 패스워드가 유효하지 않은 경우
            DropAccessDeniedError: 접근 권한이 없는 경우
            AuthenticationError: 인증이 필요하지만 제공되지 않은 경우
        """
        self.log_info("Validating drop access", key=drop_key)
        
        try:
            # 1. Drop 조회
            drop = Drop.get_by_key(self.session, drop_key)
            if not drop:
                self.log_warning("Drop not found", key=drop_key)
                raise DropNotFoundError(f"Drop with key '{drop_key}' not found")
            
            # 2. 인증 여부 확인 (필요한 경우)
            if require_auth and not auth_data and self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
                self.log_warning("Authentication required", key=drop_key)
                raise AuthenticationError("Authentication required for this operation")
            
            # 3. User-only Drop 접근 권한 확인
            if drop.user_only and not auth_data and self.settings.REQUIRE_AUTH_FOR_SENSITIVE_OPS:
                self.log_warning("Access denied to user-only drop", key=drop_key)
                raise DropAccessDeniedError("This drop requires authentication")
            
            # 4. 패스워드 검증
            if self.settings.ENABLE_PASSWORD_PROTECTION and drop.password:
                if not password:
                    self.log_warning("Password required but not provided", key=drop_key)
                    raise DropPasswordRequiredError("Password is required for this drop")
                
                if not verify_password(password, drop.password):
                    self.log_warning("Invalid password for drop", key=drop_key)
                    raise DropPasswordInvalidError("Invalid password for drop")
            
            self.log_info("Drop access validated successfully", key=drop_key)
            return drop
            
        except (DropNotFoundError, AuthenticationError, DropAccessDeniedError, 
                DropPasswordRequiredError, DropPasswordInvalidError) as e:
            # 이미 정의된 예외는 그대로 전파
            raise
            
        except Exception as e:
            # 예상치 못한 예외는 로깅 후 일반 TeledropError로 변환
            self.log_error("Unexpected error validating drop access", 
                         key=drop_key, error=str(e), exc_info=True)
            raise TeledropError(f"Error validating drop access: {str(e)}")
```

## 라우터에서의 예외 처리

라우터에서는 핸들러에서 발생한 예외를 적절한 HTTP 응답으로 변환합니다:

```python
# app/routers/api/drop_router.py
@router.get("/{key}", response_model=DropPublic)
async def get_drop(
    key: str,
    password: Optional[str] = None,
    handler: DropDetailHandler = Depends(get_drop_detail_handler()),
    auth_data: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    """Drop 조회"""
    try:
        result = handler.execute(key, password, auth_data=auth_data)
        return result
    except DropNotFoundError:
        raise HTTPException(status_code=404, detail="Drop not found")
    except DropPasswordRequiredError:
        raise HTTPException(status_code=401, detail="Password is required for this drop")
    except DropPasswordInvalidError:
        raise HTTPException(status_code=401, detail="Invalid password")
    except DropAccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied")
    except AuthenticationError:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 예상치 못한 예외는 로깅 후 500 에러
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 전역 예외 핸들러

애플리케이션 레벨에서 처리되지 않은 예외를 포착하는 전역 예외 핸들러:

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException

from app.core.exceptions import TeledropError

def create_app() -> FastAPI:
    """애플리케이션 팩토리"""
    # ... 다른 초기화 코드 ...
    
    # 전역 예외 핸들러 등록
    @app.exception_handler(TeledropError)
    async def teledrop_exception_handler(request: Request, exc: TeledropError):
        """Teledrop 예외 처리기"""
        # 예외 종류에 따라 적절한 상태 코드 결정
        status_code = 500
        if isinstance(exc, ValidationError):
            status_code = 400
        elif isinstance(exc, NotFoundError):
            status_code = 404
        elif isinstance(exc, AuthenticationError):
            status_code = 401
        elif isinstance(exc, AuthorizationError):
            status_code = 403
        
        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.message}
        )
    
    @app.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        """기본 HTTP 예외 처리기"""
        return await http_exception_handler(request, exc)
    
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """처리되지 않은 예외 처리기"""
        # 로깅
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        # 디버그 모드가 아닌 경우 일반적인 오류 메시지 반환
        if not settings.DEBUG:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
        
        # 디버그 모드에서는 상세 오류 정보 반환
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": exc.__class__.__name__
            }
        )
    
    return app
```

## HTTP 상태 코드 매핑

Teledrop은 다음과 같이 예외 유형에 따라 HTTP 상태 코드를 매핑합니다:

| 예외 유형 | HTTP 상태 코드 | 설명 |
|---------|--------------|------|
| ValidationError | 400 | 잘못된 요청 (Bad Request) |
| NotFoundError | 404 | 리소스를 찾을 수 없음 (Not Found) |
| AuthenticationError | 401 | 인증 필요 (Unauthorized) |
| AuthorizationError | 403 | 권한 없음 (Forbidden) |
| StorageError | 500 | 서버 오류 (Internal Server Error) |
| TeledropError | 500 | 기타 서버 오류 (Internal Server Error) |

## 로깅 통합

Teledrop은 예외 발생 시 상세한 로깅을 제공합니다:

```python
# app/handlers/base.py
class LoggingMixin:
    """로깅 기능을 제공하는 믹스인"""
    
    def log_info(self, message: str, **kwargs):
        """정보 로깅"""
        context = {
            "handler": self.__class__.__name__,
            **kwargs
        }
        logger.info(message, extra={"context": context})
    
    def log_error(self, message: str, **kwargs):
        """오류 로깅"""
        context = {
            "handler": self.__class__.__name__,
            **kwargs
        }
        logger.error(message, extra={"context": context})
    
    def log_warning(self, message: str, **kwargs):
        """경고 로깅"""
        context = {
            "handler": self.__class__.__name__,
            **kwargs
        }
        logger.warning(message, extra={"context": context})
```

## 구조화된 오류 응답

API 응답은 일관된 오류 형식을 유지합니다:

```json
{
  "detail": "오류 메시지",
  "code": "ERROR_CODE",  // 선택적
  "params": {}  // 선택적 추가 정보
}
```

## 트랜잭션 및 보상 트랜잭션

Teledrop은 트랜잭션 실패 시 일관성을 유지하기 위해 보상 트랜잭션 패턴을 사용합니다:

```python
# app/handlers/drop/create.py
async def _create_drop_with_file_transaction(
    self, 
    drop_data: DropCreate, 
    upload_file: UploadFile, 
    auth_data: Optional[Dict[str, Any]] = None
) -> Drop:
    """트랜잭션 내에서 실행되는 Drop과 파일 생성 로직"""
    
    saved_file_path = None  # 롤백 시 삭제할 파일 경로 추적
    
    try:
        # ... 생성 로직 ...
        
    except Exception as e:
        # 트랜잭션 롤백 시 스토리지에서도 파일 삭제 (보상 트랜잭션)
        if saved_file_path:
            try:
                await self.storage_service.delete_file(saved_file_path)
                self.log_info("Compensating transaction: deleted file from storage", path=saved_file_path)
            except Exception as cleanup_error:
                self.log_error("Failed to cleanup file during rollback", 
                             path=saved_file_path, error=str(cleanup_error))
        
        # 원래 예외를 다시 발생시켜 TransactionMixin이 DB 롤백 처리
        raise
```

## 에러 처리 모범 사례

Teledrop 프로젝트에서 따르는 에러 처리 모범 사례:

1. **계층별 책임 분리**:
   - 핸들러: 도메인 예외 발생 및 처리
   - 라우터: HTTP 예외 변환
   - 전역 핸들러: 처리되지 않은 예외 포착

2. **구체적인 예외 사용**:
   - 포괄적인 예외 대신 구체적인 예외 정의
   - 의미 있는 오류 메시지 제공

3. **적절한 로깅**:
   - 오류 발생 시 컨텍스트 정보와 함께 로깅
   - 예상된 오류와 예상치 못한 오류 구분

4. **일관된 응답 형식**:
   - 모든 API 응답에 일관된 오류 형식 사용
   - 사용자 친화적인 오류 메시지 제공

5. **개발 및 프로덕션 모드 분리**:
   - 개발 모드: 상세한 오류 정보 제공
   - 프로덕션 모드: 민감한 정보 숨김

6. **트랜잭션 안전성**:
   - DB와 파일 시스템 간 일관성 유지
   - 실패 시 보상 트랜잭션으로 정리

## 프론트엔드 오류 처리

SPA 프론트엔드에서의 오류 처리:

```javascript
// web/src/lib/api.js
async function fetchWithErrorHandling(url, options = {}) {
  try {
    const response = await fetch(url, options);
    
    // 성공적인 응답이 아닌 경우
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      
      // API 오류 객체 생성
      const error = new Error(errorData.detail || 'An unknown error occurred');
      error.status = response.status;
      error.statusText = response.statusText;
      error.data = errorData;
      
      throw error;
    }
    
    return await response.json();
  } catch (error) {
    // 네트워크 오류 등 처리
    if (!error.status) {
      error.status = 0;
      error.statusText = 'Network Error';
      error.data = { detail: 'Could not connect to the server' };
    }
    
    // 오류 로깅 (선택적)
    console.error('API Error:', error);
    
    // 오류 재전파
    throw error;
  }
}
```

## 다음 문서

- [설정 관리](configuration.md) - 환경 설정 관리
- [확장성 고려사항](extensibility.md) - 시스템 확장 가이드라인 