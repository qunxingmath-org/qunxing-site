# 群星网站 · qunxing-site

qunxingmath.org 的源码，包括：

- **静态站**：题目页、星图、统计、贡献者名单、研究守则；
- **给 Agent 读的接口**：`/api/v1` 静态 JSON 和 `llms.txt`；
- **收件接口**：接收桌面端提交的证明和科研数据。需要账号，两类内容分别同意。

> 状态：搭建中。

## 目录

- `public/`：网站的静态文件，原样发布。现在是一个占位页，以及 `robots.txt`、`llms.txt`、`/.well-known/security.txt`。
- `deploy/`：服务器配置和部署脚本，见 [deploy/README.md](deploy/README.md)。不含任何密钥。

## 题库

- `public/problems/`（中文）、`public/en/problems/`（英文）、`public/p/<编号>/`（题目页和 `.md`）、`public/api/v1/`（静态 JSON），由 `tools/build_problems.py` 从 qunxing-data 生成；`data/bank.json` 记下用的是哪个提交。
- 更新题库：
  1. 把 qunxing-data 的本地克隆切到要发布的提交；
  2. 运行 `python3 tools/build_problems.py --data <qunxing-data>`；
  3. 提交 PR。
- 生成的目录（`public/problems`、`public/en/problems`、`public/p`、`public/api/v1`）由脚本整体管理，不要手改。
- CI 按 `data/bank.json` 里的提交取 qunxing-data，检查页面是否一致。
- 以后（WEB-040）改为由 CI 构建、服务器拉取构建结果，不再把生成的文件提交进仓库。

## 下载页

- 页面 `public/download/`（中文）和 `public/en/download/`（英文）由 `tools/build_download.py` 从 `data/release.json` 生成。网站不允许脚本，所以是生成好的静态页面。
- 桌面端发布新版本后：
  1. 在 `data/release.json` 里填版本号、日期、两个文件的大小和 SHA-256，`available` 改成 `true`；
  2. 运行 `python3 tools/build_download.py`；
  3. 提交 PR。以后由发布流程自动做这几步。
- 按钮指向这个版本在 GitHub Release 上的文件，页面上的版本号和 SHA-256 与文件一一对应。
- `mirror` 为 `true` 时显示国内镜像的链接 `/download/files/<版本>/`。镜像文件不进仓库，由服务器从 Release 同步，SHA-256 一致才上线。
- CI 会检查页面和 `data/release.json` 是否一致（`python3 tools/build_download.py --check`）。

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

The download page (`public/download/`, `public/en/download/`) is generated from `data/release.json` by `tools/build_download.py`; CI checks that they match.
