package com.roma.ui;

import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Consumer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class PipelineRunnerService {
    private static final Pattern RUN_ID_PATTERN = Pattern.compile("Run completed:\\s*(\\d{8}-\\d{6})");
    private static final int PROJECT_ROOT_SEARCH_DEPTH = 8;

    public RunResult runPipeline(RunRequest request) {
        return runPipeline(request, null);
    }

    public RunResult runPipeline(RunRequest request, Consumer<String> onChunk) {
        RunResult result = new RunResult();
        Path projectRoot = locateProjectRoot();

        if (projectRoot == null) {
            result.setSuccess(false);
            result.setError("无法定位 RomaAgent 项目根目录（未找到 pyproject.toml）。请在项目目录内启动应用。");
            return result;
        }

        String ideaInput = buildIdeaInput(request);
        Path ideaFile = null;
        ProcessBuilder pb;
        try {
            ideaFile = Files.createTempFile(projectRoot, "roma-idea-", ".txt");
            Files.writeString(ideaFile, ideaInput, StandardCharsets.UTF_8);
            pb = new ProcessBuilder("roma-agent", "--idea-file", ideaFile.toString());
        } catch (IOException ex) {
            result.setSuccess(false);
            result.setError("无法创建临时输入文件: " + ex.getMessage());
            return result;
        }
        pb.directory(projectRoot.toFile());
        pb.redirectErrorStream(true);

        Map<String, String> env = pb.environment();
        env.put("PYTHONUNBUFFERED", "1");
        env.put("PYTHONIOENCODING", "utf-8");
        env.put("PYTHONUTF8", "1");
        putIfNotBlank(env, "ROMA_PROVIDER", request.getProvider());
        putIfNotBlank(env, "ROMA_AGENT_RUNTIME", request.getRuntime());
        putIfNotBlank(env, "ROMA_MODEL", request.getModel());
        putIfNotBlank(env, "OPENAI_BASE_URL", request.getOpenAiBaseUrl());
        putIfNotBlank(env, "OPENAI_API_KEY", request.getOpenAiApiKey());
        putIfNotBlank(env, "OPENAI_TIMEOUT_SECONDS", request.getOpenAiTimeoutSeconds());
        putIfNotBlank(env, "OPENAI_MAX_RETRIES", request.getOpenAiMaxRetries());
        putIfNotBlank(env, "OPENAI_RETRY_BACKOFF_SECONDS", request.getOpenAiRetryBackoffSeconds());
        putIfNotBlank(env, "OPENAI_MAX_TOKENS", request.getOpenAiMaxTokens());
        putIfNotBlank(env, "OPENAI_THINKING_TYPE", request.getOpenAiThinkingType());
        putIfNotBlank(env, "ROMA_SEARCH_PROVIDER", request.getSearchProvider());
        putIfNotBlank(env, "TAVILY_API_KEY", request.getTavilyApiKey());
        putIfNotBlank(env, "ROMA_MAX_SOURCES", request.getMaxSources());
        putIfNotBlank(env, "ROMA_OUTPUT_DIR", request.getOutputDir());
        putIfNotBlank(env, "ROMA_ENABLE_IMAGE_CONSUL", request.getEnableImageConsul());
        putIfNotBlank(env, "ROMA_IMAGE_MODEL", request.getImageModel());
        putIfNotBlank(env, "ROMA_IMAGE_COUNT", request.getImageCount());
        putIfNotBlank(env, "ROMA_IMAGE_SIZE", request.getImageSize());
        putIfNotBlank(env, "ROMA_IMAGE_POLL_INTERVAL_SECONDS", request.getImagePollIntervalSeconds());
        putIfNotBlank(env, "ROMA_IMAGE_POLL_TIMEOUT_SECONDS", request.getImagePollTimeoutSeconds());
        putIfNotBlank(env, "ROMA_SENATE_REJECT_SCORE_THRESHOLD", request.getSenateRejectScoreThreshold());
        putIfNotBlank(env, "ROMA_SENATE_MAX_REWORK_ROUNDS", request.getSenateMaxReworkRounds());
        putIfNotBlank(env, "ROMA_ARTICLE_MIN_WORDS", request.getArticleMinWords());
        putIfNotBlank(env, "ROMA_ARTICLE_MAX_WORDS", request.getArticleMaxWords());

        try {
            Process process = pb.start();
            String output = readAll(process, onChunk);

            boolean finished = process.waitFor(Duration.ofMinutes(6).toMillis(), java.util.concurrent.TimeUnit.MILLISECONDS);
            if (!finished) {
                process.destroyForcibly();
                result.setSuccess(false);
                result.setError("运行超时（>6分钟），请检查模型配额或降低参数复杂度。");
                result.setOutput(output);
                return result;
            }

            int exitCode = process.exitValue();
            result.setOutput(output);

            String runId = extractRunId(output);
            result.setRunId(runId);

            if (runId != null) {
                Path runDir = projectRoot.resolve("output").resolve(runId);
                result.setHexoMarkdown(readIfExists(runDir.resolve("deployments").resolve("hexo.md")));
                result.setZhihuMarkdown(readIfExists(runDir.resolve("deployments").resolve("zhihu.md")));
                result.setSenateBrief(readIfExists(runDir.resolve("senate_brief.md")));
                result.setTribuneReport(readIfExists(runDir.resolve("tribune_report.md")));
            }

            if (exitCode == 0) {
                result.setSuccess(true);
            } else {
                result.setSuccess(false);
                result.setError("生成失败，退出码: " + exitCode);
            }
        } catch (Exception ex) {
            result.setSuccess(false);
            result.setError("执行异常: " + ex.getMessage());
        } finally {
            if (ideaFile != null) {
                try {
                    Files.deleteIfExists(ideaFile);
                } catch (IOException ignored) {
                }
            }
        }

        return result;
    }

    private static Path locateProjectRoot() {
        Path current = Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
        for (int i = 0; i <= PROJECT_ROOT_SEARCH_DEPTH && current != null; i++) {
            if (Files.exists(current.resolve("pyproject.toml"))) {
                return current;
            }
            current = current.getParent();
        }
        return null;
    }

    private static String buildIdeaInput(RunRequest request) {
        String title = safe(request.getTitle());
        String idea = safe(request.getIdea());
        String viewpoint = safe(request.getViewpoint());

        return "标题: " + title + "\n"
                + "核心想法: " + idea + "\n"
                + "观点主张: " + viewpoint;
    }

    private static String safe(String v) {
        return v == null ? "" : v.trim();
    }

    private static void putIfNotBlank(Map<String, String> env, String key, String value) {
        if (value != null && !value.isBlank()) {
            env.put(key, value.trim());
        }
    }

    private static String readAll(Process process) throws IOException {
        return readAll(process, null);
    }

    private static String readAll(Process process, Consumer<String> onChunk) throws IOException {
        StringBuilder sb = new StringBuilder();
        try (InputStreamReader reader = new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8)) {
            int ch;
            while ((ch = reader.read()) != -1) {
                char c = (char) ch;
                sb.append(c);
                // Mirror child process output to local console in real time.
                System.out.print(c);
                System.out.flush();
                if (onChunk != null) {
                    onChunk.accept(String.valueOf(c));
                }
            }
        }
        return sb.toString();
    }

    private static String extractRunId(String output) {
        if (output == null) {
            return null;
        }
        Matcher matcher = RUN_ID_PATTERN.matcher(output);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return null;
    }

    private static String readIfExists(Path path) {
        try {
            if (Files.exists(path)) {
                return Files.readString(path, StandardCharsets.UTF_8);
            }
        } catch (IOException ignored) {
        }
        return "";
    }
}

