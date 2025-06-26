"""
Drop 읽기 관련 API 엔드포인트들

Drop의 미리보기, 다운로드, 존재 여부 확인 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.responses import StreamingResponse
from urllib import parse

from app.handlers.drop.read import DropReadHandler, DropExistsHandler, DropStreamHandler
from app.models.drop.response import DropRead, DropExistsResult
from app.models.auth import AuthData
from app.core.dependencies import get_auth_data
from app.core.exceptions import (
    DropNotFoundError,
    DropPasswordInvalidError,
    InvalidRangeHeaderError,
    RangeNotSatisfiableError,
    AuthenticationRequiredError
)


router = APIRouter()


@router.get("/{slug}/preview", response_model=DropRead)
async def get_drop_preview(
    slug: str,
    password: str | None = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_read_handler: DropReadHandler = Depends(DropReadHandler)
):
    """
    Drop 미리보기 정보를 조회합니다.
    
    - **slug**: Drop 고유 슬러그
    - **password**: Drop 패스워드 (보호된 Drop인 경우 필수)
    
    파일 다운로드 전에 Drop 정보를 확인할 수 있습니다.
    Public Drop은 인증 없이 조회 가능하며, Private Drop은 인증이 필요합니다.
    
    @authenticate(required=False) 데코레이터에 의해 접근 제어가 자동으로 처리됩니다.
    """
    try:
        # @authenticate 데코레이터가 자동으로 인증 처리
        result = await drop_read_handler.execute_preview(
            slug=slug,
            password=password,
            auth_data=auth_data
        )
        
        return result
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get drop preview: {str(e)}"
        )


@router.get("/{slug}")
async def download_drop_file(
    slug: str,
    password: str | None = Query(None, description="Drop 패스워드 (보호된 Drop인 경우)"),
    preview: bool | None = Query(False, description="미리보기 여부"),
    range: str | None = Header(None, alias="Range"),
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_stream_handler: DropStreamHandler = Depends(DropStreamHandler)
):
    """
    Drop 파일을 다운로드합니다.
    
    - **slug**: Drop 고유 슬러그
    - **password**: Drop 패스워드 (보호된 Drop인 경우 필수)
    
    Range 요청을 지원하여 부분 다운로드가 가능합니다.
    Public Drop은 인증 없이 다운로드 가능하며, Private Drop은 인증이 필요합니다.
    """
    try:
        # DropStreamHandler 사용 - Range 헤더를 그대로 전달
        async_file_streamer, start_byte, end_byte, drop_result = await drop_stream_handler.execute(
            slug=slug,
            range_header=range,
            password=password,
            auth_data=auth_data
        )
        
        if preview:
            content_disposition_type = "inline"
        else:
            content_disposition_type = "attachment"

        # 헤더 생성
        content_length = end_byte - start_byte + 1
        headers = {
            "Content-Disposition": f"{content_disposition_type}; filename*=UTF-8''{parse.quote(drop_result.file_name)}",
            "Content-Length": str(content_length),
            "Content-Type": drop_result.file_type,
            "Accept-Ranges": "bytes",
            "Access-Control-Expose-Headers": (
                "content-type, accept-ranges, content-length, "
                "content-range, content-encoding"
            ),
            "Content-Encoding": "identity"
        }
        
        # 상태코드 및 Content-Range 헤더 설정
        if start_byte > 0 or end_byte < drop_result.file_size - 1:
            status_code = status.HTTP_206_PARTIAL_CONTENT
            headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{drop_result.file_size}"
        else:
            status_code = status.HTTP_200_OK
        
        return StreamingResponse(
            async_file_streamer,
            status_code=status_code,
            headers=headers,
        )
        
    except DropNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drop not found"
        )
    except DropPasswordInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    except InvalidRangeHeaderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Range header: {str(e)}"
        )
    except RangeNotSatisfiableError as e:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=f"Range not satisfiable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/{slug}/exists", response_model=DropExistsResult)
async def check_drop_slug_exists(
    slug: str,
    auth_data: AuthData | None = Depends(get_auth_data),
    drop_exists_handler: DropExistsHandler = Depends(DropExistsHandler)
):
    """
    Drop 슬러그 존재 여부를 확인합니다.
    
    관리자 전용 기능으로 인증이 필요합니다.
    @authenticate 데코레이터를 사용하여 깔끔한 인증 처리를 구현합니다.
    
    - **slug**: 확인할 Drop 슬러그
    
    Returns:
        bool: Drop 존재 여부
    """
    try:
        # @authenticate 데코레이터가 자동으로 인증 검증 처리
        exists = await drop_exists_handler.execute(slug=slug, auth_data=auth_data)
        return DropExistsResult(exists=exists)
    except AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking slug existence: {str(e)}"
        )








 