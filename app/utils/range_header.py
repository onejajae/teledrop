"""
HTTP Range 헤더 파싱 및 검증 유틸리티
"""

def parse_range_header(range_header: str) -> tuple[int, int | None]:
    """
    HTTP Range 헤더를 파싱하여 시작과 끝 바이트 위치를 반환합니다.
    
    Args:
        range_header: HTTP Range 헤더 값 (예: "bytes=0-1023", "bytes=1000-", "bytes=-500")
        
    Returns:
        Tuple[int, Optional[int]]: (시작 바이트, 종료 바이트)
        종료 바이트가 None이면 끝까지를 의미함
        
    Raises:
        ValueError: Range 헤더 형식이 유효하지 않은 경우
        
    Examples:
        >>> parse_range_header("bytes=0-1023")
        (0, 1023)
        >>> parse_range_header("bytes=1000-")
        (1000, None)
        >>> parse_range_header("bytes=-500")
        (0, 499)  # 마지막 500바이트를 의미하지만 시작점은 파일 크기에 따라 결정
    """
    if not range_header:
        raise ValueError("Range header is empty")
    
    # "bytes=" 접두사 제거 및 정규화
    range_spec = range_header.strip().lower()
    if not range_spec.startswith("bytes="):
        raise ValueError("Range header must start with 'bytes='")
    
    range_spec = range_spec[6:]  # "bytes=" 제거
    
    # 하이픈으로 분리
    if "-" not in range_spec:
        raise ValueError("Range header must contain '-'")
    
    parts = range_spec.split("-", 1)
    if len(parts) != 2:
        raise ValueError("Invalid range format")
    
    start_str, end_str = parts
    
    try:
        # 시작 바이트 처리
        if start_str:
            start = int(start_str)
            if start < 0:
                raise ValueError("Start byte cannot be negative")
        else:
            # "-500" 형태 (suffix-byte-range-spec)
            if not end_str:
                raise ValueError("Both start and end cannot be empty")
            suffix_length = int(end_str)
            if suffix_length <= 0:
                raise ValueError("Suffix length must be positive")
            # 실제 시작점은 파일 크기에 따라 결정되므로 0으로 설정하고
            # 종료점을 suffix_length-1로 설정
            return 0, suffix_length - 1
        
        # 종료 바이트 처리
        if end_str:
            end = int(end_str)
            if end < 0:
                raise ValueError("End byte cannot be negative")
            if start > end:
                raise ValueError("Start byte cannot be greater than end byte")
            return start, end
        else:
            # "1000-" 형태
            return start, None
            
    except ValueError as e:
        if "invalid literal for int()" in str(e):
            raise ValueError("Range values must be integers")
        raise


def validate_range_header(range_header: str) -> bool:
    """
    Range 헤더의 유효성을 검증합니다.
    
    Args:
        range_header: 검증할 Range 헤더 값
        
    Returns:
        bool: 유효하면 True, 유효하지 않으면 False
    """
    try:
        parse_range_header(range_header)
        return True
    except ValueError:
        return False


def is_suffix_range(range_header: str) -> bool:
    """
    Range 헤더가 suffix-byte-range-spec 형태인지 확인합니다.
    (예: "bytes=-500" - 마지막 500바이트)
    
    Args:
        range_header: 확인할 Range 헤더 값
        
    Returns:
        bool: suffix-byte-range-spec이면 True
    """
    if not range_header:
        return False
        
    range_spec = range_header.strip().lower()
    if not range_spec.startswith("bytes="):
        return False
        
    range_spec = range_spec[6:]
    return range_spec.startswith("-") and len(range_spec) > 1
    