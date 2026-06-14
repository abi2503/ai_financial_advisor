#!/bin/bash
# Measure Alex fast-research latency (ECS direct)
set -e
cd "$(dirname "$0")/.."

ECS="${ECS_URL:-http://alex-alb-1582546453.us-east-1.elb.amazonaws.com}"
USER_ID="${1:-user_3EjDRkfojIp599preEYnkjMESKu}"
TOPIC="${2:-Brief NVDA outlook}"

echo "════════════════════════════════════════"
echo "  Alex Latency Benchmark"
echo "  ECS: $ECS"
echo "  Topic: $TOPIC"
echo "════════════════════════════════════════"

echo ""
echo "0. Waking Aurora..."
python3 scripts/aurora_warmup.py 2>&1 | head -2

bench() {
  local label="$1"
  local path="$2"
  local body="$3"
  echo ""
  echo "--- $label ---"
  curl -s -o /tmp/bench_out.txt -w "http_total: %{time_total}s\n" \
    -X POST "$ECS$path" \
    -H "Content-Type: application/json" \
    -d "$body" --max-time 120
  python3 -c "
import json, sys
raw=open('/tmp/bench_out.txt').read()
try:
    d=json.loads(raw)
    r=d.get('result','')
    print(f'status={d.get(\"status\",\"?\")} chars={len(r)}')
except Exception:
    print(raw[:200])
"
}

BODY_AUTH="{\"topic\":\"$TOPIC\",\"user_id\":\"$USER_ID\",\"session_id\":\"latency-bench\"}"
BODY_ANON="{\"topic\":\"$TOPIC\"}"

bench "Fast /research (authenticated)" "/research" "$BODY_AUTH"
bench "Fast /research (anonymous)" "/research" "$BODY_ANON"

echo ""
echo "--- Fast /research/stream (time to first token) ---"
curl -s -N -X POST "$ECS/research/stream" \
  -H "Content-Type: application/json" \
  -d "$BODY_AUTH" --max-time 120 2>/dev/null | python3 -c "
import sys, time, json
start = time.time()
first_token = None
time_to_answer = None
total = None
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('data:'): continue
    try:
        d = json.loads(line[5:].strip())
    except Exception:
        continue
    t = time.time() - start
    typ = d.get('type', '')
    if typ == 'token' and first_token is None:
        first_token = t
    if typ == 'done':
        total = d.get('latency', round(t, 1))
        time_to_answer = d.get('time_to_answer')
        break
print(f'first_token: {first_token:.1f}s' if first_token else 'first_token: never')
if time_to_answer:
    print(f'time_to_answer: {time_to_answer}s')
print(f'total_stream: {total}s' if total else 'total_stream: incomplete')
"

echo ""
echo "Targets (fast mode):"
echo "  /research:        < 12s"
echo "  first_token:      < 12s"
echo "  total_stream:     < 15s"
echo "════════════════════════════════════════"
