# damai-ticket

大麦抢票工具，基于 Python `3.11+`、`httpx` 与 `PySide6`，提供桌面 GUI、配置管理、多账号登录、票务监控与下单流程骨架。

## 当前功能

- 图形界面启动：`python -m damai`
- Cookie 登录：支持粘贴 `Cookie` 头、完整请求头、`curl` 命令或 `document.cookie` 文本自动提取
- 登录态恢复：支持读取本地已保存 Cookie
- 扫码登录：支持在内嵌官方登录页中完成登录并导入当前 Cookie
- 账号信息展示：登录成功后显示账号昵称与 UID
- 抢票流程骨架：时间同步、会话预热、票档监控、并发下单、通知接口

## 项目结构

```text
config/              配置模板
src/damai/
  core/              登录、监控、下单、mTOP 客户端
  gui/               PySide6 图形界面
  notify/            微信 / 钉钉 / 邮件通知
  utils/             配置、加密、时间同步等工具
  anti_detect/       请求头、代理、指纹相关逻辑
```

## 安装与运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m damai
```

快速语法检查：

```bash
python -m compileall src
```

## 登录说明

### Cookie 登录

必填字段：

- `_m_h5_tk`
- `_m_h5_tk_enc`

推荐包含：

- `cookie2`
- `t`
- `cna`
- `unb`
- `sgcookie`

支持直接粘贴浏览器开发者工具中的 `Cookie:` 请求头，或完整抓包文本。程序会自动提取并校验关键字段。

### 扫码登录

登录页内嵌在 GUI 中，完成扫码或账号登录后，程序会捕获当前登录 Cookie 并导入。当前实现优先使用 `m.damai.cn` 校验登录态，避免单一校验地址不可达时误判 Cookie 失效。

## 配置

- `config/default.toml`：默认运行配置
- `config/accounts.toml`：账号模板配置
- 本地运行数据默认保存在 `%USERPROFILE%\.damai-ticket`

不要提交真实 Cookie、Webhook、邮箱凭据或个人购票信息。

## 开发协作

- `AGENTS.md`：仓库协作规范
- `CLAUDE.md`：Claude 协作上下文
- `CODEX.md`：Codex 协作上下文

这三个文件用于同步当前开发状态、关键约定与下一步计划，方便多人或多代理共享进度。

## 当前状态

当前版本适合自用测试与界面/流程联调，已完成登录入口增强与基础抢票流程串联。后续可继续补充短信登录、更严格的登录态校验、正式测试用例与更完整的异常恢复逻辑。
