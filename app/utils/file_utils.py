"""
파일 관련 유틸리티 모듈

파일 해시 계산, 타입 감지, 크기 포맷팅, 파일명 검증 등의 기능을 제공합니다.
"""

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import BinaryIO, Optional, Union


def calculate_file_hash(file_content: Union[bytes, BinaryIO], algorithm: str = "sha256") -> str:
    """
    파일 해시 계산
    
    Args:
        file_content: 파일 내용 (bytes 또는 파일 객체)
        algorithm: 해시 알고리즘 (기본값: sha256)
        
    Returns:
        str: 계산된 해시값 (hex)
        
    Examples:
        >>> content = b"Hello, World!"
        >>> hash_value = calculate_file_hash(content)
        >>> len(hash_value)
        64  # SHA-256 hex digest
    """
    hasher = hashlib.new(algorithm)
    
    if isinstance(file_content, bytes):
        hasher.update(file_content)
    else:
        # 파일 객체인 경우 청크 단위로 읽기
        for chunk in iter(lambda: file_content.read(8192), b""):
            hasher.update(chunk)
    
    return hasher.hexdigest()


# 별칭 함수 (기존 코드와의 호환성을 위해)
def get_file_hash(file_content: Union[bytes, BinaryIO], algorithm: str = "sha256") -> str:
    """
    파일 해시 계산 (calculate_file_hash의 별칭)
    
    Args:
        file_content: 파일 내용 (bytes 또는 파일 객체)
        algorithm: 해시 알고리즘 (기본값: sha256)
        
    Returns:
        str: 계산된 해시값 (hex)
    """
    return calculate_file_hash(file_content, algorithm)


def get_file_type(filename: str) -> str:
    """
    파일 타입 감지
    
    Args:
        filename: 파일명
        
    Returns:
        str: MIME 타입 (감지 실패 시 'application/octet-stream')
        
    Examples:
        >>> get_file_type("document.pdf")
        'application/pdf'
        >>> get_file_type("image.jpg")
        'image/jpeg'
        >>> get_file_type("unknown")
        'application/octet-stream'
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def format_file_size(size_bytes: int) -> str:
    """
    파일 크기를 사람이 읽기 쉬운 형태로 포맷팅
    
    Args:
        size_bytes: 파일 크기 (바이트)
        
    Returns:
        str: 포맷된 파일 크기
        
    Examples:
        >>> format_file_size(1024)
        '1.0 KB'
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(1048576)
        '1.0 MB'
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def is_safe_filename(filename: str) -> bool:
    """
    안전한 파일명인지 검증
    
    Args:
        filename: 검증할 파일명
        
    Returns:
        bool: 안전한 파일명이면 True, 아니면 False
        
    Examples:
        >>> is_safe_filename("document.pdf")
        True
        >>> is_safe_filename("../../../etc/passwd")
        False
        >>> is_safe_filename("file with spaces.txt")
        True
    """
    if not filename or filename in (".", ".."):
        return False
    
    # 위험한 문자들 검사
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
    if any(char in filename for char in dangerous_chars):
        return False
    
    # 경로 순회 공격 방지
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        return False
    
    # Windows 예약어 검사
    windows_reserved = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    name_without_ext = Path(filename).stem.upper()
    if name_without_ext in windows_reserved:
        return False
    
    return True


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    파일명을 안전하게 정리
    
    Args:
        filename: 정리할 파일명
        replacement: 위험한 문자를 대체할 문자 (기본값: "_")
        
    Returns:
        str: 정리된 파일명
        
    Examples:
        >>> sanitize_filename("file<name>.txt")
        'file_name_.txt'
        >>> sanitize_filename("../dangerous.txt")
        '__dangerous.txt'
    """
    if not filename:
        return "unnamed"
    
    # 위험한 문자들을 replacement로 대체
    dangerous_chars = r'[<>:"|?*\0/\\]'
    sanitized = re.sub(dangerous_chars, replacement, filename)
    
    # 연속된 replacement 문자들을 하나로 합치기
    sanitized = re.sub(f'{re.escape(replacement)}+', replacement, sanitized)
    
    # 앞뒤 공백 및 점 제거
    sanitized = sanitized.strip('. ')
    
    # 빈 문자열이면 기본값 사용
    if not sanitized:
        return "unnamed"
    
    # Windows 예약어 처리
    windows_reserved = [
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    
    path = Path(sanitized)
    if path.stem.upper() in windows_reserved:
        sanitized = f"{path.stem}_{path.suffix}"
    
    return sanitized


def get_file_extension(filename: str) -> Optional[str]:
    """
    파일 확장자 추출
    
    Args:
        filename: 파일명
        
    Returns:
        Optional[str]: 확장자 (점 포함, 소문자), 없으면 None
        
    Examples:
        >>> get_file_extension("document.pdf")
        '.pdf'
        >>> get_file_extension("image.JPG")
        '.jpg'
        >>> get_file_extension("noextension")
        
    """
    path = Path(filename)
    extension = path.suffix.lower()
    return extension if extension else None


def is_image_file(filename: str) -> bool:
    """
    이미지 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        bool: 이미지 파일이면 True
        
    Examples:
        >>> is_image_file("photo.jpg")
        True
        >>> is_image_file("document.pdf")
        False
    """
    image_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
        '.webp', '.svg', '.ico', '.heic', '.heif'
    }
    
    extension = get_file_extension(filename)
    return extension in image_extensions if extension else False


def is_video_file(filename: str) -> bool:
    """
    비디오 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        bool: 비디오 파일이면 True
        
    Examples:
        >>> is_video_file("movie.mp4")
        True
        >>> is_video_file("song.mp3")
        False
    """
    video_extensions = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
        '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'
    }
    
    extension = get_file_extension(filename)
    return extension in video_extensions if extension else False


def is_audio_file(filename: str) -> bool:
    """
    오디오 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        bool: 오디오 파일이면 True
        
    Examples:
        >>> is_audio_file("song.mp3")
        True
        >>> is_audio_file("movie.mp4")
        False
    """
    audio_extensions = {
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a',
        '.opus', '.aiff', '.au', '.ra', '.amr'
    }
    
    extension = get_file_extension(filename)
    return extension in audio_extensions if extension else False


def is_text_file(filename: str) -> bool:
    """
    텍스트 파일인지 확인
    
    Args:
        filename: 파일명
        
    Returns:
        bool: 텍스트 파일이면 True
        
    Examples:
        >>> is_text_file("document.txt")
        True
        >>> is_text_file("script.py")
        True
        >>> is_text_file("image.jpg")
        False
    """
    text_extensions = {
        '.txt', '.md', '.rst', '.log', '.csv', '.json', '.xml', '.html',
        '.css', '.js', '.py', '.java', '.cpp', '.c', '.h', '.php',
        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh', '.bat',
        '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf'
    }
    
    extension = get_file_extension(filename)
    return extension in text_extensions if extension else False


def get_file_category(filename: str) -> str:
    """
    파일 카테고리 반환
    
    Args:
        filename: 파일명
        
    Returns:
        str: 파일 카테고리 ('image', 'video', 'audio', 'text', 'other')
        
    Examples:
        >>> get_file_category("photo.jpg")
        'image'
        >>> get_file_category("movie.mp4")
        'video'
        >>> get_file_category("document.pdf")
        'other'
    """
    if is_image_file(filename):
        return "image"
    elif is_video_file(filename):
        return "video"
    elif is_audio_file(filename):
        return "audio"
    elif is_text_file(filename):
        return "text"
    else:
        return "other" 