# 群星网站 · qunxing-site

qunxingmath.org 的源码，包括：

- **静态站**：题目页、星图、统计、贡献者名单、研究守则；
- **给 Agent 读的接口**：`/api/v1` 静态 JSON 和 `llms.txt`；
- **收件接口**：接收桌面端提交的证明和科研数据。需要账号，两类内容分别同意。

> 状态：搭建中。

## 目录

- `public/`：网站的静态文件，原样发布。现在是一个占位页，以及 `robots.txt`、`llms.txt`、`/.well-known/security.txt`。
- `deploy/`：服务器配置和部署脚本，见 [deploy/README.md](deploy/README.md)。不含任何密钥。

## 部署

- 现在：服务器每 5 分钟从 main 拉取 `public/`，原子切换，保留 5 个版本（见 `deploy/README.md`）。
- 以后：题目页和 API 由 GitHub Actions 构建，服务器按签名清单拉取新版本，同时发布 GitHub Pages 镜像。
- 本仓库不放任何密钥，也不放服务器上其他服务的配置。

## 许可

- 代码：[MIT](LICENSE)。
- 题卡文字和证明文字的许可，以 qunxing-data、qunxing-proofs 为准。
- "群星"的名称和标志不在 MIT 许可之内，见 [TRADEMARKS.md](TRADEMARKS.md)。

---

**English.** Source of qunxingmath.org:

- the static site;
- a static JSON API and `llms.txt` for agents;
- the intake API for submissions from the desktop app.

Status: under construction. Code: MIT.
