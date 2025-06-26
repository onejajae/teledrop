"""
Drop 생성 Handler

새로운 Drop을 파일과 함께 생성하는 비즈니스 로직을 처리합니다.
트랜잭션과 보상 트랜잭션 패턴을 사용하여 데이터 일관성을 보장합니다.
"""

import hashlib
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import Depends, UploadFile

from app.models import Drop
from app.handlers.base import BaseHandler
from app.handlers.mixins import DropAccessMixin
from app.handlers.decorators import authenticate

from app.infrastructure.storage.base import StorageInterface
from app.core.config import Settings
from app.core.exceptions import ValidationError, DropSlugAlreadyExistsError
from app.utils.file_utils import sanitize_filename
from app.utils.slug_generator import generate_slug
from app.core.dependencies import get_session, get_storage, get_settings
from app.models.drop.request import DropCreateForm
from app.models.drop.response import DropRead
from app.models.auth import AuthData


class DropCreateHandler(BaseHandler, DropAccessMixin):
    """Drop 생성 Handler - 파일과 함께 생성"""
    
    def __init__(
        self,
        session: AsyncSession = Depends(get_session),
        storage: StorageInterface = Depends(get_storage),
        settings: Settings = Depends(get_settings)
    ):
        self.session = session
        self.storage = storage
        self.settings = settings
    
    
    @authenticate  # 인증 필수
    async def execute(
        self,
        drop_data: DropCreateForm,
        upload_file: UploadFile,
        auth_data: AuthData | None = None,
    ) -> DropRead:
        """
        새로운 Drop을 파일과 함께 생성합니다.
        
        @authenticate 데코레이터로 인증이 자동 검증됩니다.
        
        Args:
            drop_data: 완전한 Drop 생성 데이터 (파일 정보 포함)
            upload_stream: 업로드할 파일 스트림 (BinaryIO)
            
        Returns:
            DropRead: 생성된 Drop 정보
        """
        self.log_info("Starting drop creation", user=auth_data.username)
        
        self.log_info("Creating new drop with file", 
                     title=drop_data.title, 
                     filename=upload_file.filename,
                     expected_size=upload_file.size)
        
        # ═══════════════════════════════════════════════════════════════
        # 1️⃣ DROP KEY 처리 (비즈니스 규칙)
        # ═══════════════════════════════════════════════════════════════
        slug = drop_data.slug
        if not slug or not slug.strip():
            # 사용자 친화적인 고유 키 생성 (영어 단어 3개 조합)
            max_attempts = 10
            for attempt in range(max_attempts):
                candidate_slug = generate_slug()
                if not await Drop.get_by_slug(self.session, candidate_slug):
                    slug = candidate_slug
                    self.log_info("Generated user-friendly slug", 
                                 slug=slug, 
                                 attempt=attempt + 1)
                    break
            else:
                # 모든 시도가 실패한 경우 UUID 폴백
                slug = str(uuid.uuid4())
                self.log_warning("Failed to generate unique word-based slug, using UUID", 
                               slug=slug, 
                               max_attempts=max_attempts)
        else:
            # 사용자가 직접 입력한 slug 검증
            if await Drop.get_by_slug(self.session, slug):
                raise DropSlugAlreadyExistsError(f"Drop slug already exists: {slug}")
            self.log_info("Using custom slug", slug=slug)
        
        # ═══════════════════════════════════════════════════════════════
        # 2️⃣ Generator 기반 파일 처리 및 검증 (파이프라인 패턴)
        # ═══════════════════════════════════════════════════════════════
        storage_path = str(uuid.uuid4())
        
        self.log_info("Processing file with generator pipeline", path=storage_path)
        
        # 비즈니스 로직을 위한 상태 관리
        file_hash_obj = hashlib.sha256()
        chunk_size = self.settings.WRITE_CHUNK_SIZE

        # 🔄 중간 처리 Generator (비즈니스 로직 + 전달)
        async def process_and_forward_chunks():
            try:
                while chunk := await upload_file.read(chunk_size):
                    # 비즈니스 로직 처리
                    file_hash_obj.update(chunk)
                    
                    # 스토리지로 전달
                    yield chunk
                    
            except Exception as e:
                self.log_error("Error during chunk processing", 
                              path=storage_path, error=str(e))
                raise

        try:
            # 🎯 새로운 Storage API 사용
            _, actual_file_size = await self.storage.save(
                process_and_forward_chunks(), 
                storage_path
            )

            # ═══════════════════════════════════════════════════════════════
            # 🏷️ FILENAME 처리 (해시 기반) - drop_data에서 추출
            # ═══════════════════════════════════════════════════════════════
            file_hash = file_hash_obj.hexdigest()
            filename = upload_file.filename
            
            if not filename or not filename.strip():
                # 해시는 이미 안전하므로 sanitize 불필요
                safe_filename = file_hash
                self.log_info("Generated filename from hash", 
                             generated=safe_filename,
                             full_hash=file_hash)
            else:
                # 외부 입력(신뢰할 수 없음)만 sanitize
                filename = filename.strip()
                safe_filename = sanitize_filename(filename)
                self.log_info("Using provided filename", 
                             original=filename, 
                             sanitized=safe_filename)

            # ═══════════════════════════════════════════════════════════════
            # 🔍 파일 크기 무결성 검증 (Content-Length vs 실제 크기)
            # ═══════════════════════════════════════════════════════════════
            expected_size = upload_file.size
            if expected_size is not None and expected_size != actual_file_size:
                self.log_error("File size mismatch detected", 
                              expected=expected_size, 
                              actual=actual_file_size,
                              path=storage_path)
                # 스토리지에서 파일 삭제 (보상 트랜잭션)
                try:
                    await self.storage.delete(storage_path)
                except Exception as cleanup_error:
                    self.log_error("Failed to cleanup file after size mismatch", 
                                  path=storage_path, error=str(cleanup_error))
                
                raise ValidationError(
                    f"File size mismatch: expected {expected_size} bytes, "
                    f"but received {actual_file_size} bytes"
                )
            else:
                self.log_info("File size validation passed", 
                             expected=expected_size, 
                             actual=actual_file_size)

        except Exception as e:
            self.log_error("Error during generator-based file processing", 
                          path=storage_path, error=str(e))
            # 스토리지에서 파일 삭제 (보상 트랜잭션)
            try:
                await self.storage.delete(storage_path)
                self.log_info("Successfully cleaned up storage file after error", path=storage_path)
            except Exception as cleanup_error:
                self.log_error("Failed to cleanup storage file after processing error", 
                              path=storage_path, error=str(cleanup_error))
            raise
        
        # ═══════════════════════════════════════════════════════════════
        # 3️⃣ DATABASE 트랜잭션 - Drop 생성 (모델 메서드 활용)
        # ═══════════════════════════════════════════════════════════════
        self.log_info("File processing completed successfully, creating Drop entity")
        
        try:
            # Drop 생성 데이터 준비
            create_data = {
                "title": drop_data.title,
                "description": drop_data.description,
                "password": drop_data.password,
                "is_private": drop_data.is_private,
                "is_favorite": drop_data.is_favorite,
                "updated_time": None,
                # 파일 정보 (통합된 모델)
                "file_name": safe_filename,
                "file_size": actual_file_size,
                "file_type": upload_file.content_type or "application/octet-stream",
                "file_hash": file_hash,
                "storage_type": self.storage.storage_type,
                "storage_path": storage_path
            }
            
            # 모델의 create 메서드 사용 (내부에서 commit 수행)
            drop = await Drop.create(
                session=self.session,
                drop_data=create_data,
                slug=slug
            )
            
            self.log_info("Drop created successfully", 
                         drop_id=str(drop.id), 
                         slug=slug)
            
        except Exception as e:
            # 의존성에서 자동 롤백 처리됨
            self.log_error("Database transaction failed", error=str(e))
            
            # 스토리지에서 파일 삭제 (보상 트랜잭션)
            try:
                await self.storage.delete(storage_path)
                self.log_info("Successfully cleaned up storage file after DB failure", path=storage_path)
            except Exception as cleanup_error:
                self.log_error("Failed to cleanup storage file after DB failure", 
                              path=storage_path, error=str(cleanup_error))
            
            raise
        
        # ═══════════════════════════════════════════════════════════════
        # 4️⃣ 성공 응답 반환
        # ═══════════════════════════════════════════════════════════════
        
        # DropRead 스키마로 변환하여 반환 (model_validate 사용)
        result = DropRead.model_validate(drop)
        
        self.log_info("Drop creation completed successfully", 
                     drop_id=str(drop.id), 
                     slug=slug,
                     file_size=actual_file_size)
        
        return result
