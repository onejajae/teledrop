"""
인증 관련 API 라우터

로그인, 로그아웃, 토큰 검증 등의 인증 API 엔드포인트를 제공합니다.
Handler 패턴을 사용하여 비즈니스 로직을 분리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

# from app.handlers.auth_handlers import LoginHandler, TokenValidateHandler, TokenRefreshHandler
from app.handlers.auth.login import LoginHandler
from app.handlers.auth.token import TokenValidateHandler
from app.core.exceptions import AuthenticationError
from app.models import AccessToken, TokenPayload
from app.handlers.auth.user import CurrentUserHandler


router = APIRouter(prefix="/auth")


# 요청 모델 정의
class TokenValidationRequest(BaseModel):
    """토큰 검증 요청 모델"""
    token: str


@router.post("/login", response_model=AccessToken)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    handler: LoginHandler = Depends(LoginHandler)
):
    """사용자 로그인 엔드포인트
    
    LoginHandler를 사용하여 사용자 인증 후 JWT 토큰을 발급합니다.
    성공 시 HttpOnly 쿠키에도 토큰을 설정합니다.
    
    Args:
        form_data: OAuth2 패스워드 폼 (username, password)
        handler: LoginHandler 인스턴스
        
    Returns:
        AccessToken: 액세스 토큰과 리프레시 토큰
        
    Raises:
        HTTPException: 인증 실패 시 401 에러
    """
    try:
        token_result = await handler.execute(
            username=form_data.username,
            password=form_data.password
        )
        
        # HttpOnly 쿠키에 액세스 토큰 설정 (보안)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {token_result.access_token}",
            httponly=True,
            samesite="strict",
            max_age=token_result.expires_in
        )
        
        # 리프레시 토큰도 HttpOnly 쿠키로 설정 (보안 강화)
        if token_result.refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=token_result.refresh_token,
                httponly=True,
                samesite="strict",
                max_age=30 * 24 * 60 * 60  # 30일
            )
        
        return token_result
        
    except AuthenticationError as e:
        # Handler에서 발생한 인증 에러를 HTTP 401로 변환
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        # 예상치 못한 에러를 HTTP 500으로 변환
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# @router.post("/refresh", response_model=AccessToken)
# async def refresh_token(
#     refresh_token: str,
#     handler: TokenRefreshHandler = Depends(TokenRefreshHandler)
# ):
#     """토큰 갱신 엔드포인트
    
#     TokenRefreshHandler를 사용하여 리프레시 토큰으로 새 액세스 토큰을 발급합니다.
    
#     Args:
#         refresh_token: 리프레시 토큰
#         handler: TokenRefreshHandler 인스턴스
        
#     Returns:
#         AccessToken: 새로운 액세스 토큰
        
#     Raises:
#         HTTPException: 토큰이 유효하지 않을 시 401 에러
#     """
#     try:
#         token_result = await handler.execute(refresh_token)
        
#         return token_result
        
#     except AuthenticationError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid or expired refresh token",
#             headers={"WWW-Authenticate": "Bearer"}
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error"
#         )


@router.post("/validate", response_model=TokenPayload)
async def validate_token(
    request: TokenValidationRequest,
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
    handler: TokenValidateHandler = Depends(TokenValidateHandler)
):
    """토큰 검증 엔드포인트
    
    **인증이 필요합니다.** JWT 토큰을 검증합니다.
    현재 인증된 사용자만이 토큰 검증을 수행할 수 있습니다.
    주로 다른 서비스나 디버깅 목적으로 사용됩니다.
    
    Args:
        request: 토큰 검증 요청 데이터
        current_user: 현재 인증된 사용자 정보 (인증 필수)
        handler: TokenValidateHandler 인스턴스
        
    Returns:
        TokenPayload: 토큰 페이로드 정보
        
    Raises:
        HTTPException: 인증 실패 또는 토큰이 유효하지 않을 시 401 에러
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = await handler.execute(request.token)
        
        return payload
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/logout")
async def logout(
    response: Response,
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
):
    """로그아웃 엔드포인트
    
    **인증이 필요합니다.** HttpOnly 쿠키에서 토큰들을 제거합니다.
    현재 인증된 사용자만이 로그아웃을 수행할 수 있습니다.
    프론트엔드 호환성을 위해 GET 메서드를 사용합니다.
    
    Args:
        response: HTTP 응답 객체
        current_user: 현재 인증된 사용자 정보 (인증 필수)
        
    Returns:
        dict: 로그아웃 성공 메시지
    """
    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        # HttpOnly 쿠키에서 토큰들 제거
        response.delete_cookie(key="access_token")
        response.delete_cookie(key="refresh_token")
        
        return {
            "message": "Successfully logged out",
            "user": current_user.get("username") if current_user["type"] == "jwt" else "api_user"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# Handler 패턴의 장점을 보여주는 예시 엔드포인트
@router.get("/me", response_model=dict)
async def get_current_user_info(
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
):
    """현재 사용자 정보 조회 엔드포인트
    
    인증된 사용자의 정보를 반환합니다.
    Bearer 토큰과 쿠키 인증을 모두 지원합니다.
    
    Args:
        current_user: 인증된 사용자 정보
        
    Returns:
        dict: 사용자 정보
    """

    current_user = user_handler.execute()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if current_user["type"] == "jwt":
        payload = current_user["payload"]
        return {
            "username": current_user["username"],
            "token_type": "access",
            "issued_at": payload.get("iat"),
            "expires_at": payload.get("exp"),
            "authentication_type": "jwt"
        }
    elif current_user["type"] == "api_key":
        api_key = current_user["api_key"]
        return {
            "api_key_prefix": api_key.prefix,
            "name": api_key.name,
            "created_at": api_key.created_at.isoformat(),
            "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
            "authentication_type": "api_key"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication type"
        ) 