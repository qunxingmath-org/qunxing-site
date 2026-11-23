# 部署说明（www）

这里是群星网站静态部分的服务器配置。不含任何密码、私钥或令牌，也不含服务器上其他服务（例如中转）的任何配置。

## 怎么工作

- **拉取式部署**：
  - 服务器上的 systemd 定时器每 5 分钟运行一次 `deploy-www.sh`。
  - 脚本从本仓库的 main 只读拉取（公开仓库，不需要凭据），把 `public/` 复制成一个新版本目录，再原子地切换 `current`。
  - 保留最近 5 个版本。
- **上线一个改动 = 合并一个 PR**：main 受保护，改动必须走 PR，`checks` 必须通过。合并后 5 分钟内上线。
- **服务器上不做构建**：以后的题目页和 API 由 GitHub Actions 构建，服务器只拉取产物（数据系统规格 8.10）。

## 目录和用户

| 路径或用户 | 用途 |
|---|---|
| `qx-deploy`（系统用户，不能登录） | 运行部署脚本，只能写 `/srv/qunxing/www` |
| `/srv/qunxing/www/repo` | 仓库的浅克隆 |
| `/srv/qunxing/www/releases/<提交哈希>/` | 各个版本 |
| `/srv/qunxing/www/current` | 指向当前版本的符号链接，nginx 的网站根目录 |
| `/usr/local/lib/qunxing/deploy-www.sh` | 部署脚本 |
| `/var/www/acme` | ACME HTTP-01 验证文件 |
| `/etc/qunxing/tls/www/` | 证书（`fullchain.pem`、`privkey.pem`），可以是指向 ACME 客户端目录的链接 |

以后的收件接口和机器人用各自的系统用户（例如 `qx-intake`、`qx-bot`），不和 `qx-deploy` 共用。

## 首次安装（root 执行）

```bash
# 1. 用户和目录
useradd --system --home-dir /srv/qunxing/www --shell /usr/sbin/nologin qx-deploy
install -d -o qx-deploy -g qx-deploy -m 755 /srv/qunxing/www
install -d -m 755 /var/www/acme /usr/local/lib/qunxing /etc/qunxing/tls/www

# 2. 部署脚本和定时器（在本仓库的克隆目录里执行）
install -m 755 deploy/bin/deploy-www.sh /usr/local/lib/qunxing/deploy-www.sh
install -m 644 deploy/systemd/qunxing-www-deploy.service deploy/systemd/qunxing-www-deploy.timer /etc/systemd/system/
systemctl daemon-reload
systemctl start qunxing-www-deploy.service      # 先手动部署一次
systemctl enable --now qunxing-www-deploy.timer

# 3. 证书：用支持 ARI 的 ACME 客户端，webroot 设为 /var/www/acme，
#    同时签 qunxingmath.org 和 www.qunxingmath.org（ECDSA P-256），
#    续期后重载 nginx，并把证书放到（或链接到）/etc/qunxing/tls/www/。
#    第一次签证书前，nginx 还没有证书可用：可以先只启用下面配置里的 80 端口部分。

# 4. nginx
install -m 644 deploy/nginx/qunxing-www.conf /etc/nginx/conf.d/qunxing-www.conf
nginx -t && systemctl reload nginx
```

## 检查

```bash
curl -sI http://qunxingmath.org/          # 301 → https://www.qunxingmath.org/
curl -sI https://qunxingmath.org/         # 301 → https://www.qunxingmath.org/
curl -sI https://www.qunxingmath.org/     # 200，带 HSTS、CSP、nosniff、Referrer-Policy
curl -s  https://www.qunxingmath.org/.well-known/security.txt
curl -s  https://www.qunxingmath.org/llms.txt
curl -sI https://www.qunxingmath.org/no-such-page   # 404
curl -sI -H 'Accept-Encoding: gzip' https://www.qunxingmath.org/   # Content-Encoding: gzip
journalctl -u qunxing-www-deploy.service -n 20      # 部署记录
```

另外，`.github/workflows/site-monitor.yml` 每天在 GitHub 上从外部检查一次，失败时 GitHub 会发邮件给维护者。检查的内容包括：
- 证书剩余天数，少于 21 天算失败；
- 三种跳转；
- 首页和安全响应头；
- `llms.txt`、`robots.txt`、`security.txt`；
- 404 页。

部署或改完配置后，可以在仓库的 Actions 页面手动运行一次，当作验收。

## 回滚

1. 先停定时器，否则 5 分钟后又会部署 main 的最新版本：`systemctl stop qunxing-www-deploy.timer`。
2. 把 `current` 指回旧版本：
   ```bash
   ln -sfn /srv/qunxing/www/releases/<旧版本> /srv/qunxing/www/current.new && mv -T /srv/qunxing/www/current.new /srv/qunxing/www/current
   ```
3. 在 GitHub 上用 PR 修好 main，再启动定时器：`systemctl start qunxing-www-deploy.timer`。

## 和同一台服务器上的其他服务共存

- 其他服务（例如中转）的 nginx 配置放在单独的文件里，不使用 qunxingmath.org 的任何主机名。
- 其他服务的密钥不放在 `/srv/qunxing/`，`qx-deploy` 也读不到它们。
- 本仓库是公开的，不要把其他服务的配置提交进来。
