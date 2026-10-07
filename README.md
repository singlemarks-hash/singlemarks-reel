# Singlemarks Reel Maker — Concert Every Night

롱폼 공연 영상을 업로드하면 **하이라이트 구간을 자동으로 찾아 30초 릴스 3개**와
인스타그램 캡션을 만들어 주는 자동화 편집기입니다.

영상 템플릿은 고정입니다.

- 필기체 타이틀: **Concert Every Night**
- 한글 서브타이틀: **매일 밤 열리는 낭만적인 공연**

아티스트 이름 · 계정 · 공연 일정만 바꿔 캡션에 반영됩니다.

## 실행

```bash
pip install -r requirements.txt     # ffmpeg / ffprobe 가 PATH 에 있어야 합니다
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000` 접속 → 영상 업로드 → 아티스트 정보 입력 → **하이라이트 분석**.

분석이 끝나면(30분 영상 기준 10초 안팎) **구간 조정** 화면이 열립니다.
오디오 에너지 그래프 위에서 각 클립의 시작점을 끌어서 옮기거나 시간을 직접 입력하고,
▶ 미리보기로 그 구간을 확인한 뒤 **이 구간으로 렌더링**을 누르면 릴스가 만들어집니다.
구간 추가·삭제, 자동 선택으로 되돌리기, 렌더 후 다시 조정도 가능합니다.

서버 없이 터미널에서도 실행할 수 있습니다.

```bash
python -m app.cli 공연영상.mp4 --artist 허지수 --handle j12xu \
  --schedule "10/6(화)\n1부: 8:00~8:30" --out ./결과
```

## 동작 방식

1. **하이라이트 분석** (`app/highlight.py`) — 영상 디코딩 없이 오디오만 분석해 빠릅니다.
   0.25초 단위로 음량(RMS)과 스펙트럼 플럭스(연주 에너지 변화, 박수)를 계산하고,
   30초 창을 1초씩 밀며 점수화합니다. 무음이 많은 창은 감점, 영상 맨 앞뒤는 소폭 감점.
   서로 겹치지 않는 상위 3개를 고른 뒤, 시작점을 근처의 프레이즈 경계(음량이 잠깐 꺼지는 지점)로 스냅합니다.
2. **렌더링** (`app/render.py`) — ffmpeg 한 번의 패스로
   9:16 크롭(중심 위치 조절 가능) → 1080×1920 → 옅은 비네트 →
   Mrs Saint Delafield 서명체 타이틀 + Noto Sans KR 외곽선 서브타이틀 (Pillow로 PNG에 그려 overlay) →
   H.264 / AAC, 라우드니스 -14 LUFS(인스타그램 권장) 로 정규화.
   렌더는 사용자가 구간을 확정한 뒤에만 실행되며, 재조정을 위해 원본은 작업 폴더에 보관됩니다(24시간 후 정리).
3. **캡션** (`app/caption.py`) — `app/config.py` 의 `CAPTION_TEMPLATE` 에 아티스트 정보를 채웁니다.

## 타이틀 폰트 바꾸기

구간 조정 화면의 **타이틀 폰트** 메뉴에서 고를 수 있고, 선택한 폰트로 실제 비율의 미리보기가 그려집니다.
`app/fonts/` 에 TTF/OTF 파일을 넣으면 서버를 재시작하지 않아도 목록에 자동으로 나타납니다
(예: 구매한 Brittany Signature 파일을 넣기). 기본값은 `app/config.py` 의 `TITLE_FONT` 입니다.
포함된 무료 폰트(OFL): Qwitcher Grypen(기본), Sacramento, Whisper, Tangerine, Mr De Haviland, Mrs Saint Delafield.

## 설정

`app/config.py` 에서 템플릿 문구, 폰트, 크기, 위치(화면 비율), 클립 길이·개수, 캡션 템플릿을 바꿀 수 있습니다.
폰트는 `app/fonts/` 에 포함되어 있습니다 (Mrs Saint Delafield, Noto Sans KR — OFL 라이선스).

## 폴더 구조

```
app/
  main.py        FastAPI 서버 (업로드 / 상태 / 다운로드)
  pipeline.py    잡 실행 (분석 → 렌더 → 캡션), jobs/<id>/status.json
  highlight.py   오디오 기반 하이라이트 탐지
  render.py      ffmpeg 9:16 렌더 + 고정 템플릿 오버레이
  caption.py     캡션 생성
  cli.py         커맨드라인 실행
  config.py      고정 템플릿 설정
  fonts/         GreatVibes-Regular.ttf, NotoSansKR-Regular.ttf
  static/        웹 UI
jobs/            결과물 (gitignore, 24시간 후 자동 정리)
```
