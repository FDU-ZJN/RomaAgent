# RomaAgent

RomaAgent 是一个“输入一个想法，自动产出多平台技术文章”的内容工程化系统。

核心目标：
- 让写作流程可编排、可审查、可追溯。
- 在生成质量、事实依据、安全合规与发布形态之间取得平衡。
- 用配置驱动适配不同模型网关（OpenAI 兼容、ModelScope 等）与不同发布渠道。

## 核心特性

- 罗马治理架构多角色协作（元老院/执政官/保民官/总督）。
- 联网检索（Tavily / Bing）与结构化资料包。
- LLM 量表评分 + 可配置重写回路。
- 保民官隐私脱敏审查。
- 图片执政官自动生成“架构解释型”配图。
- 配图按章节锚点插入（不是堆在文首）。
- CLI 与 Java UI 均支持流式输出。
- 完整运行工件落盘（JSON、草稿、部署稿、图片元数据）。

## 角色与流程

角色：
- Consul（执政官）：撰写正文。
- Senate Agent 1（元老院1号）：检索、提炼数据、给出大纲与配图位置建议。
- Senate Agent 2（元老院2号）：量表评分与重写建议。
- Tribune（保民官）：安全审查与脱敏。
- Image Consul（图片执政官）：生成章节配图。
- Governor（行省总督）：输出 Hexo / Zhihu 发布稿。

执行顺序：
1. 元老院1号（检索 + 资料包）
2. 执政官（初稿）
3. 元老院2号（评审，必要时重写）
4. 保民官（安全审查）
5. 图片执政官（配图）
6. 行省总督（平台部署）

## 快速开始

1. 安装依赖

```bash
pip install -e .
```

2. 配置环境

```bash
copy .env.example .env
```

3. 运行一次

```bash
roma-agent --idea "请写一篇关于 AI 时代 CPU 路线分化的技术文章"
```

大文本输入（例如整份 README / 技术文档）建议使用文件参数：

```bash
roma-agent --idea-file .\\README.md
```

4. 查看产物目录 `output/<run_id>/`

- `pipeline_result.json`
- `senate_brief.md`
- `consul_draft.md`
- `draft.md`
- `tribune_report.md`
- `images.json`
- `images/`
- `deployments/hexo.md`
- `deployments/zhihu.md`

## 关键配置

### 模型与运行时

- `ROMA_PROVIDER`：`mock` / `agent_framework`
- `ROMA_AGENT_RUNTIME`：`foundry` / `openai` / `auto`
- `ROMA_MODEL`：文本模型名
- `OPENAI_BASE_URL`：OpenAI 兼容网关地址
- `OPENAI_API_KEY`：访问密钥

### 检索

- `ROMA_SEARCH_PROVIDER`：`tavily` / `bing`
- `ROMA_MAX_SOURCES`：检索来源上限
- `TAVILY_API_KEY` / `BING_SEARCH_V7_*`

### 质量控制

- `ROMA_SENATE_REJECT_SCORE_THRESHOLD`
- `ROMA_SENATE_MAX_REWORK_ROUNDS`

### 图片执政官

- `ROMA_ENABLE_IMAGE_CONSUL=true|false`
- `ROMA_IMAGE_MODEL`
- `ROMA_IMAGE_COUNT`
- `ROMA_IMAGE_SIZE`
- `ROMA_IMAGE_POLL_INTERVAL_SECONDS`
- `ROMA_IMAGE_POLL_TIMEOUT_SECONDS`

说明：ModelScope 图片接口走异步任务模式（提交任务 + 轮询），并已在 provider 中兼容。

### 字数设置（已支持 .env 配置）

- `ROMA_ARTICLE_MIN_WORDS`
- `ROMA_ARTICLE_MAX_WORDS`

## 流式输出说明

- CLI：阶段日志 + 模型 chunk 实时输出。
- Java UI：SSE 实时推送，浏览器终端输出区逐字滚动。
- 编码兼容：针对 UTF-8/网关字符集差异做了解码兜底，降低乱码概率。

## 已处理的常见问题

- Windows 非 ASCII 路径下 `spring-boot:run` 启动异常：改为 `java -jar` 方式。
- Java UI 根目录定位失败：改为向上搜索 `pyproject.toml`。
- 评分返回 `score` 为对象导致崩溃：已兼容分项字典求和。
- 图片接口 400：已适配 ModelScope 异步任务协议。
- Hexo 整文被包进代码块：发布前剥离外层 fenced code block。

## Java UI

Java UI 详细说明见 [java-ui/README.md](java-ui/README.md)。

## Python UI

Python UI 详细说明见 [python-ui/README.md](python-ui/README.md)。

## Python UI EXE 使用与打包说明

### 运行 EXE

- 产物路径：`dist/RomaAgentPythonUI.exe`
- 支持端口参数：`-p` / `--port`

示例：

```bash
dist\RomaAgentPythonUI.exe -p 3000
```

成功启动后可访问：

```text
http://127.0.0.1:3000
```

### 打包命令（Windows）

```bash
powershell -ExecutionPolicy Bypass -File python-ui/build_exe.ps1
```

说明：

- 打包脚本使用 `cmd + conda activate roma-agent` 固定构建环境，避免多 Python 环境漂移。
- EXE 运行时不要求用户激活 conda；但打包阶段必须使用正确环境，才能冻结正确依赖版本。

### 常见问题与处理

- `agent-framework is not installed`：已在打包链路中修复（安装项目依赖 + 显式收集 `agent_framework` 动态导入模块）。
- `server.port does not work when global.developmentMode is true`：已在 `launcher.py` 关闭 development mode，并允许 `-p` 覆盖端口。
- 双击无反应难排查：当前 EXE 已开启控制台输出（debug 友好），可直接看到 traceback。

## 项目结构

```text
src/roma_agent/
  cli.py
  config.py
  models.py
  pipeline.py
  providers.py
  research.py
  writer.py
  roman_roles.py
  publisher.py
java-ui/
prompts/
examples/
AGENT.md
```

