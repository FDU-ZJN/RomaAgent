# AGENT Development Log

This file tracks implementation decisions and iteration records for RomaAgent.

## 2026-04-03 - Initialization

### User Goal
Build an automatic multi-platform blogging system (Hexo, Zhihu, more) where one idea triggers:
- research
- drafting
- quality improvement
- platform adaptation

### Technical Direction
- Base architecture on Microsoft Agent Framework concepts
- Keep the system runnable with a mock provider first
- Design provider abstraction so Agent Framework providers can be plugged in

### Initial Deliverables
- Project skeleton with modular pipeline
- Prompt templates for research, writing, and platform transforms
- CLI entrypoint for end-to-end execution
- Structured output artifacts with source traceability

### Completed in This Iteration
- Created package layout under `src/roma_agent`
- Implemented settings loader via `.env`
- Implemented provider adapter interface with `mock` and `agent_framework` stubs
- Implemented stage modules: `research`, `writer`, `publisher`
- Implemented orchestrator pipeline with output persistence
- Implemented CLI command `roma-agent --idea "..."`
- Added prompt templates and sample idea input
- Added packaging config (`pyproject.toml`) and `.gitignore`

### Current Behavior
- End-to-end run works in mock mode and produces:
	- `draft.md`
	- `hexo.md`
	- `zhihu.md`
	- `pipeline_result.json`
- Agent Framework adapter is scaffolded and isolated in `providers.py`
- Real provider invocation and live web-search integration are not wired yet

### Next Steps
- Add real search provider and citation extraction
- Integrate Agent Framework native agents/workflows
- Add quality rubric scoring and auto-revision loop
- Add integration tests for end-to-end flow

## 2026-04-04 - Roman Governance Refactor

### New Governance Model
Adopted a Roman political structure with explicit role ownership:
- Consul (执政官)
- Senate Agent 1 (元老院检索/方案)
- Senate Agent 2 (元老院评分/简单修改)
- Tribune (保民官审查)
- Governor (行省总督部署)

### Implemented Orchestration
Execution order is now hard-coded as:
1. Senate Agent 1 performs research and outputs design blueprint
2. Consul writes complete blog based on research + blueprint
3. Senate Agent 2 scores quality and applies light edits
4. Tribune performs security/privacy review and light edits
5. Governor deploys reviewed output to platform files

### Code Changes
- Added `src/roma_agent/roman_roles.py` with all five role classes
- Updated `src/roma_agent/pipeline.py` to role-based orchestration
- Extended `src/roma_agent/models.py` with quality and deployment fields
- Updated CLI to print score, issues count, and deployment paths
- Updated README architecture and output expectations

### Current Limits
- Senate Agent 1 supports Tavily/Bing live web search and falls back to seeded notes if keys are missing
- Senate Agent 2 uses LLM rubric scoring with JSON parsing and falls back to heuristic when needed
- Tribune review uses regex-based redaction for common secrets/PII patterns

## 2026-04-04 - Live Search + LLM Rubric Upgrade

### Senate Agent 1 Upgrade
- Added live web search clients in `src/roma_agent/search.py`
	- Tavily API
	- Bing Search v7 API
- Added search provider switch via `.env` (`ROMA_SEARCH_PROVIDER`)
- Refactored `ResearchAgent` to prioritize real search results and deduplicate URLs

### Senate Agent 2 Upgrade
- Replaced pure heuristic scoring with LLM rubric scoring
- Rubric dimensions:
	- structure(25)
	- factual grounding(25)
	- clarity(20)
	- practical value(20)
	- style consistency(10)
- Implemented strict JSON parse with regex extraction fallback
- Preserved heuristic fallback path to keep pipeline robust in mock or malformed outputs

### Operational Notes
- Added `requests` dependency for live search HTTP calls
- Added env variables for Tavily/Bing credentials in `.env.example`

## 2026-04-04 - Agent Framework Provider Implementation

### Problem Addressed
`AgentFrameworkProvider` was previously a scaffold and raised `NotImplementedError`,
which prevented real LLM scoring/writing execution in `ROMA_PROVIDER=agent_framework` mode.

### Implemented
- Completed `src/roma_agent/providers.py` with real generation paths:
	- Foundry runtime via Agent Framework (`ROMA_AGENT_RUNTIME=foundry`)
	- OpenAI runtime via Agent Framework (`ROMA_AGENT_RUNTIME=openai`)
	- OpenAI REST fallback if AF OpenAI client surface changes across versions
- Added async-safe execution wrapper for agent `.run(...)` calls
- Added richer runtime error aggregation and setup hints

### Configuration Additions
- Added `ROMA_AGENT_RUNTIME` to `.env.example`
- Added optional Azure auth env vars in `.env.example`
- Added `azure-identity` dependency for Foundry credential support

### User Operations Required
- Install deps: `pip install -e .`
- Choose runtime and set credentials in `.env`
- If Foundry runtime: execute `az login`

## 2026-04-04 - Content Generation Optimization

### User Feedback
- Existing output sometimes became generic and detached from topic.
- User expected Senate Agent 1 to deliver actionable reference package (URLs, PDF hints, core data, outline).
- User could not clearly see Tribune (保民官) review results.

### Implemented
- Senate Agent 1 now produces a structured brief in `senate_design`:
	- reference list with URL/PDF type hints and confidence
	- extracted core data snippets
	- writing outline (LLM + fallback)
	- writing requirements for Consul
- Consul now passes Senate brief directly into Writer prompt instead of injecting a visible process block.
- Writer fallback was upgraded to be topic-aware and reference-aware, reducing generic boilerplate output.
- Tribune now appends explicit section `## 保民官审查结果` with issue bullets in draft content.
- Pipeline now saves additional artifacts:
	- `senate_brief.md`
	- `tribune_report.md`
- CLI now prints Tribune issue details, not just count.

### Notes
- One validation run was interrupted/cancelled; user should execute a fresh run to inspect new artifacts.

## 2026-04-04 - Java UI Startup Debug (Windows)

### Symptom
- `mvn spring-boot:run` failed with:
	- `ClassNotFoundException: com.roma.ui.RomaUiApplication`

### Verification Performed
- `mvn clean compile` succeeded under `java-ui`.
- Confirmed class file exists in `target/classes/com/cosmos/ui/RomaUiApplication.class`.
- `mvn clean package -DskipTests` succeeded and produced fat jar.
- `java -jar target/roma-agent-ui-0.1.0.jar` started successfully on `localhost:8080`.

### Conclusion
- Source code and packaging are correct.
- Failure is in `spring-boot:run` launch path under current Windows environment/path setup.

### Action Taken
- Updated `java-ui/README.md` startup command to recommended stable path:
	- `mvn clean package -DskipTests`
	- `java -jar target/roma-agent-ui-0.1.0.jar`

## 2026-04-04 - Java UI Root Detection Fix

### User-Reported Error
- UI run failed with:
	- `无法定位 RomaAgent 项目根目录，请从 java-ui 目录启动应用`

### Root Cause
- `PipelineRunnerService` assumed `user.dir` must be `java-ui` and directly used its parent as project root.
- When app started from repository root, this logic incorrectly resolved to one level above repository.

### Fix
- Replaced fixed parent logic with upward directory search from current working directory.
- Added `locateProjectRoot()` to scan up to 8 levels for `pyproject.toml`.
- Updated error message to a generic root-locate failure hint.

### Validation
- `mvn -f java-ui/pom.xml clean package -DskipTests` succeeded after the change.

## 2026-04-04 - End-to-End Streaming Output

### Goal
- Enable streaming output across the whole project so generation progress and LLM text appear in real time.

### Implemented
- Extended provider interface in `src/roma_agent/providers.py`:
	- `generate(..., on_chunk=None)` now supports chunk callbacks.
	- OpenAI-compatible REST path supports streaming (`stream=true`) and SSE chunk parsing.
	- Agent Framework / mock paths emit chunks through callback as compatible fallback.
- Wired stream callbacks through role agents:
	- `ResearchAgent`, `WriterAgent`, `SenateResearchAgent`, `SenateQualityAgent` now pass chunk callbacks to provider calls.
	- Added stage logs such as `[Stream] 执政官正在撰写正文...`.
- Added pipeline stage-level realtime logs in `src/roma_agent/pipeline.py`.
- Ensured Java UI subprocess runs unbuffered by setting `PYTHONUNBUFFERED=1` in `java-ui/src/main/java/com/cosmos/ui/PipelineRunnerService.java`.

### Result
- Local console now receives incremental generation logs and chunked model output during runtime, instead of waiting for full completion.

## 2026-04-04 - Image Consul (图片执政官)

### Goal
- Add an image generation role that collaborates with existing text generation and injects visuals into blog outputs.

### Implemented
- Added image metadata model in `src/roma_agent/models.py`:
	- `ImageAsset`
	- `DraftPackage.images`
- Added image provider support in `src/roma_agent/providers.py`:
	- `ImageProvider` interface
	- `OpenAICompatibleImageProvider` using `/images/generations`
	- `build_image_provider(...)`
- Added `ImageConsulAgent` in `src/roma_agent/roman_roles.py`:
	- builds image prompts from title and section headings
	- generates configured number of images
	- stores image metadata on draft
- Wired image consul into pipeline in `src/roma_agent/pipeline.py`:
	- runs after Tribune review and before Governor deployment
	- persists `images.json` artifact
- Updated publisher in `src/roma_agent/publisher.py`:
	- injects `## 配图` section into Hexo/Zhihu markdown when images are available
- Added settings in `src/roma_agent/config.py` and `.env.example`:
	- `ROMA_ENABLE_IMAGE_CONSUL`
	- `ROMA_IMAGE_MODEL`
	- `ROMA_IMAGE_COUNT`
	- `ROMA_IMAGE_SIZE`
- Updated `README.md` with role description, outputs, and model recommendations.

### Notes
- If image model/key is missing or generation fails, article generation still continues; images are marked in metadata with skipped/failed status.

## 2026-04-04 - ModelScope Compatibility & Quality Fixes

### Stream Decoding Fix
- Problem:
	- Streaming output occasionally showed mojibake (e.g. UTF-8 text decoded as Latin-1 style garbage).
- Fix:
	- Updated streaming parsing in `src/roma_agent/providers.py` to read SSE lines as bytes and decode explicitly with UTF-8.

### ModelScope Image API Fix
- Problem:
	- `POST /v1/images/generations` returned `400` for image generation when called in synchronous OpenAI-style mode.
- Fix:
	- Added ModelScope async-task image flow in `src/roma_agent/providers.py`:
		1. submit generation task with `X-ModelScope-Async-Mode: true`
		2. poll `/v1/tasks/{task_id}` with `X-ModelScope-Task-Type: image_generation`
		3. download output image URL
	- Added image polling configs in `.env.example`:
		- `ROMA_IMAGE_POLL_INTERVAL_SECONDS`
		- `ROMA_IMAGE_POLL_TIMEOUT_SECONDS`

### Rubric Score Parsing Fix
- Problem:
	- Senate quality stage crashed when model returned `score` as dict breakdown instead of scalar.
- Fix:
	- Added score normalization in `src/roma_agent/roman_roles.py`:
		- supports numeric score
		- supports score dict by summing dimension values

## 2026-04-04 - Image Placement & Content Formatting Refinements

### Image Placement Strategy Upgrade
- Problem:
	- Generated images tended to cluster at top of article and looked title-cover oriented.
- Fix:
	- Image prompts now focus on architecture explanation and section semantics.
	- Senate Agent 1 now outputs `### 图片位置建议（供图片执政官）` in `senate_brief.md`.
	- Publisher inserts images by matched section heading anchors.
	- Enforced one-image-per-section; overflow images move to fallback placement before references.

### Removed Unwanted Auto Conclusion
- Problem:
	- A fixed `## 结语` template was auto-appended by quality stage.
- Fix:
	- Removed forced conclusion injection in `src/roma_agent/roman_roles.py`.

### Fixed Hexo Code Fence Pollution
- Problem:
	- Some generated drafts were wrapped as full-document fenced code blocks, causing Hexo output to render as code.
- Fix:
	- Added whole-document outer fence stripping in `src/roma_agent/publisher.py` before publish cleanup.

## 2026-04-04 - Article Length Config + Java UI Enhancements

### Word Count Config in `.env`
- Added:
	- `ROMA_ARTICLE_MIN_WORDS`
	- `ROMA_ARTICLE_MAX_WORDS`
- Wired into:
	- `src/roma_agent/config.py`
	- `src/roma_agent/pipeline.py`
	- `src/roma_agent/writer.py`

### Java UI Word Count Controls
- Added UI fields and backend passthrough for min/max words:
	- `java-ui/src/main/resources/templates/index.html`
	- `java-ui/src/main/java/com/cosmos/ui/RunRequest.java`
	- `java-ui/src/main/java/com/cosmos/ui/PipelineRunnerService.java`
	- `java-ui/src/main/java/com/cosmos/ui/UiController.java`

### Java UI Port Adaptation
- Added startup port check with fallback to next available port when desired port is occupied.
- Optional desired port via `ROMA_UI_PORT`.
- Implemented in `java-ui/src/main/java/com/cosmos/ui/RomaUiApplication.java`.

