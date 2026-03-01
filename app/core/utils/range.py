from app.core.exceptions import InvalidRangeHeader, RangeNotSatisfiable


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    if file_size <= 0:
        raise RangeNotSatisfiable()

    if not range_header:
        raise InvalidRangeHeader()

    normalized = range_header.strip().lower()
    if not normalized.startswith("bytes="):
        raise InvalidRangeHeader()

    range_spec = normalized[6:]
    if "," in range_spec:
        # Multiple ranges are not supported.
        raise InvalidRangeHeader()

    if "-" not in range_spec:
        raise InvalidRangeHeader()

    start_str, end_str = range_spec.split("-", 1)

    if start_str:
        try:
            start = int(start_str)
        except ValueError as exc:
            raise InvalidRangeHeader() from exc
        if start < 0:
            raise InvalidRangeHeader()

        if end_str:
            try:
                end = int(end_str)
            except ValueError as exc:
                raise InvalidRangeHeader() from exc
            if end < 0:
                raise InvalidRangeHeader()
        else:
            end = file_size - 1

        if start >= file_size:
            raise RangeNotSatisfiable()

        end = min(end, file_size - 1)
        if start > end:
            raise RangeNotSatisfiable()

        return start, end

    # Suffix range: bytes=-N
    if not end_str:
        raise InvalidRangeHeader()

    try:
        suffix_length = int(end_str)
    except ValueError as exc:
        raise InvalidRangeHeader() from exc

    if suffix_length <= 0:
        raise InvalidRangeHeader()

    start = max(file_size - suffix_length, 0)
    end = file_size - 1
    return start, end
