ALB=$(aws ssm get-parameter \
  --name "/alex/ecs_url" \
  --region us-east-1 \
  --query "Parameter.Value" \
  --output text)

echo "=== Health Check ==="
curl -s $ALB/health | python3 -m json.tool

echo ""
echo "=== Fast Research ==="
curl -s -X POST $ALB/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "NVDA stock analysis"}' \
  --max-time 120 | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Status: {d.get(\"status\")}')
print(f'Length: {len(d.get(\"result\", \"\"))}')
print(f'Preview: {d.get(\"result\", \"\")[:150]}')
"

echo ""
echo "=== Streaming ==="
curl -s -X POST $ALB/research/stream \
  -H "Content-Type: application/json" \
  -d '{"topic": "AAPL analysis"}' \
  --no-buffer --max-time 120 \
  | grep -E "status|done|error" | head -5