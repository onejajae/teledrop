"""
사용자 정보 관련 API 엔드포인트

인증된 사용자의 정보 조회 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.handlers.auth.user import CurrentUserHandler
from app.models.auth import AuthData


router = APIRouter()


@router.get("/me", response_model=dict)
async def get_current_user_info(
    user_handler: CurrentUserHandler = Depends(CurrentUserHandler),
):
    """현재 사용자 정보 조회 엔드포인트
    
    인증된 사용자의 정보를 반환합니다.
    Bearer 토큰과 쿠키 인증을 모두 지원합니다.
    
    Args:
        user_handler: 사용자 핸들러
        
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

    # AuthData 모델에서 정보 추출
    return {
        "username": current_user.username,
        "can_read": current_user.can_read,
        "can_write": current_user.can_write,
        "authentication_type": "jwt"
    } 