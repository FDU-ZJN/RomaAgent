# RomaAgent Java UI

本子项目提供本地 Web 控制台，用于配置参数并触发 `roma-agent` 生成流程（支持 SSE 实时流式输出）。

## 前置条件

- 已安装 JDK 17+
- 已安装 Maven
- 根项目可在终端执行 `roma-agent --idea "..."`

## 启动

在 `java-ui` 目录执行：

```bash
mvn clean package -DskipTests
java -jar target/roma-agent-ui-0.1.0.jar
```

浏览器打开（默认）：

```text
http://localhost:8080
```

如果 `8080` 被占用，程序会自动切到下一个可用端口，并在启动日志中提示实际端口。

可通过环境变量指定期望端口：

```bash
set ROMA_UI_PORT=8081
```

## 功能

- 输入标题、核心想法、观点主张
- 配置 Provider / Runtime / Model / Search / 打回阈值
- 配置文章字数范围（最小字数/最大字数）
- 一键触发生成
- 页面展示：
  - 元老院资料包
  - 保民官审查报告
  - Hexo 最终稿
  - 知乎最终稿
  - 终端流式输出（SSE）

## 说明

- 若 API Key 为空，将使用根目录 `.env` 中已有配置。
- Java UI 内部通过子进程调用 `roma-agent`，并读取 `output/<run_id>/` 下产物。
- Java UI 会将输入内容写入临时 UTF-8 文件并通过 `--idea-file` 传给 CLI，可稳定处理大文本输入（如粘贴整份 README）。
- 字数设置会透传为：`ROMA_ARTICLE_MIN_WORDS` / `ROMA_ARTICLE_MAX_WORDS`。
- 在部分 Windows 非 ASCII 路径（例如中文目录）下，`mvn spring-boot:run` 可能出现主类加载失败；使用上面的 `java -jar` 启动方式更稳定。

