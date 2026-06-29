#!/bin/bash
# 여행 계획 에이전트 - 공개 URL로 실행

echo "🚀 서버 시작 중..."
python3 server.py &
SERVER_PID=$!
sleep 2

echo ""
echo "🌐 공개 터널 연결 중... (URL이 나올 때까지 10~20초 소요)"
echo ""

# localhost.run SSH 터널 (설치 불필요)
ssh -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -R 80:localhost:8000 \
    nokey@localhost.run 2>&1 &
TUNNEL_PID=$!

# Ctrl+C 시 정리
trap "echo ''; echo '🛑 종료 중...'; kill $SERVER_PID $TUNNEL_PID 2>/dev/null; exit" INT

wait $TUNNEL_PID
kill $SERVER_PID 2>/dev/null
