"""
토큰 관련 API 엔드포인트

JWT 토큰 검증 및 토큰 관련 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.handlers.auth.token import TokenValidateHandler
from app.handlers.auth.user import CurrentUserHandler
from app.core.exceptions import AuthenticationError
from app.models import TokenPayload


router = APIRouter()


# 요청 모델 정의
class TokenValidationRequest(BaseModel):
    """토큰 검증 요청 모델"""
    token: str


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