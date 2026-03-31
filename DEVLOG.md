# 开发日志

## 当前阶段

目标：完善登录链路、稳定基础抢票流程，并为多设备协作保留清晰上下文。

## 已完成

- 增强 Cookie 登录，支持从 `Cookie:` 头、完整请求头、`curl`、`document.cookie` 文本自动提取
- 明确 Cookie 必填字段：`_m_h5_tk`、`_m_h5_tk_enc`
- 增加其他登录方式：已保存 Cookie、扫码登录
- 修复旧版登录校验误判：优先使用 `m.damai.cn` 判断登录态，降低单点请求失败导致的误报
- 登录成功后展示账号昵称与 UID
- 新增协作文档：`README.md`、`AGENTS.md`、`CLAUDE.md`、`CODEX.md`

## 关键文件

- `src/damai/core/auth.py`：Cookie 解析、登录校验、账号资料提取
- `src/damai/gui/widgets/login_tab.py`：登录页 UI、账号列表展示
- `src/damai/gui/widgets/qr_login_dialog.py`：扫码登录对话框
- `src/damai/gui/main_window.py`：登录流程与 GUI 事件接线
- `src/damai/gui/workers.py`：登录线程、抢票线程

## 待办

- 增加短信验证码登录
- 为核心逻辑补充测试
- 完善 README 的截图、使用示例与风险说明
- 继续验证扫码登录在不同网络环境下的稳定性
- 评估是否补充更强的登录态校验接口

## 已知问题

- `id.damai.cn/userinfo.htm` 在部分环境可能出现连接失败，不能单独作为登录态唯一判断依据
- 终端中个别中文输出可能受本地编码影响，GUI 内显示通常正常
- 当前仓库更适合自用测试与流程联调，未形成完整发布版本

## 最近一次验证

- 已通过 Python 语法检查与模块导入检查
- 已实际验证提供的 Cookie 可成功登录，不再误报“Cookie 失效”
- 已将当前代码与协作文档推送到 GitHub

## 协作建议

- 每次完成关键改动后，更新本文件的“已完成 / 待办 / 已知问题”
- 如果修改登录流程，同时同步更新 `README.md`、`CLAUDE.md`、`CODEX.md`
- 不要在仓库中提交真实 Cookie、个人信息或支付相关敏感数据
