# TS 채용 레이더

원티드 · 잡코리아 · 사람인 · 리멤버에서 **기술지원(TS) 중심 공고**를 모아
서울 / 경기 남부만 남기고, 잡플래닛 평점과 "내 경력 적합도"를 붙여 보여주는 사이트입니다.

## 구조 한눈에 보기

```
crawler/            ← 수집 프로그램 (Python)
  config.py         ← ★ 검색 키워드·지역·직군 규칙 (여기만 고치면 됨)
  build.py          ← 전체 실행: 수집 → 필터 → 중복제거 → 평점 → 점수 → 저장
  sources/          ← 사이트별 수집 코드 (wanted, jobkorea, saramin, remember, jobplanet)
site/
  index.html        ← 화면 (jobs.json을 읽어서 표로 보여줌)
  jobs.json         ← 수집 결과 (크롤러가 매번 새로 씀)
data/
  ratings_cache.json← 잡플래닛 평점 저장소 (30일간 재사용 → 빠르고 사이트 부담 적음)
update.sh           ← 수집 + GitHub 업로드를 한 번에
render.yaml         ← Render 배포 설정
```

**왜 이렇게 나눴나?** 수집(무거움)과 화면(가벼움)을 분리하면, Render에는 완성된 파일만 올리면 돼서
무료 정적 사이트로 충분합니다. 서버가 없으니 장애 날 곳도 줄어듭니다.

## 처음 한 번: 준비

맥 **터미널**을 열고:

```bash
cd ~/PycharmProjects/job-crawler
python3 -m pip install -r requirements.txt
```

## 공고 새로 모으기

```bash
./update.sh          # 수집 + (연결돼 있으면) GitHub 업로드
# 또는 수집만:
python3 crawler/build.py
```

첫 실행은 10~20분 걸릴 수 있어요(사이트마다 1초씩 쉬어 가며 요청하고, 처음 보는 회사마다 잡플래닛 페이지를 열기 때문).
한 번 확인한 회사 평점은 30일간 저장해 두므로, 그다음부터는 몇 분이면 끝납니다.

내 맥에서 화면 확인:

```bash
python3 -m http.server -d site 8000
# 브라우저에서 http://localhost:8000
```

## 매일 자동으로 돌리기

```bash
./schedule.sh          # 매일 08:30 (시각 바꾸기: ./schedule.sh 07:00)
./schedule.sh test     # 지금 한 번 시험 실행
./schedule.sh status   # 예약 상태·최근 기록
./schedule.sh off      # 예약 해제
```

- 맥이 잠자기 중이면 깨어날 때 실행하고, 전원이 꺼져 있으면 그날은 건너뜁니다.
- 자동 실행은 비밀번호를 물을 수 없으므로, **터미널에서 `./update.sh`로 한 번 업로드에 성공**(토큰 저장)한 뒤 예약하세요.
- 기록 파일: `~/Library/Logs/job-crawler.log`

## 왜 수집은 "내 맥"에서 하나요?

원티드 같은 사이트는 **클라우드 서버 IP(Render, GitHub Actions 등)에서 오는 요청을 차단**하는 경우가 많습니다
(방화벽/WAF가 봇 트래픽으로 판단). 집 인터넷에서 돌리면 일반 사용자와 같은 경로라 안정적입니다.
그래서 **수집은 맥 → 결과 파일만 GitHub → Render는 보여주기만** 하는 구조를 택했어요.

## 한 사이트가 실패하면?

나머지 사이트는 계속 수집하고, 실패한 사이트의 공고는 **직전 데이터를 유지**합니다.
화면 상단 출처 옆 점이 빨간색이면 그 사이트가 이번에 실패한 것입니다.
(사이트 구조가 바뀌면 `crawler/sources/사이트명.py`만 고치면 됩니다.)

## 수집 방식과 예의

- 원티드: 화면이 쓰는 공개 JSON(API v4)
- 잡코리아: 검색 결과 페이지에 함께 내려오는 JSON
- 사람인: 검색 결과 HTML (API 키 불필요)
- 리멤버: 공고 목록 화면이 쓰는 검색 API (로그인 불필요)
- 잡플래닛: 회사명 자동완성 → 회사 페이지의 평점. robots.txt가 막는 `/search`는 쓰지 않습니다.
- 모든 요청 사이 1초 대기, 개인 용도로만 사용.
