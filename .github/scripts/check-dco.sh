#!/usr/bin/env bash
# DCO 签名检查：PR 里每个非合并提交，都要有一行 Signed-off-by，并且邮箱与提交作者一致。
# 用法：check-dco.sh <base-sha> <head-sha>
# 作者名以 [bot] 结尾的机器人提交跳过。
set -euo pipefail

base="${1:?缺少 base 提交}"
head="${2:?缺少 head 提交}"
fail=0
count=0

while IFS= read -r sha; do
  [ -n "$sha" ] || continue
  count=$((count + 1))
  name=$(git log -1 --format='%an' "$sha")
  email=$(git log -1 --format='%ae' "$sha")
  case "$name" in
    *"[bot]") continue ;;
  esac
  signoffs=$(git log -1 --format='%(trailers:key=Signed-off-by,valueonly)' "$sha")
  if [ -z "$signoffs" ]; then
    echo "::error::提交 ${sha:0:7} 缺少 Signed-off-by。请用 git commit -s 提交，补签方法见 CONTRIBUTING.md。"
    fail=1
  elif ! printf '%s\n' "$signoffs" | grep -qiF "<${email}>"; then
    echo "::error::提交 ${sha:0:7} 的 Signed-off-by 与作者邮箱 <${email}> 不一致。"
    fail=1
  fi
done < <(git rev-list --no-merges "${base}..${head}")

if [ "$fail" -eq 0 ]; then
  echo "DCO 签名检查通过（${count} 个提交）。"
fi
exit "$fail"
