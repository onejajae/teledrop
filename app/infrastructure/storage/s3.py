"""AWS S3 스토리지 구현

AWS S3를 사용하는 스토리지 백엔드 구현입니다.
boto3 라이브러리를 사용하여 S3 API와 통신합니다.
"""

import boto3
import io
import anyio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError

from .base import StorageInterface


class S3Storage(StorageInterface):
    """AWS S3를 사용하는 스토리지 구현"""

    def __init__(
        self,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ):
        """S3Storage 초기화
        
        Args:
            bucket_name: S3 버킷 이름
            access_key_id: AWS Access Key ID
            secret_access_key: AWS Secret Access Key
            region: AWS 리전
            endpoint_url: 커스텀 S3 엔드포인트 (MinIO 등)
        """
        self.bucket_name = bucket_name
        self._storage_type = "s3"
        
        try:
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

    async def save_file(self, file_stream: BinaryIO, file_path: str) -> str:
        """파일을 S3에 저장합니다."""
        try:
            # boto3 upload_fileobj는 동기 함수이므로 anyio.to_thread로 실행
            await anyio.to_thread.run_sync(
                self.s3_client.upload_fileobj,
                file_stream,
                self.bucket_name,
                file_path,
                {"ServerSideEncryption": "AES256"}  # 서버 사이드 암호화
            )
            return file_path
            
        except ClientError as e:
            raise RuntimeError(f"Failed to upload file to S3: {e}")

    @asynccontextmanager
    async def write_stream(self, file_path: str):
        """스트리밍 쓰기를 위한 스트림 컨텍스트 매니저를 반환합니다.
        
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

    async def read_file(self, file_path: str) -> AsyncGenerator[bytes, None]:
        """S3에서 파일의 전체 내용을 읽어서 반환합니다."""
        try:
            response = await anyio.to_thread.run_sync(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=file_path
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

    async def read_file_range(
        self, file_path: str, start: int, end: int
    ) -> AsyncGenerator[bytes, None]:
        """S3에서 파일의 지정된 범위를 읽어서 반환합니다."""
        try:
            # HTTP Range 헤더 사용
            range_header = f"bytes={start}-{end}"
            
            response = await anyio.to_thread.run_sync(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=file_path,
                Range=range_header
            )
            
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
            raise RuntimeError(f"Failed to read file range from S3: {e}")

    async def delete_file(self, file_path: str) -> bool:
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

    async def file_exists(self, file_path: str) -> bool:
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

    async def get_file_size(self, file_path: str) -> int:
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

    async def move_file(self, old_path: str, new_path: str) -> None:
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