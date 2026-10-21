"""인스타그램 캡션을 템플릿에서 생성합니다. 아티스트 정보만 바뀝니다."""
from datetime import date

from . import config as C


def format_schedule(items: list[dict]) -> str:
    """[{"date": "2026-10-06", "parts": [1, 2]}, ...] → "10/6(화)\n1부: 8:00~8:30\n2부: 10:00~10:30" """
    blocks = []
    for it in sorted(items, key=lambda x: x.get("date", "")):
        try:
            d = date.fromisoformat(it["date"])
        except (KeyError, ValueError):
            continue
        parts = sorted({int(p) for p in it.get("parts", [1]) if int(p) in C.PART_TIMES}) or [1]
        lines = [f"{d.month}/{d.day}({C.WEEKDAYS_KO[d.weekday()]})"]
        lines += [f"{p}부: {C.PART_TIMES[p]}" for p in parts]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_caption(artist_name: str, artist_handle: str, schedule: str) -> str:
    handle = artist_handle.strip()
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    return C.CAPTION_TEMPLATE.format(
        artist_name=artist_name.strip() or "아티스트",
        artist_handle=handle or "@",
        schedule=schedule.strip() or "(공연 일정을 입력하세요)",
    )
