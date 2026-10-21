# Singlemarks Reel Maker — Concert Every Night

롱폼 공연 영상을 업로드하면 **하이라이트 구간을 자동으로 찾아 30초 릴스 3개**와
인스타그램 캡션을 만들어 주는 자동화 편집기입니다.

영상 템플릿은 고정입니다.

- 필기체 타이틀: **Concert Every Night**
- 한글 서브타이틀: **매일 밤 열리는 낭만적인 공연**

아티스트 이름 · 계정 · 공연 일정만 바꿔 캡션에 반영됩니다.

## 직원용 설치 안내 (3단계)

git, Python, ffmpeg 를 몰라도 됩니다. 처음 한 번만 아래를 하면 됩니다.

1. **코드 받기**: https://github.com/singlemarks-hash/singlemarks-reel/tree/claude/loving-feynman-1bq8lj 에서
   초록색 **Code → Download ZIP** 을 누르고, 받은 ZIP 을 더블클릭해 풉니다.
   (git 을 쓸 줄 알면 `git clone` 후 `git checkout claude/loving-feynman-1bq8lj` 도 됩니다. 이 경우 실행할 때마다 자동 업데이트됩니다.)
2. **실행**: 풀린 폴더 안의 **`start.command`** (Mac) 또는 **`start.bat`** (Windows) 를 더블클릭합니다.
   - Mac 에서 **"start.command"을(를) 열 수 없습니다 / Apple이 확인할 수 없습니다** 경고가 뜨면 (그 Mac에서 한 번만):
     **Done** 을 누른 뒤 **시스템 설정 → 개인정보 보호 및 보안** 맨 아래의 **그래도 열기(Open Anyway)** 를 누르고 다시 더블클릭합니다.
     또는 터미널에 `xattr -d com.apple.quarantine ` 을 입력하고 start.command 파일을 끌어다 놓은 뒤 Enter.
   - Mac 에서 "명령어 라인 개발자 도구" 설치 팝업이 뜨면 **[설치]** 를 누르고, 끝나면 다시 더블클릭합니다.
   - 처음에는 ffmpeg(약 100MB)와 패키지를 자동으로 내려받아 1~3분 걸립니다. 두 번째부터는 몇 초면 켜집니다.
3. 검은 창이 뜨고 브라우저가 자동으로 열립니다. **그 창은 닫지 말고** 쓰세요. 끝낼 때 Ctrl + C 또는 창 닫기.

폰으로 찍은 영상은 AirDrop 등으로 컴퓨터에 옮긴 뒤 화면에 끌어다 놓으면 됩니다.
영상은 그 컴퓨터 안에서만 처리되고 외부로 나가지 않습니다. 결과물은 폴더 안 `jobs/` 에 24시간 보관됩니다.

터미널에서 직접 실행하려면:

```bash
pip install -r requirements.txt     # ffmpeg / ffprobe 가 PATH 에 있어야 합니다
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## (선택) 클라우드 배포

직원 컴퓨터에서 직접 실행하는 것이 기본입니다. 서버에 올리고 싶다면 `Dockerfile` 과 `railway.json` / `fly.toml` 이 준비돼 있습니다.
원본 영상은 결과 화면의 **완료** 버튼으로 즉시 삭제되고, 누르지 않아도 2시간 뒤 자동 삭제됩니다.

## 동작 방식

1. **하이라이트 분석** (`app/highlight.py`) — 영상 디코딩 없이 오디오만 분석해 빠릅니다.
   0.25초 단위로 음량(RMS)과 스펙트럼 플럭스(연주 에너지 변화, 박수)를 계산하고,
   30초 창을 1초씩 밀며 점수화합니다. 무음이 많은 창은 감점, 영상 맨 앞뒤는 소폭 감점.
   서로 겹치지 않는 상위 3개를 고른 뒤, 시작점을 근처의 프레이즈 경계(음량이 잠깐 꺼지는 지점)로 스냅합니다.
2. **렌더링** (`app/render.py`) — ffmpeg 한 번의 패스로
   9:16 크롭 → 1080×1920 →
   Mrs Saint Delafield 서명체 타이틀 + Noto Sans KR 외곽선 서브타이틀 (Pillow로 PNG에 그려 overlay) →
   H.264 CRF 18 / AAC 256k, 라우드니스 -14 LUFS(인스타그램 권장) 로 정규화.

   **화질 정책**: 원본을 한 번 재인코딩하지만 시각적으로 구분이 어려운 수준(CRF 18)으로 유지합니다.
   원본 프레임레이트(24/30/60fps)는 그대로 보존하고, 아이폰 HDR(HLG/Dolby Vision) 영상은
   색이 바래지 않도록 SDR로 톤매핑합니다. 비네트·페이드 같은 효과는 넣지 않습니다.
   4K 원본은 인스타그램 최대 규격인 1080 폭으로 줄어듭니다.
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
