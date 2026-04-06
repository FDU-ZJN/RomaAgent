# RomaAgent Python UI

这是一个直接耦合 `roma_agent` 的 Python Web UI。

- 不通过子进程调用 CLI
- 直接在进程内调用 `Settings` + `RomaPipeline`
- 表单参数可覆盖 `.env` 关键配置

## 启动

在仓库根目录执行：

```bash
pip install -e .
streamlit run python-ui/app.py
```

默认打开：

```text
http://localhost:8501
```

## 说明

- UI 初始值读取当前环境变量（通常来自 `.env` 加载）。
- 点击“开始生成”后会把表单值写入进程环境变量，再调用 pipeline。
- 产物仍落在 `output/<run_id>/`，页面会直接读取并展示。

## 打包为 EXE（Windows）

在仓库根目录执行：

```bash
powershell -ExecutionPolicy Bypass -File python-ui/build_exe.ps1
```

打包完成后可执行文件位于：

```text
dist/RomaAgentPythonUI.exe
```

运行后会在本机启动 Streamlit 服务（默认 `127.0.0.1:8501`）。

可通过参数指定端口：

```bash
dist\RomaAgentPythonUI.exe -p 3000
```

或：

```bash
dist\RomaAgentPythonUI.exe --port 3000
```

说明：

- 此 EXE 已包含 `python-ui` 与 `roma_agent` 代码。
- 运行时仍需可访问你配置的模型/API 网关与密钥。
- 如需固定配置，可在 EXE 同目录放置 `.env` 文件。

## 打包前提与构建环境

- 打包阶段使用固定 conda 环境：`roma-agent`。
- `build_exe.ps1` 已按 `cmd /c "call conda activate roma-agent & ..."` 方式执行，避免多 Python 环境导致的版本漂移。
- EXE 运行阶段不需要用户激活 conda。

## 调试与排障

- 当前 EXE 为控制台模式，双击时会弹出终端并打印日志/异常栈，便于定位问题。
- 若出现 `agent-framework is not installed`：请重新执行打包脚本，当前配置会显式打入 `agent_framework` 动态导入模块。
- 若出现 `server.port does not work when global.developmentMode is true`：使用最新构建产物（已在启动器中关闭 development mode）。
