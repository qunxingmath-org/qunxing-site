# 安全问题报告

## 怎么报告

请**不要**在公开的 Issue、PR 或讨论里贴出漏洞细节。

- **首选**：打开出问题的仓库，进入 **Security** 页（有的界面叫 Security and quality），在 **Advisories** 里点 **Report a vulnerability**，私下提交。
- **也可以**：发邮件到 team@qunxingmath.org，标题写 `[security]`。

请尽量写清：
- 影响哪个组件和版本；
- 怎么复现；
- 可能造成什么影响。

## 我们会怎么处理

- 7 天内答复，确认收到并给出初步判断。
- 修复后发布安全公告。你同意的话，会在公告里致谢。
- 修复发布之前，请不要公开细节。

## 范围

- 群星桌面端（qunxing-app）。
- 网站、收件接口和账号（qunxing-site）。
- 数据和证明仓库的自动流程（qunxing-data、qunxing-proofs）。

**不在范围内**：拒绝服务和压力测试、社会工程、实际访问其他用户的数据。测试时只用你自己的账号和数据。

## 发现泄露的密钥

如果你在群星的仓库里看到密钥或令牌，请按上面的方式私下告诉我们，不要使用它。

---

## English

- Please do not disclose vulnerabilities publicly.
- Report them privately: in the affected repository, open **Security → Advisories → Report a vulnerability**, or email team@qunxingmath.org with `[security]` in the subject.
- We aim to respond within 7 days.
