# 参与群星

感谢你愿意参与。这份说明适用于 qunxingmath-org 下的所有仓库，每个公开仓库里都放了一份相同的。

## 可以做什么

- **报告问题**：在对应仓库开 Issue，选合适的模板。安全问题不要公开发，见 [SECURITY.md](SECURITY.md)。
- **题面异议**：在 qunxing-data 开 Issue，选"题面异议"，指出具体位置。
- **改代码或文档**：开 PR。改动较大的，先开 Issue 讨论。
- **提交证明、点亮星星**：用群星桌面端提交，桌面端会附上检查参数和同意记录。直接向 qunxing-proofs 开的 PR 不会点亮星星。

## 提交规则

1. **每个提交都要签名（DCO）**。
   - 用 `git commit -s` 提交，提交说明末尾会多一行 `Signed-off-by: 你的名字 <你的邮箱>`。这个邮箱要和提交作者的邮箱一致。
   - 签名表示你同意 [Developer Certificate of Origin 1.1](https://developercertificate.org/)，也就是你有权提交这份贡献。
   - 忘了签名的话，最后一个提交用 `git commit --amend -s`，多个提交用 `git rebase --signoff main`，然后 `git push --force-with-lease`。
2. **许可**：你的贡献按所在仓库的许可发布。代码用 MIT，Lean 代码用 Apache-2.0，数据和文字见各仓库的 LICENSE。
3. **不要提交**：密钥、令牌、个人信息、别人的对话记录。CI 会检查常见的密钥格式。
4. **用了 AI 的话**：在 PR 里写明用了哪些模型和工具。AI 生成的内容，同样要你自己确认并签名。
5. **一个 PR 只做一件事**：写清改了什么、为什么改、怎么验证的。

## 合并

- 所有改动都通过 PR 合并到 main。CI 通过后（签名检查、仓库卫生检查），由维护者合并。
- 外部贡献者的 PR，要等维护者批准后，工作流才会运行。

## 行为

- 请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
- 不要用 Agent 代你点星、评论或刷量。GitHub 的可接受使用政策也禁止这样做。

---

## English summary

- Open an issue or pull request in the relevant repository; discuss large changes in an issue first.
- Every commit needs a DCO sign-off (`git commit -s`) whose email matches the commit author.
- Contributions are licensed under the license of the repository they go into.
- Never commit secrets, tokens or personal data.
- If you used AI tools, name the models and tools in the pull request.
- Proofs that light stars are submitted through the Qunxing desktop app. Pull requests opened directly against qunxing-proofs do not light stars.
