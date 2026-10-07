"""고정 템플릿 설정. 아티스트만 바뀌고 나머지는 항상 동일하게 유지됩니다."""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FONT_DIR = BASE_DIR / "fonts"
JOBS_DIR = BASE_DIR.parent / "jobs"

# ── 영상 템플릿 ─────────────────────────────────────────────
TITLE_TEXT = "Concert Every Night"
SUBTITLE_TEXT = "매일 밤 열리는 낭만적인 공연"
TITLE_FONT = FONT_DIR / "QwitcherGrypen.ttf"     # 기본 타이틀 폰트 (가는 서명체)
# app/fonts/ 에 TTF/OTF 를 넣으면 UI 목록에 자동으로 나타납니다 (한글 폰트 제외)
TITLE_FONT_EXCLUDE = {"NotoSansKR-Regular.ttf"}


def title_fonts() -> list[dict]:
    out = []
    for f in sorted(FONT_DIR.glob("*.[ot]tf")):
        if f.name in TITLE_FONT_EXCLUDE:
            continue
        name = f.stem.replace("-Regular", "").replace("_", " ")
        name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
        out.append({"file": f.name, "name": name, "default": f == TITLE_FONT})
    return out
SUBTITLE_FONT = FONT_DIR / "NotoSansKR-Regular.ttf"    # 한글

OUT_W, OUT_H = 1080, 1920          # 9:16 릴스
FPS = 30                           # 원본 프레임레이트가 23~61 범위면 원본 유지, 아니면 이 값
CRF = 18                           # H.264 품질 (낮을수록 고화질, 18 = 시각적으로 원본과 구분 어려움)
X264_PRESET = "medium"
VIGNETTE = False                   # 가장자리 어둡게 (원본 색 유지하려면 False)
AUDIO_NORMALIZE = True             # 인스타그램 권장 -14 LUFS 로 음량 정규화
TITLE_WIDTH = 0.88                 # 타이틀 글자 폭 = 화면 폭의 88% (크기는 자동 계산)
TITLE_Y = 0.29                     # 타이틀 세로 중심 (화면 높이 비율)
SUBTITLE_SIZE = 35                 # px
SUBTITLE_Y = 0.376                 # 서브타이틀 세로 중심
SUBTITLE_TRACKING = 0.14           # 자간 (글자 크기 비율)
SUBTITLE_WORD_GAP = 0.62           # 단어 사이 간격 (글자 크기 비율)
SUBTITLE_STROKE = 2                # 검은 외곽선 두께 px

CLIP_SECONDS = 30
CLIP_COUNT = 3

# ── 캡션 템플릿 ─────────────────────────────────────────────
CAPTION_TEMPLATE = """서울 도심 속, 문을 여는 순간 펼쳐지는 🇫🇷파리의 어느 Jazz Bar.

사랑하는 사람에게 영화 같은 하루를 선물하고 싶은 날,
혹은 평범한 일상을 특별한 기억으로 채우고 싶은 날

매일 밤 열리는 공연과 함께 로맨틱한 순간을 선물해 보세요.

📅 {artist_name} 다음 공연 일정 안내
🎤 Artist: {artist_handle}

{schedule}

🎹 @singlemarks_art 팔로우하고,
매일 열리는 공연의 라인업을 가장 먼저 확인하세요!

필요할 때 꺼내 볼 수 있도록 이 영상을 <저장>하고,
위로와 응원을 전하고 싶은 소중한 사람에게 ’공유‘로
오늘 나의 마음을 전해보면 어떨까요?

💌 네이버 & 캐치테이블 ‘작은따옴표 도림천점’
브런치 & 디너 1,2부 예약 가능합니다.

* 워크인도 가능하지만, 예약을 권장드립니다.

☕️🥂 Salon Space:
Bruch Cafe & Dining Bar ‘_______‘ 작은따옴표(@singlemarks_world)

#작은따옴표 #작은따옴표도림천점
#라이브공연 #서울재즈바 #라이브바"""
