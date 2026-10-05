#!/bin/bash
# 공고를 새로 수집하고 GitHub에 올립니다. → Render가 자동으로 사이트를 갱신합니다.
# 사용법: 터미널에서  ./update.sh
set -e
set -o pipefail   # 수집이 실패하면 업로드 단계로 넘어가지 않게
cd "$(dirname "$0")"

mkdir -p logs
LOG="logs/$(date +%Y-%m).log"
echo "===== $(date '+%Y-%m-%d %H:%M') =====" >> "$LOG"

# 맥에는 python3가 여러 개 설치돼 있을 수 있어요.
# (예: 옛 인텔 전용 버전은 M칩 맥에서 'Bad CPU type' 오류)
# 실제로 실행되고 requests 라이브러리가 있는 python3를 골라 씁니다.
PY=""
for cand in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if "$cand" -c "import requests, bs4" >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "✘ 쓸 수 있는 python3를 못 찾았어요. 먼저 실행: /usr/bin/python3 -m pip install -r requirements.txt" | tee -a "$LOG"
  exit 1
fi
echo "사용하는 Python: $PY" | tee -a "$LOG"

"$PY" crawler/build.py 2>&1 | tee -a "$LOG"

# GitHub 저장소가 연결되어 있을 때만 올립니다.
if git remote get-url origin >/dev/null 2>&1; then
  git add site/jobs.json data/ratings_cache.json
  if git diff --cached --quiet; then
    echo "변경된 공고가 없어 업로드를 건너뜁니다." | tee -a "$LOG"
  else
    git commit -m "공고 갱신 $(date '+%Y-%m-%d %H:%M')" >> "$LOG" 2>&1
    git push >> "$LOG" 2>&1 && echo "✔ GitHub 업로드 완료 → Render가 1~2분 안에 사이트를 갱신합니다." | tee -a "$LOG"
  fi
else
  echo "(GitHub 저장소가 아직 연결되지 않아 수집만 했어요. site/index.html 을 열어 확인하세요.)"
fi
