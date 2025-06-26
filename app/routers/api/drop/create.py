"""
Drop 생성 API 엔드포인트

새로운 Drop을 생성하는 기능을 제공합니다.
UploadFile을 직접 핸들러로 전달하여 FastAPI 최적화를 활용합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File

from app.handlers.drop.create import DropCreateHandler
from app.models.drop.request import DropCreateForm
from app.models.drop.response import DropRead
from app.models.auth import AuthData
from app.core.dependencies import get_auth_data
from app.core.exceptions import (
    ValidationError,
    DropSlugAlreadyExistsError,
    AuthenticationRequiredError
)


router = APIRouter()


@router.post("/", response_model=DropRead, status_code=status.HTTP_201_CREATED)
async def create_drop(
    auth_data: AuthData | None = Depends(get_auth_data),
    file: UploadFile = File(..., description="업로드할 파일 (필수)"),
    # DropCreateForm을 Form으로 받기 위해 개별 필드로 분해 (파일 정보 제외)
    slug: str | None = Form(None, description="Drop 슬러그 (없으면 자동 생성)"),
    title: str | None = Form(None, description="Drop 제목"),
    description: str | None = Form(None, description="Drop 설명"),
    password: str | None = Form(None, description="Drop 패스워드"),
    is_private: bool = Form(True, description="비공개 여부"),
    is_favorite: bool = Form(False, description="즐겨찾기 여부"),
    drop_create_handler: DropCreateHandler = Depends(DropCreateHandler)
):
    """
    파일과 함께 Drop을 생성합니다. (모든 Drop은 반드시 파일을 가져야 함)
    
    UploadFile을 직접 핸들러로 전달하여 FastAPI의 최적화를 활용합니다.
    @authenticate 데코레이터가 핸들러에서 인증을 자동으로 검증합니다.
    
    - **file**: 업로드할 파일 (필수) - 메타데이터 자동 추출
    - **slug**: Drop 슬러그 (없으면 자동 생성)
    - **title**: Drop 제목
    - **description**: Drop 설명
    - **password**: Drop 패스워드
    - **is_private**: 비공개 여부
    - **is_favorite**: 즐겨찾기 여부
    
    인증이 필요합니다.
    """
    try:
        # DropCreateForm 생성 (순수 Drop 메타데이터만, 파일 정보 제외)
        drop_data = DropCreateForm(
            slug=slug,
            title=title,
            description=description,
            password=password,
            is_private=is_private,
            is_favorite=is_favorite
            # 파일 정보 제거됨 - UploadFile에서 직접 추출
        )
        
        # 핸들러에 Form과 UploadFile을 분리해서 전달
        result = await drop_create_handler.execute(
            drop_data=drop_data,
            upload_file=file,  # UploadFile 직접 전달 (file.file 대신)
            auth_data=auth_data
        )
        
        return result
        
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except DropSlugAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create drop: {str(e)}"
        ) 
