"""
Drop 슬러그 중복 확인 API 엔드포인트

Drop 슬러그의 사용 가능 여부를 확인하는 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.handlers.drop.keycheck import DropSlugCheckHandler


router = APIRouter()


@router.get("/keycheck/{slug}")
async def check_drop_key(
    slug: str,
    handler: DropSlugCheckHandler = Depends(DropSlugCheckHandler)
):
    """
    Drop 슬러그의 존재 여부를 확인합니다.
    
    - **slug**: 확인할 Drop 슬러그
    
    인증 없이 사용 가능한 공개 API입니다.
    """
    
    try:
        exists = handler.execute(slug=slug)
        
        return {
            "exists": exists,
            "slug": slug,
            "message": f"Drop slug {'exists' if exists else 'is available'}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking slug"
        ) 