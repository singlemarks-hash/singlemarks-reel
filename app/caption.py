"""인스타그램 캡션을 템플릿에서 생성합니다. 아티스트 정보만 바뀝니다."""
from . import config as C


def build_caption(artist_name: str, artist_handle: str, schedule: str) -> str:
    handle = artist_handle.strip()
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    return C.CAPTION_TEMPLATE.format(
        artist_name=artist_name.strip() or "아티스트",
        artist_handle=handle or "@",
        schedule=schedule.strip() or "(공연 일정을 입력하세요)",
    )
