# 仓库指南

## 项目结构与模块组织
本仓库使用 Python 的 `src` 目录布局，主要代码位于 `src/damai/`。其中，`core/` 负责登录、监控、下单与接口访问；`gui/` 包含基于 PySide6 的桌面界面与组件；`utils/` 提供配置、加密、时间同步等通用工具；`notify/` 放置通知渠道实现；`anti_detect/` 用于请求头、指纹和代理相关逻辑。运行配置模板位于 `config/`，如 `default.toml` 和 `accounts.toml`。

## 构建、测试与开发命令
- `python -m venv .venv && .venv\Scripts\activate`：在 Windows 上创建并激活虚拟环境。
- `pip install -r requirements.txt`：安装运行依赖。
- `pip install -e .`：以可编辑模式安装项目，便于本地开发。
- `python -m damai`：通过 `src/damai/__main__.py` 启动图形界面。
- `python -m compileall src`：在缺少正式测试时做快速语法检查。

## 代码风格与命名规范
项目要求 Python `>=3.11`。遵循现有代码风格：使用 4 个空格缩进；函数、模块采用 `snake_case`；类名采用 `PascalCase`；公共接口保持简洁 docstring，并在合适场景补充类型标注。新增代码应优先放入现有相近模块，避免创建过于泛化的工具文件。`pyproject.toml` 中暂未配置格式化或 lint 工具，因此请保持与周边代码一致，并统一导入分组风格。

## 测试指南
当前仓库未提交 `tests/` 目录。若修改核心逻辑，仅在同时引入测试框架时补充针对性测试；否则优先使用小范围验证，例如运行 `python -m compileall src`，并在本地手动检查相关 GUI 或配置流程。后续若新增测试，建议使用按功能命名方式，例如 `tests/test_order.py`。

## 提交与合并请求规范
当前工作区不可见 Git 历史，因此无法确认仓库既有提交规范。建议使用简短、祈使句风格的提交信息，例如 `Add account config validation` 或 `Fix proxy fallback`。提交 Pull Request 时，应说明用户可见改动、列出受影响模块、标明 `config/` 下的配置调整；若涉及界面改动，请附截图。

## 安全与配置建议
不要提交真实的 Cookie、购买人信息、Webhook 地址或邮箱凭据。`config/` 下文件应视为模板，个人敏感配置请保存在未跟踪文件或用户本地目录中，例如 `%USERPROFILE%\.damai-ticket`。
