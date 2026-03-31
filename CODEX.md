# Codex 协作说明

## 已完成内容

- 中文化 `AGENTS.md`
- 增强 Cookie 登录：支持从粘贴文本自动提取
- 明确 Cookie 必填字段：`_m_h5_tk`、`_m_h5_tk_enc`
- 增加其他登录方式：已保存 Cookie、扫码登录
- 修正登录态校验策略，避免将网络异常误判为 Cookie 失效
- 登录成功后在界面中展示大麦昵称与 UID

## 开发注意事项

- 项目为 `src` 布局，主入口为 `python -m damai`
- GUI 基于 `PySide6`
- 新增账号展示字段时，不要影响 `AccountConfig` 的运行时装载
- 登录相关逻辑优先修改 `src/damai/core/auth.py`

## 推荐检查项

- 语法检查：`python -m compileall src`
- 导入检查：设置 `PYTHONPATH=src` 后执行模块导入
- GUI 变更后手动验证登录页、扫码弹窗、账号列表

## 共享进度

该文件与 `CLAUDE.md`、`AGENTS.md` 一起提交到仓库，用于记录当前阶段的开发进度与协作上下文。
