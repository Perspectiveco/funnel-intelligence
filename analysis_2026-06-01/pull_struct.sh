#!/bin/zsh
# Resilient one-time pull of funnel_struct_v1 -> local CSV. Survives flaky BQ connection.
cd /Users/alexanderdupre/Claude/funnel-intelligence/analysis_2026-06-01
DST="data/funnel_struct.csv"
GCS="gs://perspective-bi-funnel-intelligence/_tmp/fs"
for attempt in $(seq 1 40); do
  echo "[attempt $attempt] extract..."
  if bq extract --destination_format=CSV \
       perspective-bi:funnel_intelligence.funnel_struct_v1 \
       "${GCS}_*.csv" >/dev/null 2>&1; then
    echo "[attempt $attempt] extract OK, downloading..."
    rm -f data/fs_*.csv
    if gcloud storage cp "${GCS}_*.csv" data/ >/dev/null 2>&1; then
      shards=(data/fs_*.csv)
      if [[ -e ${shards[1]} ]]; then
        head -1 ${shards[1]} > "$DST"
        for f in data/fs_*.csv; do tail -n +2 "$f" >> "$DST"; done
        rm -f data/fs_*.csv
        rows=$(($(wc -l < "$DST")-1))
        if [[ $rows -gt 1000 ]]; then echo "SUCCESS rows=$rows"; exit 0; fi
      fi
    fi
  fi
  echo "[attempt $attempt] not yet; sleeping 30s"
  sleep 30
done
echo "GAVE_UP after 40 attempts"
exit 1
