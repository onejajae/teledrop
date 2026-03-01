from __future__ import annotations


def normalize_pagination(
    page: int | None,
    page_size: int | None,
    default_page_size: int,
    max_page_size: int,
) -> tuple[int, int]:
    resolved_page = page or 1
    if resolved_page < 1:
        resolved_page = 1

    resolved_page_size = page_size or default_page_size
    if resolved_page_size < 1:
        resolved_page_size = 1
    if resolved_page_size > max_page_size:
        resolved_page_size = max_page_size

    return resolved_page, resolved_page_size
