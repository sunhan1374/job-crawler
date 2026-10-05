#!/bin/bash
# 매일 정해진 시각에 update.sh(수집 + GitHub 업로드)를 자동 실행하도록 맥에 예약합니다.
#
# 사용법
#   ./schedule.sh            → 매일 08:30에 실행 (기본값)
#   ./schedule.sh 07:00      → 매일 07:00에 실행
#   ./schedule.sh off        → 예약 해제
#   ./schedule.sh test       → 지금 바로 한 번 실행해 보기 (예약이 잘 걸렸는지 확인용)
#   ./schedule.sh status     → 예약 상태와 최근 실행 기록 보기
#
# 원리: macOS 기본 예약 기능인 launchd에 "작업 설명서(plist)"를 등록합니다.
#       맥이 잠자기 중이라 그 시각을 놓치면, 깨어날 때 한 번 실행해 줍니다. (전원이 꺼져 있으면 건너뜀)
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
LABEL="com.sunhan.job-crawler"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
OUT="$HOME/Library/Logs/job-crawler.log"
DOMAIN="gui/$(id -u)"

case "${1:-08:30}" in
  off)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✔ 자동 실행 예약을 해제했어요."
    exit 0 ;;
  test)
    launchctl kickstart -k "$DOMAIN/$LABEL" && echo "▶ 지금 실행을 시작했어요. 진행 상황: tail -f \"$OUT\""
    exit 0 ;;
  status)
    launchctl print "$DOMAIN/$LABEL" 2>/dev/null | grep -E "state|last exit code|runs" || echo "예약이 없어요."
    echo "── 최근 실행 기록 ($OUT) ──"
    tail -n 15 "$OUT" 2>/dev/null || echo "(아직 기록 없음)"
    exit 0 ;;
esac

TIME="${1:-08:30}"
if ! [[ "$TIME" =~ ^([01]?[0-9]|2[0-3]):[0-5][0-9]$ ]]; then
  echo "✘ 시각은 07:00 처럼 HH:MM 형식으로 적어 주세요."; exit 1
fi
HOUR=$((10#${TIME%%:*})); MIN=$((10#${TIME##*:}))

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$DIR/update.sh</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>$MIN</integer></dict>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>GIT_TERMINAL_PROMPT</key><string>0</string>
  </dict>
  <key>StandardOutPath</key><string>$OUT</string>
  <key>StandardErrorPath</key><string>$OUT</string>
</dict>
</plist>
EOF

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"
printf "✔ 매일 %02d:%02d에 자동으로 공고를 수집하고 올리도록 예약했어요.\n" "$HOUR" "$MIN"
echo "  · 지금 바로 시험: ./schedule.sh test"
echo "  · 상태/기록 보기: ./schedule.sh status"
echo "  · 예약 해제:     ./schedule.sh off"
