#!/usr/bin/env bash
# 仓库卫生检查：不收密钥、不收常见的密钥文件、不收大文件。
# 只输出文件名和行号，不把疑似密钥打印到公开的日志里。
# 环境变量：MAX_FILE_MB（单个文件的上限，默认 10）。
set -euo pipefail

max_mb="${MAX_FILE_MB:-10}"
self=".github/scripts/check-hygiene.sh"
fail=0

# 1. 常见的密钥文件名（.env.example 除外）
bad_names=$(git ls-files | grep -E -i \
  '(^|/)(\.env(\.[^/]*)?|id_(rsa|dsa|ecdsa|ed25519)|[^/]*\.(pem|key|p12|pfx|jks|keystore|agekey)|credentials(\.json)?|[^/]*age-identity[^/]*)$' \
  | grep -v -E '(^|/)\.env\.example$' || true)
if [ -n "$bad_names" ]; then
  echo "::error::发现疑似密钥文件，请删除，并换掉其中的密钥："
  printf '%s\n' "$bad_names" | sed 's/^/  /'
  fail=1
fi

# 2. 文件内容里的密钥（只列位置）
patterns=(
  '-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY-----'
  '-----BEGIN PGP PRIVATE KEY BLOCK-----'
  'AGE-SECRET-KEY-1[0-9A-Z]{58}'
  'gh[pousr]_[A-Za-z0-9]{36}'
  'github_pat_[A-Za-z0-9_]{60,}'
  '(^|[^A-Za-z0-9_-])sk-(ant-|proj-)?[A-Za-z0-9_-]{32,}'
  'AKIA[0-9A-Z]{16}'
  'AIza[0-9A-Za-z_-]{35}'
  'xox[abprs]-[A-Za-z0-9-]{10,}'
)
for p in "${patterns[@]}"; do
  hits=$(git grep -I -n -E -e "$p" -- . ":(exclude)${self}" | cut -d: -f1,2 || true)
  if [ -n "$hits" ]; then
    echo "::error::发现疑似密钥，请删除，并换掉这个密钥（只列位置）："
    printf '%s\n' "$hits" | sed 's/^/  /'
    fail=1
  fi
done

# 3. 大文件
limit=$((max_mb * 1024 * 1024))
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  size=$(stat -c %s -- "$f")
  if [ "$size" -gt "$limit" ]; then
    echo "::error file=${f}::文件超过 ${max_mb} MB（约 $((size / 1024 / 1024)) MB）。"
    fail=1
  fi
done < <(git ls-files -z)

if [ "$fail" -eq 0 ]; then
  echo "仓库卫生检查通过。"
fi
exit "$fail"
