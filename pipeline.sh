#! /bin/bash

page_ids=(221451469 142776653 162173292)

for page_id in "${page_ids[@]}"; do
  uv run confluence-export \
    --page-id "$page_id" \
    --format markdown \
    --output ./export \
    --recursive
done
