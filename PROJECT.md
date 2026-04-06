# RomaAgent 技术总览与实现文档（对内版）

## 1. 项目定位

RomaAgent 是一个“从单点想法到多平台发布稿”的自动化内容系统。系统核心目标是将“选题输入”转化为“可发布的 Hexo/知乎文章”，并在生成过程中引入结构化调研、质量审查、安全审查、图片生成与部署输出。

系统关键价值是：
- 把内容生产流程工程化，而不是只做一次性文本生成。
- 通过多角色治理机制提升可控性、可解释性和稳定性。
- 通过配置驱动支持不同模型、检索源与发布策略。
- 通过本地 Web 控制台提供实时流式可视化运行体验。

---

## 2. 核心能力清单

- 单命令触发端到端内容流水线。
- 罗马治理架构多 Agent 协作。
- 实时联网检索（Tavily / Bing）与资料整编。
- LLM 量表评分与可配置重写回路。
- 保民官安全审查（敏感信息脱敏）。
- 图片执政官生成配图并插入文档。
- 多平台产物输出（Hexo / Zhihu）。
- 运行过程流式输出（CLI + Java UI SSE）。
- Python UI 可直接耦合运行并支持打包 EXE。
- EXE 支持命令行端口参数（`-p`）。
- 运行痕迹全量落盘（JSON + markdown + images metadata）。

---

## 3. 总体架构

采用“**四大治理块 + 块内细分单元**”的编排模式，分别为：

- 元老院（Senate）：
负责前置研究与质量治理。
  - 元老院研究单元（原元老院1号）：检索、核心数据提炼、写作大纲、写作要求、配图段落建议。
  - 元老院质控单元（原元老院2号）：量表评分、问题归类、重写触发判定与回路控制。
- 执政官（Consul）：
负责内容生产与视觉协同。
  - 正文生成单元：基于元老院资料包生成完整正文草稿。
  - 配图生成单元（原图片执政官）：基于章节语义生成架构解释型图片。
- 保民官（Tribune）：
负责隐私与安全审查，执行敏感信息识别与脱敏。
- 行省总督（Governor）：
负责平台封装与部署落盘，输出可发布稿件。

执行顺序（四阶段）：
1. 元老院阶段（研究单元 -> 质控单元，可触发重写）
2. 执政官阶段（正文生成 -> 配图生成）
3. 保民官阶段（安全审查与脱敏）
4. 行省总督阶段（多平台发布产物输出）

---

## 4. 生成流程（端到端）

输入：
- 一条 idea 文本（可包含主题、受众、重点观点、风格要求）。

流程：
1. 元老院研究单元构建检索查询词并抓取资料。
2. 元老院研究单元生成结构化“元老院资料包”。
3. 执政官正文生成单元产出标题与正文内容。
4. 元老院质控单元执行评分并按规则决定是否重写。
5. 执政官配图生成单元执行图片生成并绑定章节目标。
6. 保民官执行安全审查并输出审查意见。
7. 行省总督输出平台稿件并写入运行目录。

输出目录（每次 run_id 独立）：
- pipeline_result.json
- senate_brief.md
- consul_draft.md
- draft.md
- tribune_report.md
- images.json
- images/
- deployments/hexo.md
- deployments/zhihu.md

---

## 5. 模型与 Provider 设计

文本生成支持：
- mock provider
- agent_framework provider（runtime: foundry/openai/auto）
- OpenAI 兼容 REST 兜底

关键实现点：
- provider 接口统一为 generate(system_prompt, user_prompt, on_chunk)。
- 支持流式 chunk 回调。
- OpenAI 兼容 REST 支持 stream=true。
- 为兼容网关差异保留多级 fallback。

图片生成支持：
- ImageProvider 抽象接口。
- OpenAI 兼容图片接口。
- 针对 ModelScope 增加异步任务模式：
  - 提交任务
  - 轮询任务状态
  - 下载图片 URL
- 失败不阻断主流程，仅在 images.json 标记状态。

---

## 6. 检索与知识整编

检索层：
- Tavily / Bing 双适配。
- URL 去重。
- 最大来源数量可配。

整编层：
- 抽取关键观点。
- 提取核心数据句段。
- 生成写作大纲。
- 生成“图片规划（供执政官1号细化）”。

---

## 7. 质量审查机制（元老院2号）

评分量表维度：
- 结构
- 事实依据
- 清晰度
- 实用价值
- 风格一致性

兼容性增强：
- 兼容 score 为单值数字。
- 兼容 score 为分项字典并自动求和。
- JSON 解析失败时回退启发式评分。

重写触发逻辑：
- 低于阈值触发。
- 或可执行问题数量达到阈值触发。
- 最大重写轮次可配置。

---

## 8. 安全审查机制（保民官）

主要规则：
- 识别并脱敏疑似 API Key。
- 识别并脱敏邮箱。
- 识别并脱敏手机号。

输出：
- 审查后草稿。
- 结构化 issue 列表。
- tribune_report.md。

---

## 9. 图片执政官策略（当前版本）

目标：
- 配图聚焦“核心架构解释”，避免仅标题海报化。

当前规则：
- 采用“规划 -> 细化 -> 生成”的链路：
  - 元老院研究单元产出图片规划。
  - 执政官正文生成单元细化为结构化图片提示。
  - 配图生成单元按提示生成图片并回传元数据。
- 过滤非核心章节（如参考资料、结语、质控意见等）。
- 提示词强调模块关系、数据流向、分层与交互路径。
- 不要求可读文字，避免水印、品牌标志。

插入策略：
- 按章节锚点插入，不再统一堆到文首。
- 每个章节最多插入 1 张图。
- 同章节多余图片降级到文末参考资料前兜底。
- 不再增加“## 配图”标题，避免覆盖正文结构。

---

## 10. 流式输出机制

CLI：
- Pipeline 阶段日志实时输出。
- LLM chunk 流式输出。
- stdout/stderr 强制 UTF-8 与行缓冲。

Java UI：
- SSE 双阶段接口：
  - /run/prepare
  - /run/stream
- 前端 EventSource 实时追加输出。
- 运行结束后回填结果面板（状态、run_id、草稿、报告等）。

编码稳定性措施：
- Python 子进程设置 PYTHONUNBUFFERED。
- 强制 PYTHONIOENCODING 与 UTF-8 相关变量。
- 流式解析按字节读取并显式 UTF-8 解码，避免 mojibake。

Python UI（Streamlit）：
- 直接调用 `RomaPipeline`，非子进程封装。
- 支持线程 + 队列的实时日志刷新。
- 支持历史运行目录回放。
- EXE 入口支持 `-p` 参数指定 localhost 端口。
- 调试构建可启用控制台输出，双击可见 traceback。

---

## 11. 配置项说明（关键）

基础：
- ROMA_PROVIDER
- ROMA_AGENT_RUNTIME
- ROMA_MODEL
- OPENAI_API_KEY
- OPENAI_BASE_URL

检索：
- ROMA_SEARCH_PROVIDER
- ROMA_MAX_SOURCES
- TAVILY_API_KEY
- BING_SEARCH_V7_ENDPOINT
- BING_SEARCH_V7_KEY

质控：
- ROMA_SENATE_REJECT_SCORE_THRESHOLD
- ROMA_SENATE_MAX_REWORK_ROUNDS

图片：
- ROMA_ENABLE_IMAGE_CONSUL
- ROMA_IMAGE_MODEL
- ROMA_IMAGE_COUNT
- ROMA_IMAGE_SIZE
- ROMA_IMAGE_POLL_INTERVAL_SECONDS
- ROMA_IMAGE_POLL_TIMEOUT_SECONDS

稳定性：
- OPENAI_TIMEOUT_SECONDS
- OPENAI_MAX_RETRIES
- OPENAI_RETRY_BACKOFF_SECONDS

---

## 12. 已解决的关键问题

- AgentFrameworkProvider 从占位实现升级为可运行实现。
- 联网检索与 LLM 量表评分接入完成。
- 流式输出从 CLI 扩展到 Java UI。
- Windows + 非 ASCII 路径下启动问题已规避。
- 根目录定位逻辑已修复，不再依赖固定启动目录。
- 模型返回 score 为 dict 的兼容崩溃已修复。
- ModelScope 图片 400 问题已通过异步任务模式修复。
- 文本流式乱码问题已通过显式 UTF-8 解码修复。
- 图片插入位置从“文首堆叠”升级为“章节锚点插入”。
- Streamlit 启动签名差异导致的 EXE 启动异常已修复。
- `global.developmentMode` 与自定义 `server.port` 冲突已修复。
- `streamlit.runtime.scriptrunner.magic_funcs` 漏打包问题已修复。
- `agent-framework is not installed` 的 EXE 依赖漏打包问题已修复。
- Windows 非 ASCII 路径下 editable `.pth` 导致的 Python 启动崩溃已规避。

---

## 13. 已知风险与建议

- 429 限流仍可能出现。
建议通过降低 sources/image_count、增大重试退避、错峰请求来缓解。
- 不同兼容网关的响应格式可能漂移。
建议保留接口探测与格式容错。
- 生成式系统存在事实幻觉风险。
建议持续强化“来源-结论”绑定和后验核查。
- EXE 和中间产物体积较大，误提交到 Git 会触发 GitHub 100MB 限制。
建议忽略 `build/`、`dist/`，发布二进制请使用 Release 附件或对象存储。

---

## 14. 后续规划建议

- 将“问题数量阈值”也做成可配置项。
- 增加 score_breakdown 全链路展示（CLI/UI/JSON）。
- 加入“停止生成”能力（中断后端子进程）。
- 加入断线重连与续跑机制。
- 增加平台适配器（公众号、掘金、CSDN）。
- 增加自动测试集与回归基线（质量、格式、稳定性）。

---

## 15. 给 RomaAgent 的写作指令模板（可直接二次投喂）

请基于以上技术文档，撰写一篇面向技术读者的项目介绍文章，要求：
- 准确描述系统架构与执行流程。
- 重点解释罗马治理模型、流式输出、图片执政官与章节锚点插图机制。
- 展示工程化能力、配置灵活性与可靠性设计。
- 保持“事实可追溯、术语清晰、结构专业”，避免营销话术。
- 输出 Hexo 友好的 Markdown 正文与参考资料章节。
