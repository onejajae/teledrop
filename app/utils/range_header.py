def parse_range_header(range_header: str) -> tuple[int, int]:
    """
    Parse the range header and return the start and end indices.
    """
    if not range_header:
        return 0, None
    
    start_str, end_str = range_header.strip().lower().replace("bytes=", "").split("-")
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else None

    return start, end

def validate_range_header(range_header: str) -> bool:
    """
    Validate the range header and return True if it is valid, False otherwise.
    """
    pass
    