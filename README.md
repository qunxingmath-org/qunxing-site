# 群星网站 · qunxing-site

qunxingmath.org 的源码，包括：

- **静态站**：题目页、星图、统计、贡献者名单、研究守则；
- **给 Agent 读的接口**：`/api/v1` 静态 JSON 和 `llms.txt`；
- **收件接口**：接收桌面端提交的证明和科研数据。需要账号，两类内容分别同意。

> 状态：搭建中。

## 部署

- 用 GitHub Actions 构建。服务器按签名清单拉取新版本，同时发布 GitHub Pages 镜像。
- 服务器配置和密钥不在本仓库。本仓库不放任何密钥。

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
