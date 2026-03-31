# Claude 协作说明

## 当前状态

- 已完成 Cookie 文本自动提取与关键字段校验
- 已完成已保存 Cookie 恢复登录
- 已完成内嵌官方页面的扫码登录导入
- 已完成登录成功后显示大麦昵称与 UID
- 已修复旧版登录校验对 `id.damai.cn` 连通性过度依赖导致的误判

## 关键文件

- `src/damai/core/auth.py`：Cookie 解析、登录校验、账号资料提取
- `src/damai/gui/widgets/login_tab.py`：登录页 UI 与账号列表展示
- `src/damai/gui/widgets/qr_login_dialog.py`：扫码登录对话框
- `src/damai/gui/main_window.py`：登录流程接线
- `src/damai/gui/workers.py`：登录线程与抢票线程

## 下一步建议

- 补充短信验证码登录
- 增加更稳定的账号资料获取接口
- 为 `core/` 层增加测试
- 完善 README 与配置示例

## 协作约定

- 优先保持改动小而集中
- 不提交真实 Cookie 或个人信息
- 变更登录流程时同步更新 `README.md`、`AGENTS.md`、`CODEX.md`
