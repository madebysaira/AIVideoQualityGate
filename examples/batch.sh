# Batch usage

The command is intentionally ordinary enough to call from n8n's Execute Command node, a shell queue, or a CI job.

```bash
mkdir -p reports
for file in exports/*.mp4; do
  name="$(basename "$file" .mp4)"
  python3 qualitygate.py "$file" --profile vertical \
    --markdown "reports/$name.md" \
    --json "reports/$name.json" || printf '%s\n' "$file" >> reports/review-queue.txt
done
```

Keep the report beside the render. A human can inspect the timestamps before deciding whether a black section is an actual failure or an intentional transition.
