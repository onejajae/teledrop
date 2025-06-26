"""S3 스토리지 구현

AWS S3 또는 호환 가능한 오브젝트 스토리지를 사용하는 백엔드 구현입니다.
"""

import io
import anyio
import anyio.to_thread
from contextlib import asynccontextmanager
from typing import AsyncGenerator, BinaryIO

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .base import StorageInterface


class S3Storage(StorageInterface):
    """S3 호환 오브젝트 스토리지를 사용하는 스토리지 구현"""

    def __init__(
        self,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        write_chunk_size: int = 1024 * 1024 * 4,
    ):
        """S3Storage 초기화
        
        Args:
            bucket_name: S3 버킷 이름
            access_key_id: AWS 액세스 키 ID
            secret_access_key: AWS 시크릿 액세스 키
            region: AWS 리전 (기본값: us-east-1)
            endpoint_url: S3 호환 서비스의 엔드포인트 URL (MinIO 등)
            write_chunk_size: 파일 쓰기 시 사용할 청크 크기 (기본 4MB)
        """
        self.bucket_name = bucket_name
        self._storage_type = "s3"
        self.write_chunk_size = write_chunk_size
        
        try:
            # S3 클라이언트 생성
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region,
                endpoint_url=endpoint_url,
            )
            
            # 버킷 존재 여부 확인
            self.s3_client.head_bucket(Bucket=bucket_name)
            
        except NoCredentialsError:
            raise ValueError("AWS credentials not found")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise ValueError(f"Bucket '{bucket_name}' not found")
            raise ValueError(f"S3 connection failed: {e}")

    @property
    def storage_type(self) -> str:
        """스토리지 타입을 반환합니다."""
        return self._storage_type

    @asynccontextmanager
    async def _write_stream(self, file_path: str):
        """스트리밍 쓰기를 위한 스트림 컨텍스트 매니저 (내부 구현)
        
        S3는 직접 스트리밍 쓰기를 지원하지 않으므로 메모리 버퍼를 사용합니다.
        대용량 파일의 경우 메모리 사용량이 클 수 있으니 주의하세요.
        """
        buffer = io.BytesIO()
        try:
            yield buffer
            
            # 버퍼의 내용을 S3에 업로드
            buffer.seek(0)
            await anyio.to_thread.run_sync(
                self.s3_client.upload_fileobj,
                buffer,
                self.bucket_name,
                file_path,
                {"ServerSideEncryption": "AES256"}
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload file to S3: {e}")
        finally:
            buffer.close()

    async def read(
        self, 
        file_path: str, 
        start: int | None = None, 
        end: int | None = None
    ) -> AsyncGenerator[bytes, None]:
        """S3에서 파일의 내용을 읽어서 반환합니다."""
        try:
            # Range 헤더 설정
            kwargs = {
                "Bucket": self.bucket_name,
                "Key": file_path
            }
            
            if start is not None or end is not None:
                # HTTP Range 헤더 구성
                if start is not None and end is not None:
                    range_header = f"bytes={start}-{end}"
                elif start is not None:
                    range_header = f"bytes={start}-"
                else:  # end is not None
                    range_header = f"bytes=-{end + 1}"
                
                kwargs["Range"] = range_header
            
            response = await anyio.to_thread.run_sync(
                self.s3_client.get_object,
                **kwargs
            )
            
            # 스트리밍 방식으로 데이터 읽기
            chunk_size = 1024 * 1024  # 1MB 청크
            
            with response["Body"] as stream:
                while True:
                    chunk = await anyio.to_thread.run_sync(stream.read, chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {file_path}")
            raise RuntimeError(f"Failed to read file from S3: {e}")

    async def delete(self, file_path: str) -> bool:
        """S3에서 파일을 삭제합니다."""
        try:
            await anyio.to_thread.run_sync(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
            
        except ClientError as e:
            # S3에서는 존재하지 않는 파일을 삭제해도 에러가 발생하지 않음
            # 하지만 다른 에러는 처리
            if e.response["Error"]["Code"] != "NoSuchKey":
                raise RuntimeError(f"Failed to delete file from S3: {e}")
            return False

    async def exists(self, file_path: str) -> bool:
        """S3에서 파일이 존재하는지 확인합니다."""
        try:
            await anyio.to_thread.run_sync(
                self.s3_client.head_object,
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise RuntimeError(f"Failed to check file existence in S3: {e}")

    async def size(self, file_path: str) -> int:
        """S3에서 파일 크기를 반환합니다."""
        try:
            response = await anyio.to_thread.run_sync(
                self.s3_client.head_object,
                Bucket=self.bucket_name,
                Key=file_path
            )
            return response["ContentLength"]
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File not found: {file_path}")
            raise RuntimeError(f"Failed to get file size from S3: {e}")

    async def move(self, old_path: str, new_path: str) -> None:
        """S3 내에서 객체를 복사하고 이전 객체를 삭제하여 이동을 흉내냅니다."""
        try:
            # 객체 복사
            await anyio.to_thread.run_sync(
                self.s3_client.copy_object,
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': old_path},
                Key=new_path,
                ExtraArgs={'ServerSideEncryption': 'AES256'}
            )
            
            # 이전 객체 삭제
            await anyio.to_thread.run_sync(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=old_path
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"Source file not found in S3: {old_path}")
            from app.core.exceptions import StorageError
            raise StorageError(f"Failed to move file in S3 from {old_path} to {new_path}: {e}") 