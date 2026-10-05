#!/bin/bash
# 공고를 새로 수집하고 GitHub에 올립니다. → Render가 자동으로 사이트를 갱신합니다.
# 사용법: 터미널에서  ./update.sh
set -e
cd "$(dirname "$0")"

mkdir -p logs
LOG="logs/$(date +%Y-%m).log"
echo "===== $(date '+%Y-%m-%d %H:%M') =====" >> "$LOG"

python3 crawler/build.py 2>&1 | tee -a "$LOG"

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
