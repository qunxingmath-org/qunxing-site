#!/usr/bin/env bash
# 群星网站（www）的拉取式部署：
# - 从公开仓库 qunxing-site 的 main 只读拉取，不需要任何凭据；
# - 把 public/ 复制成一个新版本目录，预压缩后，用原子改名切换 current；
# - 保留最近 KEEP 个版本。
# 由 systemd 定时器以 qx-deploy 用户运行，见 deploy/systemd/。
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/qunxingmath-org/qunxing-site.git}"
BRANCH="${BRANCH:-main}"
BASE="${BASE:-/srv/qunxing/www}"
KEEP="${KEEP:-5}"

cache="$BASE/repo"
releases="$BASE/releases"
current="$BASE/current"
mkdir -p "$releases"

# 1. 拉取最新的 main（浅克隆，只读）
if [ -d "$cache/.git" ]; then
  git -C "$cache" fetch --quiet --depth 1 origin "$BRANCH"
  git -C "$cache" reset --quiet --hard FETCH_HEAD
else
  git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$cache"
fi
rev=$(git -C "$cache" rev-parse HEAD)
target="$releases/$rev"

# 2. 已经是这个版本就什么都不做
if [ -L "$current" ] && [ "$(readlink -f "$current")" = "$(readlink -f "$target" 2>/dev/null || true)" ]; then
  exit 0
fi

# 3. 准备新版本目录（同一版本已存在时直接复用）
if [ ! -d "$target" ]; then
  if [ ! -f "$cache/public/index.html" ]; then
    echo "public/index.html 不存在，放弃部署 $rev" >&2
    exit 1
  fi
  tmp="$releases/.tmp-$rev"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  cp -a "$cache/public/." "$tmp/"
  # 给 nginx 的 gzip_static 准备 .gz 文件
  find "$tmp" -type f \( -name '*.html' -o -name '*.css' -o -name '*.js' -o -name '*.json' \
    -o -name '*.txt' -o -name '*.svg' -o -name '*.xml' -o -name '*.md' \) -exec gzip -9 -k -n -f {} +
  chmod -R u=rwX,go=rX "$tmp"
  mv "$tmp" "$target"
fi

# 4. 原子切换
ln -sfn "$target" "$BASE/current.new"
mv -T "$BASE/current.new" "$current"
echo "已部署 $rev"

# 5. 只保留最近 KEEP 个版本，当前版本永远保留
live=$(readlink -f "$current")
count=0
while IFS= read -r dir; do
  dir="${dir%/}"
  [ "$(readlink -f "$dir")" = "$live" ] && continue
  count=$((count + 1))
  if [ "$count" -ge "$KEEP" ]; then
    rm -rf -- "$dir"
  fi
done < <(ls -1dt "$releases"/*/ 2>/dev/null)
